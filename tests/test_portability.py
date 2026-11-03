import importlib.util
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
        spec.loader.exec_module(result)
    return result


package = module("package_skill_support")
restorer = module("restore_skill_state")
installer = module("install_skill_library")
with patch.dict("sys.modules", {"restore_skill_state": restorer, "package_skill_support": package}):
    merger = module("merge_skill_state")


class PrivateArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.destination = self.root / "migration-private" / "snapshot"
        self.config = {"private": [{"name": "sample", "source": str(self.source)}]}
        self.mock_root = patch.object(package, "ROOT", self.root)
        self.mock_root.start()

    def tearDown(self):
        self.mock_root.stop()
        shutil.rmtree(package.io_path(self.root))
        self.temporary.cleanup()

    def test_roundtrip_deduplicates_and_preserves_binary_and_sqlite(self):
        (self.source / "one.mp4").write_bytes(b"same-media\x00")
        (self.source / "two.mp4").write_bytes(b"same-media\x00")
        (self.source / "not-sqlite.db").write_bytes(b"some-other-database")
        database = self.source / "state.sqlite3"
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE state (value TEXT)")
            connection.execute("INSERT INTO state VALUES ('identity retained')")
            connection.commit()
            package.collect_private(self.config, self.destination)
        finally:
            connection.close()
        output = self.root / "restored"
        result = restorer.restore(self.destination, output)
        self.assertEqual(result["verifiedFiles"], 4)
        self.assertEqual(result["verifiedObjects"], 3)
        self.assertEqual((output / "sample" / "two.mp4").read_bytes(), b"same-media\x00")
        connection = sqlite3.connect(output / "sample" / "state.sqlite3")
        try:
            self.assertEqual(connection.execute("SELECT value FROM state").fetchone()[0], "identity retained")
        finally:
            connection.close()
        self.assertFalse((output / "sample" / "state.sqlite3-wal").exists())

    def test_secrets_and_pruned_directories_are_accounted_for(self):
        (self.source / ".npmrc").write_text("private-auth", encoding="utf-8")
        (self.source / "state.json").write_text('{"api_key":"sensitive-value"}', encoding="utf-8")
        (self.source / ".venv").mkdir()
        (self.source / ".venv" / "cached").write_bytes(b"not-portable")
        package.collect_private(self.config, self.destination)
        output = self.root / "restored"
        restorer.restore(self.destination, output)
        self.assertIn("[REDACTED]", (output / "sample" / "state.json").read_text())
        rows = [json.loads(row) for row in (self.destination / "files.jsonl").read_text().splitlines()]
        self.assertEqual(len([r for r in rows if "excluded" in r]), 2)

    def test_corruption_and_existing_destination_are_rejected(self):
        (self.source / "file").write_bytes(b"correct")
        package.collect_private(self.config, self.destination)
        with self.assertRaises(FileExistsError):
            restorer.restore(self.destination, self.source)
        blob = next((self.destination / "objects").iterdir())
        blob.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "Corrupt"):
            restorer.restore(self.destination)

    def test_incomplete_export_can_resume_but_complete_export_cannot(self):
        (self.source / "file").write_bytes(b"retained")
        package.collect_private(self.config, self.destination)
        marker = self.destination / "manifest.json"
        manifest = json.loads(marker.read_text())
        manifest["complete"] = False
        marker.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "complete"):
            restorer.restore(self.destination)
        package.collect_private(self.config, self.destination, resume=True)
        self.assertEqual(restorer.restore(self.destination)["verifiedObjects"], 1)
        with self.assertRaises(FileExistsError):
            package.collect_private(self.config, self.destination, resume=True)

    def test_unsafe_restore_paths_and_public_destinations_are_rejected(self):
        for value in ("..\\outside", "C:\\outside", "C:outside", "\\\\host\\share", "file:stream"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                restorer.relative_path("sample", value)
        with self.assertRaises(ValueError):
            restorer.relative_path("../outside", "file")
        with self.assertRaisesRegex(ValueError, "inside"):
            package.package_public({"public": [{"source": str(self.source), "destination": "../outside"}]})

    def test_busy_sqlite_stops_explicitly_without_publishing_a_complete_archive(self):
        database = self.source / "busy.sqlite3"
        connection = sqlite3.connect(database)
        connection.execute("CREATE TABLE state (value TEXT)")
        connection.close()
        original = Mock()
        snapshot = Mock()
        original.backup.side_effect = lambda target, pages, progress: progress(5, 1, 1)
        with patch.object(package.sqlite3, "connect", side_effect=[original, snapshot]), patch.object(
            package.time, "monotonic", side_effect=[0, 31]
        ), self.assertRaisesRegex(TimeoutError, "busy"):
            package.collect_private(self.config, self.destination)
        self.assertFalse(json.loads((self.destination / "manifest.json").read_text())["complete"])
        self.assertTrue(database.is_file())
        original.close.assert_called_once()
        snapshot.close.assert_called_once()

    def test_merge_deduplicates_between_collections_and_restores_both_paths(self):
        (self.source / "shared.mp4").write_bytes(b"identical-media")
        package.collect_private(self.config, self.destination)
        other = self.root / "migration-private" / "other"
        package.collect_private({"private": [{"name": "other", "source": str(self.source)}]}, other)
        destination = self.root / "migration-private" / "merged"
        with patch.object(merger, "ROOT", self.root):
            result = merger.merge([self.destination, other], destination)
        self.assertEqual(result["files"], 2)
        self.assertEqual(result["uniqueObjects"], 1)
        output = self.root / "restored"
        restorer.restore(destination, output)
        self.assertEqual((output / "sample" / "shared.mp4").read_bytes(), b"identical-media")
        self.assertEqual((output / "other" / "shared.mp4").read_bytes(), b"identical-media")

    def test_long_paths_preserve_binary_and_readonly_sqlite_and_restore(self):
        nested = self.source
        for number in range(9):
            nested /= f"nested-{number}-" + "x" * 25
        package.io_path(nested).mkdir(parents=True)
        package.io_path(nested / "frame.png").write_bytes(b"long-path-media")
        database = nested / "state.sqlite3"
        connection = sqlite3.connect(package.io_path(database))
        try:
            connection.execute("CREATE TABLE state (value TEXT)")
            connection.execute("INSERT INTO state VALUES ('preserved')")
            connection.commit()
        finally:
            connection.close()
        package.collect_private(self.config, self.destination)
        other = self.root / "migration-private" / "second"
        package.collect_private({"private": [{"name": "other", "source": str(self.source)}]}, other)
        destination = self.root / "migration-private" / nested.relative_to(self.source) / "merged"
        with patch.object(merger, "ROOT", self.root):
            merger.merge([self.destination, other], destination)
        output = self.root / "restored" / nested.relative_to(self.source)
        result = restorer.restore(destination, output)
        self.assertEqual(result["verifiedFiles"], 4)
        restored = output / "sample" / nested.relative_to(self.source)
        self.assertEqual(package.io_path(restored / "frame.png").read_bytes(), b"long-path-media")
        snapshot = sqlite3.connect(package.io_path(restored / "state.sqlite3"))
        try:
            self.assertEqual(snapshot.execute("SELECT value FROM state").fetchone()[0], "preserved")
        finally:
            snapshot.close()


class InstallationTests(unittest.TestCase):
    def test_standalone_binding_rebases_commands_and_guards_existing_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            for name in installer.RUNTIMES:
                source = repository / "skills" / name / "implementation"
                source.mkdir(parents=True)
                (source / "source.txt").write_text("unchanged", encoding="utf-8")
            skill = repository / "skills" / "documentation-mesh" / "SKILL.md"
            skill.write_text(
                "# Documentation Mesh\n\n## Runtime resolution\n\n"
                "Wrong plugin-relative fallback.\n\n## Build\n\n"
                "```powershell\ndocumentation-mesh build --validate\n```\n",
                encoding="utf-8",
            )
            (repository / "source-inventory.json").write_text(
                json.dumps([{"name": "documentation-mesh"}]), encoding="utf-8"
            )
            example = repository / "skills" / "context-mesh" / "implementation" / "config.example.json"
            example.write_text('{"roots":[]}', encoding="utf-8")
            docs = repository / "skills" / "documentation-mesh" / "implementation" / "runtime" / "windows-x64"
            docs.mkdir(parents=True)
            executable = docs / "documentation-mesh.exe"
            executable.write_bytes(b"test-payload-not-executable")
            (docs / "version-manifest.json").write_text(json.dumps({
                "executable": executable.name,
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            runtime = root / "runtime with spaces"
            skills = root / "installed"
            with patch.object(installer, "ROOT", repository):
                installer.install(runtime, skills)
                installed = (skills / "documentation-mesh" / "SKILL.md").read_text(encoding="utf-8")
                command = f'& "{runtime / "documentation-mesh" / "runtime" / "windows-x64" / executable.name}"'
                self.assertIn(command + " --version", installed)
                self.assertIn(command + " build --validate", installed)
                self.assertNotIn("Wrong plugin-relative fallback", installed)
                self.assertEqual(json.loads((runtime / "context-mesh" / "config.json").read_text())["roots"][0], str(repository))
                (runtime / "speak" / "source.txt").write_text("local edits", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    installer.install(runtime, skills)
                self.assertEqual((runtime / "speak" / "source.txt").read_text(), "local edits")


if __name__ == "__main__":
    unittest.main()
