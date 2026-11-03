"""Merge verified private snapshots, keeping exactly one object per content hash."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from restore_skill_state import digest, io_path, restore
from package_skill_support import verify_private_boundary


ROOT = Path(__file__).resolve().parents[1]


def merge(inputs: list[Path], destination: Path) -> dict:
    destination = destination.resolve()
    if (ROOT / "migration-private").resolve() not in destination.parents:
        raise ValueError("Merged private snapshots must remain under ignored migration-private.")
    if io_path(destination).exists():
        raise FileExistsError(destination)
    manifests = []
    names = set()
    for source in inputs:
        restore(source)
        manifest = json.loads(io_path(source / "manifest.json").read_text(encoding="utf-8"))
        for collection in manifest["collections"]:
            if collection["name"] in names:
                raise ValueError(f"Duplicate collection across inputs: {collection['name']}")
            names.add(collection["name"])
        manifests.append(manifest)
    objects = destination / "objects"
    io_path(objects).mkdir(parents=True)
    marker = destination / "manifest.json"
    io_path(marker).write_text('{"schemaVersion":1,"complete":false}\n', encoding="utf-8")
    seen = set()
    unique_bytes = 0
    records = destination / "files.jsonl"
    with io_path(records).open("w", encoding="utf-8", newline="\n") as output:
        for source in inputs:
            with io_path(source / "files.jsonl").open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    checksum = row.get("sha256")
                    if checksum and checksum not in seen:
                        os.link(io_path(source / "objects" / checksum), io_path(objects / checksum))
                        seen.add(checksum)
                        unique_bytes += row["bytes"]
                    output.write(line)
    counts = {
        key: sum(manifest["counts"][key] for manifest in manifests)
        for key in ("files", "sourceBytes", "redacted", "excluded")
    }
    counts.update({"uniqueObjects": len(seen), "storedBytes": unique_bytes})
    result = {
        "schemaVersion": 1, "complete": True, "counts": counts,
        "startedAt": min(manifest["startedAt"] for manifest in manifests),
        "collections": [group for manifest in manifests for group in manifest["collections"]],
        "recordsSha256": digest(records),
        "sourceArchives": [source.name for source in inputs],
        "boundary": "PRIVATE. Immutable hash objects; never upload. Per-file live snapshots, not a global transaction. Credential exclusions and limited text redaction are not a guarantee of secret-free historical content.",
    }
    io_path(marker).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"privateBundle": str(destination), **counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_private_boundary(args.output)
    print(json.dumps(merge(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
