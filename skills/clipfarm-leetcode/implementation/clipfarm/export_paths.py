"""Readable, collision-safe studio output directories and legacy job-path migration."""
from __future__ import annotations

import re
import unicodedata
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

from .models import Job, Project

if TYPE_CHECKING:
    from .store import Store

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_RESERVED.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))


def safe_title(title: str) -> str:
    name = _UNSAFE.sub(" - ", unicodedata.normalize("NFKC", title))
    name = re.sub(r"\s+", " ", name).strip(" .-")[:100].rstrip(" .-") or "Untitled clip"
    if name.split(".", 1)[0].upper() in _RESERVED:
        name = "Clip - " + name
    return name


def export_label(project: Project, job: Job) -> str:
    if job.kind == "transcribe":
        return safe_title(project.name) + " - transcript"
    clip = next((clip for clip in project.clips if clip.id == job.clip_id), None)
    if clip is None:
        raise ValueError("The saved export snapshot does not contain this clip.")
    suffix = {"export": "", "preview": " - preview", "analyze": " - analysis"}[job.kind]
    return safe_title(clip.title) + suffix


def _candidates(root: Path, label: str):
    for version in count(1):
        yield root / (label if version == 1 else f"{label} ({version})")


def create_export_folder(root: Path, project: Project, job: Job) -> Path:
    exports = root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    for folder in _candidates(exports, export_label(project, job)):
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        return folder


def _stored_folder(exports: Path, name: str) -> Path:
    if not name or _UNSAFE.search(name) or name.endswith((" ", ".")) or name in {".", ".."}:
        raise ValueError("Invalid stored export-folder name.")
    folder = exports / name
    if folder.resolve().parent != exports.resolve():
        raise ValueError("Export folders must stay inside the exports directory.")
    return folder


def rename_legacy_exports(store: Store) -> int:
    """Run under the studio data lock, before the media worker starts."""
    exports = store.root / "exports"
    renamed = 0
    for job in reversed(store.jobs()):
        old = exports / job.id
        references_old = any(
            value and Path(value).is_relative_to(old)
            for value in (job.output, job.subtitles)
        )
        if not old.exists() and (job.export_folder is None or not references_old):
            continue
        if job.status in ("queued", "running"):
            raise ValueError("Stop active jobs before renaming their export folders.")
        if old.is_symlink() or (old.exists() and not old.is_dir()):
            raise ValueError(f"Refusing to migrate a linked or non-directory export: {old}")
        if job.export_folder is None:
            project = Project.model_validate(store.snapshot(job.id)["project"])
            folder = next(path for path in _candidates(exports, export_label(project, job))
                          if not path.exists() and not path.is_symlink())
            job.export_folder = folder.name
            # Persist the intended destination first so a crash after rename can resume.
            store.save_job(job)
        folder = _stored_folder(exports, job.export_folder)
        if old.exists():
            if folder.exists() or folder.is_symlink():
                raise ValueError(f"Export migration would overwrite {folder}; existing files were preserved.")
            old.rename(folder)
            renamed += 1
        elif not folder.is_dir():
            raise ValueError(f"Cannot resume export migration: neither {old} nor {folder} exists.")
        for field in ("output", "subtitles"):
            value = getattr(job, field)
            if value and Path(value).is_relative_to(old):
                setattr(job, field, str(folder / Path(value).relative_to(old)))
        store.save_job(job)
    return renamed
