"""Inventory referenced local media outside a runtime; never scan unrelated downloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from package_skill_support import excluded_file, files_below

PATTERN = re.compile(
    r"""(?i)([a-z]:[\\/][^"'<>|\r\n]*?\.(?:mp4|mov|mkv|webm|m4a|wav|mp3|flac|png|jpe?g|svg|gif|webp|onnx|safetensors))(?=["'\s,;)]|$)"""
)


def discover(roots: list[Path], allowed: list[Path]) -> dict:
    found = {}
    missing = set()
    for root in roots:
        for path in files_below(root):
            if excluded_file(path) or path.suffix.lower() not in {".json", ".jsonl", ".md", ".py", ".ps1", ".txt"}:
                continue
            if path.stat().st_size > 20 * 1024 * 1024:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in PATTERN.finditer(text):
                candidate = Path(match[1].replace("\\\\", "\\"))
                if not any(candidate.is_relative_to(base) for base in allowed):
                    continue
                if candidate.is_file():
                    found[str(candidate)] = candidate.stat().st_size
                else:
                    missing.add(str(candidate))
    collections = [
        {"name": "referenced-input-" + hashlib.sha256(name.lower().encode()).hexdigest()[:16], "source": name}
        for name in sorted(found)
    ]
    return {
        "private": collections, "bytes": sum(found.values()),
        "missingReferencedInputs": sorted(missing),
        "boundary": "Only existing media explicitly referenced in the supplied roots and inside the allowed input roots.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, action="append", required=True)
    parser.add_argument("--allow", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = discover(args.scan, args.allow)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"referencedInputs": len(result["private"]), "bytes": result["bytes"], "missingReferences": len(result["missingReferencedInputs"])}))


if __name__ == "__main__":
    main()
