from __future__ import annotations

import fnmatch
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import VERSION


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SETEXT_RE = re.compile(r"^\s*(=+|-+)\s*$")
INLINE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
REFERENCE_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)")
HTML_LINK_RE = re.compile(r"<a\b[^>]*\bhref=[\"']([^\"']+)[\"']", re.I)
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
SECRET_RE = re.compile(
    r"(?i)\b(token|password|secret|api[_ -]?key|authorization|connectionstring|sas)\b"
    r"\s*[:=]\s*([^\s,;]+)"
)
CODE_PATH_RE = re.compile(
    r"(?i)(?<![\w])(?:[a-z]:\\|\.{0,2}[\\/])[^`\"'<>\r\n]+?\."
    r"(?:cs|ts|tsx|js|jsx|py|go|rs|java|cpp|c|h|hpp|ps1|sh|json|ya?ml|xml|sql|kql)"
)
ADO_RE = re.compile(r"https?://[^)\s]+/_workitems/edit/(\d+)", re.I)
PR_RE = re.compile(r"https?://[^)\s]+/pullrequest/(\d+)", re.I)
ICM_RE = re.compile(r"https?://portal\.microsofticm\.com/[^)\s]*/incidents/details/(\d+)", re.I)
COMMAND_RE = re.compile(
    r"(?<![\w-])(?:az|git|dotnet|npm|npx|python|python3|pwsh|powershell|kubectl|helm|curl)\s+"
    r"[^`\r\n]{1,160}",
    re.I,
)
STATUS_WORDS = {
    "deprecated": "deprecated",
    "archived": "archived",
    "archive": "archived",
    "draft": "draft",
    "generated": "generated",
    "active": "active",
}
EDGE_CLASSES = {"explicit", "structural", "inferred", "incidental"}
CONFIDENCE_LEVELS = {"high", "medium", "low", "unknown"}


def runtime_root() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def canonical(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def redact(value: str, limit: int = 480) -> str:
    value = SECRET_RE.sub(lambda match: f"{match.group(1)}=[redacted]", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."


def slugify(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[^\w\s-]", "", value.lower(), flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", value).strip("-")


def path_matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for raw_pattern in patterns:
        pattern = raw_pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(normalized, pattern[3:]):
            return True
    return False


def atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        if isinstance(content, bytes):
            temporary.write_bytes(content)
        else:
            temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return value


def resolve_workspace_path(config_path: Path, value: str) -> Path:
    candidate = Path(os.path.expanduser(value))
    if not candidate.is_absolute():
        candidate = config_path.parent / candidate
    return candidate.resolve()


def validate_config(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    required = {
        "schemaVersion",
        "sourceRoots",
        "includeGlobs",
        "excludeGlobs",
        "outputDirectory",
        "cachePath",
        "runtimeVersion",
        "pluginVersion",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise RuntimeError(f"Configuration is missing required keys: {', '.join(missing)}")
    if config["schemaVersion"] != 1:
        raise RuntimeError(f"Unsupported config schemaVersion: {config['schemaVersion']}")
    if not isinstance(config["sourceRoots"], list) or not config["sourceRoots"]:
        raise RuntimeError("sourceRoots must contain at least one directory")
    source_roots = [resolve_workspace_path(config_path, str(value)) for value in config["sourceRoots"]]
    missing_roots = [str(path) for path in source_roots if not path.is_dir()]
    if missing_roots:
        raise RuntimeError(f"Source roots do not exist: {', '.join(missing_roots)}")
    workspace = config_path.parent.resolve()
    output = resolve_workspace_path(config_path, str(config["outputDirectory"]))
    cache = resolve_workspace_path(config_path, str(config["cachePath"]))
    try:
        output.relative_to(workspace)
        cache.relative_to(workspace)
    except ValueError as error:
        raise RuntimeError("Output and cache paths must remain inside the generated workspace") from error
    if any(workspace == root or workspace.is_relative_to(root) for root in source_roots):
        raise RuntimeError("Generated workspace must not be inside a configured source root")
    result = dict(config)
    result["_configPath"] = str(config_path.resolve())
    result["_workspace"] = str(workspace)
    result["_sourceRoots"] = source_roots
    result["_output"] = output
    result["_cache"] = cache
    return result


def parse_frontmatter(lines: list[str]) -> tuple[dict[str, Any], int, list[str]]:
    if not lines or lines[0].strip() != "---":
        return {}, 0, []
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), -1)
    if end < 0:
        return {}, 0, ["Unclosed YAML frontmatter"]
    values: dict[str, Any] = {}
    warnings: list[str] = []
    current_list: str | None = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list:
            values.setdefault(current_list, []).append(stripped[2:].strip().strip("\"'"))
            continue
        if ":" not in line:
            warnings.append(f"Unparsed frontmatter line: {redact(line, 120)}")
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            continue
        if not raw:
            values[key] = []
            current_list = key
        elif raw.startswith("[") and raw.endswith("]"):
            values[key] = [item.strip().strip("\"'") for item in raw[1:-1].split(",") if item.strip()]
            current_list = None
        elif raw.lower() in {"true", "false"}:
            values[key] = raw.lower() == "true"
            current_list = None
        else:
            values[key] = raw.strip("\"'")
            current_list = None
    return values, end + 1, warnings


def line_evidence(relative_path: str, line: int, text: str, end_line: int | None = None) -> dict[str, Any]:
    return {
        "sourceFile": relative_path,
        "lineStart": line,
        "lineEnd": end_line or line,
        "excerpt": redact(text),
    }


def parse_document(path: Path, root: Path, root_name: str, config: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    relative = path.relative_to(root).as_posix()
    collection_path = f"{root_name}/{relative}"
    frontmatter, content_start, warnings = parse_frontmatter(lines)
    headings: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    code_references: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    work_items: list[dict[str, Any]] = []
    pull_requests: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    reference_defs: dict[str, tuple[str, int, str]] = {}
    fence = False
    fence_marker = ""
    mermaid_count = 0
    current_heading = ""
    current_heading_line = 0
    body_lines: list[str] = []

    for index, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        fence_match = re.match(r"^\s*(```+|~~~+)\s*([A-Za-z0-9_-]*)", raw)
        if fence_match:
            marker = fence_match.group(1)[0]
            if not fence:
                fence = True
                fence_marker = marker
                if fence_match.group(2).lower() == "mermaid":
                    mermaid_count += 1
            elif marker == fence_marker:
                fence = False
                fence_marker = ""
            continue
        if fence:
            continue
        if index <= content_start:
            continue
        heading = HEADING_RE.match(raw)
        if heading:
            current_heading = re.sub(r"\s+\{#.*\}\s*$", "", heading.group(2)).strip()
            current_heading_line = index
            headings.append(
                {
                    "id": stable_id("sec", f"{collection_path}#{slugify(current_heading)}"),
                    "documentId": stable_id("doc", canonical(collection_path)),
                    "level": len(heading.group(1)),
                    "title": current_heading,
                    "anchor": slugify(current_heading),
                    "line": index,
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
            continue
        if index > 1 and SETEXT_RE.match(raw) and lines[index - 2].strip():
            current_heading = lines[index - 2].strip()
            current_heading_line = index - 1
            headings.append(
                {
                    "id": stable_id("sec", f"{collection_path}#{slugify(current_heading)}"),
                    "documentId": stable_id("doc", canonical(collection_path)),
                    "level": 1 if raw.strip().startswith("=") else 2,
                    "title": current_heading,
                    "anchor": slugify(current_heading),
                    "line": index - 1,
                    "evidence": line_evidence(collection_path, index - 1, lines[index - 2], index),
                }
            )
        definition = REFERENCE_DEF_RE.match(raw)
        if definition:
            reference_defs[definition.group(1).strip().lower()] = (definition.group(2), index, raw)
        for match in IMAGE_RE.finditer(raw):
            images.append(
                {
                    "alt": match.group(1),
                    "target": match.group(2),
                    "line": index,
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
        without_images = IMAGE_RE.sub("", raw)
        for match in INLINE_LINK_RE.finditer(without_images):
            links.append(
                {
                    "label": match.group(1),
                    "target": match.group(2),
                    "line": index,
                    "heading": current_heading,
                    "headingLine": current_heading_line,
                    "syntax": "markdown",
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
        for match in HTML_LINK_RE.finditer(raw):
            links.append(
                {
                    "label": "",
                    "target": match.group(1),
                    "line": index,
                    "heading": current_heading,
                    "headingLine": current_heading_line,
                    "syntax": "html",
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
        for match in WIKI_LINK_RE.finditer(raw):
            links.append(
                {
                    "label": match.group(1),
                    "target": match.group(1),
                    "line": index,
                    "heading": current_heading,
                    "headingLine": current_heading_line,
                    "syntax": "wiki",
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
        for match in REFERENCE_LINK_RE.finditer(raw):
            key = (match.group(2) or match.group(1)).strip().lower()
            links.append(
                {
                    "label": match.group(1),
                    "referenceKey": key,
                    "target": "",
                    "line": index,
                    "heading": current_heading,
                    "headingLine": current_heading_line,
                    "syntax": "reference",
                    "evidence": line_evidence(collection_path, index, raw),
                }
            )
        for match in CODE_PATH_RE.finditer(raw):
            code_references.append(
                {"value": match.group(0), "line": index, "evidence": line_evidence(collection_path, index, raw)}
            )
        for match in COMMAND_RE.finditer(raw):
            commands.append(
                {"value": redact(match.group(0), 180), "line": index, "evidence": line_evidence(collection_path, index, raw)}
            )
        for pattern, target in ((ADO_RE, work_items), (PR_RE, pull_requests), (ICM_RE, incidents)):
            for match in pattern.finditer(raw):
                target.append(
                    {"id": match.group(1), "line": index, "evidence": line_evidence(collection_path, index, raw)}
                )
        if stripped and not stripped.startswith(("#", ">", "|")):
            body_lines.append(stripped)

    for link in links:
        if link.get("referenceKey"):
            definition = reference_defs.get(link["referenceKey"])
            if definition:
                link["target"] = definition[0]
                link["definitionEvidence"] = line_evidence(collection_path, definition[1], definition[2])
            else:
                link["unresolvedReference"] = True

    title = str(frontmatter.get("title") or "").strip()
    if not title and headings:
        title = headings[0]["title"]
    if not title:
        title = path.stem.replace("-", " ").replace("_", " ").strip()
    owner = frontmatter.get("owner") or frontmatter.get("owners") or frontmatter.get("author") or ""
    if isinstance(owner, list):
        owner = ", ".join(str(value) for value in owner)
    tags = frontmatter.get("tags") or []
    if isinstance(tags, str):
        tags = [value.strip() for value in tags.split(",") if value.strip()]
    status = str(frontmatter.get("status") or "").lower()
    if status not in STATUS_WORDS.values():
        lowered = collection_path.lower()
        status = next((value for word, value in STATUS_WORDS.items() if word in lowered), "unknown")
    if path_matches(collection_path, config.get("generatedDocumentGlobs", [])):
        status = "generated"
    elif path_matches(collection_path, config.get("archivedDocumentGlobs", [])):
        status = "archived"
    purpose = next((redact(line, 360) for line in body_lines if len(line) > 35), "")
    summary = " ".join(body_lines[:3])
    doc_id = stable_id("doc", canonical(collection_path))
    family = relative.split("/", 1)[0] if "/" in relative else root_name
    return {
        "id": doc_id,
        "title": title,
        "sourceRoot": str(root),
        "rootName": root_name,
        "relativePath": relative,
        "collectionPath": collection_path,
        "absolutePath": str(path),
        "fileType": path.suffix.lower().lstrip("."),
        "family": family,
        "parentSection": str(Path(relative).parent).replace("\\", "/"),
        "summary": redact(summary, 520),
        "purpose": purpose,
        "audience": str(frontmatter.get("audience") or ""),
        "status": status,
        "owner": str(owner),
        "frontmatter": frontmatter,
        "tags": sorted(set(str(value) for value in tags)),
        "headings": headings,
        "anchors": sorted(set(section["anchor"] for section in headings if section["anchor"])),
        "links": links,
        "images": images,
        "codeReferences": code_references,
        "commands": commands,
        "workItems": work_items,
        "pullRequests": pull_requests,
        "incidents": incidents,
        "hasDiagrams": mermaid_count > 0,
        "mermaidBlocks": mermaid_count,
        "warnings": warnings + (["Unclosed code fence"] if fence else []),
        "contentHash": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
        "normalizedText": redact(" ".join(body_lines), 12000).lower(),
        "lineCount": len(lines),
    }


def discover_files(config: dict[str, Any]) -> tuple[list[tuple[Path, Path, str]], list[dict[str, Any]]]:
    selected: list[tuple[Path, Path, str]] = []
    skipped: list[dict[str, Any]] = []
    used_names: Counter[str] = Counter()
    roots: list[Path] = config["_sourceRoots"]
    for root in roots:
        used_names[root.name.lower()] += 1
    for root_index, root in enumerate(roots):
        root_name = root.name if used_names[root.name.lower()] == 1 else f"{root.name}-{root_index + 1}"
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if path_matches(relative, config["excludeGlobs"]):
                continue
            if not path_matches(relative, config["includeGlobs"]):
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root.resolve())
            except (OSError, ValueError):
                skipped.append({"path": str(path), "reason": "Path escaped configured source root"})
                continue
            selected.append((resolved, root, root_name))
    selected.sort(key=lambda value: canonical(f"{value[2]}/{value[0].relative_to(value[1]).as_posix()}"))
    return selected, skipped


def file_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"size": stat.st_size, "mtimeNs": stat.st_mtime_ns}


def load_cache(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schemaVersion": 1, "generatorVersion": VERSION, "files": {}}
    try:
        cache = load_json(path)
    except RuntimeError:
        return {"schemaVersion": 1, "generatorVersion": VERSION, "files": {}}
    if cache.get("schemaVersion") != 1 or cache.get("generatorVersion") != VERSION:
        return {"schemaVersion": 1, "generatorVersion": VERSION, "files": {}}
    return cache


def parse_with_cache(
    files: list[tuple[Path, Path, str]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int], list[dict[str, Any]]]:
    old_cache = load_cache(config["_cache"])
    new_cache = {"schemaVersion": 1, "generatorVersion": VERSION, "files": {}}
    documents: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    reused = 0
    reparsed = 0
    for path, root, root_name in files:
        key = canonical(f"{root_name}/{path.relative_to(root).as_posix()}")
        try:
            signature = file_signature(path)
            cached = old_cache.get("files", {}).get(key)
            if cached and cached.get("signature") == signature and isinstance(cached.get("document"), dict):
                document = cached["document"]
                reused += 1
            else:
                document = parse_document(path, root, root_name, config)
                reparsed += 1
            documents.append(document)
            new_cache["files"][key] = {"signature": signature, "document": document}
        except OSError as error:
            skipped.append({"path": str(path), "reason": str(error)})
    documents.sort(key=lambda value: canonical(value["collectionPath"]))
    return documents, new_cache, {"reused": reused, "reparsed": reparsed}, skipped


def git_provenance(documents: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("gitHistoryEnabled", True):
        return {"enabled": False, "repositories": [], "documents": {}}
    by_root: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        by_root[document["sourceRoot"]].append(document)
    output: dict[str, Any] = {"enabled": True, "repositories": [], "documents": {}, "warnings": []}
    for root_value, root_documents in sorted(by_root.items()):
        root = Path(root_value)
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if probe.returncode != 0:
            output["warnings"].append(f"Git history unavailable for {root}")
            continue
        repo = Path(probe.stdout.strip()).resolve()
        output["repositories"].append(str(repo))
        command = [
            "git",
            "-C",
            str(repo),
            "log",
            "--reverse",
            "--date=iso-strict",
            "--format=@@@%H%x09%aI%x09%an%x09%ae%x09%s",
            "--name-status",
            "--",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            output["warnings"].append(f"Git log failed for {repo}: {redact(result.stderr)}")
            continue
        current: dict[str, str] | None = None
        history: dict[str, list[dict[str, str]]] = defaultdict(list)
        renames: dict[str, list[dict[str, str]]] = defaultdict(list)
        for raw in result.stdout.splitlines():
            if raw.startswith("@@@"):
                parts = raw[3:].split("\t", 4)
                if len(parts) == 5:
                    current = {
                        "commit": parts[0],
                        "timestamp": parts[1],
                        "author": parts[2],
                        "email": parts[3],
                        "subject": redact(parts[4], 220),
                    }
                continue
            if not current or not raw.strip():
                continue
            fields = raw.split("\t")
            status = fields[0]
            paths = fields[1:]
            target = paths[-1] if paths else ""
            if not target:
                continue
            event = dict(current)
            event["changeType"] = status[0]
            history[canonical(target)].append(event)
            if status.startswith("R") and len(paths) == 2:
                renames[canonical(target)].append({"from": paths[0], "to": paths[1], **event})
        for document in root_documents:
            relative_to_repo = Path(document["absolutePath"]).resolve().relative_to(repo).as_posix()
            events = history.get(canonical(relative_to_repo), [])
            if not events:
                continue
            first = events[0]
            last = events[-1]
            contributors = sorted({event["author"] for event in events if event.get("author")})
            record = {
                "creation": {
                    "timestamp": first["timestamp"],
                    "source": "git-first-commit",
                    "confidence": "high",
                    "commit": first["commit"],
                    "author": first["author"],
                },
                "lastMeaningfulUpdate": {
                    "timestamp": last["timestamp"],
                    "source": "git-last-commit",
                    "confidence": "high",
                    "commit": last["commit"],
                    "author": last["author"],
                    "subject": last["subject"],
                },
                "contributors": contributors,
                "commitCount": len(events),
                "renames": renames.get(canonical(relative_to_repo), []),
            }
            output["documents"][document["id"]] = record
            document["earliestKnownCreationDate"] = first["timestamp"]
            document["lastMeaningfulUpdate"] = last["timestamp"]
            document["dateProvenance"] = "git"
            document["contributors"] = contributors
    for document in documents:
        if document["id"] in output["documents"]:
            continue
        stat = Path(document["absolutePath"]).stat()
        timestamp = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        document["earliestKnownCreationDate"] = ""
        document["lastMeaningfulUpdate"] = timestamp
        document["dateProvenance"] = "filesystem-modification"
        document["contributors"] = []
    output["repositories"] = sorted(set(output["repositories"]))
    return output


def assign_inherited_owners(documents: list[dict[str, Any]], provenance: dict[str, Any]) -> None:
    repository_roots = [Path(value).resolve() for value in provenance.get("repositories", [])]
    owner_cache: dict[Path, tuple[str, dict[str, Any]] | None] = {}
    for document in documents:
        if document["owner"]:
            continue
        source_path = Path(document["absolutePath"]).resolve()
        repository = next(
            (root for root in repository_roots if source_path == root or source_path.is_relative_to(root)),
            Path(document["sourceRoot"]).resolve(),
        )
        current = source_path.parent
        inherited: tuple[str, dict[str, Any]] | None = None
        while current == repository or current.is_relative_to(repository):
            owner_file = current / "owners.txt"
            if owner_file in owner_cache:
                inherited = owner_cache[owner_file]
            elif owner_file.is_file():
                aliases: list[str] = []
                first_line = 1
                for line_number, raw in enumerate(
                    owner_file.read_text(encoding="utf-8-sig", errors="replace").splitlines(),
                    start=1,
                ):
                    stripped = raw.strip()
                    if not stripped or stripped.startswith(";"):
                        continue
                    aliases.append(stripped.lstrip("*"))
                    first_line = min(first_line if aliases[:-1] else line_number, line_number)
                inherited = (
                    (
                        ", ".join(sorted(set(aliases))),
                        line_evidence(str(owner_file), first_line, ", ".join(aliases)),
                    )
                    if aliases
                    else None
                )
                owner_cache[owner_file] = inherited
            else:
                owner_cache[owner_file] = None
            if inherited:
                break
            if current == repository:
                break
            current = current.parent
        if inherited:
            document["owner"] = inherited[0]
            document["ownerEvidence"] = inherited[1]
            document["ownerSource"] = "inherited-owners-file"


def resolve_internal_links(
    documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    lookup: dict[str, dict[str, Any]] = {}
    absolute_lookup: dict[str, dict[str, Any]] = {}
    for document in documents:
        lookup[canonical(document["collectionPath"])] = document
        absolute_lookup[canonical(document["absolutePath"])] = document
    edges: list[dict[str, Any]] = []
    broken: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, int]] = set()
    for document in documents:
        source_path = Path(document["absolutePath"])
        for link in document["links"]:
            target = str(link.get("target") or "").strip().strip("<>")
            if not target or target.startswith("#"):
                anchor = urllib.parse.unquote(target[1:]) if target.startswith("#") else ""
                if anchor and slugify(anchor) not in document["anchors"]:
                    broken.append(
                        {
                            "type": "broken-anchor",
                            "documentId": document["id"],
                            "target": target,
                            "evidence": link["evidence"],
                        }
                    )
                continue
            if URL_RE.match(target) or target.startswith("//"):
                external.append({"documentId": document["id"], "url": target, "evidence": link["evidence"]})
                continue
            decoded = urllib.parse.unquote(target)
            path_part, _, anchor_part = decoded.partition("#")
            path_part = path_part.split("?", 1)[0].replace("/", os.sep)
            candidate = (source_path.parent / path_part).resolve()
            raw_candidate = str(candidate)
            candidates = [candidate]
            if candidate.suffix == "":
                candidates.extend([candidate.with_suffix(".md"), candidate / "index.md", candidate / "README.md"])
            target_document = next((absolute_lookup.get(canonical(str(value))) for value in candidates if canonical(str(value)) in absolute_lookup), None)
            if not target_document:
                for value in candidates:
                    if not value.exists():
                        continue
                    resolved_case_path = canonical(str(value))
                    case_insensitive = absolute_lookup.get(resolved_case_path)
                    if case_insensitive:
                        target_document = case_insensitive
                        break
            if not target_document:
                suffix = Path(path_part).suffix.lower()
                if suffix and suffix not in {".md", ".mdx"}:
                    broken.append(
                        {
                            "type": "missing-asset",
                            "documentId": document["id"],
                            "target": target,
                            "evidence": link["evidence"],
                        }
                    )
                    continue
                broken.append(
                    {
                        "type": "broken-link",
                        "documentId": document["id"],
                        "target": target,
                        "evidence": link["evidence"],
                    }
                )
                continue
            if anchor_part and slugify(anchor_part) not in target_document["anchors"]:
                broken.append(
                    {
                        "type": "broken-anchor",
                        "documentId": document["id"],
                        "targetDocumentId": target_document["id"],
                        "target": target,
                        "evidence": link["evidence"],
                    }
                )
            heading = str(link.get("heading") or "").lower()
            label = str(link.get("label") or "").lower()
            relation = "document-link"
            reason = "The source document contains a direct internal link to the target document."
            if any(word in heading or word in label for word in ("see also", "related")):
                relation = "see-also"
                reason = "The source document explicitly lists the target in a related or see-also context."
            elif any(word in heading or word in label for word in ("prerequisite", "before you begin")):
                relation = "prerequisite"
                reason = "The source document explicitly identifies the target as prerequisite material."
            elif any(word in heading or word in label for word in ("next step", "next steps")):
                relation = "next-step"
                reason = "The source document explicitly identifies the target as a next step."
            elif any(word in heading or word in label for word in ("deprecated", "replacement", "replaced by")):
                relation = "replacement"
                reason = "The source document explicitly links the target in a replacement or deprecation context."
            signature = (document["id"], target_document["id"], relation, int(link["line"]))
            if signature in seen_edges:
                continue
            seen_edges.add(signature)
            edge_id = stable_id("edge", "|".join(map(str, signature)))
            edges.append(
                {
                    "id": edge_id,
                    "source": document["id"],
                    "target": target_document["id"],
                    "type": relation,
                    "relationshipClass": "explicit",
                    "confidence": "high",
                    "reason": reason,
                    "evidence": [link["evidence"]],
                    "directional": True,
                    "extractionMethod": f"{link['syntax']}-link",
                    "shownByDefault": True,
                    "caveat": "",
                }
            )
    edges.sort(key=lambda value: value["id"])
    return edges, broken, external


def parse_navigation(documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    doc_by_absolute = {canonical(document["absolutePath"]): document for document in documents}
    sections: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    source_roots = sorted({Path(document["sourceRoot"]) for document in documents}, key=lambda value: str(value).lower())
    toc_paths = sorted(
        {path for root in source_roots for path in root.rglob("toc.y*ml")},
        key=lambda value: str(value).lower(),
    )
    for toc in toc_paths:
        try:
            lines = toc.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        stack: list[tuple[int, str]] = []
        pending_name: dict[int, tuple[str, int, str]] = {}
        for index, raw in enumerate(lines, start=1):
            name_match = re.match(r"^(\s*)-\s+name:\s*(.+?)\s*$", raw, re.I)
            if name_match:
                indent = len(name_match.group(1))
                name = name_match.group(2).strip().strip("\"'")
                pending_name[indent] = (name, index, raw)
                stack = [entry for entry in stack if entry[0] < indent]
                parent_id = stack[-1][1] if stack else ""
                section_id = stable_id("nav", f"{toc}|{indent}|{name}|{index}")
                relative_toc = toc.name if not toc.parent else toc.as_posix()
                sections[section_id] = {
                    "id": section_id,
                    "type": "navigation-section",
                    "title": name,
                    "sourceFile": str(toc),
                    "line": index,
                    "parentId": parent_id,
                    "evidence": line_evidence(relative_toc, index, raw),
                }
                if parent_id:
                    edges.append(
                        {
                            "id": stable_id("edge", f"{parent_id}|{section_id}|contains"),
                            "source": parent_id,
                            "target": section_id,
                            "type": "contains",
                            "relationshipClass": "structural",
                            "confidence": "high",
                            "reason": "The navigation file nests this section beneath its parent.",
                            "evidence": [line_evidence(str(toc), index, raw)],
                            "directional": True,
                            "extractionMethod": "toc-yaml",
                            "shownByDefault": False,
                            "caveat": "Structural navigation containment is not semantic similarity.",
                        }
                    )
                stack.append((indent, section_id))
                continue
            href_match = re.match(r"^(\s+)href:\s*(.+?)\s*$", raw, re.I)
            if not href_match or not stack:
                continue
            target = href_match.group(2).strip().strip("\"'")
            if URL_RE.match(target):
                continue
            candidate = (toc.parent / urllib.parse.unquote(target.split("#", 1)[0])).resolve()
            canonical_candidate = canonical(str(candidate))
            document = doc_by_absolute.get(canonical_candidate)
            case_mismatch = False
            if not document:
                try:
                    parent_entries = {entry.name.casefold(): entry for entry in candidate.parent.iterdir()}
                    actual = parent_entries.get(candidate.name.casefold())
                    if actual:
                        document = doc_by_absolute.get(canonical(str(actual.resolve())))
                        case_mismatch = document is not None and actual.name != candidate.name
                except OSError:
                    pass
            if not document:
                continue
            section_id = stack[-1][1]
            edges.append(
                {
                    "id": stable_id("edge", f"{section_id}|{document['id']}|toc-membership|{index}"),
                    "source": section_id,
                    "target": document["id"],
                    "type": "toc-membership",
                    "relationshipClass": "structural",
                    "confidence": "high",
                    "reason": "The persisted navigation file explicitly lists this document under the section.",
                    "evidence": [line_evidence(str(toc), index, raw)],
                    "directional": True,
                    "extractionMethod": "toc-yaml",
                    "shownByDefault": False,
                    "caveat": "Navigation membership is structural and hidden in the core document graph.",
                }
            )
            if case_mismatch:
                edges[-1]["caveat"] = "The navigation target resolves only after case-insensitive path matching."
    return sorted(sections.values(), key=lambda value: value["id"]), sorted(edges, key=lambda value: value["id"])


def entity_records(documents: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    fields = [
        ("code-file", "codeReferences", "value"),
        ("command", "commands", "value"),
        ("work-item", "workItems", "id"),
        ("pull-request", "pullRequests", "id"),
        ("incident", "incidents", "id"),
    ]
    for document in documents:
        for entity_type, field, value_key in fields:
            for reference_index, reference in enumerate(document[field]):
                value = str(reference[value_key]).strip()
                if not value:
                    continue
                key = (entity_type, value.lower())
                if key not in entities:
                    entities[key] = {
                        "id": stable_id("ent", f"{entity_type}|{value.lower()}"),
                        "type": entity_type,
                        "name": value,
                        "references": 0,
                    }
                entities[key]["references"] += 1
                entity = entities[key]
                edges.append(
                    {
                        "id": stable_id(
                            "edge",
                            f"{document['id']}|{entity['id']}|{entity_type}|"
                            f"{reference['line']}|{reference_index}|{value}",
                        ),
                        "source": document["id"],
                        "target": entity["id"],
                        "type": "references",
                        "relationshipClass": "explicit",
                        "confidence": "high",
                        "reason": f"The document explicitly references this {entity_type.replace('-', ' ')}.",
                        "evidence": [reference["evidence"]],
                        "directional": True,
                        "extractionMethod": "exact-reference",
                        "shownByDefault": False,
                        "caveat": "Referenced entities are available only in expanded graph detail.",
                    }
                )
    ranked = sorted(entities.values(), key=lambda value: (-value["references"], value["type"], value["name"].lower()))
    allowed_ids = {entity["id"] for entity in ranked[:limit]}
    return ranked[:limit], sorted((edge for edge in edges if edge["target"] in allowed_ids), key=lambda value: value["id"])


def simhash(text: str) -> int:
    words = re.findall(r"[a-z0-9_]{3,}", text.lower())
    counts = Counter(words)
    vector = [0] * 64
    for word, weight in counts.items():
        value = int(hashlib.sha256(word.encode()).hexdigest()[:16], 16)
        for bit in range(64):
            vector[bit] += weight if value & (1 << bit) else -weight
    return sum(1 << bit for bit, score in enumerate(vector) if score >= 0)


def health_findings(
    documents: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    broken: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    inbound = Counter(edge["target"] for edge in edges if edge["shownByDefault"])
    outbound = Counter(edge["source"] for edge in edges if edge["shownByDefault"])
    by_id = {document["id"]: document for document in documents}
    for issue in broken:
        evidence = issue["evidence"]
        findings.append(
            {
                "id": stable_id("health", json.dumps(issue, sort_keys=True)),
                "type": issue["type"],
                "severity": "error",
                "documentId": issue["documentId"],
                "title": f"{issue['type'].replace('-', ' ').title()}: {issue['target']}",
                "reason": "The referenced internal target or anchor could not be resolved.",
                "evidence": [evidence],
            }
        )
    for document in documents:
        evidence = line_evidence(document["collectionPath"], 1, document["title"])
        if not document["title"]:
            findings.append(
                {
                    "id": stable_id("health", f"missing-title|{document['id']}"),
                    "type": "missing-title",
                    "severity": "warning",
                    "documentId": document["id"],
                    "title": "Missing document title",
                    "reason": "No frontmatter title, heading, or usable filename title was found.",
                    "evidence": [evidence],
                }
            )
        if not document["owner"]:
            findings.append(
                {
                    "id": stable_id("health", f"missing-owner|{document['id']}"),
                    "type": "missing-owner",
                    "severity": "info",
                    "documentId": document["id"],
                    "title": "No explicit owner metadata",
                    "reason": "The document does not explicitly declare an owner or author.",
                    "evidence": [evidence],
                }
            )
        if not inbound[document["id"]] and not outbound[document["id"]]:
            findings.append(
                {
                    "id": stable_id("health", f"orphan|{document['id']}"),
                    "type": "orphan",
                    "severity": "warning",
                    "documentId": document["id"],
                    "title": "Orphan document",
                    "reason": "No strong incoming or outgoing document relationship was found.",
                    "evidence": [evidence],
                }
            )
        elif not inbound[document["id"]]:
            findings.append(
                {
                    "id": stable_id("health", f"no-inbound|{document['id']}"),
                    "type": "no-inbound-links",
                    "severity": "info",
                    "documentId": document["id"],
                    "title": "No strong inbound links",
                    "reason": "No other document strongly links to this document.",
                    "evidence": [evidence],
                }
            )
        if not outbound[document["id"]]:
            findings.append(
                {
                    "id": stable_id("health", f"no-outbound|{document['id']}"),
                    "type": "no-outbound-links",
                    "severity": "info",
                    "documentId": document["id"],
                    "title": "No strong outbound links",
                    "reason": "This document does not strongly link to another indexed document.",
                    "evidence": [evidence],
                }
            )
        for warning in document["warnings"]:
            finding_type = "invalid-frontmatter" if "frontmatter" in warning.lower() else "invalid-markdown"
            findings.append(
                {
                    "id": stable_id("health", f"{finding_type}|{document['id']}|{warning}"),
                    "type": finding_type,
                    "severity": "warning",
                    "documentId": document["id"],
                    "title": warning,
                    "reason": "The parser found malformed or unsupported persisted syntax.",
                    "evidence": [evidence],
                }
            )
    hashes: dict[str, list[str]] = defaultdict(list)
    simhashes: list[tuple[str, int]] = []
    for document in documents:
        hashes[document["contentHash"]].append(document["id"])
        if len(document["normalizedText"]) > 240:
            simhashes.append((document["id"], simhash(document["normalizedText"])))
    duplicate_pairs: set[tuple[str, str]] = set()
    for ids in hashes.values():
        if len(ids) > 1:
            for left, right in zip(ids, ids[1:]):
                duplicate_pairs.add(tuple(sorted((left, right))))
    buckets: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for item in simhashes:
        buckets[item[1] >> 48].append(item)
    for bucket in buckets.values():
        for index, (left_id, left_hash) in enumerate(bucket):
            for right_id, right_hash in bucket[index + 1 :]:
                distance = (left_hash ^ right_hash).bit_count()
                if distance <= 3:
                    duplicate_pairs.add(tuple(sorted((left_id, right_id))))
    for left, right in sorted(duplicate_pairs):
        finding_type = "duplicate-document" if by_id[left]["contentHash"] == by_id[right]["contentHash"] else "near-duplicate-document"
        findings.append(
            {
                "id": stable_id("health", f"{finding_type}|{left}|{right}"),
                "type": finding_type,
                "severity": "warning",
                "documentId": left,
                "relatedDocumentId": right,
                "title": finding_type.replace("-", " ").title(),
                "reason": "The normalized document content is identical or has a very close SimHash.",
                "evidence": [
                    line_evidence(by_id[left]["collectionPath"], 1, by_id[left]["title"]),
                    line_evidence(by_id[right]["collectionPath"], 1, by_id[right]["title"]),
                ],
            }
        )
    return sorted(findings, key=lambda value: (value["type"], value["documentId"], value["id"]))


def family_color(name: str) -> str:
    digest = int(hashlib.sha256(name.lower().encode()).hexdigest()[:8], 16)
    hue = digest % 360
    return f"hsl({hue} 72% 62%)"


def build_graph(
    documents: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    degree = Counter()
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    nodes = [
        {
            "id": document["id"],
            "type": "document",
            "label": document["title"],
            "path": document["collectionPath"],
            "family": document["family"],
            "outlineColor": family_color(document["family"]),
            "status": document["status"],
            "date": document["earliestKnownCreationDate"] or document["lastMeaningfulUpdate"],
            "dateSource": document["dateProvenance"],
            "dateConfidence": "high" if document["dateProvenance"] == "git" else "low",
            "degree": degree[document["id"]],
            "shownByDefault": True,
        }
        for document in documents
    ]
    nodes.extend(
        {
            "id": section["id"],
            "type": "section",
            "label": section["title"],
            "path": section["sourceFile"],
            "family": "Navigation",
            "outlineColor": family_color("Navigation"),
            "status": "active",
            "date": "",
            "dateSource": "unknown",
            "dateConfidence": "unknown",
            "degree": degree[section["id"]],
            "shownByDefault": False,
        }
        for section in sections
    )
    nodes.extend(
        {
            "id": entity["id"],
            "type": entity["type"],
            "label": entity["name"],
            "path": "",
            "family": entity["type"],
            "outlineColor": family_color(entity["type"]),
            "status": "unknown",
            "date": "",
            "dateSource": "unknown",
            "dateConfidence": "unknown",
            "degree": degree[entity["id"]],
            "shownByDefault": False,
        }
        for entity in entities
    )
    return {"nodes": sorted(nodes, key=lambda value: value["id"]), "edges": sorted(edges, key=lambda value: value["id"])}


def validate_index(index: dict[str, Any]) -> None:
    required = {
        "schemaVersion",
        "generatedAt",
        "generatorVersion",
        "sourceRoots",
        "documents",
        "sections",
        "entities",
        "graph",
        "healthFindings",
    }
    missing = sorted(required - index.keys())
    if missing:
        raise RuntimeError(f"Index is missing required fields: {', '.join(missing)}")
    node_ids = [node["id"] for node in index["graph"]["nodes"]]
    edge_ids = [edge["id"] for edge in index["graph"]["edges"]]
    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError("Duplicate graph node IDs detected")
    if len(edge_ids) != len(set(edge_ids)):
        raise RuntimeError("Duplicate graph edge IDs detected")
    node_id_set = set(node_ids)
    document_ids = {document["id"] for document in index["documents"]}
    if not document_ids.issubset(node_id_set):
        raise RuntimeError("One or more documents are missing graph nodes")
    for edge in index["graph"]["edges"]:
        if edge["source"] not in node_id_set or edge["target"] not in node_id_set:
            raise RuntimeError(f"Dangling graph edge: {edge['id']}")
        if edge["relationshipClass"] not in EDGE_CLASSES:
            raise RuntimeError(f"Invalid relationship class on {edge['id']}")
        if edge["confidence"] not in CONFIDENCE_LEVELS:
            raise RuntimeError(f"Invalid confidence on {edge['id']}")
        for evidence in edge.get("evidence", []):
            if int(evidence.get("lineStart", 0)) < 1 or int(evidence.get("lineEnd", 0)) < int(evidence.get("lineStart", 0)):
                raise RuntimeError(f"Invalid evidence line range on {edge['id']}")


def json_for_script(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_html(index: dict[str, Any]) -> str:
    root = runtime_root()
    css_path = root / "templates" / "dashboard" / "dashboard.css"
    js_path = root / "templates" / "dashboard" / "dashboard.js"
    vendor_path = root / "templates" / "dashboard" / "vendor.min.js"
    for path in (css_path, js_path, vendor_path):
        if not path.is_file():
            raise RuntimeError(f"Required offline dashboard asset is missing: {path}")
    css = css_path.read_text(encoding="utf-8")
    javascript = js_path.read_text(encoding="utf-8")
    vendor = vendor_path.read_text(encoding="utf-8")
    payload = json_for_script(index)
    generated = html.escape(index["generatedAt"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Documentation Mesh</title><style>{css}</style></head>
<body><header><h1>Documentation Mesh</h1><div class="subtitle">Evidence-backed offline documentation intelligence · generated {generated}</div>
<nav class="tabs"><button class="tab active" data-view="catalogue">Catalogue</button><button class="tab" data-view="graph">Knowledge graph</button><button class="tab" data-view="health">Health</button><button class="tab" data-view="timeline">Timeline</button><button class="tab" data-view="provenance">Provenance</button></nav></header>
<main>
<section id="catalogue" class="view active"><div id="summary" class="metrics"></div><div id="catalogue-controls" class="toolbar"></div><div id="documents"></div></section>
<section id="graph" class="view"><div id="graph-controls" class="toolbar"></div><div id="animation-status"></div><div class="graph-shell"><div id="graph-canvas"></div><aside id="inspector" class="panel"><h2>Select a node or edge</h2></aside></div></section>
<section id="health" class="view"><div id="health-summary" class="metrics"></div><div id="health-controls" class="toolbar"></div><div id="health-findings"></div></section>
<section id="timeline" class="view"><div id="timeline-controls" class="toolbar"></div><div id="timeline-events"></div></section>
<section id="provenance" class="view"><div class="panel"><h2>Source and artifact provenance</h2><input id="provenance-search" placeholder="Search path, filename, commit, author, or artifact"><div id="provenance-results"></div></div></section>
</main><script>{vendor}</script><script>window.DOCUMENTATION_MESH_INDEX={payload};</script><script>{javascript}</script></body></html>"""


def render_digest(index: dict[str, Any]) -> str:
    stats = index["statistics"]
    health = Counter(finding["type"] for finding in index["healthFindings"])
    lines = [
        "# Documentation Mesh — Startup Digest",
        "",
        f"> Generated: {index['generatedAt']}",
        "> Source documentation is read-only. The JSON index is the source of truth.",
        "",
        "## Portfolio summary",
        "",
        f"- Source roots: {len(index['sourceRoots'])}",
        f"- Documents: {stats['documentCount']}",
        f"- Graph: {stats['graphNodeCount']} nodes / {stats['graphEdgeCount']} edges",
        f"- Strong default relationships: {stats['defaultEdgeCount']}",
        f"- Optional relationships: {stats['optionalEdgeCount']}",
        f"- Cache: {stats['cacheReused']} reused / {stats['cacheReparsed']} reparsed",
        f"- Broken links: {health['broken-link']}",
        f"- Broken anchors: {health['broken-anchor']}",
        f"- Orphans: {health['orphan']}",
        "",
        "## Largest documentation families",
        "",
    ]
    families = Counter(document["family"] for document in index["documents"])
    lines.extend(f"- {name}: {count}" for name, count in families.most_common(12))
    lines.extend(
        [
            "",
            "## Known limitations and warnings",
            "",
        ]
    )
    lines.extend(f"- {warning}" for warning in index["warnings"]) if index["warnings"] else lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## Hydration protocol",
            "",
            "1. Read this digest for portfolio scope and health.",
            "2. Use `documentation-index.json` for exact evidence, paths, graph data, and provenance.",
            "3. Treat source Markdown as read-only.",
            "",
        ]
    )
    return "\n".join(lines)


def build(config_path: Path, validate: bool = True) -> tuple[dict[str, Any], dict[str, Path]]:
    start = time.perf_counter()
    config = validate_config(load_json(config_path), config_path)
    files, discovery_skips = discover_files(config)
    if not files:
        raise RuntimeError("No Markdown or MDX files matched the configured scope")
    documents, cache, cache_stats, parse_skips = parse_with_cache(files, config)
    provenance = git_provenance(documents, config)
    assign_inherited_owners(documents, provenance)
    explicit_edges, broken, external = resolve_internal_links(documents)
    sections, navigation_edges = parse_navigation(documents)
    entities, entity_edges = entity_records(documents, int(config.get("maximumOptionalEntityNodes", 2500)))
    all_edges = explicit_edges + navigation_edges + entity_edges
    findings = health_findings(documents, explicit_edges, broken, config)
    graph = build_graph(documents, sections, entities, all_edges)
    timeline = []
    for document in documents:
        if document["earliestKnownCreationDate"]:
            timeline.append(
                {
                    "id": stable_id("event", f"created|{document['id']}"),
                    "documentId": document["id"],
                    "timestamp": document["earliestKnownCreationDate"],
                    "type": "created",
                    "source": document["dateProvenance"],
                    "confidence": "high" if document["dateProvenance"] == "git" else "low",
                    "title": f"Created: {document['title']}",
                }
            )
        if document["lastMeaningfulUpdate"]:
            timeline.append(
                {
                    "id": stable_id("event", f"updated|{document['id']}|{document['lastMeaningfulUpdate']}"),
                    "documentId": document["id"],
                    "timestamp": document["lastMeaningfulUpdate"],
                    "type": "updated",
                    "source": document["dateProvenance"],
                    "confidence": "high" if document["dateProvenance"] == "git" else "low",
                    "title": f"Updated: {document['title']}",
                }
            )
    timeline.sort(key=lambda value: (value["timestamp"] or "9999", value["id"]))
    warnings = list(provenance.get("warnings", []))
    if parse_skips or discovery_skips:
        warnings.append(f"{len(parse_skips) + len(discovery_skips)} source files were skipped")
    if config.get("sessionProvenanceEnabled"):
        warnings.append("Local session provenance is enabled but this runtime version indexes Git provenance only.")
    duration = round(time.perf_counter() - start, 3)
    index = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(),
        "generatorVersion": VERSION,
        "sourceRoots": [str(path) for path in config["_sourceRoots"]],
        "configuration": {
            key: value
            for key, value in config.items()
            if not key.startswith("_") and key not in {"sessionStateRoot"}
        },
        "statistics": {
            "documentCount": len(documents),
            "sectionCount": len(sections),
            "entityCount": len(entities),
            "graphNodeCount": len(graph["nodes"]),
            "graphEdgeCount": len(graph["edges"]),
            "defaultEdgeCount": sum(1 for edge in graph["edges"] if edge["shownByDefault"]),
            "optionalEdgeCount": sum(1 for edge in graph["edges"] if not edge["shownByDefault"]),
            "healthFindingCount": len(findings),
            "externalLinkCount": len(external),
            "cacheReused": cache_stats["reused"],
            "cacheReparsed": cache_stats["reparsed"],
            "buildSeconds": duration,
        },
        "documents": documents,
        "sections": sections,
        "entities": entities,
        "graph": graph,
        "timeline": timeline,
        "healthFindings": findings,
        "gitProvenance": provenance,
        "artifactProvenance": {"enabled": False, "records": []},
        "externalLinks": external,
        "warnings": warnings,
        "skippedFiles": discovery_skips + parse_skips,
    }
    if validate:
        validate_index(index)
    output: Path = config["_output"]
    paths = {
        "index": output / "documentation-index.json",
        "html": output / "documentation-mesh.html",
        "digest": output / "DOCUMENTATION-MESH.md",
        "cache": config["_cache"],
    }
    atomic_write(paths["index"], json.dumps(index, ensure_ascii=False, indent=2))
    atomic_write(paths["html"], render_html(index))
    atomic_write(paths["digest"], render_digest(index))
    atomic_write(paths["cache"], json.dumps(cache, ensure_ascii=False, separators=(",", ":")))
    return index, paths
