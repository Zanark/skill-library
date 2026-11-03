import json
import tempfile
import unittest
from pathlib import Path

from documentation_mesh.cli import initialize
from documentation_mesh.core import (
    build,
    json_for_script,
    parse_document,
    redact,
    validate_config,
)


class DocumentationMeshRuntimeTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "Guides").mkdir(parents=True)
        (root / "README.md").write_text(
            """---
title: Fixture Home
owner: Docs Team
tags: [fixture, home]
---
# Fixture Home

See [Guide](Guides/Guide%20One.md#setup).

```markdown
[Not a relationship](Missing.md)
```
""",
            encoding="utf-8",
        )
        (root / "Guides" / "Guide One.md").write_text(
            """# Guide One

## Setup

Run `az account show`.

See also [Home](../README.md).
""",
            encoding="utf-8",
        )
        (root / "Guides" / "Broken.md").write_text(
            "# Broken\n\n[Missing](Missing.md)\n",
            encoding="utf-8",
        )
        (root / "toc.yml").write_text(
            "- name: Home\n  href: README.md\n- name: Guides\n  items:\n    - name: Guide One\n      href: Guides/Guide One.md\n",
            encoding="utf-8",
        )

    def test_build_and_cache_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            workspace = base / "workspace"
            source.mkdir()
            self.fixture(source)
            config = initialize(source, workspace)
            first, first_paths = build(config)
            self.assertEqual(3, first["statistics"]["documentCount"])
            self.assertEqual(3, first["statistics"]["cacheReparsed"])
            self.assertTrue(first_paths["html"].is_file())
            self.assertTrue(any(edge["shownByDefault"] for edge in first["graph"]["edges"]))
            self.assertTrue(any(finding["type"] == "broken-link" for finding in first["healthFindings"]))
            second, _ = build(config)
            self.assertEqual(3, second["statistics"]["cacheReused"])
            self.assertEqual(0, second["statistics"]["cacheReparsed"])
            (source / "Guides" / "Broken.md").write_text(
                "# Broken\n\n[Home](../README.md)\n",
                encoding="utf-8",
            )
            third, _ = build(config)
            self.assertEqual(2, third["statistics"]["cacheReused"])
            self.assertEqual(1, third["statistics"]["cacheReparsed"])

    def test_code_fence_links_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "README.md"
            path.write_text("# Home\n\n```\n[Fake](Missing.md)\n```\n", encoding="utf-8")
            config = {"generatedDocumentGlobs": [], "archivedDocumentGlobs": []}
            document = parse_document(path, root, "root", config)
            self.assertEqual([], document["links"])

    def test_workspace_cannot_be_inside_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "README.md").write_text("# Home\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                initialize(source, source / "generated")

    def test_output_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            workspace = base / "workspace"
            source.mkdir()
            workspace.mkdir()
            config_path = workspace / "config.json"
            config = {
                "schemaVersion": 1,
                "sourceRoots": [str(source)],
                "includeGlobs": ["**/*.md"],
                "excludeGlobs": [],
                "outputDirectory": "../escape",
                "cachePath": "output/cache.json",
                "runtimeVersion": "0.1.0",
                "pluginVersion": "0.1.0",
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validate_config(config, config_path)

    def test_secret_and_script_escaping(self):
        self.assertEqual("token=[redacted]", redact("token=do-not-keep"))
        payload = json_for_script({"value": "</script>\u2028\u2029"})
        self.assertNotIn("<", payload)
        self.assertIn("\\u2028", payload)
        self.assertIn("\\u2029", payload)


if __name__ == "__main__":
    unittest.main()
