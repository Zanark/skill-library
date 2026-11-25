import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("clipfarm_copy_installer", ROOT / "scripts" / "install_skill_library.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ClipFarmCopyTests(unittest.TestCase):
    def repository(self, root):
        repository = root / "repository"
        for name in installer.RUNTIMES:
            path = repository / "skills" / name / "implementation"
            path.mkdir(parents=True)
            (path / "source.txt").write_text("bundled baseline", encoding="utf-8")
        runtime = repository / "skills" / "documentation-mesh" / "implementation" / "runtime" / "windows-x64"
        runtime.mkdir(parents=True)
        binary = runtime / "fixture.exe"
        binary.write_bytes(b"fixture-not-an-executable")
        (runtime / "version-manifest.json").write_text(json.dumps({
            "executable": binary.name, "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        }), encoding="utf-8")
        (repository / "skills" / "context-mesh" / "implementation" / "config.example.json").write_text(
            '{"roots":[]}', encoding="utf-8")
        entries = [
            {"name": "clipfarm-leetcode"},
            {"name": "clipfarm-cinematic-music-video", "installation": "clipfarm-checkout"},
        ]
        for entry in entries:
            path = repository / "skills" / entry["name"] / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "Repository: `__CLIPFARM_ROOT__`\n"
                "Read `__CLIPFARM_ROOT__\\skills\\guide.md`.\n"
                "Python `__CLIPFARM_ROOT__\\.venv\\Scripts\\python.exe`.\n"
                "Output `__CLIPFARM_ROOT__\\results\\session_<timestamp>\\<clip-folder>\\`.\n",
                encoding="utf-8",
            )
        (repository / "source-inventory.json").write_text(json.dumps(entries), encoding="utf-8")
        return repository

    def checkout(self, root):
        checkout = root / "current ClipFarm"
        for name in ("pyproject.toml", "AGENTS.md", "clipfarm/__main__.py", "clipfarm/grading_cli.py", "skills/guide.md"):
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("external source must stay unchanged", encoding="utf-8")
        return checkout

    def test_default_preserves_legacy_route_and_reports_checkout_entries_skipped(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self.repository(root)
            with patch.object(installer, "ROOT", repository):
                result = installer.install(root / "runtime", root / "installed")
            self.assertEqual(result["installedSkills"], 1)
            self.assertEqual(result["skippedSkillsRequiringClipFarmCheckout"], ["clipfarm-cinematic-music-video"])
            self.assertTrue((root / "runtime" / "clipfarm" / "source.txt").is_file())
            self.assertFalse((root / "installed" / "clipfarm-cinematic-music-video").exists())

    def test_explicit_checkout_binds_all_copies_without_copying_or_changing_application(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self.repository(root)
            checkout = self.checkout(root)
            before = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}
            with patch.object(installer, "ROOT", repository):
                result = installer.install(root / "runtime", root / "installed", clipfarm_root=checkout)
                self.assertEqual(result["installedSkills"], 2)
                self.assertEqual(result["skippedSkillsRequiringClipFarmCheckout"], [])
                for name in ("clipfarm-leetcode", "clipfarm-cinematic-music-video"):
                    text = (root / "installed" / name / "SKILL.md").read_text(encoding="utf-8")
                    self.assertIn(str(checkout), text)
                    self.assertNotIn("__CLIPFARM_ROOT__", text)
                installed = root / "installed" / "clipfarm-cinematic-music-video" / "SKILL.md"
                installed.write_text("preserve personal edit", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    installer.install(root / "runtime", root / "installed", clipfarm_root=checkout)
                self.assertEqual(installed.read_text(), "preserve personal edit")
            self.assertFalse((root / "runtime" / "clipfarm").exists())
            self.assertFalse((checkout / ".venv").exists())
            self.assertEqual(before, {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()})

    def test_incomplete_checkout_fails_before_runtime_or_skill_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self.repository(root)
            checkout = self.checkout(root)
            (checkout / "clipfarm" / "grading_cli.py").unlink()
            with patch.object(installer, "ROOT", repository), self.assertRaises(FileNotFoundError):
                installer.install(root / "runtime", root / "installed", clipfarm_root=checkout)
            self.assertFalse((root / "runtime").exists())
            self.assertFalse((root / "installed").exists())

    def test_dependency_restore_does_not_install_into_external_clipfarm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self.repository(root)
            checkout = self.checkout(root)
            with patch.object(installer, "ROOT", repository), patch.object(
                installer.shutil, "which", return_value="npm"
            ), patch.object(installer.subprocess, "run") as run:
                installer.install(root / "runtime", root / "installed",
                                  clipfarm_root=checkout, dependencies=True)
            self.assertTrue(run.call_args_list)
            for call in run.call_args_list:
                self.assertEqual(call.args[0][0], "npm")
                self.assertNotEqual(call.kwargs["cwd"], checkout)
            self.assertFalse((checkout / ".venv").exists())

    def test_public_manifest_binds_exact_normative_snapshots_and_has_no_application_payload(self):
        manifest = json.loads((ROOT / "docs" / "clipfarm-source-manifest.json").read_text(encoding="utf-8"))
        inventory = {r["name"]: r for r in json.loads((ROOT / "source-inventory.json").read_text(encoding="utf-8"))}
        self.assertEqual(len(manifest["skills"]), len(set(manifest["skills"])))
        for name in manifest["skills"]:
            data = (ROOT / "skills" / name / "SKILL.md").read_bytes()
            row = next(r for r in manifest["files"] if r["destination"] == f"skills/{name}/SKILL.md")
            self.assertEqual(row["sourceSha256"], row["publishedSha256"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), inventory[name]["sha256"])
        for row in manifest["files"]:
            path = Path(row["destination"])
            self.assertNotIn("implementation", path.parts)
            self.assertFalse(any(p in {".agent-context", ".clipfarm", ".env", "results", ".venv"} for p in path.parts))
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), row["publishedSha256"])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 exercises the real documentation validator")
    def test_runbook_profile_does_not_require_five_duplicate_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            skill = root / "skills" / "sample"
            skill.mkdir(parents=True)
            for name in ("SKILL.md", "README.md", "RUNBOOK.md"):
                (skill / name).write_text("# Real fixture documentation\n", encoding="utf-8")
            row = {"name": "sample", "sha256": hashlib.sha256((skill / "SKILL.md").read_bytes()).hexdigest(),
                   "documentationProfile": "runbook"}
            inventory = root / "source-inventory.json"
            inventory.write_text(json.dumps([row]), encoding="utf-8")
            validator = root / "scripts" / "Validate-SkillLibrary.ps1"
            shutil.copy2(ROOT / "scripts" / validator.name, validator)
            result = subprocess.run(["pwsh", "-NoProfile", "-File", str(validator)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            row["documentationProfile"] = "unknown"
            inventory.write_text(json.dumps([row]), encoding="utf-8")
            result = subprocess.run(["pwsh", "-NoProfile", "-File", str(validator)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown documentation profile", result.stderr)


if __name__ == "__main__":
    unittest.main()
