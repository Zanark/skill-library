"""Exercise the packaged self-contained EXE with new, fictional Markdown input."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    executable = args.runtime / "documentation-mesh" / "runtime" / "windows-x64" / "documentation-mesh.exe"
    with tempfile.TemporaryDirectory(prefix="skill-docs-smoke-") as directory:
        root = Path(directory)
        source = root / "input"
        source.mkdir()
        (source / "README.md").write_text("# Fictional library\n\nSee [guide](guide.md).\n", encoding="utf-8")
        (source / "guide.md").write_text("# Fictional guide\n\nA complete portable example.\n", encoding="utf-8")
        workspace = root / "workspace"
        subprocess.run([str(executable), "init", "--source", str(source), "--workspace", str(workspace)], check=True)
        subprocess.run([str(executable), "build", "--config", str(workspace / "config.json"), "--validate"], check=True)
        index = workspace / "output" / "documentation-index.json"
        subprocess.run([str(executable), "validate", "--index", str(index)], check=True)
        if not (workspace / "output" / "documentation-mesh.html").is_file():
            raise RuntimeError("The self-contained runtime did not generate its dashboard.")
        print(json.dumps({"selfContainedDocumentationRuntime": True, "fictionalInput": True}))


if __name__ == "__main__":
    main()
