from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import media
from .jobs import JobManager, now
from .models import Clip, Cue, Model, Project, new_id
from .store import ConflictError, Store
from .transcribe import available
from .transcripts import parse_transcript, suggest_clips

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mts", ".m2ts", ".ts"}
STATIC = Path(__file__).with_name("static")


class ImportRequest(Model):
    path: str = Field(min_length=1)
    name: str | None = Field(default=None, max_length=160)


class ProjectUpdate(Model):
    revision: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    cues: list[Cue] | None = None
    clips: list[Clip] | None = None


class TranscriptRequest(Model):
    filename: str = "transcript.srt"
    content: str = Field(max_length=20 * 1024 * 1024)


class SuggestRequest(Model):
    min_duration: float = Field(default=20, ge=1, le=180)
    max_duration: float = Field(default=60, ge=1, le=180)
    count: int = Field(default=6, ge=1, le=30)
    keywords: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def lengths(self):
        if self.min_duration > self.max_duration:
            raise ValueError("Minimum duration must not exceed maximum duration.")
        return self


class JobRequest(Model):
    kind: Literal["analyze", "preview", "export", "transcribe"]
    clip_id: str | None = None
    model: Literal["tiny", "base", "small"] = "base"


class DataLock:
    """Prevent a second server from interrupting jobs owned by a live first server."""

    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def acquire(self):
        self.file = self.path.open("a+b")
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            self.file = None
            raise RuntimeError("Another ClipFarm server is using this data directory.") from exc

    def release(self):
        if self.file is not None:
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()
            self.file = None


def create_app(data_dir: Path | None = None) -> FastAPI:
    store = Store(data_dir or Path(os.environ.get("CLIPFARM_DATA_DIR", ".clipfarm")))
    data_lock = DataLock(store.root / "server.lock")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        data_lock.acquire()
        try:
            app.state.jobs = JobManager(store)
            yield
        finally:
            if hasattr(app.state, "jobs"):
                app.state.jobs.close()
            data_lock.release()

    app = FastAPI(title="ClipFarm", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme != request.url.scheme or parsed.netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin access is disabled for this local studio."},
                                    status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site access is disabled."}, status_code=403)
        # Large videos stream via the upload endpoint; JSON requests should never be video-sized.
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
            if length > 25 * 1024 * 1024:
                return JSONResponse({"detail": "JSON request exceeds 25 MB."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    @app.exception_handler(KeyError)
    async def not_found(request, exc):
        return JSONResponse({"detail": str(exc.args[0])}, status_code=404)

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(media.MediaError)
    async def media_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "ffmpeg": Path(media.ffmpeg_exe()).is_file(),
                "transcription": available(), "version": "0.1.0"}

    @app.get("/api/projects")
    def projects():
        return [{"id": p.id, "name": p.name, "media": p.media, "created_at": p.created_at,
                 "clip_count": len(p.clips), "revision": p.revision} for p in store.projects()]

    def register(source: Path, name: str | None) -> Project:
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError("Choose MP4, MOV, MKV, WEBM, AVI, M4V, MTS, M2TS, or TS video.")
        if not source.is_file():
            raise ValueError("Video file not found. Use its absolute local path.")
        info = media.probe(source)
        project = Project(name=(name or source.stem)[:160], source=str(source.resolve()),
                          media=info, created_at=now())
        directory = store.root / "projects" / project.id
        directory.mkdir(parents=True)
        try:
            media.thumbnail(source, directory / "poster.jpg", min(1, info.duration / 2))
            return store.create_project(project)
        except Exception:
            (directory / "poster.jpg").unlink(missing_ok=True)
            directory.rmdir()
            raise

    @app.post("/api/projects/import")
    def import_video(body: ImportRequest):
        path = body.path.strip().strip('"')
        if "://" in path or path.startswith(("\\\\", "//")):
            raise ValueError("Only local files are supported, not URLs or network shares.")
        source = Path(path).expanduser()
        if not source.is_absolute():
            raise ValueError("Use an absolute path, for example C:\\Videos\\recording.mp4.")
        return register(source.resolve(), body.name)

    @app.post("/api/projects/upload")
    def upload_video(file: UploadFile = File(...), name: str | None = Form(default=None)):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video extension.")
        directory = store.root / "uploads"
        directory.mkdir(exist_ok=True)
        target = directory / f"{new_id()}{suffix}"
        try:
            with target.open("xb") as out:
                while chunk := file.file.read(4 * 1024 * 1024):
                    out.write(chunk)
            return register(target, name or Path(file.filename or "Video").stem)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()

    @app.get("/api/projects/{project_id}")
    def project(project_id: str):
        return store.project(project_id)

    @app.patch("/api/projects/{project_id}")
    def update_project(project_id: str, body: ProjectUpdate):
        current = store.project(project_id)
        changes = body.model_dump(exclude_unset=True, exclude={"revision"})
        if any(value is None for value in changes.values()):
            raise ValueError("Fields cannot be null.")
        updated = Project.model_validate(current.model_dump() | changes)
        updated.cues.sort(key=lambda c: (c.start, c.end))
        if any(c.end > updated.media.duration + 0.1 for c in updated.cues):
            raise ValueError("Caption timing extends beyond the video.")
        if len({c.id for c in updated.cues}) != len(updated.cues):
            raise ValueError("Caption IDs must be unique.")
        original = {c.id: c for c in current.clips}
        framing_fields = ("start", "end", "layout", "focus_x", "focus_y", "face_region", "content_region")
        for clip in updated.clips:
            old = original.get(clip.id)
            if old is None or any(getattr(old, field) != getattr(clip, field) for field in framing_fields):
                clip.analysis = None
            else:
                # Analysis comes from the worker, never from editable browser JSON.
                clip.analysis = old.analysis
        return store.save_project(updated, body.revision)

    @app.post("/api/projects/{project_id}/transcript")
    def transcript(project_id: str, body: TranscriptRequest):
        p = store.project(project_id)
        p.cues, p.transcript_note = parse_transcript(body.content, body.filename, p.media.duration)
        return store.save_project(p, p.revision)

    @app.post("/api/projects/{project_id}/suggest")
    def suggest(project_id: str, body: SuggestRequest):
        p = store.project(project_id)
        clips = suggest_clips(p.cues, p.media.duration, body.min_duration, body.max_duration,
                              body.count, body.keywords)
        # Do not duplicate suggestions if the user clicks again with identical settings.
        p.clips.extend(c for c in clips if not any(
            abs(c.start - old.start) < 0.1 and abs(c.end - old.end) < 0.1 for old in p.clips
        ))
        return store.save_project(p, p.revision)

    @app.get("/api/projects/{project_id}/source")
    def source(project_id: str):
        path = Path(store.project(project_id).source)
        if not path.is_file():
            raise HTTPException(404, "Source video moved or was deleted.")
        return FileResponse(path)

    @app.get("/api/projects/{project_id}/poster")
    def poster(project_id: str):
        store.project(project_id)
        path = store.root / "projects" / project_id / "poster.jpg"
        if not path.is_file():
            raise HTTPException(404, "Poster not found.")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/projects/{project_id}/jobs")
    def start_job(project_id: str, body: JobRequest, request: Request):
        p = store.project(project_id)
        if body.kind == "transcribe":
            if not available():
                raise ValueError("Transcription is not installed. Run .\\Start-ClipFarm.ps1 -Transcription.")
            if not p.media.has_audio:
                raise ValueError("This video has no audio stream.")
        return request.app.state.jobs.submit(p, body.kind, body.clip_id, body.model)

    @app.get("/api/projects/{project_id}/jobs")
    def jobs(project_id: str):
        store.project(project_id)
        return store.jobs(project_id)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel(job_id: str, request: Request):
        return request.app.state.jobs.cancel(job_id)

    def completed_file(job_id: str, field: str, suffix: str):
        job = store.job(job_id)
        value = getattr(job, field)
        if job.status != "completed" or not value:
            raise HTTPException(404, "This job has no completed file yet.")
        path = Path(value)
        if path.suffix != suffix or not path.is_file():
            raise HTTPException(404, "Output file not found.")
        return job, path

    @app.get("/api/jobs/{job_id}/video")
    def video(job_id: str, download: bool = False):
        job, path = completed_file(job_id, "output", ".mp4")
        return FileResponse(path, media_type="video/mp4",
                            filename=f"{path.parent.name}.mp4" if download else None)

    @app.get("/api/jobs/{job_id}/subtitles")
    def subtitles(job_id: str):
        job, path = completed_file(job_id, "subtitles", ".srt")
        return FileResponse(path, media_type="application/x-subrip",
                            filename=f"{path.parent.name}.srt")

    @app.get("/api/jobs/{job_id}/transcript")
    def transcript_result(job_id: str):
        _, path = completed_file(job_id, "output", ".json")
        return FileResponse(path, media_type="application/json", filename="transcript.json")

    if STATIC.is_dir():
        app.mount("/", StaticFiles(directory=STATIC, html=True), name="studio")
    return app
