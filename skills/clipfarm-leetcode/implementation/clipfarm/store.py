from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import Job, Project


class ConflictError(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "studio.sqlite3"
        with self.connection() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    document TEXT NOT NULL, snapshot TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_project ON jobs(project_id);
            """)

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.db, timeout=30)
        try:
            with con:
                yield con
        finally:
            con.close()

    def create_project(self, project: Project) -> Project:
        with self.connection() as con:
            con.execute("INSERT INTO projects VALUES (?,?)", (project.id, project.model_dump_json()))
        return project

    def project(self, project_id: str) -> Project:
        with self.connection() as con:
            row = con.execute("SELECT document FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise KeyError("Project not found.")
        return Project.model_validate_json(row[0])

    def projects(self) -> list[Project]:
        with self.connection() as con:
            rows = con.execute("SELECT document FROM projects ORDER BY rowid DESC").fetchall()
        return [Project.model_validate_json(row[0]) for row in rows]

    def save_project(self, project: Project, expected_revision: int) -> Project:
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT document FROM projects WHERE id=?", (project.id,)).fetchone()
            if row is None:
                raise KeyError("Project not found.")
            current = json.loads(row[0])
            if current["revision"] != expected_revision:
                raise ConflictError("The project changed. Reload before saving your edits.")
            project = project.model_copy(update={"revision": expected_revision + 1})
            con.execute("UPDATE projects SET document=? WHERE id=?",
                        (project.model_dump_json(), project.id))
        return project

    def create_job(self, job: Job, snapshot: dict) -> Job:
        with self.connection() as con:
            con.execute("INSERT INTO jobs VALUES (?,?,?,?)",
                        (job.id, job.project_id, job.model_dump_json(), json.dumps(snapshot)))
        return job

    def job(self, job_id: str) -> Job:
        with self.connection() as con:
            row = con.execute("SELECT document FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("Job not found.")
        return Job.model_validate_json(row[0])

    def snapshot(self, job_id: str) -> dict:
        with self.connection() as con:
            row = con.execute("SELECT snapshot FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("Job not found.")
        return json.loads(row[0])

    def save_job(self, job: Job) -> None:
        with self.connection() as con:
            con.execute("UPDATE jobs SET document=? WHERE id=?", (job.model_dump_json(), job.id))

    def jobs(self, project_id: str | None = None) -> list[Job]:
        with self.connection() as con:
            if project_id is None:
                rows = con.execute("SELECT document FROM jobs ORDER BY rowid DESC").fetchall()
            else:
                rows = con.execute("SELECT document FROM jobs WHERE project_id=? ORDER BY rowid DESC",
                                   (project_id,)).fetchall()
        return [Job.model_validate_json(row[0]) for row in rows]
