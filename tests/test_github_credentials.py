import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "with_github_token",
    ROOT / "skills" / "development-documentation-manual" / "scripts" / "with_github_token.py",
)
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)


class CredentialLoaderTests(unittest.TestCase):
    def test_strict_parser_does_not_evaluate_or_expose_invalid_values(self):
        self.assertEqual(loader.parse_token("# local\nTODO_SYNC_GITHUB_TOKEN='fixture_token'\n"), "fixture_token")
        for text in (
            "TODO_SYNC_GITHUB_TOKEN=",
            "TODO_SYNC_GITHUB_TOKEN=$(fixture_secret)",
            "TODO_SYNC_GITHUB_TOKEN='fixture_secret",
            "TODO_SYNC_GITHUB_TOKEN=fixture_secret\nTODO_SYNC_GITHUB_TOKEN=duplicate",
            "OTHER_KEY=fixture_secret",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError) as error:
                loader.parse_token(text)
            self.assertNotIn("fixture_secret", str(error.exception))

    def test_local_file_overrides_stale_environment_and_requires_git_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            skill = root / "skills" / "manual"
            skill.mkdir(parents=True)
            credential = skill / ".env"
            credential.write_text("TODO_SYNC_GITHUB_TOKEN=fixture_token", encoding="utf-8")
            with patch.dict(os.environ, {"TODO_SYNC_GITHUB_TOKEN": "stale_token"}):
                self.assertEqual(loader.load_token(skill), "fixture_token")
                credential.write_text("TODO_SYNC_GITHUB_TOKEN=", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Empty"):
                    loader.load_token(skill)
            subprocess.run(["git", "-C", str(root), "add", "-f", str(credential)], check=True)
            with self.assertRaisesRegex(ValueError, "untracked"):
                loader.load_token(skill)
            subprocess.run(["git", "-C", str(root), "rm", "--cached", "-f", "--quiet", str(credential)], check=True)
            (root / ".gitignore").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Git-ignored"):
                loader.load_token(skill)

    def test_trusted_child_receives_credential_without_changing_parent_or_printing_it(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"GH_TOKEN": "original", "GH_DEBUG": "api"}), patch.object(
            loader, "load_token", return_value="fixture_token"
        ), patch.object(loader.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value.returncode = 7
            self.assertEqual(loader.main(["--", "gh", "api", "user"]), 7)
            self.assertEqual(run.call_args.kwargs["env"]["GH_TOKEN"], "fixture_token")
            self.assertEqual(run.call_args.kwargs["env"]["TODO_SYNC_GITHUB_TOKEN"], "fixture_token")
            self.assertNotIn("GH_DEBUG", run.call_args.kwargs["env"])
            self.assertEqual(os.environ["GH_TOKEN"], "original")
        self.assertEqual(output.getvalue(), "")

    def test_provisioning_failure_never_launches_child(self):
        output = io.StringIO()
        with patch.object(loader, "load_token", side_effect=ValueError("TODO sync credential is not configured.")), patch.object(
            loader.subprocess, "run"
        ) as run, contextlib.redirect_stderr(output):
            self.assertEqual(loader.main(["--", "gh", "api", "user"]), 1)
            run.assert_not_called()
        self.assertIn("not configured", output.getvalue())

    def test_runner_works_from_another_directory_without_printing_fixture_secret(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            scripts = root / "skills" / "manual" / "scripts"
            scripts.mkdir(parents=True)
            runner = scripts / "with_github_token.py"
            shutil.copy2(SPEC.origin, runner)
            (scripts.parent / ".env").write_text("TODO_SYNC_GITHUB_TOKEN=fixture_token", encoding="utf-8")
            other = root / "another-project"
            other.mkdir()
            result = subprocess.run(
                [
                    sys.executable, str(runner), "--", sys.executable, "-c",
                    "import os; assert os.environ['GH_TOKEN'] == 'fixture_token'; "
                    "assert os.environ['TODO_SYNC_GITHUB_TOKEN'] == 'fixture_token'; "
                    "assert 'GH_DEBUG' not in os.environ",
                ],
                cwd=other,
                env={**os.environ, "TODO_SYNC_GITHUB_TOKEN": "stale_token", "GH_DEBUG": "api"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
