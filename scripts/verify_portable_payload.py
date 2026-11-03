"""Build or verify the public, repository-relative payload checksum catalogue."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = "portable-files.json"
PRIVATE = {".agent-context", "migration-private", ".skill-library-runtime"}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(root: Path) -> dict:
    paths = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True, capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    files = []
    for name in sorted(set(paths)):
        if not name or name == CATALOGUE or Path(name).parts[0] in PRIVATE:
            continue
        path = root / name
        if path.is_file():
            files.append({"path": name.replace("/", "\\"), "bytes": path.stat().st_size, "sha256": digest(path)})
    result = {"schemaVersion": 1, "scope": "Public payload only; no private state or authentication.", "files": files}
    (root / CATALOGUE).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"publicFiles": len(files), "publicBytes": sum(row["bytes"] for row in files)}


def verify(root: Path) -> dict:
    catalogue = json.loads((root / CATALOGUE).read_text(encoding="utf-8"))
    if catalogue["schemaVersion"] != 1:
        raise ValueError("Unsupported public catalogue schema.")
    for row in catalogue["files"]:
        path = (root / row["path"]).resolve()
        if root.resolve() not in path.parents or path.relative_to(root.resolve()).parts[0] in PRIVATE:
            raise ValueError("Unsafe path in public catalogue.")
        if not path.is_file() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"Public payload mismatch: {row['path']}")
    return {"verifiedPublicFiles": len(catalogue["files"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()) if args.build else verify(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
