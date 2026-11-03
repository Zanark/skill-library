"""Verify and restore a private CAS archive into a NEW, isolated directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil


def io_path(path: Path) -> Path:
    value = str(path.absolute())
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        value = "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
    return Path(value)


def logical_path(path: Path) -> Path:
    value = str(path)
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def digest(path: Path) -> str:
    with io_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative_path(collection: str, value: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", collection):
        raise ValueError(f"Invalid collection name: {collection!r}")
    path = PureWindowsPath(value)
    if path.drive or path.root or not path.parts or ".." in path.parts or any(
        ":" in p or (os.name == "nt" and os.path.isreserved(p)) for p in path.parts
    ):
        raise ValueError(f"Unsafe archive path: {value!r}")
    return Path(collection, *path.parts)


def restore(bundle: Path, destination: Path | None = None) -> dict:
    bundle = bundle.resolve()
    manifest = json.loads(io_path(bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1 or manifest.get("complete") is not True:
        raise ValueError("Only a complete version-1 private archive can be restored.")
    records = bundle / "files.jsonl"
    if digest(records) != manifest["recordsSha256"]:
        raise ValueError("The private file catalogue checksum does not match.")
    if destination is not None:
        destination = destination.resolve()
        if io_path(destination).exists():
            raise FileExistsError(f"Restoration requires a new destination: {destination}")
        if bundle == destination or bundle in destination.parents:
            raise ValueError("Do not restore into the source archive.")
    objects = bundle / "objects"
    checked: set[str] = set()
    paths: set[Path] = set()
    files = 0
    with io_path(records).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if "sha256" not in row:
                continue
            target = relative_path(row["collection"], row["path"])
            if target in paths:
                raise ValueError(f"Duplicate target in archive: {target}")
            paths.add(target)
            checksum = row["sha256"]
            if not re.fullmatch("[0-9a-f]{64}", checksum):
                raise ValueError("Invalid archive object name.")
            blob = io_path(objects / checksum)
            if blob.is_symlink() or not blob.is_file() or blob.stat().st_size != row["bytes"]:
                raise ValueError(f"Missing, linked or incorrectly sized object: {checksum}")
            if checksum not in checked:
                if digest(blob) != checksum:
                    raise ValueError(f"Corrupt archive object: {checksum}")
                checked.add(checksum)
            files += 1
    if files != manifest["counts"]["files"] or len(checked) != manifest["counts"]["uniqueObjects"]:
        raise ValueError("The archive file/object counts do not match its catalogue.")
    if destination is not None:
        io_path(destination).mkdir(parents=True)
        with io_path(records).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if "sha256" not in row:
                    continue
                target = io_path(destination / relative_path(row["collection"], row["path"]))
                target.parent.mkdir(parents=True, exist_ok=True)
                # Never create links or overwrite an existing file.
                with io_path(objects / row["sha256"]).open("rb") as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
    return {"verifiedFiles": files, "verifiedObjects": len(checked), "restoredTo": str(destination) if destination else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.bundle, args.output), indent=2))


if __name__ == "__main__":
    main()
