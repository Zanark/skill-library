from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import media
from .export_paths import create_export_folder, rename_legacy_exports
from .models import Job, Project
from .store import ConflictError, Store
from .transcribe import transcribe

logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobManager:
    """One bounded media worker; persisted snapshots keep edits out of in-flight exports."""

    def __init__(self, store: Store):
        self.store = store
        self.queue: queue.Queue[str | None] = queue.Queue()
        self.events: dict[str, threading.Event] = {}
        self.lock = threading.RLock()
        self.closing = False
        for job in store.jobs():
            if job.status in ("queued", "running"):
                job.status = "interrupted"
                job.message = "The previous process stopped. Submit the job again."
                store.save_job(job)
        rename_legacy_exports(store)
        self.worker = threading.Thread(target=self._run, name="clipfarm-media", daemon=True)
        self.worker.start()

    def submit(self, project: Project, kind: str, clip_id: str | None, model: str) -> Job:
        with self.lock:
            if self.closing:
                raise ValueError("The studio is shutting down.")
            if kind != "transcribe" and not any(c.id == clip_id for c in project.clips):
                raise ValueError("Choose a saved clip first.")
            pending = sum(j.status in ("queued", "running") for j in self.store.jobs())
            if pending >= 100:
                raise ValueError("The queue is full (100 jobs). Wait for an export to finish.")
            job = Job(project_id=project.id, clip_id=clip_id, kind=kind, created_at=now(),
                      revision=project.revision)
            self.store.create_job(job, {"project": project.model_dump(), "model": model})
            self.events[job.id] = threading.Event()
            self.queue.put(job.id)
            return job

    def cancel(self, job_id: str) -> Job:
        with self.lock:
            job = self.store.job(job_id)
            if job.status not in ("queued", "running"):
                return job
            event = self.events.get(job_id)
            if event:
                event.set()
            if job.status == "queued":
                job.status = "cancelled"
                job.message = "Cancelled before starting."
            else:
                job.message = "Cancelling; waiting for the current processing step to stop."
            self.store.save_job(job)
            return job

    def close(self):
        with self.lock:
            self.closing = True
            for event in self.events.values():
                event.set()
            self.queue.put(None)
        self.worker.join(timeout=15)
        if self.worker.is_alive():
            logger.warning("Media worker is still stopping (a model download may be in progress).")

    def _run(self):
        while True:
            job_id = self.queue.get()
            if job_id is None:
                return
            try:
                self._execute(job_id)
            except Exception:
                # Only the job boundary catches unexpected errors, and records explicit failure.
                logger.exception("Unexpected failure executing job %s", job_id)
                with self.lock:
                    job = self.store.job(job_id)
                    job.status = "failed"
                    job.error = "An unexpected worker error occurred. See the studio terminal."
                    job.message = job.error
                    self.store.save_job(job)
            finally:
                with self.lock:
                    self.events.pop(job_id, None)
                self.queue.task_done()

    def _execute(self, job_id: str):
        with self.lock:
            job = self.store.job(job_id)
            event = self.events[job_id]
            if job.status == "cancelled":
                return
            job.status = "running"
            job.message = "Starting"
            self.store.save_job(job)
        snapshot = self.store.snapshot(job_id)
        project = Project.model_validate(snapshot["project"])
        folder = create_export_folder(self.store.root, project, job)
        job.export_folder = folder.name
        with self.lock:
            self.store.save_job(job)
        last_progress = 0.0

        def progress(value: float, message: str):
            nonlocal last_progress
            current = time.monotonic()
            if current - last_progress < 0.25 and value < 1:
                return
            last_progress = current
            with self.lock:
                status = self.store.job(job_id)
                status.progress = max(0, min(1, value))
                if not event.is_set():
                    status.message = message
                self.store.save_job(status)

        try:
            if event.is_set():
                raise media.CancelledError("Cancelled.")
            source = Path(project.source)
            if not source.is_file():
                raise media.MediaError("The source video moved or was deleted. Import its new location.")
            completion = "Ready"
            if job.kind == "transcribe":
                cues = transcribe(source, project.media, snapshot["model"], progress, event)
                project.cues = cues
                project.transcript_note = (
                    "Local machine transcription. Review names and wording. Timing at 10-minute "
                    "chunk boundaries may need correction; imported transcript text was not force-aligned."
                )
                transcript = folder / "transcript.json"
                transcript.write_text(
                    "[" + ",".join(c.model_dump_json() for c in cues) + "]", encoding="utf-8"
                )
                job.output = str(transcript)
                try:
                    saved = self.store.save_project(project, job.revision)
                    job.revision = saved.revision
                    completion = "Transcription ready. Review captions before exporting."
                except ConflictError:
                    completion = "Transcript saved, but project changed. Download it and import to apply."
            else:
                clip = next(c for c in project.clips if c.id == job.clip_id)
                if job.kind == "analyze":
                    clip.analysis = media.analyze(source, project.media, clip, progress, event)
                    try:
                        saved = self.store.save_project(project, job.revision)
                        job.revision = saved.revision
                        completion = "Framing analysis ready. Review before exporting."
                    except ConflictError:
                        completion = "Project changed during analysis. Analyze the saved clip again."
                else:
                    output = folder / "clip.mp4"
                    analysis = media.render(source, project.media, clip, project.cues, output,
                                            job.kind == "preview", progress, event)
                    if not output.is_file() or not output.stat().st_size:
                        raise media.MediaError("The encoder finished without a usable output file.")
                    job.output = str(output)
                    srt = output.with_suffix(".srt")
                    if srt.is_file() and srt.stat().st_size:
                        job.subtitles = str(srt)
                    completion = "Preview ready" if job.kind == "preview" else "1080 x 1920 export ready"
                    if analysis:
                        completion += f". Framing analysis: {analysis.message}"
                        if clip.layout == "follow" and analysis.layout == "fit":
                            completion += " Follow fell back to Fit; review before posting."
            if event.is_set():
                raise media.CancelledError("Cancelled.")
            job.status = "completed"
            job.progress = 1
            job.message = completion
        except media.CancelledError as exc:
            job.status = "cancelled"
            job.message = str(exc) or "Cancelled."
            job.output = None
            job.subtitles = None
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            job.status = "failed"
            job.error = str(exc) or type(exc).__name__
            job.message = job.error
            job.output = None
            job.subtitles = None
        with self.lock:
            self.store.save_job(job)
