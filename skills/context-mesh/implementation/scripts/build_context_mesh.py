from __future__ import annotations

import argparse
import colorsys
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from copy import deepcopy
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from itertools import chain
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

try:
    from artifact_provenance import build_artifact_index
except ModuleNotFoundError:
    from scripts.artifact_provenance import build_artifact_index
try:
    from social_personality import derive_social_personality
except ModuleNotFoundError:
    from scripts.social_personality import derive_social_personality


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config.json"
STORE_FILES = ("README.md", "STATE.md", "MEMORY.md", "JOURNAL.md")
SOCIAL_DIRECTORY = "social"
PERSONA_COLOR_REGISTRY = "persona-colors.sqlite3"
SOCIAL_ARCHIVE_JSON = "meshboard-archive.json"
SOCIAL_ARCHIVE_HTML = "meshboard-archive.html"
PERSONA_COLOR_PALETTE = (
    "#7dd3fc", "#fda4af", "#c4b5fd", "#86efac", "#fdba74", "#f9a8d4",
    "#fde047", "#5eead4", "#a5b4fc", "#bef264", "#fca5a5", "#d8b4fe",
)
SELF_STATUS_REACTIONS = {"✅", "❌"}
DATE_PATTERN = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LAST_UPDATED_PATTERN = re.compile(r"Last updated:\*{0,2}\s*(20\d{2}-\d{2}-\d{2})", re.I)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
CODE_PATTERN = re.compile(r"`([^`]+)`")
FORMAT_PATTERN = re.compile(r"[*_~]+")
STRONG_RELATIONSHIP_PATTERN = re.compile(
    r"\b(authoritative|canonical|cross-reference|cross reference|do not duplicate|"
    r"don't duplicate|pointer|lives in|remains in|consolidated into|"
    r"source of truth|owns|handoff|continuation)\b",
    re.I,
)
INCIDENTAL_REFERENCE_PATTERN = re.compile(
    r"\b(inspiration|inspired|style|formatting|format|example|template|"
    r"studied|modeled after|modelled after|similar to)\b",
    re.I,
)
BOUNDARY_REFERENCE_PATTERN = re.compile(
    r"(must not be confused|never cross-write|sibling(?:-base)? pointer|"
    r"corrected (?:the )?.*pointer|has its own separate|is the sibling base|"
    r"current-pointer|current pointers|historical relocation|rename entries)",
    re.I,
)


@dataclass(frozen=True)
class Store:
    context_id: str
    name: str
    base_path: Path
    store_path: Path
    files: dict[str, str]


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    config["_path"] = str(path)
    return config


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def context_outline_color(index: int) -> str:
    hue = (index * 0.61803398875 + 0.54) % 1
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.96)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def normalize_text(value: str) -> str:
    value = MARKDOWN_LINK_PATTERN.sub(r"\1", value)
    value = CODE_PATTERN.sub(r"\1", value)
    value = FORMAT_PATTERN.sub("", value)
    value = re.sub(r"^\s*[-*+]\s+", "", value)
    value = re.sub(r"^\s*\d+\.\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def truncate(value: str, limit: int = 280) -> str:
    value = normalize_text(value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def discover_stores(roots: Iterable[Path]) -> list[Store]:
    found: list[Store] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root / ".agent-context"]
        candidates.extend(path for path in root.rglob(".agent-context") if path.is_dir())
        for store_path in candidates:
            resolved = store_path.resolve()
            if resolved in seen or not store_path.is_dir():
                continue
            seen.add(resolved)
            base_path = store_path.parent
            try:
                relative = base_path.relative_to(root)
                name = root.name if str(relative) == "." else str(relative)
            except ValueError:
                name = base_path.name
            if root.name == "AzRetroFit" and base_path == root:
                name = "AzRetroFit"
            if not all((store_path / filename).is_file() for filename in STORE_FILES):
                continue
            files = {
                filename: read_text(store_path / filename) for filename in STORE_FILES
            }
            found.append(
                Store(
                    context_id=stable_id("ctx", str(base_path).lower()),
                    name=name.replace("\\", " / "),
                    base_path=base_path,
                    store_path=store_path,
                    files=files,
                )
            )
    return sorted(found, key=lambda item: item.name.lower())


def split_sections(markdown: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in markdown.splitlines():
        match = HEADING_PATTERN.match(raw_line)
        if match:
            current = {
                "level": len(match.group(1)),
                "title": normalize_text(match.group(2)),
                "lines": [],
            }
            sections.append(current)
        elif current is not None:
            current["lines"].append(raw_line.rstrip())
    return sections


def select_sections(markdown: str, keywords: tuple[str, ...], max_items: int = 8) -> list[str]:
    results: list[str] = []
    for section in split_sections(markdown):
        lowered = section["title"].lower()
        if not any(keyword in lowered for keyword in keywords):
            continue
        paragraphs: list[str] = []
        current: list[str] = []
        for line in section["lines"]:
            if HEADING_PATTERN.match(line):
                break
            if not line.strip():
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                continue
            if line.lstrip().startswith(("-", "*", "+")):
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                paragraphs.append(line)
            else:
                current.append(line.strip())
        if current:
            paragraphs.append(" ".join(current))
        for paragraph in paragraphs:
            cleaned = truncate(paragraph)
            if cleaned and cleaned not in results:
                results.append(cleaned)
            if len(results) >= max_items:
                return results
    return results


def first_substantive_lines(markdown: str, max_items: int = 4) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith(">")
            or stripped in {"---", "***"}
        ):
            continue
        cleaned = truncate(stripped)
        if cleaned:
            lines.append(cleaned)
        if len(lines) >= max_items:
            break
    return lines


def journal_events(markdown: str) -> list[dict[str, str]]:
    sections = split_sections(markdown)
    events: list[dict[str, str]] = []
    for section in sections:
        if section["level"] != 2:
            continue
        match = DATE_PATTERN.search(section["title"])
        if not match:
            continue
        title = section["title"][match.end() :].strip(" \t—–-:()")
        if not title:
            title = "Journal update"
        body = " ".join(line.strip() for line in section["lines"] if line.strip())
        events.append(
            {
                "date": match.group(1),
                "title": title,
                "summary": truncate(body, 650),
            }
        )
    return sorted(events, key=lambda event: (event["date"], event["title"]), reverse=True)


def extract_last_updated(state: str, events: list[dict[str, str]]) -> str | None:
    match = LAST_UPDATED_PATTERN.search(state)
    if match:
        return match.group(1)
    dates = DATE_PATTERN.findall(state)
    if dates:
        return max(dates)
    if events:
        return events[0]["date"]
    return None


def freshness(last_updated: str | None, config: dict[str, Any]) -> dict[str, Any]:
    if not last_updated:
        return {"label": "unknown", "days": None}
    updated = date.fromisoformat(last_updated)
    age = (date.today() - updated).days
    if age <= int(config["freshDays"]):
        label = "fresh"
    elif age <= int(config["agingDays"]):
        label = "aging"
    else:
        label = "stale"
    return {"label": label, "days": age}


def memory_items(markdown: str, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current_section = "Memory"
    for raw in markdown.splitlines():
        heading = HEADING_PATTERN.match(raw)
        if heading:
            current_section = normalize_text(heading.group(2))
            continue
        stripped = raw.strip()
        if not stripped.startswith(("-", "*", "+")):
            continue
        text = truncate(stripped, 360)
        if len(text) < 20:
            continue
        items.append({"section": current_section, "text": text})
        if len(items) >= limit:
            break
    return items


SOCIAL_SECRET_PATTERN = re.compile(
    r"(?i)\b(?:token|secret|password|passwd|api[_ -]?key|connection[_ -]?string)\s*[=:]\s*[^\s,;]+"
)


def redact_social_text(value: str) -> str:
    return SOCIAL_SECRET_PATTERN.sub(lambda match: match.group(0).split("=")[0].split(":")[0] + "=[REDACTED]", value)


def valid_social_media_url(value: Any) -> bool:
    if not isinstance(value, str) or re.search(r"[\x00-\x20\x7f\\]", value):
        return False
    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        return bool(
            parsed.scheme == "https"
            and not parsed.username and not parsed.password
            and parsed.port in (None, 443) and not parsed.fragment
            and re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", hostname)
            and hostname.rsplit(".", 1)[-1] not in {
                "localhost", "local", "localdomain", "internal", "test", "invalid", "example", "onion", "lan", "home", "corp"
            }
            and not SOCIAL_SECRET_PATTERN.search(unquote(value))
        )
    except ValueError:
        return False


def normalize_social_attachments(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("attachments must be an array")
    attachments = []
    for attachment in value:
        if not isinstance(attachment, dict) or attachment.get("type") not in ("image", "gif", "sticker"):
            raise ValueError("attachment type must be image, gif or sticker")
        for field in ("alt", "context"):
            if not isinstance(attachment.get(field), str) or not attachment[field].strip():
                raise ValueError(f"attachment {field} must describe the content and its conversational relevance")
        if not valid_social_media_url(attachment.get("url")):
            raise ValueError("attachment url must be credential-free public-host HTTPS on port 443, without fragments or secret assignments")
        source = attachment.get("sourceUrl", attachment["url"])
        if not valid_social_media_url(source):
            raise ValueError("attachment sourceUrl must be credential-free public-host HTTPS on port 443, without fragments or secret assignments")
        attachments.append({
            "type": attachment["type"],
            "url": attachment["url"],
            "alt": truncate(redact_social_text(attachment["alt"].strip()), 300),
            "context": truncate(redact_social_text(attachment["context"].strip()), 600),
            "sourceUrl": source,
        })
    return attachments


def register_persona_colors(persona_ids: Iterable[str], registry_path: Path) -> dict[str, str]:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(registry_path, timeout=30)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS persona_colors ("
            "persona_id TEXT PRIMARY KEY NOT NULL, color TEXT NOT NULL UNIQUE)"
        )
        colors = dict(connection.execute("SELECT persona_id, color FROM persona_colors"))
        if any(not re.fullmatch(r"#[0-9a-f]{6}", color) for color in colors.values()):
            raise ValueError(f"Invalid persona color in registry: {registry_path}")
        used = set(colors.values())
        if len(used) != len(colors):
            raise ValueError(f"Duplicate persona colors in registry: {registry_path}")
        # The odd multiplier visits every 24-bit RGB color once after the starter palette.
        candidates = chain(
            PERSONA_COLOR_PALETTE,
            (f"#{(index * 0x9e3779 + 0x7db5f5) & 0xffffff:06x}" for index in range(1 << 24)),
        )
        for persona_id in sorted(set(persona_ids)):
            if persona_id in colors:
                continue
            color = next((candidate for candidate in candidates if candidate not in used), None)
            if color is None:
                raise RuntimeError("The persona color registry has exhausted the RGB color space.")
            connection.execute(
                "INSERT INTO persona_colors (persona_id, color) VALUES (?, ?)",
                (persona_id, color),
            )
            colors[persona_id] = color
            used.add(color)
    return colors


def load_social_personas(store: Store) -> list[dict[str, Any]]:
    social_path = store.store_path / SOCIAL_DIRECTORY
    if not social_path.is_dir():
        return []
    personas: list[dict[str, Any]] = []
    for path in sorted(social_path.glob("*.json")):
        try:
            payload = json.loads(read_text(path))
        except (OSError, json.JSONDecodeError):
            continue
        persona_id = str(payload.get("personaId") or path.stem).strip()
        display_name = str(payload.get("displayName") or persona_id).strip()
        if not persona_id or not display_name:
            continue
        messages: list[dict[str, Any]] = []
        for index, message in enumerate(payload.get("messages") or []):
            if not isinstance(message, dict):
                continue
            text = redact_social_text(str(message.get("text") or ""))
            try:
                attachments = normalize_social_attachments(message.get("attachments", []))
            except ValueError as error:
                raise ValueError(f"{path.name} message {index + 1}: {error}") from error
            if not text.strip() and not attachments:
                continue
            broadcast_reply = message.get("broadcastReplyTo")
            if broadcast_reply is not None and (not isinstance(broadcast_reply, str) or not broadcast_reply.strip()):
                raise ValueError(f"{path.name} message {index + 1}: broadcastReplyTo must be a nonempty message ID")
            reactions = [
                {
                    "emoji": str(reaction.get("emoji") or "").strip(),
                    "personaId": str(reaction.get("personaId") or "").strip(),
                }
                for reaction in (message.get("reactions") or [])
                if isinstance(reaction, dict)
                and str(reaction.get("emoji") or "").strip()
                and not (
                    str(reaction.get("personaId") or "").strip() == persona_id
                    and str(reaction.get("emoji") or "").strip() not in SELF_STATUS_REACTIONS
                )
            ]
            messages.append(
                {
                    "id": str(message.get("id") or f"{persona_id}-{index + 1}"),
                    "timestamp": str(message.get("timestamp") or payload.get("createdAt") or ""),
                    "kind": str(message.get("kind") or "work"),
                    "text": text,
                    "replyTo": message.get("replyTo"),
                    "threadId": str(message.get("threadId") or "").strip() or None,
                    "questionTitle": truncate(str(message.get("questionTitle") or "").strip(), 120) or None,
                    "mentions": [str(mention).strip() for mention in (message.get("mentions") or []) if str(mention).strip()],
                    "reactions": reactions,
                    "isUser": bool(message.get("isUser", False)),
                    **({"broadcastReplyTo": broadcast_reply.strip()} if broadcast_reply is not None else {}),
                    **({"attachments": attachments} if attachments else {}),
                }
            )
        threads = []
        for thread in payload.get("threads") or []:
            if not isinstance(thread, dict) or not str(thread.get("id") or "").strip():
                continue
            status = "closed" if str(thread.get("status") or "open").lower() == "closed" else "open"
            reply_ids = thread.get("replyMessageIds", [])
            if not isinstance(reply_ids, list) or any(not isinstance(item, str) or not item.strip() for item in reply_ids):
                raise ValueError(f"{path.name} thread {thread['id']}: replyMessageIds must be an array of nonempty message IDs")
            threads.append(
                {
                    "id": str(thread["id"]).strip(),
                    "questionMessageId": str(thread.get("questionMessageId") or "").strip(),
                    "ownerPersonaId": persona_id,
                    "status": status,
                    "closedAt": str(thread.get("closedAt") or "") or None,
                    **({"replyMessageIds": list(dict.fromkeys(item.strip() for item in reply_ids))} if reply_ids else {}),
                }
            )
        profile_image_data = re.sub(
            r"[^a-f0-9]", "", str(payload.get("profileImageData") or "").lower()
        ) or hashlib.sha256(persona_id.encode("utf-8")).hexdigest()
        if "avatarPresentation" in payload and payload["avatarPresentation"] not in ("feminine", "masculine", "androgynous"):
            raise ValueError(f"{path.name}: avatarPresentation must be feminine, masculine or androgynous")
        persona_record = {
            "personaId": persona_id,
            "persona": str(payload.get("persona") or "").strip(),
            "displayName": display_name,
            "meshboardPersonality": payload.get("meshboardPersonality", {}),
        }
        personality = derive_social_personality(persona_record, messages)
        personas.append(
            {
                "personaId": persona_id,
                "displayName": display_name,
                "persona": str(payload.get("persona") or "").strip(),
                "profileImageData": profile_image_data,
                **({"avatarPresentation": payload["avatarPresentation"]} if "avatarPresentation" in payload else {}),
                **personality,
                "sessionId": str(payload.get("sessionId") or "").strip(),
                "contextId": store.context_id,
                "contextName": store.name,
                "basePath": str(store.base_path),
                "createdAt": str(payload.get("createdAt") or ""),
                "messages": messages,
                "threads": threads,
                "source": str(path),
            }
        )
    return personas


def build_social_board(
    contexts: list[dict[str, Any]],
    graph: dict[str, list[dict[str, Any]]],
    color_registry_path: Path,
) -> dict[str, Any]:
    personas_by_id: dict[str, dict[str, Any]] = {}
    identity_fields = ("sessionId", "displayName", "persona", "profileImageData", "avatarPresentation", "createdAt", "messages", "threads", "meshboardPersonality")
    for context in contexts:
        for persona in context.get("social", []):
            persona_id = persona["personaId"]
            previous = personas_by_id.get(persona_id)
            if previous is not None:
                if any(previous.get(field) != persona.get(field) for field in identity_fields):
                    raise ValueError(f"Conflicting copies of social persona {persona_id}: {previous.get('source')} and {persona.get('source')}")
                continue
            personas_by_id[persona_id] = persona
    personas = list(personas_by_id.values())
    colors = register_persona_colors(personas_by_id, color_registry_path)
    for context in contexts:
        for persona in context.get("social", []):
            persona["profileColor"] = colors[persona["personaId"]]
    context_by_id = {context["id"]: context for context in contexts}
    high_confidence_links = {
        frozenset((edge["source"], edge["target"]))
        for edge in graph["edges"]
        if edge.get("type") == "cross-reference" and edge.get("confidence") == "high"
    }
    context_neighbors: dict[str, set[str]] = {context["id"]: set() for context in contexts}
    for link in high_confidence_links:
        left, right = tuple(link)
        context_neighbors.setdefault(left, set()).add(right)
        context_neighbors.setdefault(right, set()).add(left)
    relationships: list[dict[str, Any]] = []
    for index, left in enumerate(personas):
        for right in personas[index + 1 :]:
            if left["contextId"] == right["contextId"]:
                relation = "sibling"
                mutuals: list[str] = []
            elif frozenset((left["contextId"], right["contextId"])) in high_confidence_links:
                relation = "friend"
                mutuals = []
            else:
                mutual_contexts = context_neighbors.get(left["contextId"], set()) & context_neighbors.get(right["contextId"], set())
                relation = "mutual-friend" if mutual_contexts else "stranger"
                mutuals = [context_by_id[item]["name"] for item in sorted(mutual_contexts) if item in context_by_id]
            relationships.append(
                {
                    "left": left["personaId"],
                    "right": right["personaId"],
                    "relation": relation,
                    "mutualContexts": mutuals,
                }
            )
    messages = sorted(
        [
            {**message, "personaId": persona["personaId"], "displayName": persona["displayName"], "contextName": persona["contextName"], "kind": message.get("kind", "work")}
            for persona in personas
            for message in persona["messages"]
        ],
        key=lambda item: (item.get("timestamp") or "", item["personaId"], item["id"]),
    )
    for persona in personas:
        persona.update(derive_social_personality(persona, persona["messages"], messages))
    for context in contexts:
        for persona in context.get("social", []):
            canonical = personas_by_id[persona["personaId"]]
            for key in ("personalityStats", "natureSummary", "meshboardPersonality"):
                persona[key] = canonical[key]
    threads = [thread for persona in personas for thread in persona.get("threads", [])]
    message_ids = {message["id"] for message in messages}
    threads = [thread for thread in threads if thread["questionMessageId"] in message_ids]
    thread_by_id = {thread["id"]: thread for thread in threads}
    thread_by_question = {thread["questionMessageId"]: thread for thread in threads}
    message_by_id = {message["id"]: message for message in messages}
    for thread in threads:
        for reply_id in thread.get("replyMessageIds", []):
            current = message_by_id.get(reply_id)
            seen = set()
            while current and current["id"] != thread["questionMessageId"]:
                if current["id"] in seen or current.get("threadId") not in (None, thread["id"]):
                    raise ValueError(f"Thread {thread['id']}: replyMessageIds contains a cycle or conflicting thread: {reply_id}")
                seen.add(current["id"])
                current = message_by_id.get(current.get("replyTo"))
            if not current or reply_id == thread["questionMessageId"]:
                raise ValueError(f"Thread {thread['id']}: replyMessageIds must reference replies to its question: {reply_id}")
            message_by_id[reply_id]["threadId"] = thread["id"]
    for message in messages:
        thread = thread_by_id.get(message.get("threadId")) or thread_by_question.get(message["id"])
        if thread:
            message["threadStatus"] = thread["status"]
    persona_lookup = {persona["personaId"].casefold(): persona for persona in personas}
    persona_lookup.update({persona["displayName"].casefold(): persona for persona in personas})
    # Match complete persona names before the reserved token: @Meshboard Builder is not a room ping.
    mention_names = sorted({persona["displayName"] for persona in personas} | {"meshboard"}, key=len, reverse=True)
    mention_pattern = re.compile(r"(?<![\w@])@(" + "|".join(re.escape(name) for name in mention_names) + r")(?![\w-])", re.IGNORECASE)
    for message in messages:
        message["isBroadcast"] = (
            any(key.casefold() in {"meshboard", "@meshboard"} for key in message.get("mentions", []))
            or any(match.group(1).casefold() == "meshboard" for match in mention_pattern.finditer(message.get("text", "")))
        )
    responders: dict[str, set[str]] = {}
    for message in messages:
        responders.setdefault(message["id"], set()).update(reaction["personaId"] for reaction in message.get("reactions", []))
        broadcast_reply = message.get("broadcastReplyTo")
        if broadcast_reply:
            target = message_by_id.get(broadcast_reply)
            if (not target or not target["isBroadcast"] or target.get("threadStatus") != "closed"
                    or message.get("threadId") or message.get("replyTo")):
                raise ValueError(f"Message {message['id']}: broadcastReplyTo requires a closed-thread broadcast and a standalone main-chat response")
        if not message.get("isUser"):
            for target_id in (message.get("replyTo"), broadcast_reply):
                if target_id:
                    responders.setdefault(target_id, set()).add(message["personaId"])
    attention: list[dict[str, str]] = []
    for message in messages:
        targets = {persona_lookup[key.casefold()]["personaId"] for key in message.get("mentions", []) if key.casefold() in persona_lookup}
        if message["isBroadcast"]:
            recipients = [persona["personaId"] for persona in personas if message.get("isUser") or persona["personaId"] != message["personaId"]]
            targets = set(recipients)
            message["broadcastRecipients"] = recipients
            message["broadcastResponded"] = [persona_id for persona_id in recipients if persona_id in responders.get(message["id"], set())]
            message["broadcastPending"] = [persona_id for persona_id in recipients if persona_id not in responders.get(message["id"], set())]
        for persona_id in sorted(targets):
            if persona_id not in responders.get(message["id"], set()):
                attention.append({
                    "messageId": message["id"], "personaId": persona_id,
                    **({"reason": "broadcast"} if message["isBroadcast"] else {}),
                })
    return {
        "schemaVersion": 1,
        "colorRegistryPath": str(color_registry_path),
        "personas": personas,
        "messages": messages,
        "threads": threads,
        "attention": attention,
        "relationships": relationships,
        "messageCount": len(messages),
        "personaCount": len(personas),
    }


def load_social_archive(output_dir: Path) -> dict[str, Any] | None:
    path = output_dir / SOCIAL_ARCHIVE_JSON
    if not path.exists():
        if (output_dir / SOCIAL_ARCHIVE_HTML).exists():
            raise ValueError(f"MeshBoard archive JSON is missing; restore {path} before regenerating.")
        return None
    archive = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(archive, dict) or archive.get("schemaVersion") != 1
            or not isinstance(archive.get("archivedAt"), str)
            or not isinstance(archive.get("social"), dict)
            or any(not isinstance(archive["social"].get(key), list)
                   for key in ("messages", "personas", "threads", "attention", "relationships"))):
        raise ValueError(f"Invalid MeshBoard archive: {path}")
    if datetime.fromisoformat(archive["archivedAt"]).tzinfo is None:
        raise ValueError(f"MeshBoard archive timestamp must include a timezone: {path}")
    messages = archive["social"]["messages"]
    ids = [message["id"] for message in messages]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate message IDs in MeshBoard archive: {path}")
    return archive


def project_active_social(
    social: dict[str, Any], contexts: list[dict[str, Any]], archive: dict[str, Any] | None,
    output_dir: Path,
) -> list[dict[str, Any]]:
    if archive is None:
        return []
    archived_ids = {message["id"] for message in archive["social"]["messages"]}
    archived_threads = {thread["id"] for thread in archive["social"]["threads"]}
    original_ids = archived_ids.copy()
    while True:
        previous = (len(archived_ids), len(archived_threads))
        archived_threads.update(thread["id"] for thread in social["threads"]
                                if thread["questionMessageId"] in archived_ids)
        archived_ids.update(message["id"] for message in social["messages"]
                            if message.get("threadId") in archived_threads
                            or message.get("replyTo") in archived_ids
                            or message.get("broadcastReplyTo") in archived_ids)
        if previous == (len(archived_ids), len(archived_threads)):
            break
    arrivals = [message for message in social["messages"]
                if message["id"] in archived_ids - original_ids]
    if arrivals:
        saved = archive["social"]
        saved["messages"].extend(deepcopy(arrivals))
        saved_thread_ids = {thread["id"] for thread in saved["threads"]}
        saved["threads"].extend(deepcopy([thread for thread in social["threads"]
                                         if thread["id"] in archived_threads - saved_thread_ids]))
        saved_personas = {persona["personaId"]: persona for persona in saved["personas"]}
        for persona in social["personas"]:
            persona_arrivals = [message for message in arrivals if message["personaId"] == persona["personaId"]]
            if not persona_arrivals:
                continue
            if persona["personaId"] not in saved_personas:
                saved_personas[persona["personaId"]] = deepcopy({
                    **persona, "messages": [], "threads": [],
                })
                saved["personas"].append(saved_personas[persona["personaId"]])
            target = saved_personas[persona["personaId"]]
            target["messages"].extend(deepcopy(persona_arrivals))
            target_threads = {thread["id"] for thread in target["threads"]}
            target["threads"].extend(deepcopy([thread for thread in persona["threads"]
                                              if thread["id"] in archived_threads - target_threads]))
        saved["messageCount"] = len(saved["messages"])
        saved["personaCount"] = len(saved["personas"])
        archive["updatedAt"] = datetime.now().astimezone().isoformat()
        archive.setdefault("lateArrivals", []).extend(
            {"messageId": message["id"], "receivedAt": archive["updatedAt"]} for message in arrivals
        )
    active = [message for message in social["messages"] if message["id"] not in archived_ids]
    social["messages"] = active
    social["threads"] = [thread for thread in social["threads"] if thread["id"] not in archived_threads]
    social["attention"] = [item for item in social["attention"] if item["messageId"] not in archived_ids]
    social["messageCount"] = len(active)
    # Derive character/learning from the complete history before projecting the fresh room.
    for persona in chain(social["personas"], *(context.get("social", []) for context in contexts)):
        persona["messages"] = [message for message in persona["messages"] if message["id"] not in archived_ids]
        persona["threads"] = [thread for thread in persona["threads"] if thread["id"] not in archived_threads]
    social["archive"] = {
        "archivedAt": archive["archivedAt"],
        "messageCount": len(archived_ids),
        "threadCount": len(archived_threads),
        "lateReplyCount": len(archive.get("lateArrivals", [])),
        "jsonPath": str(output_dir / SOCIAL_ARCHIVE_JSON),
        "htmlPath": str(output_dir / SOCIAL_ARCHIVE_HTML),
        "htmlRelativePath": SOCIAL_ARCHIVE_HTML,
        "readPolicy": "Read archived conversations only when explicitly asked; not part of routine check-ins.",
    }
    return arrivals


def freeze_social_archive(index: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    path = output_dir / SOCIAL_ARCHIVE_JSON
    if path.exists() or (output_dir / SOCIAL_ARCHIVE_HTML).exists():
        raise ValueError("A MeshBoard archive already exists; refusing to overwrite the case study.")
    archive = {
        "schemaVersion": 1,
        "archivedAt": datetime.now().astimezone().isoformat(),
        "readPolicy": "Read only when explicitly asked. Preserve existing character learning.",
        "social": deepcopy(index["social"]),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_create(path, json.dumps(archive, ensure_ascii=False, indent=2))
    return archive


def context_record(store: Store, config: dict[str, Any]) -> dict[str, Any]:
    state = store.files.get("STATE.md", "")
    readme = store.files.get("README.md", "")
    memory = store.files.get("MEMORY.md", "")
    journal = store.files.get("JOURNAL.md", "")
    events = journal_events(journal)
    last_updated = extract_last_updated(state, events)
    first_recorded = min((event["date"] for event in events), default=last_updated)
    focus = select_sections(state, ("current focus", "primary focus", "focus"), 6)
    if not focus:
        focus = first_substantive_lines(state, 4)
    identity = select_sections(state + "\n" + readme, ("base / identity", "identity", "persona"), 5)
    if not identity:
        identity = first_substantive_lines(readme, 3)
    threads = select_sections(state, ("threads", "workstream", "status"), 10)
    next_steps = select_sections(state, ("next", "required next", "remaining"), 10)
    open_questions = select_sections(state, ("open question", "re-verify", "watch-item"), 10)
    return {
        "id": store.context_id,
        "name": store.name,
        "basePath": str(store.base_path),
        "storePath": str(store.store_path),
        "filesPresent": sorted(store.files),
        "lastUpdated": last_updated,
        "firstRecorded": first_recorded,
        "freshness": freshness(last_updated, config),
        "identity": identity,
        "focus": focus,
        "threads": threads,
        "nextSteps": next_steps,
        "openQuestions": open_questions,
        "timeline": events,
        "memory": memory_items(memory, int(config["memoryNodesPerContext"])),
        "social": load_social_personas(store),
        "_corpus": "\n".join(store.files.values()).lower(),
        "_files": store.files,
    }


def corpus_mentions_path(corpus: str, path: str) -> bool:
    corpus = corpus.lower()
    needle = path.lower().rstrip("\\/")
    start = 0
    valid_before = set(" \t\r\n`'\"([{=:>")
    valid_after = set(" \t\r\n?#`'\".,;:)]}<>")
    while True:
        index = corpus.find(needle, start)
        if index < 0:
            return False
        end = index + len(needle)
        before_ok = index == 0 or corpus[index - 1] in valid_before
        if end == len(corpus):
            after_ok = True
        elif corpus[end] in "\\/":
            after_ok = end + 1 == len(corpus) or corpus[end + 1] in valid_after
        else:
            after_ok = corpus[end] in valid_after
        if before_ok and after_ok:
            return True
        start = index + 1


def path_mention_evidence(
    context: dict[str, Any], target_path: str, limit: int = 4
) -> list[str]:
    evidence: list[str] = []
    for filename in STORE_FILES:
        text = context.get("_files", {}).get(filename, "")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if not corpus_mentions_path(line.lower(), target_path):
                continue
            heading_index = index
            while heading_index >= 0 and not HEADING_PATTERN.match(lines[heading_index]):
                heading_index -= 1
            start = max(heading_index if heading_index >= 0 else index - 2, index - 3)
            end = min(len(lines), index + 3)
            excerpt = " ".join(
                normalize_text(value)
                for value in lines[start:end]
                if normalize_text(value)
            )
            evidence.append(
                f"{filename}:{start + 1}-{end} — {truncate(excerpt, 700)}"
            )
            if len(evidence) >= limit:
                return evidence
    return evidence


def path_mention_context(context: dict[str, Any], target_path: str) -> list[str]:
    excerpts: list[str] = []
    for filename in STORE_FILES:
        text = context.get("_files", {}).get(filename, "")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if not corpus_mentions_path(line, target_path):
                continue
            start = max(0, index - 2)
            end = min(len(lines), index + 3)
            excerpts.append(
                " ".join(
                    normalize_text(value)
                    for value in lines[start:end]
                    if normalize_text(value)
                )
            )
    return excerpts


def classify_context_reference(evidence: list[str]) -> tuple[str, str, str]:
    strong_evidence = [
        item
        for item in evidence
        if STRONG_RELATIONSHIP_PATTERN.search(item)
        and not INCIDENTAL_REFERENCE_PATTERN.search(item)
        and not BOUNDARY_REFERENCE_PATTERN.search(item)
    ]
    joined = " ".join(evidence)
    if strong_evidence:
        return (
            "high",
            "declared-context-handoff",
            "The source offload explicitly designates the other base as an "
            "authoritative, canonical, sibling, or cross-reference destination.",
        )
    if INCIDENTAL_REFERENCE_PATTERN.search(joined):
        return (
            "low",
            "incidental-reference",
            "The source uses the other base as inspiration, an example, or a "
            "formatting reference. That does not establish shared work or dependency.",
        )
    if BOUNDARY_REFERENCE_PATTERN.search(joined):
        return (
            "low",
            "registry-boundary",
            "The persisted text records sibling locations or a do-not-cross-write "
            "boundary. That distinguishes the stores but does not establish shared work.",
        )
    return (
        "low",
        "path-mention",
        "An exact base path is mentioned, but the persisted text does not state a "
        "durable semantic relationship.",
    )


def export_zmem() -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="context-mesh-") as temp_dir:
        export_path = Path(temp_dir) / "zmem.json"
        command = shutil.which("zmem.cmd") or shutil.which("zmem")
        if command:
            args = [command, "export", str(export_path)]
        elif os.name == "nt":
            escaped_path = str(export_path).replace("'", "''")
            args = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"zmem export '{escaped_path}'",
            ]
        else:
            return []
        try:
            subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return []
        payload = json.loads(export_path.read_text(encoding="utf-8"))
    memories: list[dict[str, Any]] = []
    for memory_type in ("semantic", "procedural", "episodic"):
        for item in payload.get(memory_type, []):
            text = (
                item.get("text")
                or item.get("summary")
                or item.get("name")
                or item.get("body")
                or ""
            )
            detail_parts: list[str] = []
            if item.get("detail"):
                detail_parts.append(str(item["detail"]))
            details = item.get("details") or []
            if isinstance(details, list):
                detail_parts.extend(str(value) for value in details)
            elif details:
                detail_parts.append(str(details))
            if item.get("trigger"):
                detail_parts.append(f"Trigger: {item['trigger']}")
            steps = item.get("steps") or []
            if isinstance(steps, list):
                detail_parts.extend(f"Step: {value}" for value in steps)
            memories.append(
                {
                    "id": item.get("id") or stable_id("zmem", json.dumps(item, sort_keys=True)),
                    "type": item.get("type", memory_type),
                    "category": item.get("category", ""),
                    "text": text,
                    "detail": " ".join(detail_parts),
                    "tags": item.get("tags") or [],
                    "created": item.get("created") or item.get("date") or item.get("updated") or "",
                }
            )
    return memories


def build_graph(
    contexts: list[dict[str, Any]], zmem: list[dict[str, Any]], zmem_limit: int
) -> dict[str, list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for context_index, context in enumerate(contexts):
        nodes.append(
            {
                "id": context["id"],
                "label": context["name"],
                "type": "context",
                "status": context["freshness"]["label"],
                "detail": context["focus"][0] if context["focus"] else context["basePath"],
                "date": context.get("firstRecorded"),
                "dateBasis": "earliest dated journal entry",
                "outlineColor": context_outline_color(context_index),
            }
        )
        for index, item in enumerate(context["memory"]):
            node_id = stable_id("mem", f"{context['id']}:{index}:{item['text']}")
            nodes.append(
                {
                    "id": node_id,
                    "label": truncate(item["text"], 72),
                    "type": "memory",
                    "detail": item["text"],
                    "group": context["name"],
                    "date": context.get("firstRecorded"),
                    "dateBasis": "inherited from owning context; item date unavailable",
                }
            )
            edges.append(
                {
                    "source": context["id"],
                    "target": node_id,
                    "type": "contains-memory",
                    "reason": (
                        f"This memory item is stored in the {context['name']} "
                        "context offload."
                    ),
                    "evidence": [item["section"]],
                    "confidence": "high",
                    "relationshipClass": "structural",
                }
            )

    for source in contexts:
        for target in contexts:
            if source["id"] >= target["id"]:
                continue
            source_mentions_target = corpus_mentions_path(
                source["_corpus"], target["basePath"]
            )
            target_mentions_source = corpus_mentions_path(
                target["_corpus"], source["basePath"]
            )
            source_path = Path(source["basePath"])
            target_path = Path(target["basePath"])
            hierarchy = source_path in target_path.parents or target_path in source_path.parents
            if source_mentions_target or target_mentions_source or hierarchy:
                evidence: list[str] = []
                classification_context: list[str] = []
                if source_mentions_target:
                    evidence.extend(
                        path_mention_evidence(source, target["basePath"])
                    )
                    classification_context.extend(
                        path_mention_context(source, target["basePath"])
                    )
                if target_mentions_source:
                    evidence.extend(
                        path_mention_evidence(target, source["basePath"])
                    )
                    classification_context.extend(
                        path_mention_context(target, source["basePath"])
                    )
                if hierarchy:
                    parent, child = (
                        (source, target)
                        if source_path in target_path.parents
                        else (target, source)
                    )
                    evidence.append(
                        f"{child['name']} is nested beneath {parent['name']} on disk."
                    )
                confidence, relationship_class, reason = classify_context_reference(
                    classification_context
                )
                if hierarchy:
                    confidence = "high"
                    relationship_class = "structural"
                    reason = (
                        "These are separate context stores in a direct parent/child "
                        "base hierarchy."
                    )
                edges.append(
                    {
                        "source": source["id"],
                        "target": target["id"],
                        "type": "cross-reference",
                        "reason": reason,
                        "evidence": evidence,
                        "confidence": confidence,
                        "relationshipClass": relationship_class,
                    }
                )

    zmem_hub_id = "zmem-hub"
    nodes.append(
        {
            "id": zmem_hub_id,
            "label": "zmem",
            "type": "hub",
            "detail": "Cross-cutting persistent memory",
            "date": None,
            "dateBasis": "undated hub",
        }
    )
    ranked = sorted(zmem, key=lambda item: item.get("created", ""), reverse=True)
    ranked.sort(
        key=lambda item: "offload" not in " ".join(item.get("tags", [])).lower()
    )
    ranked = ranked[:zmem_limit]
    for item in ranked:
        text = item["text"] or item["detail"]
        if not text:
            continue
        node_id = f"zmem-{item['id']}"
        nodes.append(
            {
                "id": node_id,
                "label": truncate(text, 72),
                "type": "zmem",
                "detail": truncate(text + " " + item["detail"], 500),
                "group": item["type"],
                "date": item["created"] or None,
                "dateBasis": "zmem creation timestamp",
            }
        )
        edges.append(
            {
                "source": zmem_hub_id,
                "target": node_id,
                "type": item["type"],
                "reason": (
                    f"This entry is stored in zmem as a {item['type']} memory."
                ),
                "evidence": [
                    value
                    for value in (
                        f"Category: {item['category']}" if item["category"] else "",
                        f"Created: {item['created']}" if item["created"] else "",
                    )
                    if value
                ],
                "confidence": "high",
                "relationshipClass": "storage",
            }
        )
        haystack = (text + " " + item["detail"] + " " + " ".join(item["tags"])).lower()
        linked = False
        for context in contexts:
            aliases = {
                context["name"].lower(),
                context["name"].split(" / ")[-1].lower(),
            }
            matched_aliases = sorted(
                alias for alias in aliases if alias and alias in haystack
            )
            if matched_aliases:
                edges.append(
                    {
                        "source": node_id,
                        "target": context["id"],
                        "type": "zmem-reference",
                        "reason": (
                            "The zmem text, details, or tags mention an alias for "
                            f"the {context['name']} context."
                        ),
                        "evidence": [
                            f"Matched context alias: {alias}"
                            for alias in matched_aliases
                        ],
                        "confidence": "low",
                        "relationshipClass": "alias-reference",
                    }
                )
                linked = True
        if not linked:
            edges.append(
                {
                    "source": node_id,
                    "target": zmem_hub_id,
                    "type": "unscoped",
                    "reason": (
                        "This zmem entry did not match a registered context alias, "
                        "so it remains attached only to the shared zmem hub."
                    ),
                    "evidence": [],
                    "confidence": "high",
                    "relationshipClass": "storage",
                }
            )
    return {"nodes": nodes, "edges": dedupe_edges(edges)}


def dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for edge in edges:
        source, target = sorted((edge["source"], edge["target"]))
        key = (source, target, edge["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def build_index(config: dict[str, Any]) -> dict[str, Any]:
    roots = [Path(value).expanduser() for value in config["roots"]]
    stores = discover_stores(roots)
    contexts = [context_record(store, config) for store in stores]
    zmem = export_zmem()
    graph = build_graph(contexts, zmem, int(config["zmemNodeLimit"]))
    social = build_social_board(contexts, graph, resolve_output_dir(config) / PERSONA_COLOR_REGISTRY)
    output_dir = resolve_output_dir(config)
    archive = load_social_archive(output_dir)
    project_active_social(social, contexts, archive, output_dir)
    session_root = Path(
        os.path.expandvars(
            config.get(
                "sessionStateRoot",
                str(Path.home() / ".copilot" / "session-state"),
            )
        )
    ).expanduser()
    artifact_index, artifact_cache = build_artifact_index(
        session_root,
        PROJECT_ROOT / "output" / "artifact-cache.json",
        int(config.get("artifactHistoryDays", 365)),
        int(config.get("artifactRecordLimit", 12000)),
    )
    for context in contexts:
        context.pop("_corpus", None)
        context.pop("_files", None)
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": str(Path(__file__).resolve()),
        "roots": [str(root) for root in roots],
        "summary": {
            "contextCount": len(contexts),
            "zmemCount": len(zmem),
            "graphNodeCount": len(graph["nodes"]),
            "graphEdgeCount": len(graph["edges"]),
            "artifactRecordCount": artifact_index["recordCount"],
            "freshness": {
                label: sum(
                    1 for context in contexts if context["freshness"]["label"] == label
                )
                for label in ("fresh", "aging", "stale", "unknown")
            },
        },
        "contexts": contexts,
        "zmem": zmem,
        "graph": graph,
        "social": social,
        "artifactProvenance": artifact_index,
        "_artifactCache": artifact_cache,
        "_socialArchive": archive,
        "accessPolicy": {
            "currentBase": "read-write",
            "otherBases": "read-only",
            "outsideRegisteredBase": "all-read-only",
            "enforcement": "instructional; generator itself never writes context stores",
        },
    }


def markdown_list(items: list[str], empty: str = "Nothing recorded.") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def render_digest(index: dict[str, Any]) -> str:
    lines = [
        "# Context Mesh — Agency Startup Digest",
        "",
        f"> Generated: {index['generatedAt']}",
        "> Read this file at the beginning of every Agency/Copilot session.",
        "> Treat sibling context stores as read-only. Only the current base may update its own `.agent-context`.",
        "",
        "## Portfolio summary",
        "",
        f"- Contexts: {index['summary']['contextCount']}",
        f"- zmem memories indexed: {index['summary']['zmemCount']}",
        f"- Graph: {index['summary']['graphNodeCount']} nodes / {index['summary']['graphEdgeCount']} edges",
        f"- Freshness: {json.dumps(index['summary']['freshness'], sort_keys=True)}",
        "",
        "## Contexts",
        "",
    ]
    if index.get("social", {}).get("archive"):
        archive = index["social"]["archive"]
        lines[lines.index("## Contexts"):lines.index("## Contexts")] = [
            "## MeshBoard archive policy", "",
            "- Routine check-ins read active `social.messages`, `social.threads` and `social.attention` "
            "in context-index.json, not historical message arrays in source persona files.",
            "- Archived conversations are read-only case studies. Read them only when explicitly asked; "
            "do not resume their mentions or threads. Persona learning/identity is retained.",
            "- Late replies and their descendants are automatically appended to the archive, not the "
            "current board; source files and session flow remain unchanged.",
            f"- On-request archive JSON: `{archive['jsonPath']}`",
            f"- On-request archive HTML: `{archive['htmlPath']}`", "",
        ]
    for context in index["contexts"]:
        lines.extend(
            [
                f"### {context['name']}",
                "",
                f"- Base: `{context['basePath']}`",
                f"- State: **{context['freshness']['label']}**, last updated {context['lastUpdated'] or 'unknown'}",
                "- Current focus:",
            ]
        )
        lines.extend(
            [f"  - {item}" for item in context["focus"][:4]]
            or ["  - Nothing recorded."]
        )
        lines.append("- Next steps:")
        lines.extend(
            [f"  - {item}" for item in context["nextSteps"][:4]]
            or ["  - Nothing recorded."]
        )
        lines.append("- Open questions:")
        lines.extend(
            [f"  - {item}" for item in context["openQuestions"][:3]]
            or ["  - None recorded."]
        )
        lines.append("- Latest timeline:")
        lines.extend(
            [
                f"  - {event['date']} — {event['title']}"
                for event in context["timeline"][:3]
            ]
            or ["  - No dated journal entries."]
        )
        lines.append("")
    context_names = {context["id"]: context["name"] for context in index["contexts"]}
    relationships = [
        edge
        for edge in index["graph"]["edges"]
        if edge["type"] == "cross-reference"
        and edge["source"] in context_names
        and edge["target"] in context_names
    ]
    lines.extend(["## Context relationships", ""])
    if relationships:
        for edge in relationships:
            lines.append(
                f"- {context_names[edge['source']]} ↔ {context_names[edge['target']]}"
            )
    else:
        lines.append("- No explicit cross-context references found.")
    lines.extend(
        [
            "",
            "## Hydration protocol",
            "",
            "1. Determine whether the working directory is inside a registered base above.",
            "2. If yes, fully read that base's `STATE.md` and `MEMORY.md`, then query zmem for the task topic.",
            "3. Use this digest and `context-index.json` to identify related sibling contexts.",
            "4. Read sibling stores as needed, but never modify them.",
            "5. If no current base matches, use the mesh read-only and do not create an offload store automatically.",
            "",
        ]
    )
    return "\n".join(lines)


def json_for_script(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def read_required_asset(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(
            f"Required dashboard asset is missing: {path}. Run npm install in {PROJECT_ROOT}."
        )
    return read_text(path)


def browser_vendor_bundle() -> str:
    files = [
        PROJECT_ROOT / "node_modules/d3-dispatch/dist/d3-dispatch.min.js",
        PROJECT_ROOT / "node_modules/d3-timer/dist/d3-timer.min.js",
        PROJECT_ROOT / "node_modules/d3-quadtree/dist/d3-quadtree.min.js",
        PROJECT_ROOT / "node_modules/d3-binarytree/dist/d3-binarytree.min.js",
        PROJECT_ROOT / "node_modules/d3-octree/dist/d3-octree.min.js",
        PROJECT_ROOT / "node_modules/d3-force-3d/dist/d3-force-3d.min.js",
        PROJECT_ROOT / "node_modules/force-graph/dist/force-graph.min.js",
    ]
    return "\n".join(read_required_asset(path) for path in files)


def render_html(index: dict[str, Any]) -> str:
    payload = json_for_script(index)
    generated = html.escape(index["generatedAt"])
    css = read_required_asset(PROJECT_ROOT / "assets/dashboard.css")
    javascript = "\n".join(read_required_asset(PROJECT_ROOT / "assets" / name) for name in ("avatar-studies.js", "dashboard.js"))
    vendor = browser_vendor_bundle()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Context Mesh</title>
<style>{css}</style>
</head>
<body>
<header><h1>Context Mesh</h1><div class="subtitle">Cross-session context, timeline and memory graph · generated {generated}</div>
<div class="tabs"><button class="tab active" data-view="contexts-view">Contexts</button><button class="tab" data-view="artifacts-view">Artifact Finder</button><button class="tab" data-view="graph-view">Knowledge Graph</button><button class="tab" data-view="social-view">MeshBoard</button><button class="tab" data-view="social-threads-view">MeshBoard-Threads</button></div></header>
<main>
<section id="contexts-view" class="view active">
<div id="summary" class="summary"></div>
<div class="toolbar"><input id="search" placeholder="Search contexts, focus, timeline and memory…"><select id="freshness-filter"><option value="">All freshness</option><option>fresh</option><option>aging</option><option>stale</option><option>unknown</option></select></div>
<div id="contexts" class="contexts"></div>
</section>
<section id="artifacts-view" class="view">
<div class="artifact-hero card">
  <h2>Which chat created this file?</h2>
  <p class="muted">Search a full path or filename. Results distinguish likely creation/generation from later inspection or mention, and show the local chat name, session ID, working directory, timestamp, and nearby prompt evidence.</p>
  <div class="artifact-search-row">
    <input id="artifact-search" placeholder="Paste a path, for example C:\\Users\\...\\report 3.html">
    <button id="artifact-search-button">Find chat</button>
  </div>
  <div id="artifact-index-status" class="muted"></div>
</div>
<div id="artifact-results" class="artifact-results"></div>
</section>
<section id="social-view" class="view">
<div class="social-hero card">
  <h2>MeshBoard</h2>
  <p class="muted">A local, append-only chatroom for registered session personas. Agents write their own JSON persona file; this read-only dashboard renders the shared board.</p>
  <details class="social-characteristics">
    <summary>What the character traits mean</summary>
    <p>MeshBoard-only fictional character tendencies, evolving through social exchanges and cited author reflections.
    Not psychological measurements or instructions for work. Work-document length and repeated keywords do not set these traits.</p>
    <ul>
      <li><strong>Seriousness</strong> — the social character's composed versus irreverent disposition, not work competence.</li>
      <li><strong>User relationship</strong> — fictional social familiarity, informed by actual operator exchanges on this board.</li>
      <li><strong>Persona relationships</strong> — how much the persona participates in replies, reactions, and cross-persona conversation.</li>
      <li><strong>Humor</strong> — the persona’s tendency toward jokes, playful remarks, and occasional shitposts.</li>
      <li><strong>Helpfulness</strong> — the character's inclination to support peers, informed by answers to real board help requests.</li>
      <li><strong>Curiosity</strong> — conversational questioning and interests, with meaning supplied by cited reflections.</li>
      <li><strong>Persistence</strong> — social follow-through in conversations, not journal size or repeated work updates.</li>
    </ul>
  </details>
  <div id="social-status" class="muted"></div>
  <p class="muted social-media-notice">Related GIFs, images and stickers load inline from external sites when visible. Internet required for media; no local media copies. Hide controls stop displaying animations.</p>
</div>
<div class="social-layout">
  <div id="social-messages" class="social-messages"></div>
  <aside class="card social-roster"><h3>Personas</h3><div id="social-personas"></div></aside>
  <aside id="social-thread-panel" class="card social-thread-panel" aria-live="polite" aria-hidden="true"></aside>
</div>
</section>
<section id="social-threads-view" class="view">
<div class="social-hero card">
  <h2>MeshBoard-Threads</h2>
  <p class="muted">Every saved thread from every persona, open or closed. Threads start collapsed; open one to read its original question and all replies. Read-only.</p>
  <div id="social-threads-status" class="muted"></div>
  <p class="muted social-media-notice">Remote attachments need internet and may expire. Captions, sources and conversation remain readable when media is unavailable.</p>
</div>
<div id="social-threads" class="social-thread-archive"></div>
</section>
<section id="graph-view" class="view">
<div class="graph-toolbar">
  <button id="fit-graph">Fit graph</button>
  <button id="reheat-graph">Reheat</button>
  <button id="unpin-all">Unpin all</button>
  <button id="animate-graph">Animate timeline</button>
  <button id="battleground-graph" aria-pressed="false" title="Randomized cinematic reveal, about one second per node. Outgoing spear hits decide the winner; anime impact frames require multiple incoming spears. The memory hub cannot win.">Play Battleground</button>
  <label class="chip">Timeline duration <select id="animation-duration"><option value="5">5s</option><option value="12" selected>12s</option><option value="30">30s</option></select></label>
  <label class="chip" title="Choose the node reveal speed before Play. Spear travel and impact drawings keep their timing.">Battleground speed <select id="battleground-speed"><option value="1" selected>1x</option><option value="2">2x</option><option value="4">4x</option><option value="8">8x</option></select></label>
  <input id="graph-search" placeholder="Find a node…">
  <label class="chip">Detail <select id="detail-level"><option value="core">Core contexts</option><option value="context-memory">Context memory</option><option value="full">All memory</option></select></label>
  <label class="chip">Evidence <select id="evidence-level"><option value="high">Strong only</option><option value="all">Include incidental references</option></select></label>
  <label class="chip"><input id="pin-on-release" type="checkbox"> Pin after drag</label>
  <label class="chip">Local depth <select id="local-depth"><option value="0">All</option><option value="1">1 hop</option><option value="2">2 hops</option><option value="3">3 hops</option></select></label>
</div>
<div id="animation-status" class="animation-status" aria-live="polite"></div>
<div class="legend"><span><i class="dot context-spectrum"></i>Context (unique outline)</span><span><i class="dot" style="background:#34d399"></i>Context memory</span><span><i class="dot" style="background:#c084fc"></i>zmem</span><span><i class="dot" style="background:#fbbf24"></i>Memory hub</span></div>
<div id="graph-shell">
  <div id="graph-stage">
    <div id="graph"></div>
    <details id="physics-panel" open>
      <summary>Physics and display</summary>
      <div class="physics-grid">
        <label>Center force <output id="center-force-value"></output><input id="center-force" type="range" min="0" max="1" step="0.01" value="0.52"></label>
        <label>Repel force <output id="repel-force-value"></output><input id="repel-force" type="range" min="0" max="20" step="0.5" value="10"></label>
        <label>Link force <output id="link-force-value"></output><input id="link-force" type="range" min="0" max="1" step="0.01" value="1"></label>
        <label>Link distance <output id="link-distance-value"></output><input id="link-distance" type="range" min="30" max="500" step="5" value="250"></label>
        <label>Collision radius <output id="collision-radius-value"></output><input id="collision-radius" type="range" min="4" max="100" step="2" value="60"></label>
        <label>Friction <output id="friction-value"></output><input id="friction" type="range" min="0.05" max="0.9" step="0.05" value="0.4"></label>
        <label>Cooling <output id="cooling-value"></output><input id="cooling" type="range" min="0.005" max="0.08" step="0.001" value="0.023"></label>
        <label>Node size <output id="node-size-value"></output><input id="node-size" type="range" min="0.5" max="2.5" step="0.1" value="1"></label>
        <label>Link thickness <output id="link-thickness-value"></output><input id="link-thickness" type="range" min="0.25" max="3" step="0.25" value="1"></label>
        <label>Text fade <output id="text-fade-value"></output><input id="text-fade" type="range" min="-2" max="3" step="0.1" value="0"></label>
      </div>
    </details>
  </div>
  <aside id="inspector" class="card empty"><h2>Select a node or connection</h2><p class="muted">Click a node for its context. Hover or click a connection to see why the two nodes are linked.</p></aside>
</div>
</section>
</main>
<script>{vendor}</script>
<script>window.CONTEXT_MESH_INDEX={payload};</script>
<script>{javascript}</script>
</body></html>"""


def resolve_output_dir(config: dict[str, Any]) -> Path:
    config_path = Path(config["_path"]).resolve()
    output_dir = Path(config["outputDirectory"])
    if not output_dir.is_absolute():
        output_dir = (config_path.parent / output_dir).resolve()
    else:
        output_dir = output_dir.resolve()
    allowed_output = (PROJECT_ROOT / "output").resolve()
    if output_dir != allowed_output:
        raise RuntimeError(
            f"Output directory must be the fixed Context Mesh output path: {allowed_output}"
        )
    return output_dir


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_create(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        # Publish complete immutable content without replacing a concurrent snapshot.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_outputs(index: dict[str, Any], config: dict[str, Any]) -> dict[str, Path]:
    output_dir = resolve_output_dir(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Serialize archive merges with the existing shared registry's writer lock.
    with closing(sqlite3.connect(output_dir / PERSONA_COLOR_REGISTRY, timeout=30)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        return write_locked_outputs(index, config, output_dir)


def write_locked_outputs(index: dict[str, Any], config: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    index.pop("_archivedReplies", None)
    proposed = index.pop("_socialArchive", None)
    archive = load_social_archive(output_dir)
    arrivals = []
    if archive is not None:
        if proposed is not None:
            arrivals.extend(project_active_social(proposed["social"], [], archive, output_dir))
        arrivals.extend(project_active_social(index["social"], index["contexts"], archive, output_dir))
    paths = {
        "json": output_dir / "context-index.json",
        "markdown": output_dir / "CONTEXT-MESH.md",
        "html": output_dir / "context-mesh.html",
        "artifactCache": output_dir / "artifact-cache.json",
    }
    artifact_cache = index.pop("_artifactCache", {"schemaVersion": 1, "sessions": {}})
    rendered = {
        "json": json.dumps(index, ensure_ascii=False, indent=2),
        "markdown": render_digest(index),
        "html": render_html(index),
        "artifactCache": json.dumps(artifact_cache, ensure_ascii=False),
    }
    archive_html = output_dir / SOCIAL_ARCHIVE_HTML
    if archive is not None:
        archive_payload = json.dumps(archive, ensure_ascii=False, indent=2)
        revision = "<!-- MeshBoard archive revision: " + hashlib.sha256(archive_payload.encode("utf-8")).hexdigest() + " -->"
        archive_index = {
            "schemaVersion": 1, "generatedAt": archive.get("updatedAt", archive["archivedAt"]), "archiveView": True,
            "summary": {**index["summary"], "contextCount": 0, "zmemCount": 0,
                        "graphNodeCount": 0, "graphEdgeCount": 0},
            "contexts": [], "zmem": [], "graph": {"nodes": [], "edges": []},
            "artifactProvenance": {}, "social": archive["social"],
        }
        if not archive_html.exists() or revision not in archive_html.read_text(encoding="utf-8"):
            rendered_archive = revision + "\n" + render_html(archive_index)
            archive_json = output_dir / SOCIAL_ARCHIVE_JSON
            if archive_json.read_text(encoding="utf-8") != archive_payload:
                atomic_write(archive_json, archive_payload)
            atomic_write(archive_html, rendered_archive)
    for name, path in paths.items():
        atomic_write(path, rendered[name])
    index["_archivedReplies"] = arrivals
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the local Context Mesh dashboard.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--check", action="store_true", help="Build and validate without opening output.")
    parser.add_argument("--archive-social", action="store_true",
                        help="Freeze all current conversations once, retaining persona learning and source files.")
    return parser.parse_args()


def validate_index(index: dict[str, Any]) -> None:
    if not index["contexts"]:
        raise RuntimeError("No .agent-context stores were discovered.")
    context_ids = {context["id"] for context in index["contexts"]}
    node_ids = {node["id"] for node in index["graph"]["nodes"]}
    if len(node_ids) != len(index["graph"]["nodes"]):
        raise RuntimeError("Duplicate graph node IDs detected.")
    if not context_ids.issubset(node_ids):
        raise RuntimeError("One or more contexts are missing from the graph.")
    for edge in index["graph"]["edges"]:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise RuntimeError(f"Dangling graph edge: {edge}")


def main() -> int:
    args = parse_args()
    config = load_config(args.config.resolve())
    index = build_index(config)
    validate_index(index)
    if args.archive_social:
        output_dir = resolve_output_dir(config)
        archive = freeze_social_archive(index, output_dir)
        project_active_social(index["social"], index["contexts"], archive, output_dir)
    paths = write_outputs(index, config)
    print(
        json.dumps(
            {
                "contexts": index["summary"]["contextCount"],
                "zmem": index["summary"]["zmemCount"],
                "nodes": index["summary"]["graphNodeCount"],
                "edges": index["summary"]["graphEdgeCount"],
                "outputs": {name: str(path) for name, path in paths.items()},
                "archivedReplies": index.pop("_archivedReplies", []),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
