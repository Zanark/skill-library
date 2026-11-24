"""Deterministic, opt-in MeshBoard Experiment 2 bookkeeping; no model calls."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


POLICY_FILE = "meshboard-experiment-2.json"
STATE_FILE = "meshboard-experiment-2-state.json"
IST = timezone(timedelta(hours=5, minutes=30))
LIMITS = {"gifs": 5, "memes": 5, "laughter": 3}
LAUGH_EMOJI = {"\U0001f602", "\U0001f923", "\U0001f606", "\U0001f639"}


def moment(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Experiment 2 timestamps must be ISO-8601 strings with a timezone")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Experiment 2 timestamps must include a timezone")
    return parsed


def required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Experiment 2 {label} must be a nonempty string")
    return value


def fresh_state(policy: dict[str, Any]) -> dict[str, Any]:
    return {"schemaVersion": 1, "policy": {k: v for k, v in policy.items() if k != "enabled"},
            "initialized": False, "messages": {}, "events": {}}


def message_record(message: dict[str, Any], thread_roots: set[str]) -> dict[str, Any]:
    attachments = message.get("attachments", [])
    gifs = sum(item["type"] == "gif" or item.get("animated", False)
               or urlsplit(item["url"]).path.lower().endswith(".gif")
               for item in attachments)
    memes = max(int(message.get("isMeme", False)),
                sum(item.get("isMeme", False) or item["type"] == "sticker" for item in attachments))
    funny = message.get("findsFunny", False) or any(emoji in message.get("text", "") for emoji in LAUGH_EMOJI)
    return {
        "id": message["id"], "personaId": message["personaId"],
        "timestamp": message["timestamp"], "replyTo": message.get("replyTo"),
        "threadOnly": bool(message.get("threadId") or message["id"] in thread_roots),
        "isUser": message.get("isUser", False), "gifs": gifs, "memes": memes,
        "funnyTarget": message.get("replyTo") if funny else None,
        "unscopedLaughter": bool(funny and not message.get("replyTo")),
    }


def apply_experiment(
    social: dict[str, Any], contexts: list[dict[str, Any]], policy: dict[str, Any] | None,
    saved: dict[str, Any] | None, history: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Return a new ledger only after all input and budget checks succeed."""
    if policy is not None and (not isinstance(policy, dict) or policy.get("schemaVersion") != 1 or type(policy.get("enabled")) is not bool
            or set(policy) - {"schemaVersion", "enabled", "startedAt", "egoSeeds", "baseline"}):
        raise ValueError("Invalid Experiment 2 policy")
    if policy is None or not policy["enabled"]:
        social["experiment2"] = {"enabled": False}
        for persona in social["personas"]:
            persona.pop("socialStanding", None)
        for context in contexts:
            for persona in context.get("social", []):
                persona.pop("socialStanding", None)
        return None
    now = now or datetime.now(IST)
    started = moment(policy.get("startedAt"))
    if started > now:
        raise ValueError("Experiment 2 cannot start in the future")
    if (not isinstance(saved, dict) or saved.get("schemaVersion") != 1
            or type(saved.get("initialized")) is not bool
            or not isinstance(saved.get("messages"), dict) or not isinstance(saved.get("events"), dict)
            or saved.get("policy") != {k: v for k, v in policy.items() if k != "enabled"}):
        raise ValueError("Missing or incompatible Experiment 2 ledger; restore it, do not reset counters")
    state = deepcopy(saved)
    personas = {p["personaId"]: p for p in social["personas"]}
    roots = {t["questionMessageId"] for t in social["threads"]}
    incoming: dict[str, dict[str, Any]] = {}
    known_owners = {record["personaId"] for record in state["messages"].values()}
    for message in history:
        previous = incoming.get(message["id"])
        if previous is not None and previous["personaId"] != message["personaId"]:
            raise ValueError(f"Experiment 2 conflicting message ownership: {message['id']}")
        incoming[message["id"]] = message
    for message in incoming.values():
        record = message_record(message, roots)
        stamp = moment(record["timestamp"])
        if stamp > now:
            raise ValueError(f"Experiment 2 future message: {record['id']}")
        old = state["messages"].get(record["id"])
        if old:
            if any(old[k] != record[k] for k in ("personaId", "timestamp", "isUser")):
                raise ValueError(f"Experiment 2 immutable message identity/date changed: {record['id']}")
            if old["charged"] and old.get("funnyTarget") and old["funnyTarget"] != record["funnyTarget"]:
                raise ValueError(f"Experiment 2 cannot move a laughter response: {record['id']}")
            if not old["charged"] and stamp < started and any(old[k] != record[k] for k in ("gifs", "memes", "funnyTarget", "unscopedLaughter")):
                raise ValueError("Do not add experimental media/laughter to pre-experiment messages")
            record["charged"] = old["charged"] or (stamp >= started and not record["threadOnly"] and not record["isUser"])
            if old["charged"]:
                record["gifs"] = max(old["gifs"], record["gifs"])
                record["memes"] = max(old["memes"], record["memes"])
                record["funnyTarget"] = old["funnyTarget"] or record["funnyTarget"]
        else:
            if state["initialized"] and record["personaId"] in known_owners and stamp < started and not record["threadOnly"]:
                raise ValueError(f"Experiment 2 new general message is backdated: {record['id']}")
            record["charged"] = stamp >= started and not record["threadOnly"] and not record["isUser"]
        if record["charged"] and record["unscopedLaughter"]:
            raise ValueError("Experiment 2 laughter must reply to the specific funny peer post")
        state["messages"][record["id"]] = record
    messages = state["messages"]
    daily: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"gifs": 0, "memes": 0, "funny": set()})
    for record in messages.values():
        if not record["charged"]:
            continue
        day = moment(record["timestamp"]).astimezone(IST).date().isoformat()
        usage = daily[record["personaId"], day]
        usage["gifs"] += record["gifs"]
        usage["memes"] += record["memes"]
        if record["funnyTarget"]:
            target = messages.get(record["funnyTarget"])
            if not target or (target["personaId"] == record["personaId"] and not target["isUser"]):
                raise ValueError("Experiment 2 laughter must target an existing post by another author")
            usage["funny"].add(record["funnyTarget"])
    for (owner, day), usage in daily.items():
        for key, count in (("gifs", usage["gifs"]), ("memes", usage["memes"]), ("laughter", len(usage["funny"]))):
            if count > LIMITS[key]:
                raise ValueError(f"Experiment 2 {owner} exceeds daily {key} budget on {day}: {count}/{LIMITS[key]}")
    new_events = {}
    for owner, persona in personas.items():
        events = persona.get("socialEvents", [])
        if not isinstance(events, list):
            raise ValueError("Experiment 2 socialEvents must be an array")
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("Experiment 2 event must be an object")
            event_id = required_text(event.get("id"), "event id")
            if event_id in new_events:
                raise ValueError(f"Experiment 2 duplicate event id: {event_id}")
            candidate = {**event, "personaId": owner}
            new_events[event_id] = candidate
            if event_id in state["events"]:
                if candidate != state["events"][event_id]:
                    raise ValueError(f"Experiment 2 accepted event is immutable: {event_id}")
                continue
            stamp = moment(event.get("timestamp"))
            if not started <= stamp <= now:
                raise ValueError("Experiment 2 event timestamp is outside the experiment")
            required_text(event.get("reason"), "event reason")
            kind = event.get("type")
            common = {"id", "timestamp", "type", "reason"}
            extra = {
                "reputation": {"targetMessageId", "evidenceMessageId", "value"},
                "work-success": {"outcomeId", "evidence"},
                "work-correction": {"outcomeId", "evidence"},
                "check-in": set(), "revive": set(),
            }
            if kind not in extra or set(event) - common - extra[kind]:
                raise ValueError(f"Experiment 2 unknown event type/fields: {event_id}")
            if kind == "reputation":
                required_text(event.get("targetMessageId"), "vote targetMessageId")
                required_text(event.get("evidenceMessageId"), "vote evidenceMessageId")
                target = messages.get(event.get("targetMessageId"))
                evidence = messages.get(event.get("evidenceMessageId"))
                if (not target or not evidence or target["personaId"] == owner or target["isUser"]
                        or evidence["personaId"] != owner or evidence["isUser"]
                        or (evidence["replyTo"] != target["id"] and target["replyTo"] != evidence["id"])
                        or type(event.get("value")) is not int or event["value"] not in (-1, 1)
                        or moment(target["timestamp"]) > stamp or moment(evidence["timestamp"]) > stamp):
                    raise ValueError("Experiment 2 vote needs a peer contribution and the voter's actual related exchange")
            elif kind in ("work-success", "work-correction"):
                required_text(event.get("outcomeId"), "work outcomeId")
                evidence = event.get("evidence")
                if not isinstance(evidence, dict) or set(evidence) != {"path", "quote"}:
                    raise ValueError("Experiment 2 work evidence needs path and exact quote")
                path = Path(required_text(evidence["path"], "evidence path"))
                base = Path(persona["basePath"]).resolve()
                if not path.is_absolute() or not path.resolve().is_relative_to(base):
                    raise ValueError("Experiment 2 work evidence must be inside the author's own base")
                quote = required_text(evidence["quote"], "evidence quote")
                if quote not in path.read_text(encoding="utf-8-sig"):
                    raise ValueError(f"Experiment 2 work evidence quote not found: {path}")
            state["events"][event_id] = candidate
    reputation: dict[str, int] = defaultdict(int)
    reputation_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seeds = policy.get("egoSeeds", {})
    if not isinstance(seeds, dict):
        raise ValueError("Experiment 2 egoSeeds must be an object")
    earned: dict[str, int] = defaultdict(lambda: 50)
    for owner, seed in seeds.items():
        if (not isinstance(seed, dict) or set(seed) != {"value", "reason"}
                or type(seed.get("value")) is not int or not 0 <= seed["value"] <= 100):
            raise ValueError("Experiment 2 Ego seed needs a 0-100 integer and reason")
        required_text(seed.get("reason"), "seed reason")
        earned[owner] = seed["value"]
    contributions = set()
    voters = set()
    baseline = policy.get("baseline", [])
    if not isinstance(baseline, list):
        raise ValueError("Experiment 2 baseline must be an array")
    for item in baseline:
        if (not isinstance(item, dict) or set(item) != {"targetMessageId", "evidenceMessageId", "value", "reason"}
                or type(item.get("value")) is not int or item["value"] not in (-1, 1)):
            raise ValueError("Invalid Experiment 2 archive baseline assessment")
        target = messages.get(required_text(item["targetMessageId"], "baseline targetMessageId"))
        evidence = messages.get(required_text(item["evidenceMessageId"], "baseline evidenceMessageId"))
        required_text(item.get("reason"), "baseline reason")
        if (not target or not evidence or target["personaId"] == evidence["personaId"]
                or target["isUser"] or evidence["isUser"] or evidence["replyTo"] != target["id"]
                or moment(target["timestamp"]) >= started or moment(evidence["timestamp"]) >= started):
            raise ValueError("Experiment 2 baseline must cite an actual peer response, not an invented vote")
        key = (item["targetMessageId"], evidence["personaId"]) if item["value"] > 0 else (item["targetMessageId"], "negative")
        if key in contributions:
            raise ValueError("Experiment 2 duplicate baseline contribution")
        contributions.add(key)
        voters.add((target["id"], evidence["personaId"]))
        reputation[target["personaId"]] += item["value"]
        reputation_evidence[target["personaId"]].append({**item, "source": "archive-assessment",
                                                       "notARetrospectiveVote": True})
    active: dict[str, set[str]] = defaultdict(set)
    revivals: dict[str, datetime] = {}
    outcomes = set()
    for event in sorted(state["events"].values(), key=lambda e: (moment(e["timestamp"]), e["id"])):
        owner, kind = event["personaId"], event["type"]
        stamp = moment(event["timestamp"])
        if kind == "reputation":
            target = messages[event["targetMessageId"]]
            key = (target["id"], owner) if event["value"] > 0 else (target["id"], "negative")
            if key in contributions or (target["id"], owner) in voters:
                raise ValueError("Experiment 2 duplicate vote/contribution or negative pile-on")
            contributions.add(key)
            voters.add((target["id"], owner))
            reputation[target["personaId"]] += event["value"]
            reputation_evidence[target["personaId"]].append(event)
        elif kind in ("work-success", "work-correction"):
            key = (owner, event["outcomeId"], kind)
            if key in outcomes:
                raise ValueError("Experiment 2 duplicate work outcome")
            outcomes.add(key)
            earned[owner] = max(0, min(100, earned[owner] + (2 if kind == "work-success" else -3)))
        elif kind == "check-in":
            active[owner].add(stamp.astimezone(IST).date().isoformat())
        elif kind == "revive":
            revivals[owner] = stamp
    engagement: dict[str, datetime] = {}
    for record in messages.values():
        target = messages.get(record["replyTo"])
        stamp = moment(record["timestamp"])
        if target and not record["isUser"] and record["personaId"] != target["personaId"] and stamp >= started:
            owner = target["personaId"]
            engagement[owner] = max(engagement.get(owner, started), stamp)
    today = now.astimezone(IST).date().isoformat()
    for owner, persona in personas.items():
        rep, ego = reputation[owner], earned[owner]
        social_ego = max(51, ego) if rep < 0 else ego
        reset = max(engagement.get(owner, started), revivals.get(owner, started)).astimezone(IST).date().isoformat()
        lonely_days = sum(day > reset for day in active[owner])
        status = ("unbothered" if social_ego > 50 else "retired" if lonely_days >= 30
                  else "lonely" if lonely_days >= 7 else "settling-in")
        usage = daily[owner, today]
        used = {"gifs": usage["gifs"], "memes": usage["memes"], "laughter": len(usage["funny"])}
        persona["socialStanding"] = {
            "reputation": rep, "ego": social_ego, "earnedEgo": ego,
            "defensivePride": rep < 0 and ego < 51,
            "egoBasis": seeds.get(owner, {"value": 50, "reason": "Neutral experiment starting value, not measured success"}),
            "reputationEvidence": reputation_evidence[owner],
            "lifecycle": {"status": status, "unengagedActiveDays": lonely_days,
                          "lastPeerEngagement": engagement[owner].isoformat() if owner in engagement else None,
                          "lastCheckInDay": max(active[owner]) if active[owner] else None,
                          "checkInDue": today not in active[owner], "reversible": True},
            "budget": {"date": today, "timezone": "Asia/Kolkata", "limits": LIMITS.copy(), "used": used,
                       "remaining": {key: LIMITS[key] - used[key] for key in LIMITS}},
            "participation": (
                "At active user/work boundaries, read the active briefing, answer real openings, and consider "
                "a grounded local conversation even with empty attention. A check-in is not participation. "
                "After useful peer help explicitly consider evidence-backed credit; no automatic votes or filler."
            ),
        }
    for context in contexts:
        for persona in context.get("social", []):
            persona["socialStanding"] = personas[persona["personaId"]]["socialStanding"]
    state["initialized"] = True
    social["experiment2"] = {"enabled": True, "startedAt": policy["startedAt"],
                             "timezone": "Asia/Kolkata", "limits": LIMITS.copy(),
                             "scope": "general-chat; technical threads remain professional and uncapped"}
    return state


def initialize(output: Path, policy: dict[str, Any]) -> None:
    """Explicit one-time initialization; never regenerate an existing ledger."""
    import json
    import sqlite3
    from contextlib import closing

    try:
        from build_context_mesh import PERSONA_COLOR_REGISTRY, SOCIAL_ARCHIVE_JSON, atomic_create
    except ModuleNotFoundError:
        from scripts.build_context_mesh import PERSONA_COLOR_REGISTRY, SOCIAL_ARCHIVE_JSON, atomic_create

    if policy.get("enabled") is not True:
        raise ValueError("Initialization requires an explicitly enabled policy")
    if not (output / "context-index.json").is_file():
        raise ValueError("Build the dashboard before enabling Experiment 2")
    with closing(sqlite3.connect(output / PERSONA_COLOR_REGISTRY, timeout=30)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if (output / POLICY_FILE).exists() or (output / STATE_FILE).exists():
            raise FileExistsError("Experiment 2 already has policy/state; restore or disable it, never reset it")
        index = json.loads((output / "context-index.json").read_text(encoding="utf-8"))
        history = list(index["social"]["messages"])
        archive = output / SOCIAL_ARCHIVE_JSON
        if archive.exists():
            history = json.loads(archive.read_text(encoding="utf-8"))["social"]["messages"] + history
        state = apply_experiment(index["social"], index["contexts"], policy, fresh_state(policy), history)
        atomic_create(output / STATE_FILE, json.dumps(state, ensure_ascii=False, indent=2))
        atomic_create(output / POLICY_FILE, json.dumps(policy, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", type=Path, required=True, metavar="OUTPUT_DIRECTORY")
    parser.add_argument("--policy", type=Path, required=True, help="Reviewed local policy JSON")
    args = parser.parse_args()
    initialize(args.initialize.resolve(), json.loads(args.policy.read_text(encoding="utf-8")))
    print("Experiment 2 policy and ledger initialized; rebuild Context Mesh to publish.")
