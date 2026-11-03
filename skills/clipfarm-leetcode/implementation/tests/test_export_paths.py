import sqlite3
from email.message import Message
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clipfarm.app import create_app
from clipfarm.export_paths import create_export_folder, export_label, rename_legacy_exports, safe_title
from clipfarm.models import Clip, Job, MediaInfo, Project
from clipfarm.store import Store


def legacy_export(root, title="Contains Duplicate: Why a Set Fits", kind="export"):
    store = Store(root)
    clip = Clip(title=title, start=0, end=3)
    project = Project(
        name="LeetCode recording", source=str(root / "source.mp4"),
        media=MediaInfo(duration=10, width=1280, height=720, fps=30),
        created_at="2026-09-20T00:00:00Z", clips=[clip],
    )
    store.create_project(project)
    job = Job(
        project_id=project.id, clip_id=clip.id, kind=kind,
        status="completed", created_at=project.created_at,
    )
    folder = root / "exports" / job.id
    folder.mkdir(parents=True)
    (folder / "clip.mp4").write_bytes(b"original video")
    (folder / "clip.srt").write_text("original captions")
    job.output = str(folder / "clip.mp4")
    job.subtitles = str(folder / "clip.srt")
    store.create_job(job, {"project": project.model_dump(), "model": "base"})
    return store, project, job


@pytest.mark.parametrize(("title", "expected"), [
    ("Contains Duplicate: Accepted / 15 ms?", "Contains Duplicate - Accepted - 15 ms"),
    ("  The Hammer.  ", "The Hammer"),
    ("../Outside\\directory", "Outside - directory"),
    ("NUL", "Clip - NUL"),
    ("con.txt", "Clip - con.txt"),
    ("LPT1", "Clip - LPT1"),
    ("COM\u00b9", "Clip - COM1"),
    ("CONIN$", "Clip - CONIN$"),
    ("  ...<>:*?  ", "Untitled clip"),
    ("Caf\u00e9 algorithm", "Caf\u00e9 algorithm"),
    ("A\nnew\x00title", "A - new - title"),
    ("x" * 120, "x" * 100),
])
def test_windows_safe_readable_title(title, expected):
    assert safe_title(title) == expected


def test_unique_folders_preserve_previous_versions(tmp_path):
    _, project, job = legacy_export(tmp_path)
    first = create_export_folder(tmp_path, project, job)
    (first / "keep.txt").write_text("do not overwrite")
    second = create_export_folder(tmp_path, project, job)
    assert first.name == "Contains Duplicate - Why a Set Fits"
    assert second.name == first.name + " (2)"
    assert (first / "keep.txt").read_text() == "do not overwrite"
    job.kind = "preview"
    assert create_export_folder(tmp_path, project, job).name == first.name + " - preview"
    job.kind = "transcribe"
    assert export_label(project, job) == "LeetCode recording - transcript"


def test_startup_migrates_legacy_folders_and_preserves_download_urls(tmp_path):
    store, _, job = legacy_export(tmp_path)
    original_snapshot = store.snapshot(job.id)
    with TestClient(create_app(tmp_path), base_url="http://127.0.0.1") as client:
        saved = store.job(job.id)
        assert saved.export_folder == "Contains Duplicate - Why a Set Fits"
        assert not (tmp_path / "exports" / job.id).exists()
        assert Path(saved.output).read_bytes() == b"original video"
        assert Path(saved.subtitles).read_text() == "original captions"
        video = client.get(f"/api/jobs/{job.id}/video?download=true")
        assert video.status_code == 200 and video.content == b"original video"
        headers = Message()
        headers["Content-Disposition"] = video.headers["content-disposition"]
        assert headers.get_filename() == "Contains Duplicate - Why a Set Fits.mp4"
        assert client.get(f"/api/jobs/{job.id}/subtitles").text == "original captions"
    assert store.snapshot(job.id) == original_snapshot
    assert rename_legacy_exports(store) == 0


def test_migration_resumes_after_rename_before_database_update(tmp_path, monkeypatch):
    store, _, job = legacy_export(tmp_path)
    original_save = store.save_job
    calls = 0

    def fail_second_save(value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise sqlite3.OperationalError("Simulated database interruption")
        original_save(value)

    monkeypatch.setattr(store, "save_job", fail_second_save)
    with pytest.raises(sqlite3.OperationalError, match="interruption"):
        rename_legacy_exports(store)
    interrupted = store.job(job.id)
    assert interrupted.output == job.output
    assert interrupted.export_folder == "Contains Duplicate - Why a Set Fits"
    assert (tmp_path / "exports" / interrupted.export_folder / "clip.mp4").is_file()
    monkeypatch.setattr(store, "save_job", original_save)
    rename_legacy_exports(store)
    assert Path(store.job(job.id).output).read_bytes() == b"original video"
    assert Path(store.job(job.id).output).parent.name == interrupted.export_folder


def test_migration_never_overwrites_an_existing_destination(tmp_path):
    store, _, job = legacy_export(tmp_path)
    job.export_folder = "Already exists"
    store.save_job(job)
    destination = tmp_path / "exports" / job.export_folder
    destination.mkdir()
    (destination / "keep.txt").write_text("user data")
    with pytest.raises(ValueError, match="would overwrite"):
        rename_legacy_exports(store)
    assert Path(job.output).read_bytes() == b"original video"
    assert (destination / "keep.txt").read_text() == "user data"


def test_duplicate_legacy_titles_get_distinct_names(tmp_path):
    store, _, first = legacy_export(tmp_path, title="Same title", kind="preview")
    _, _, second = legacy_export(tmp_path, title="Same title", kind="preview")
    assert rename_legacy_exports(store) == 2
    assert store.job(first.id).export_folder == "Same title - preview"
    assert store.job(second.id).export_folder == "Same title - preview (2)"


def test_active_exports_are_not_renamed(tmp_path):
    store, _, job = legacy_export(tmp_path)
    job.status = "running"
    store.save_job(job)
    with pytest.raises(ValueError, match="active jobs"):
        rename_legacy_exports(store)
    assert Path(job.output).is_file()


def test_unsafe_persisted_destination_is_rejected(tmp_path):
    store, _, job = legacy_export(tmp_path)
    job.export_folder = "..\\outside"
    store.save_job(job)
    with pytest.raises(ValueError, match="Invalid stored"):
        rename_legacy_exports(store)
    assert Path(job.output).is_file()
