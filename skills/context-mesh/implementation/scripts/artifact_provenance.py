from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 3
ARTIFACT_EXTENSIONS = (
    "html|htm|md|pdf|ps1|py|json|csv|txt|msg|png|jpg|jpeg|svg|"
    "docx|xlsx|pptx|zip|sql|kql|cs|ts|tsx|js|mjs|yaml|yml"
)
QUOTED_PATH_PATTERN = re.compile(
    rf"""(?i)(?P<quote>["'`])(?P<path>[a-z]:\\.+?\.(?:{ARTIFACT_EXTENSIONS}))(?P=quote)"""
)
UNQUOTED_PATH_PATTERN = re.compile(
    rf"""(?i)\b[a-z]:\\[^\s"'`<>|]+\.(?:{ARTIFACT_EXTENSIONS})\b"""
)
OUTPUT_PATH_PATTERN = re.compile(
    rf"""(?i)(?:created file|generated|wrote|saved|output(?: file)?[: ]+)\s+"""
    rf"""(?P<path>[a-z]:\\[^\r\n]+?\.(?:{ARTIFACT_EXTENSIONS}))(?=$|[\r\n,;])"""
)
BARE_FILE_PATTERN = re.compile(
    rf"""(?i)(?<![\w.-])(?P<name>[a-z0-9_][a-z0-9_.() -]{{0,120}}\.(?:{ARTIFACT_EXTENSIONS}))"""
)
COPY_SUFFIX_PATTERN = re.compile(r"\s+(?:\(\d+\)|\d+)$")
SECRET_PATTERN = re.compile(
    r"(?i)\b(token|password|secret|api[_ -]?key|authorization)\b\s*[:=]\s*\S+"
)
ACTION_RANK = {
    "created": 100,
    "generated": 90,
    "modified": 80,
    "requested": 35,
    "mentioned": 25,
    "inspected": 10,
}


def truncate(value: str, limit: int = 520) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = SECRET_PATTERN.sub(r"\1=[redacted]", value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def parse_workspace(path: Path, session_id: str) -> dict[str, str]:
    metadata = {
        "sessionId": session_id,
        "sessionName": session_id,
        "cwd": "",
        "createdAt": "",
        "updatedAt": "",
    }
    if not path.is_file():
        return metadata
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        value = value.strip().strip("\"'")
        if key == "name" and value:
            metadata["sessionName"] = value
        elif key == "cwd":
            metadata["cwd"] = value
        elif key == "created_at":
            metadata["createdAt"] = value
        elif key == "updated_at":
            metadata["updatedAt"] = value
    return metadata


def logical_name(value: str) -> str:
    stem = Path(value).stem
    suffix = Path(value).suffix.lower()
    return f"{COPY_SUFFIX_PATTERN.sub('', stem).lower()}{suffix}"


def normalize_candidate(value: str) -> str | None:
    value = value.strip().strip("\"'`[](){}<>,;")
    if not value:
        return None
    suffix = Path(value).suffix.lower().lstrip(".")
    if not suffix or suffix not in ARTIFACT_EXTENSIONS.split("|"):
        return None
    lowered = value.lower()
    if "\\node_modules\\" in lowered or "\\.copilot\\session-state\\" in lowered:
        return None
    return value


def extract_candidates(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for pattern in (QUOTED_PATH_PATTERN, OUTPUT_PATH_PATTERN):
        for match in pattern.finditer(text):
            candidate = normalize_candidate(match.group("path"))
            if candidate and candidate not in found:
                found.append(candidate)
    for match in UNQUOTED_PATH_PATTERN.finditer(text):
        candidate = normalize_candidate(match.group(0))
        if candidate and candidate not in found:
            found.append(candidate)
    for match in BARE_FILE_PATTERN.finditer(text):
        candidate = normalize_candidate(match.group("name"))
        if candidate and candidate not in found:
            found.append(candidate)
    return found


def iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def excerpt_around(text: str, candidate: str) -> str:
    needle = Path(candidate).name
    index = text.lower().find(needle.lower())
    if index < 0:
        return truncate(text)
    start = max(0, index - 220)
    end = min(len(text), index + len(needle) + 260)
    return truncate(text[start:end])


def classify_tool(tool_name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    lowered = tool_name.lower()
    if lowered in {"create", "create_file"}:
        return "created", "high"
    if lowered in {"edit", "apply_patch"}:
        return "modified", "high"
    if lowered == "powershell":
        command = str(arguments.get("command", "")).lower()
        if re.search(
            r"\b(set-content|out-file|new-item|copy-item|move-item)\b|"
            r">\s*[^|]|python\s+.+(?:build|render|report|generate)",
            command,
        ):
            return "generated", "medium"
        return "inspected", "low"
    if lowered in {"view", "rg", "glob"}:
        return "inspected", "low"
    return "mentioned", "low"


def add_record(
    records: dict[str, dict[str, Any]],
    candidate: str,
    metadata: dict[str, str],
    timestamp: str,
    action: str,
    confidence: str,
    tool: str,
    evidence: str,
    prompt: str,
) -> None:
    key = logical_name(candidate)
    record = records.get(key)
    if record is None:
        absolute_path = candidate if re.match(r"(?i)^[a-z]:\\", candidate) else ""
        record = {
            "path": absolute_path,
            "paths": [absolute_path] if absolute_path else [],
            "fileName": Path(candidate).name,
            "logicalName": key,
            **metadata,
            "firstSeen": timestamp,
            "lastSeen": timestamp,
            "action": action,
            "confidence": confidence,
            "tool": tool,
            "evidence": [],
        }
        records[key] = record
    elif re.match(r"(?i)^[a-z]:\\", candidate):
        if candidate.lower() not in {value.lower() for value in record["paths"]}:
            record["paths"].append(candidate)
            record["paths"] = record["paths"][:6]
        if not record["path"]:
            record["path"] = candidate
    record["firstSeen"] = min(filter(None, (record["firstSeen"], timestamp)), default="")
    record["lastSeen"] = max(record["lastSeen"], timestamp)
    if ACTION_RANK.get(action, 0) > ACTION_RANK.get(record["action"], 0):
        record["action"] = action
        record["confidence"] = confidence
        record["tool"] = tool
    evidence_entry = {
        "timestamp": timestamp,
        "action": action,
        "tool": tool,
        "excerpt": excerpt_around(evidence, candidate),
        "prompt": truncate(prompt, 420),
    }
    signature = (
        evidence_entry["timestamp"],
        evidence_entry["action"],
        evidence_entry["excerpt"],
    )
    existing = {
        (item["timestamp"], item["action"], item["excerpt"])
        for item in record["evidence"]
    }
    if signature not in existing and len(record["evidence"]) < 4:
        record["evidence"].append(evidence_entry)


def scan_session(session_dir: Path) -> list[dict[str, Any]]:
    events_path = session_dir / "events.jsonl"
    metadata = parse_workspace(session_dir / "workspace.yaml", session_dir.name)
    records: dict[str, dict[str, Any]] = {}
    last_prompt = ""
    generator_run = False
    with events_path.open(encoding="utf-8", errors="replace") as stream:
        for raw_line in stream:
            if not any(
                marker in raw_line
                for marker in (
                    '"type":"hook.start"',
                    '"type":"user.message"',
                    '"type":"assistant.message"',
                    '"type":"tool.execution_start"',
                    '"type":"tool.execution_complete"',
                )
            ):
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type", "")
            data = event.get("data") or {}
            timestamp = str(event.get("timestamp") or "")
            if event_type == "hook.start" and data.get("hookType") == "userPromptSubmitted":
                last_prompt = str((data.get("input") or {}).get("prompt") or "")
                continue
            if event_type == "user.message":
                last_prompt = str(data.get("content") or data.get("message") or "")
                continue
            if event_type == "tool.execution_start":
                tool_name = str(data.get("toolName") or "")
                arguments = data.get("arguments") or {}
                if not isinstance(arguments, dict):
                    arguments = {"value": str(arguments)}
                action, confidence = classify_tool(tool_name, arguments)
                texts: list[str] = []
                for key in ("path", "file_path", "command", "patch"):
                    if arguments.get(key):
                        texts.append(str(arguments[key]))
                shell_info = data.get("shellToolInfo") or {}
                texts.extend(str(value) for value in shell_info.get("possiblePaths") or [])
                command = str(arguments.get("command") or "")
                if re.search(r"(?i)python\s+.+(?:build|render|report|generate)", command):
                    generator_run = True
                for text in texts:
                    for candidate in extract_candidates(text):
                        add_record(
                            records,
                            candidate,
                            metadata,
                            timestamp,
                            action,
                            confidence,
                            tool_name,
                            text,
                            last_prompt,
                        )
                if tool_name.lower() == "create":
                    source_text = str(arguments.get("file_text") or "")
                    for candidate in extract_candidates(source_text):
                        add_record(
                            records,
                            candidate,
                            metadata,
                            timestamp,
                            "mentioned",
                            "low",
                            "source-content",
                            source_text,
                            last_prompt,
                        )
                continue
            if event_type == "tool.execution_complete" and data.get("success") is not False:
                result_text = " ".join(iter_strings(data.get("result") or {}))
                for candidate in extract_candidates(result_text):
                    add_record(
                        records,
                        candidate,
                        metadata,
                        timestamp,
                        "generated"
                        if re.search(r"(?i)\b(created|generated|wrote|saved)\b", result_text)
                        else "inspected",
                        "medium",
                        "tool-result",
                        result_text,
                        last_prompt,
                    )
                continue
            if event_type == "assistant.message":
                content = str(data.get("content") or "")
                for candidate in extract_candidates(content):
                    add_record(
                        records,
                        candidate,
                        metadata,
                        timestamp,
                        "mentioned",
                        "low",
                        "assistant",
                        content,
                        last_prompt,
                    )

    if generator_run:
        for record in records.values():
            if (
                "report" in record["logicalName"]
                and (
                    not record["paths"]
                    or any("\\downloads\\" not in value.lower() for value in record["paths"])
                )
                and ACTION_RANK[record["action"]] < ACTION_RANK["generated"]
            ):
                record["action"] = "generated"
                record["confidence"] = "medium"
                record["tool"] = "generator-run"
                record["evidence"].insert(
                    0,
                    {
                        "timestamp": record["firstSeen"],
                        "action": "generated",
                        "tool": "generator-run",
                        "excerpt": (
                            "This session ran a report-oriented generator and "
                            f"referenced {record['fileName']}."
                        ),
                        "prompt": "",
                    },
                )
                record["evidence"] = record["evidence"][:4]
    return list(records.values())


def build_artifact_index(
    session_root: Path,
    cache_path: Path,
    history_days: int,
    record_limit: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    previous: dict[str, Any] = {}
    if cache_path.is_file():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("schemaVersion") == SCHEMA_VERSION:
                previous = payload.get("sessions") or {}
        except (OSError, json.JSONDecodeError):
            previous = {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=history_days)
    sessions: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    scanned = 0
    reused = 0
    if session_root.is_dir():
        for session_dir in session_root.iterdir():
            events_path = session_dir / "events.jsonl"
            if not session_dir.is_dir() or not events_path.is_file():
                continue
            stat = events_path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            if modified < cutoff:
                continue
            workspace_path = session_dir / "workspace.yaml"
            workspace_mtime = (
                workspace_path.stat().st_mtime_ns if workspace_path.is_file() else 0
            )
            signature = {
                "eventsSize": stat.st_size,
                "eventsMtime": stat.st_mtime_ns,
                "workspaceMtime": workspace_mtime,
            }
            cached = previous.get(session_dir.name)
            if cached and cached.get("signature") == signature:
                session_records = cached.get("records") or []
                reused += 1
            else:
                session_records = scan_session(session_dir)
                scanned += 1
            sessions[session_dir.name] = {
                "signature": signature,
                "records": session_records,
            }
            records.extend(session_records)

    # Cap histories only after placing each artifact's strongest, earliest evidence first.
    histories: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        histories.setdefault(record["logicalName"], []).append(record)
    ordered_histories = sorted(
        histories.values(),
        key=lambda history: (
            max(ACTION_RANK.get(item.get("action", ""), 0) for item in history),
            max(item.get("lastSeen", "") for item in history),
        ),
        reverse=True,
    )
    records = [
        record
        for history in ordered_histories
        for record in sorted(
            history,
            key=lambda item: (
                -ACTION_RANK.get(item.get("action", ""), 0),
                item.get("firstSeen", ""),
                item.get("sessionId", ""),
            ),
        )
    ][:record_limit]
    return (
        {
            "sessionRoot": str(session_root),
            "historyDays": history_days,
            "recordCount": len(records),
            "sessionCount": len(sessions),
            "scannedSessions": scanned,
            "reusedSessions": reused,
            "records": records,
        },
        {"schemaVersion": SCHEMA_VERSION, "sessions": sessions},
    )
