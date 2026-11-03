import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clipfarm import app as app_module
from clipfarm import media
from clipfarm.app import DataLock, create_app
from clipfarm.models import MediaInfo


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "probe", lambda _: MediaInfo(
        duration=120, width=1280, height=720, fps=30, has_audio=True))
    monkeypatch.setattr(media, "thumbnail", lambda _, path, at=0: path.write_bytes(b"poster"))
    source = tmp_path / "source video.mp4"
    source.write_bytes(b"0123456789")
    app = create_app(tmp_path / "data")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/projects/import", json={"path": str(source)})
        assert response.status_code == 200, response.text
        yield client, response.json(), app, source


def wait_job(client, pid, jid):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = next(j for j in client.get(f"/api/projects/{pid}/jobs").json() if j["id"] == jid)
        if job["status"] not in ("queued", "running"):
            return job
        time.sleep(0.02)
    raise AssertionError("Job did not finish")


def test_import_and_byte_range(studio):
    client, project, _, _ = studio
    assert project["media"]["width"] == 1280
    response = client.get(f"/api/projects/{project['id']}/source", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.content == b"2345"
    assert client.get("/api/projects").json()[0]["clip_count"] == 0


def test_cross_origin_and_host_guards(studio):
    client, _, _, source = studio
    response = client.post("/api/projects/import", json={"path": str(source)},
                           headers={"Origin": "https://not-the-studio.example"})
    assert response.status_code == 403
    assert client.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
    assert client.get("/api/projects", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/api/projects", headers={"Origin": "null"}).status_code == 403


def test_projects_cannot_mutate_source_or_accept_invalid_times(studio):
    client, project, _, _ = studio
    route = f"/api/projects/{project['id']}"
    assert client.patch(route, json={"revision": 0, "source": "C:\\secret"}).status_code == 422
    assert client.patch(route, json={"revision": 0, "cues": None}).status_code == 422
    assert client.patch(route, json={"revision": 0, "clips": [{"start": 110, "end": 140}]}).status_code == 422
    response = client.patch(route, json={"revision": 0, "clips": [{"start": 1, "end": 30}]})
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    assert client.patch(route, json={"revision": 0, "name": "Stale"}).status_code == 409
    assert client.get(route).json()["name"] == project["name"]


def test_transcript_suggestions_and_duplicate_prevention(studio):
    client, p, _, _ = studio
    route = f"/api/projects/{p['id']}"
    content = '[{"start":0,"end":30,"text":"Why this works."},{"start":40,"end":75,"text":"The second lesson."}]'
    r = client.post(route + "/transcript", json={"filename": "captions.json", "content": content})
    assert r.status_code == 200 and len(r.json()["cues"]) == 2
    suggestions = client.post(route + "/suggest", json={"min_duration": 20, "max_duration": 40}).json()
    assert len(suggestions["clips"]) == 2
    assert len(client.post(route + "/suggest", json={"min_duration": 20, "max_duration": 40}).json()["clips"]) == 2
    assert client.post(route + "/suggest", json={"min_duration": 60, "max_duration": 20}).status_code == 422


def test_untimed_transcript_and_missing_transcription(studio, monkeypatch):
    client, p, _, _ = studio
    route = f"/api/projects/{p['id']}"
    response = client.post(route + "/transcript", json={"content": "Some spoken words."})
    assert response.status_code == 422 and "Plain text" in response.json()["detail"]
    monkeypatch.setattr(app_module, "available", lambda: False)
    assert client.post(route + "/jobs", json={"kind": "transcribe"}).status_code == 422


def test_import_granular_timestamped_text(studio):
    client, p, _, _ = studio
    response = client.post(f"/api/projects/{p['id']}/transcript", json={
        "filename": "transcript_granular.txt",
        "content": "# Export header\n00:00:17.199 First line.\n00:00:20.400 Second line.\n",
    })
    assert response.status_code == 200, response.text
    saved = response.json()
    assert len(saved["cues"]) == 2
    assert saved["cues"][0]["start"] == 17.199
    assert saved["cues"][0]["end"] == 20.4
    assert saved["cues"][-1]["end"] == 28.4
    assert "inferred" in saved["transcript_note"]


def test_no_network_or_relative_imports(studio):
    client, _, _, _ = studio
    for path in ("https://example.com/video.mp4", "\\\\host\\share\\video.mp4", "video.mp4"):
        assert client.post("/api/projects/import", json={"path": path}).status_code == 422


def test_upload_streams_to_local_project(studio):
    client, _, _, _ = studio
    response = client.post("/api/projects/upload", files={"file": ("a.mp4", b"fakevideo", "video/mp4")})
    assert response.status_code == 200
    assert Path(response.json()["source"]).read_bytes() == b"fakevideo"
    assert client.post("/api/projects/upload", files={"file": ("a.txt", b"text")}).status_code == 422


def test_snapshot_export_survives_edits_and_serves_download(studio, monkeypatch):
    client, p, _, _ = studio
    started, release = threading.Event(), threading.Event()
    received = []

    def render(source, info, clip, cues, output, preview, progress, cancel):
        received.append(clip.title)
        started.set()
        assert release.wait(5)
        output.write_bytes(b"encoded")
        output.with_suffix(".srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi")

    monkeypatch.setattr(media, "render", render)
    route = f"/api/projects/{p['id']}"
    p = client.patch(route, json={"revision": 0, "clips": [{"title": "Original", "start": 0, "end": 5}]}).json()
    clip = p["clips"][0]
    job = client.post(route + "/jobs", json={"kind": "export", "clip_id": clip["id"]}).json()
    try:
        assert started.wait(5)
        clip["title"] = "Edited"
        assert client.patch(route, json={"revision": p["revision"], "clips": [clip]}).status_code == 200
    finally:
        release.set()
    result = wait_job(client, p["id"], job["id"])
    assert received == ["Original"]
    assert result["status"] == "completed"
    assert Path(result["output"]).parent.name == "Original"
    assert result["export_folder"] == "Original"
    video = client.get(f"/api/jobs/{job['id']}/video?download=true")
    assert video.content == b"encoded"
    assert 'filename="Original.mp4"' in video.headers["content-disposition"]
    assert 'filename="Original.srt"' in client.get(
        f"/api/jobs/{job['id']}/subtitles").headers["content-disposition"]
    assert client.get(route).json()["clips"][0]["title"] == "Edited"


def test_failed_export_does_not_offer_partial_file(studio, monkeypatch):
    client, p, _, _ = studio

    def fail(*args):
        raise media.MediaError("Deliberate encoder failure")

    monkeypatch.setattr(media, "render", fail)
    route = f"/api/projects/{p['id']}"
    p = client.patch(route, json={"revision": 0, "clips": [{"start": 0, "end": 2}]}).json()
    job = client.post(route + "/jobs", json={"kind": "export", "clip_id": p["clips"][0]["id"]}).json()
    result = wait_job(client, p["id"], job["id"])
    assert result["status"] == "failed" and "Deliberate" in result["error"]
    assert client.get(f"/api/jobs/{job['id']}/video").status_code == 404


def test_cancelling_active_and_queued_jobs(studio, monkeypatch):
    client, p, _, _ = studio
    started = threading.Event()

    def cancellable(source, info, clip, cues, output, preview, progress, cancel):
        started.set()
        if not cancel.wait(5):
            raise AssertionError("Worker never received cancellation.")
        raise media.CancelledError("Export cancelled.")

    monkeypatch.setattr(media, "render", cancellable)
    route = f"/api/projects/{p['id']}"
    p = client.patch(route, json={"revision": 0, "clips": [{"start": 0, "end": 2}]}).json()
    body = {"kind": "export", "clip_id": p["clips"][0]["id"]}
    active = client.post(route + "/jobs", json=body).json()
    assert started.wait(5)
    queued = client.post(route + "/jobs", json=body).json()
    assert client.post(f"/api/jobs/{queued['id']}/cancel").json()["status"] == "cancelled"
    client.post(f"/api/jobs/{active['id']}/cancel")
    assert wait_job(client, p["id"], active["id"])["status"] == "cancelled"
    assert wait_job(client, p["id"], queued["id"])["status"] == "cancelled"
    assert client.get(f"/api/jobs/{active['id']}/video").status_code == 404


def test_persistence_after_restart(tmp_path, monkeypatch):
    from clipfarm.models import Job, Project
    from clipfarm.jobs import now
    from clipfarm.store import Store

    root = tmp_path / "persisted"
    store = Store(root)
    project = Project(name="Saved", source=str(tmp_path / "video.mp4"),
                      media=MediaInfo(duration=4, width=640, height=360, fps=30), created_at=now())
    store.create_project(project)
    job = Job(project_id=project.id, kind="transcribe", created_at=now(), status="running")
    store.create_job(job, {"project": project.model_dump(), "model": "base"})
    with TestClient(create_app(root), base_url="http://127.0.0.1") as client:
        assert client.get(f"/api/projects/{project.id}").json()["name"] == "Saved"
        result = client.get(f"/api/projects/{project.id}/jobs").json()[0]
        assert result["status"] == "interrupted"
        assert "Submit" in result["message"]


def test_data_directory_lock(tmp_path):
    one, two = DataLock(tmp_path / "lock"), DataLock(tmp_path / "lock")
    one.acquire()
    try:
        with pytest.raises(RuntimeError, match="Another"):
            two.acquire()
    finally:
        one.release()
    two.acquire()
    two.release()
