import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PluginContractTests(unittest.TestCase):
    def test_manifests_are_consistent(self):
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        agency = json.loads((ROOT / "agency.json").read_text(encoding="utf-8"))
        self.assertEqual("documentation-mesh", plugin["name"])
        self.assertEqual("0.1.0", plugin["version"])
        self.assertEqual(["copilot"], agency["engines"])
        self.assertEqual(["windows"], agency["platforms"])
        self.assertFalse((ROOT / ".claude-plugin" / "plugin.json").exists())

    def test_skill_contract_and_runtime_references(self):
        skill = (ROOT / "skills" / "documentation-mesh" / "SKILL.md").read_text(encoding="utf-8")
        for trigger in (
            "create documentation mesh",
            "build docs graph",
            "analyse Markdown collection",
            "EngHub documentation report",
            "refresh documentation mesh",
        ):
            self.assertIn(trigger, skill)
        self.assertIn("read-only", skill)
        self.assertIn("documentation-mesh build", skill)
        self.assertFalse(
            re.search(
                r"\b(?:npm|pip|winget|choco|apt|brew)\s+(?:install|add)\b",
                skill,
                flags=re.I,
            )
        )

    def test_required_payload_files_exist(self):
        required = [
            "plugin.json",
            "agency.json",
            "README.md",
            "LICENSE",
            "skills/documentation-mesh/SKILL.md",
            "templates/config.default.json",
            "templates/dashboard/dashboard.css",
            "templates/dashboard/dashboard.js",
            "templates/dashboard/vendor.min.js",
            "schemas/config.schema.json",
            "schemas/documentation-index.schema.json",
            "packaging/agency.artifact.template.json",
            "src/DocumentationMesh.Runtime/DocumentationMesh.Runtime.csproj",
            "src/DocumentationMesh.Runtime/Program.cs",
            "tests/consumer-contract.ps1",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_versions_agree(self):
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        config = json.loads((ROOT / "templates" / "config.default.json").read_text(encoding="utf-8"))
        init_source = (ROOT / "src" / "documentation_mesh" / "__init__.py").read_text(encoding="utf-8")
        runtime_version = re.search(r'VERSION\s*=\s*"([^"]+)"', init_source).group(1)
        self.assertEqual(plugin["version"], runtime_version)
        self.assertEqual(plugin["version"], config["runtimeVersion"])
        self.assertEqual(plugin["version"], config["pluginVersion"])

    def test_official_runtime_build_uses_dotnet_not_pyinstaller(self):
        build = (ROOT / "packaging" / "build-runtime.ps1").read_text(encoding="utf-8")
        self.assertIn("dotnet publish", build)
        self.assertIn("--self-contained true", build)
        self.assertIn("PublishSingleFile=true", build)
        self.assertNotIn("pyinstaller", build.lower())


if __name__ == "__main__":
    unittest.main()
