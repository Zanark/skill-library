import csv
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "folder-heatmap" / "scripts" / "folder_heatmap.py"
spec = importlib.util.spec_from_file_location("folder_heatmap", SCRIPT)
heatmap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(heatmap)


class FolderHeatmapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "input"
        self.root.mkdir()
        self.output = self.base / "report"

    def test_nested_hidden_empty_and_direct_totals_and_exports(self):
        (self.root / "root.bin").write_bytes(b"123")
        (self.root / ".hidden").mkdir()
        (self.root / ".hidden" / "nested").mkdir()
        (self.root / ".hidden" / "nested" / "child.bin").write_bytes(b"45678")
        (self.root / "empty").mkdir()
        data = heatmap.scan(self.root)
        self.assertEqual(data["nodes"][0]["size"], 8)
        self.assertEqual(data["nodes"][0]["direct"], 3)
        self.assertEqual(data["nodes"][0]["files"], 2)
        self.assertEqual(data["errors"], [])
        self.assertEqual(len(data["nodes"]), 4)
        result = heatmap.save(data, self.output)
        self.assertEqual(Path(result["report"]), self.output / "index.html")
        self.assertEqual(json.loads((self.output / "snapshot.json").read_text()),
                         json.loads(json.dumps(data)))
        with (self.output / "folder-sizes.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 4)
        child = next(row for row in rows if row["Full path"].endswith("nested"))
        self.assertEqual(child["Full path"], str(self.root / ".hidden" / "nested"))
        self.assertEqual(child["Total bytes"], "5")
        self.assertEqual(child["Recursive file count"], "1")

    def test_top_twenty_files_do_not_truncate_totals(self):
        for i in range(25):
            (self.root / f"{i:02}.bin").write_bytes(b"x" * i)
        node = heatmap.scan(self.root)["nodes"][0]
        self.assertEqual(node["files"], 25)
        self.assertEqual(node["size"], sum(range(25)))
        self.assertEqual(len(node["largest"]), 20)
        self.assertEqual(node["largest"][0], (24, "24.bin"))
        self.assertEqual(node["largest"][-1], (5, "05.bin"))

    def test_links_are_excluded_and_linked_root_rejected(self):
        external = self.base / "external"
        external.mkdir()
        (external / "outside.bin").write_bytes(b"not in scope")
        link = self.root / "linked"
        try:
            link.symlink_to(external, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Creating symlinks is not permitted: {exc}")
        data = heatmap.scan(self.root)
        self.assertEqual(data["nodes"][0]["size"], 0)
        self.assertEqual(len(data["nodes"]), 1)
        self.assertEqual(data["skipped"][0]["path"], str(link))
        with self.assertRaisesRegex(ValueError, "root must not be a link"):
            heatmap.scan(link)

    def test_windows_reparse_point_is_not_traversed(self):
        info = type("Info", (), {"st_mode": 0o040755, "st_file_attributes": 0x400})()
        entry = type("Entry", (), {"path": str(self.root / "junction"), "stat": lambda *a, **k: info})()
        with patch.object(heatmap.os, "scandir") as scandir:
            scandir.return_value.__enter__.return_value = [entry]
            data = heatmap.scan(self.root)
        self.assertEqual(len(data["nodes"]), 1)
        self.assertEqual(len(data["skipped"]), 1)

    def test_partial_scan_reports_the_exact_error_and_exit_two(self):
        real_scan = heatmap.os.scandir
        denied = self.root / "denied"
        denied.mkdir()

        def guarded_scan(path):
            if Path(path) == denied:
                raise PermissionError("fixture permission denied")
            return real_scan(path)

        with patch.object(heatmap.os, "scandir", side_effect=guarded_scan):
            with redirect_stdout(io.StringIO()) as stdout:
                code = heatmap.main(["--root", str(self.root), "--output", str(self.output)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "partial")
        data = json.loads((self.output / "snapshot.json").read_text())
        self.assertEqual(data["errors"], [{"path": str(denied), "error": "fixture permission denied"}])

    def test_invalid_root_and_output_boundaries_fail_before_writing(self):
        for root, output in [(self.root / "missing", self.output),
                             (self.root, self.root), (self.root, self.root / "report")]:
            with self.subTest(root=root, output=output), redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(heatmap.main(["--root", str(root), "--output", str(output)]), 1)
                self.assertIn("Folder heatmap failed:", stderr.getvalue())
        self.assertFalse((self.root / "report").exists())

    def test_empty_root_and_refresh_recount_moved_files(self):
        arguments = ["--root", str(self.root), "--output", str(self.output)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(heatmap.main(arguments), 0)
        (self.output / "keep.txt").write_text("unrelated", encoding="utf-8")
        (self.root / "moved.bin").write_bytes(b"new")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(heatmap.main(arguments), 0)
        self.assertEqual(json.loads((self.output / "snapshot.json").read_text())["nodes"][0]["size"], 3)
        self.assertEqual((self.output / "keep.txt").read_text(), "unrelated")

    def test_report_escapes_embedded_script_like_names(self):
        data = heatmap.scan(self.root)
        data["nodes"][0]["name"] = "</script><script>window.injected=true</script>"
        heatmap.save(data, self.output)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", html, re.S)
        self.assertEqual(len(scripts), 2)
        self.assertEqual(json.loads(scripts[0])["nodes"][0]["name"], data["nodes"][0]["name"])
        self.assertNotIn("</script>", scripts[0])

    def test_inconsistent_totals_and_browser_failures_are_explicit(self):
        data = heatmap.scan(self.root)
        data["nodes"][0]["size"] = 1
        with self.assertRaisesRegex(ValueError, "totals"):
            heatmap.save(data, self.output)
        self.assertFalse(self.output.exists())
        with patch.object(heatmap.webbrowser, "open", return_value=False), redirect_stderr(io.StringIO()) as stderr:
            with redirect_stdout(io.StringIO()):
                code = heatmap.main(["--root", str(self.root), "--output", str(self.output), "--open"])
        self.assertEqual(code, 1)
        self.assertIn("Could not open browser", stderr.getvalue())
        self.assertTrue((self.output / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
