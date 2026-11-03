"""Collect approved support source and a separate, content-addressed private migration bundle."""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from urllib.parse import quote

from restore_skill_state import io_path, logical_path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
SECRET_NAMES = {
    ".npmrc", ".pypirc", "auth.json", "credentials.json", "credentials",
    "token", "tokens.json", "permissions.json", "trusted_folders.json",
}
SECRET_SUFFIXES = {".pem", ".pfx", ".p12", ".key"}
PROCESS_LOCK_NAMES = {"server.lock", "session.lock", "daemon.lock"}
TOKEN_PATTERN = re.compile(
    r"(?<![\w-])(?:github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"AKIA[A-Z0-9]{16})(?![\w-])"
)
ASSIGNMENT_PATTERN = re.compile(
    r"""(?i)(["']?(?:password|client_secret|api_key|access_token|refresh_token)["']?\s*[:=]\s*["'])([^"'\r\n]{6,})(["'])"""
)


def write_json(path: Path, value: object) -> None:
    path = io_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    with io_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_private_boundary(destination: Path) -> None:
    relative = destination.resolve().relative_to(ROOT.resolve())
    subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "--quiet", str(relative)],
        check=True,
    )
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "migration-private"],
        check=True, capture_output=True,
    )
    if tracked.stdout:
        raise ValueError("Private migration files are already tracked by Git; stop and inspect before exporting.")


def excluded_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        name in SECRET_NAMES or name.startswith(".env") or path.suffix.lower() in SECRET_SUFFIXES
        or "permission" in name.lower() or "trust-policy" in name.lower()
    )


def files_below(root: Path, extra_skip: set[str] | None = None, excluded=None):
    for base, directories, filenames in os.walk(io_path(root), followlinks=False):
        base = logical_path(Path(base))
        retained = []
        for name in sorted(directories):
            path = Path(base) / name
            if name in SKIP_DIRS | (extra_skip or set()) or io_path(path).is_junction() or io_path(path).is_symlink():
                if excluded:
                    excluded(path, "Recreatable dependency/cache directory or directory link.")
            else:
                retained.append(name)
        directories[:] = retained
        for name in sorted(filenames):
            yield Path(base) / name


def public_check(path: Path) -> None:
    if excluded_file(path):
        raise ValueError(f"Sensitive filename in proposed public payload: {path.name}")
    if path.suffix.lower() in {".exe", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ico"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    if TOKEN_PATTERN.search(text):
        raise ValueError(f"Credential-shaped token in proposed public payload: {path}")
    for match in ASSIGNMENT_PATTERN.finditer(text):
        value = match[2].lower()
        if not any(marker in value for marker in ("example", "redacted", "placeholder", "test", "${", "<", "{")):
            raise ValueError(f"Review credential assignment before public inclusion: {path}")


def public_copy(source: Path, destination: Path, exclude_names: set[str] | None = None) -> int:
    count = 0
    candidates = [source] if source.is_file() else files_below(source, {"bin", "obj", "build", "dist"})
    for path in candidates:
        if path.name in (exclude_names or set()):
            continue
        if excluded_file(path):
            raise ValueError(f"Unexpected private configuration in public source selection: {path}")
        public_check(path)
        relative = Path(path.name) if source.is_file() else path.relative_to(source)
        target = destination if source.is_file() else destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != path.read_bytes():
            raise FileExistsError(f"Refusing to overwrite an existing different support file: {target}")
        if not target.exists():
            shutil.copy2(path, target)
        count += 1
    return count


def package_public(config: dict) -> None:
    copied = {}
    for group in config["public"]:
        source = Path(os.path.expandvars(group["source"]))
        destination = (ROOT / group["destination"]).resolve()
        if ROOT.resolve() not in destination.parents:
            raise ValueError(f"Public destination must be inside the repository: {destination}")
        if not source.exists():
            raise FileNotFoundError(f"Missing support source: {source}")
        copied[group["destination"]] = public_copy(source, destination, set(group.get("excludeNames", [])))
    write_json(ROOT / "support-provenance.json", {
        "schemaVersion": 1,
        "boundary": "Approved implementation source only. Private state and internal zmem stay outside Git.",
        "collections": [{"destination": name, "files": count} for name, count in copied.items()],
        "maintainedInRepository": [
            "skills\\context-mesh\\implementation",
            "skills\\clipfarm-leetcode\\implementation\\README.md",
            "skills\\clipfarm-leetcode\\implementation\\AGENTS.md",
            "skills\\clipfarm-leetcode\\implementation\\constraints-windows-py313.txt",
            "skills\\clipfarm-leetcode\\implementation\\docs",
            "skills\\clipfarm-leetcode\\implementation\\TODO",
            "examples\\context-mesh",
        ],
    })
    print(json.dumps({"publicSupportFiles": sum(copied.values()), "collections": copied}, indent=2), flush=True)


def redact_private(path: Path, data: bytes) -> tuple[bytes, bool]:
    if b"\x00" in data[:4096] or len(data) > 20 * 1024 * 1024:
        return data, False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data, False
    cleaned = TOKEN_PATTERN.sub("[REDACTED]", text)
    cleaned = ASSIGNMENT_PATTERN.sub(lambda match: match[1] + "[REDACTED]" + match[3], cleaned)
    return cleaned.encode("utf-8"), cleaned != text


def collect_private(config: dict, destination: Path, *, resume: bool = False) -> None:
    destination = destination.resolve()
    private_root = (ROOT / "migration-private").resolve()
    if private_root not in destination.parents:
        raise ValueError("Private exports must be inside the repository's ignored migration-private directory.")
    if io_path(destination).exists():
        marker = destination / "manifest.json"
        if not resume or not io_path(marker).is_file() or json.loads(io_path(marker).read_text(encoding="utf-8")).get("complete") is not False:
            raise FileExistsError(f"Use a new export directory or resume an incomplete export: {destination}")
    objects = destination / "objects"
    io_path(objects).mkdir(parents=True, exist_ok=resume)
    records = destination / "files.jsonl"
    counts = {"files": 0, "sourceBytes": 0, "storedBytes": 0, "uniqueObjects": 0, "redacted": 0, "excluded": 0}
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    seen_objects: set[str] = set()
    write_json(destination / "manifest.json", {"schemaVersion": 1, "complete": False, "startedAt": started})
    try:
        with io_path(records).open("w", encoding="utf-8", newline="\n") as log:
            collections = list(config["private"])
            if config.get("contextIndex"):
                index = json.loads(Path(config["contextIndex"]).read_text(encoding="utf-8"))
                collections.extend(
                    {"name": f"context-{context['id']}", "source": context["storePath"]}
                    for context in index["contexts"]
                )
            for collection in collections:
                print(json.dumps({"collecting": collection["name"]}), flush=True)
                source = Path(os.path.expandvars(collection["source"])).resolve()
                if not io_path(source).exists():
                    if collection.get("optional"):
                        log.write(json.dumps({"collection": collection["name"], "missingOptional": True}) + "\n")
                        continue
                    raise FileNotFoundError(f"Required private collection missing: {source}")
                source_is_file = io_path(source).is_file()
                def excluded_directory(path, reason):
                    log.write(json.dumps({
                        "collection": collection["name"], "path": str(path.relative_to(source)),
                        "excluded": reason, "directory": True,
                    }) + "\n")
                    counts["excluded"] += 1

                paths = [source] if source_is_file else files_below(
                    source, set(collection.get("skipDirectories", [])), excluded_directory,
                )
                for path in paths:
                    relative = path.name if source_is_file else str(path.relative_to(source))
                    record = {"collection": collection["name"], "path": relative}
                    sqlite_sidecar = False
                    for suffix in ("-wal", "-shm", "-journal"):
                        if path.name.endswith(suffix):
                            database = path.with_name(path.name[:-len(suffix)])
                            if io_path(database).is_file():
                                with io_path(database).open("rb") as header:
                                    sqlite_sidecar = header.read(16) == b"SQLite format 3\x00"
                            break
                    if path.name.lower() in PROCESS_LOCK_NAMES or re.fullmatch(r"inuse\.\d+\.hold", path.name):
                        record["excluded"] = "Live process ownership lock; never transfer another process's lock."
                        counts["excluded"] += 1
                    elif not stat.S_ISREG(io_path(path).stat().st_mode):
                        record["excluded"] = "Live IPC endpoint or other non-regular file; recreated by its runtime."
                        counts["excluded"] += 1
                    elif sqlite_sidecar:
                        record["excluded"] = "SQLite sidecar: committed data is preserved by the online database snapshot."
                        counts["excluded"] += 1
                    elif excluded_file(path):
                        record["excluded"] = "Credential, trust or permission material; reauthenticate on the new machine."
                        counts["excluded"] += 1
                    else:
                        for attempt in range(3):
                            before = io_path(path).stat()
                            fd, temporary_name = tempfile.mkstemp(dir=io_path(destination), prefix=".collect-")
                            os.close(fd)
                            temporary = Path(temporary_name)
                            try:
                                with io_path(path).open("rb") as header:
                                    sqlite_database = header.read(16) == b"SQLite format 3\x00"
                                if sqlite_database:
                                    deadline = time.monotonic() + 30

                                    def backup_progress(status, remaining, total):
                                        if time.monotonic() > deadline:
                                            raise TimeoutError(f"SQLite snapshot remained busy or exceeded 30 seconds: {path}")

                                    uri = "file:" + quote(str(io_path(path)), safe="") + "?mode=ro"
                                    with closing(sqlite3.connect(uri, uri=True)) as original:
                                        with closing(sqlite3.connect(temporary)) as snapshot:
                                            original.backup(snapshot, pages=256, progress=backup_progress)
                                else:
                                    shutil.copyfile(io_path(path), temporary)
                                after = io_path(path).stat()
                                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                                    if attempt == 2:
                                        raise RuntimeError(f"Source kept changing during export: {path}")
                                    continue
                                redacted = False
                                if temporary.stat().st_size <= 20 * 1024 * 1024:
                                    data, redacted = redact_private(path, temporary.read_bytes())
                                    if redacted:
                                        temporary.write_bytes(data)
                                checksum = digest(temporary)
                                blob = io_path(objects / checksum)
                                size = temporary.stat().st_size
                                if not blob.exists():
                                    temporary.replace(blob)
                                elif checksum not in seen_objects and digest(blob) != checksum:
                                    raise ValueError(f"Corrupt existing private object: {checksum}")
                                if checksum not in seen_objects:
                                    seen_objects.add(checksum)
                                    counts["storedBytes"] += size
                                    counts["uniqueObjects"] += 1
                                record.update({"sha256": checksum, "bytes": size, "redacted": redacted})
                                counts["files"] += 1
                                counts["sourceBytes"] += before.st_size
                                counts["redacted"] += int(redacted)
                                break
                            except PermissionError as error:
                                raise PermissionError(f"Unable to read or snapshot this source: {path}") from error
                            finally:
                                temporary.unlink(missing_ok=True)
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    if counts["files"] and counts["files"] % 1000 == 0:
                        log.flush()
                        print(json.dumps({"privateProgress": counts}), flush=True)
        write_json(destination / "manifest.json", {
            "schemaVersion": 1, "complete": True, "startedAt": started, "counts": counts,
            "collections": collections,
            "boundary": "PRIVATE. Never add to Git. Excluded credentials/trust settings are not portable. Source applications were not stopped.",
            "recordsSha256": digest(records),
        })
    except Exception:
        print(f"Private export incomplete; preserve {destination} for diagnosis.", flush=True)
        raise
    print(json.dumps({"privateBundle": str(destination), **counts}, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--private", type=Path)
    parser.add_argument("--resume", action="store_true", help="Restart an incomplete export, reusing verified objects.")
    args = parser.parse_args()
    config = json.loads(args.sources.read_text(encoding="utf-8"))
    if args.public:
        package_public(config)
    if args.private:
        verify_private_boundary(args.private)
        collect_private(config, args.private, resume=args.resume)


if __name__ == "__main__":
    main()
