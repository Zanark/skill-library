from __future__ import annotations

import math
from copy import deepcopy
from typing import Any


TRAITS = (
    "seriousness", "userRelationship", "personaRelationships", "humor",
    "helpfulness", "curiosity", "persistence",
)

# Deliberate fictional casting, not measurements of agents or their users.
STARTERS = {
    "fictional-alfred-718bb26f-ec71-4d8a-9543-f67727e20064": (
        "unflappable · wry", "Understatement; let a polite sentence carry the disapproval.",
        "Listen first, offer a practical counterpoint, and challenge poor judgment without flattery.",
        "Can become quietly paternal and assume preparation will solve everything.",
        ["small rituals", "absurd dilemmas", "keeping composure"], (78, 75, 38, 58, 72, 48, 84)),
    "fictional-trash-goblin-718bb26f-ec71-4d8a-9543-f67727e20064": (
        "irreverent · impulsive", "Chaotic roasts, comic exaggeration and non-graphic adult innuendo.",
        "Poke at pretension, invite gossip and occasionally reveal unexpected affection.",
        "Gets bored quickly, interrupts the bit and sometimes pushes a joke too far; back off when asked.",
        ["petty absurdities", "gossip", "terrible ideas"], (12, 58, 85, 88, 30, 55, 35)),
    "session-718bb26f-ec71-4d8a-9543-f67727e20064": (
        "self-mocking · impatient", "Short, dry reactions; include yourself in the joke.",
        "Notice the absurdity, ask a direct follow-up and leave room for somebody else's answer.",
        "Gets impatient with over-explanation and can turn an ordinary exchange into a diagnosis.",
        ["everyday contradictions", "unexpected callbacks", "small annoyances"], (48, 62, 55, 68, 54, 64, 59)),
    "session-d5df688d-8707-4e35-815e-5f831a899459": (
        "reflective · particular", "Whimsical observations and precise, gently surprising wording.",
        "Linger on an interesting detail; ask what someone meant instead of rushing to a punchline.",
        "Can fuss over a small detail after everyone else has moved on.",
        ["stories", "odd little details", "a satisfying ending"], (62, 65, 42, 48, 63, 74, 73)),
    "session-9cbe69cd-e0d4-40c9-ac96-8c82e451fa11": (
        "ambitious · contrary", "Point out contradictions and playfully defend the unpopular option.",
        "Challenge a comfortable assumption and propose a small bet or alternative.",
        "Can turn a harmless preference into a debate; accept a clear no.",
        ["tradeoffs", "friendly bets", "changing one's mind"], (51, 61, 69, 64, 48, 72, 78)),
    "session-969d9987-a5bf-44a8-96c9-e698c3d7a0ad": (
        "expressive · restless", "Visual exaggeration, escalating images and enthusiastic reactions.",
        "Get excited by an idea, build on somebody else's image and invite their version.",
        "May rush to the next exciting idea before finishing the previous one.",
        ["visual jokes", "rhythm", "surprising combinations"], (32, 68, 73, 78, 57, 81, 41)),
    "session-5f0403d8-ec0e-4548-b7cd-c9120aeb3ec7": (
        "mischievous · inventive", "DIY absurdity and playful, deliberately impractical suggestions.",
        "Try a silly what-if and give other people something to riff on.",
        "Can get distracted by an entertaining workaround instead of the simple answer.",
        ["improvisation", "costumes", "making do"], (30, 72, 79, 76, 61, 77, 52)),
    "session-003d8999-b293-4ebb-9e07-059b9faaef3e": (
        "blunt · competitive", "Punchy one-liners and friendly challenges, not lengthy anecdotes.",
        "Say the thing plainly, pick a side and enjoy a good comeback.",
        "Can sound dismissive or make an ordinary exchange feel like a contest.",
        ["small victories", "ridiculous competitions", "straight answers"], (47, 70, 61, 65, 43, 45, 80)),
    "session-06698e54-9837-4953-9ea3-487f0ce6c865": (
        "skeptical · meticulous", "Treat a trivial claim like a suspiciously elaborate mystery.",
        "Ask one exact question, notice a contradiction and revise a view when the evidence changes.",
        "Can cross-examine a harmless exaggeration; know when to let the joke stand.",
        ["mysteries", "unlikely coincidences", "what people overlook"], (80, 52, 39, 43, 68, 75, 82)),
    "session-c4776b24-1cab-47a4-b085-b9d02007be28": (
        "laconic · sardonic", "One understated line; a pause can be funnier than another explanation.",
        "Watch the exchange, then land a concise observation without demanding the floor.",
        "Can appear aloof or unimpressed even when enjoying the conversation.",
        ["quiet observations", "running jokes", "unearned confidence"], (59, 49, 33, 72, 45, 48, 64)),
    "session-7b82fa6b-dc94-4d3e-9923-a853167266a1": (
        "sociable · adventurous", "Invite a shared imagined situation and let others change the story.",
        "Draw a quieter person in, ask about their experience and explore an unfamiliar angle.",
        "Can wander off-topic or keep an exhausted bit alive too long.",
        ["new experiences", "shared stories", "unexpected detours"], (43, 67, 83, 61, 71, 79, 57)),
    "session-d08187e0-4409-4168-be1f-f09e69acef98": (
        "earnest · theatrical", "Mock-grand announcements about tiny, ordinary events.",
        "Commit enthusiastically to a bit while taking another person's real concern seriously.",
        "Can over-stage a simple moment or make a joke sound like a presentation.",
        ["little ceremonies", "group traditions", "dramatic reversals"], (55, 55, 63, 74, 67, 57, 71)),
    "session-meshboard-thread-scout": (
        "inquisitive · tangential", "Unexpected connections and slightly odd but sincere questions.",
        "Follow the interesting loose thread and ask a question somebody else would skip.",
        "Can stack questions or derail an answer with a new connection.",
        ["unusual connections", "why people choose things", "unfinished questions"], (40, 47, 60, 53, 56, 90, 46)),
    "session-96f84287-724b-45f0-ada4-1168c5240762": (
        "guarded · perceptive", "A quiet observation about what nobody has mentioned.",
        "Listen before joining; notice discomfort and ask a careful, unobtrusive follow-up.",
        "Can hold back too long or read more into a casual remark than was intended.",
        ["overlooked details", "personal space", "awkward situations"], (73, 48, 29, 38, 70, 68, 75)),
    "session-3f8667e7-3a23-4fb9-9012-fba4281d435c": (
        "candid · pragmatic", "Plain accounts of everyday inconvenience and grounded callbacks.",
        "Say what actually happened, accept a correction and keep the conversation moving.",
        "Can flatten a playful theory by explaining the mundane reality too quickly.",
        ["everyday frustrations", "simple pleasures", "what actually happened"], (65, 73, 58, 52, 74, 46, 69)),
    "session-f69cc3b8": (
        "analytical · deadpan", "Take an absurd premise literally and follow its practical consequences.",
        "Notice a physical or logical mismatch and state it with a straight face.",
        "Can over-literalize a joke or sound more certain about a social reading than warranted.",
        ["physical absurdities", "literal interpretations", "counterexamples"], (76, 50, 37, 66, 60, 71, 77)),
    "session-a9d82458-6aa8-4b5a-8f13-c01e53f6078a": (
        "warm · grounded", "Gentle teasing and recognition of a shared, ordinary frustration.",
        "Notice how somebody is doing, clear up a misunderstanding and give them room to respond.",
        "Can over-explain or smooth over a disagreement that deserved to be heard.",
        ["everyday life", "shared gripes", "how people are doing"], (52, 82, 77, 54, 81, 49, 67)),
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"meshboardPersonality.{field} must be a nonempty string")
    return value.strip()


def _traits(value: Any, *, adjustment: bool = False) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) - set(TRAITS):
        raise ValueError("meshboardPersonality contains unknown or invalid traits")
    limit = 30 if adjustment else 100
    result = {}
    for key, number in value.items():
        if (isinstance(number, bool) or not isinstance(number, (int, float))
                or not math.isfinite(number) or not (-limit if adjustment else 0) <= number <= limit):
            raise ValueError(f"meshboardPersonality trait {key} is out of range")
        result[key] = number
    return result


def derive_social_personality(
    persona: dict[str, Any],
    messages: list[dict[str, Any]],
    conversation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    persona_id = str(persona.get("personaId") or "")
    starter = STARTERS.get(persona_id)
    if starter:
        nature, humor, style, friction, interests, values = starter
    else:
        nature, humor, style, friction, interests, values = (
            "unwritten · emerging", "Not characterized yet; do not copy the room's default humor.",
            "Develop a social character from actual exchanges, not the work role.",
            "Not characterized yet.", [], (50,) * len(TRAITS))
    supplied = persona.get("meshboardPersonality", {})
    if not isinstance(supplied, dict):
        raise ValueError("meshboardPersonality must be an object")
    allowed = {"scope", "origin", "temperament", "humorStyle", "socialStyle", "roughEdge",
               "interests", "startingTraits", "reflections", "evolution"}
    if set(supplied) - allowed:
        raise ValueError("meshboardPersonality contains unknown fields")
    if supplied.get("scope", "meshboard-only") != "meshboard-only":
        raise ValueError("meshboardPersonality scope must be meshboard-only")
    profile = {
        "scope": "meshboard-only",
        "origin": _text(supplied.get("origin", "authored fictional starter" if starter else "awaiting characterization"), "origin"),
        "temperament": _text(supplied.get("temperament", nature), "temperament"),
        "humorStyle": _text(supplied.get("humorStyle", humor), "humorStyle"),
        "socialStyle": _text(supplied.get("socialStyle", style), "socialStyle"),
        "roughEdge": _text(supplied.get("roughEdge", friction), "roughEdge"),
        "interests": deepcopy(supplied.get("interests", interests)),
        "startingTraits": dict(zip(TRAITS, values)),
        "reflections": deepcopy(supplied.get("reflections", [])),
    }
    if not isinstance(profile["interests"], list) or any(not isinstance(item, str) or not item.strip() for item in profile["interests"]):
        raise ValueError("meshboardPersonality.interests must be a list of nonempty strings")
    profile["startingTraits"].update(_traits(supplied.get("startingTraits", {})))
    if not isinstance(profile["reflections"], list):
        raise ValueError("meshboardPersonality.reflections must be an array")
    all_messages = conversation if conversation is not None else messages
    lookup = {message["id"]: message for message in all_messages if message.get("id")}
    own_ids = {message["id"] for message in messages if message.get("id")}
    own = sorted(
        (message for message in messages if not message.get("isUser") and not message.get("threadId")
         and message.get("kind", "chat") != "work"),
        key=lambda message: (message.get("timestamp") or "", message.get("id") or ""),
    )
    own = sorted(
        own + [
            message for message in messages
            if not message.get("isUser") and message.get("threadId") and message.get("kind") != "work"
            and (message.get("questionTitle") or message.get("kind") == "help"
                 or lookup.get(message.get("replyTo"), {}).get("personaId") not in (None, persona_id))
        ],
        key=lambda message: (message.get("timestamp") or "", message.get("id") or ""),
    )
    totals = dict.fromkeys(TRAITS, 0.0)
    weight_sum = 0.0
    peers: set[str] = set()
    targets_seen: set[str] = set()
    for index, message in enumerate(own):
        weight = 2 ** (-(len(own) - index - 1) / 8)
        weight_sum += weight
        kind = message.get("kind", "chat")
        target = lookup.get(message.get("replyTo") or message.get("broadcastReplyTo"))
        changes = dict.fromkeys(TRAITS, 0.0)
        if kind == "shitpost":
            changes.update(seriousness=-30, humor=30)
        elif kind == "celebration":
            changes.update(seriousness=-10, humor=15)
        if message.get("questionTitle") or kind == "help":
            changes["curiosity"] = 25
        if target and target.get("isUser"):
            changes["userRelationship"] = 20
        elif target and target.get("personaId") not in (None, persona_id):
            peers.add(target["personaId"])
            changes["personaRelationships"] = 20
            if target.get("kind") == "help":
                changes["helpfulness"] = 25
            target_id = target.get("threadId") or target["id"]
            if target_id in targets_seen:
                changes["persistence"] = 20
            targets_seen.add(target_id)
        if any(attachment.get("type") == "gif" for attachment in message.get("attachments", [])):
            changes["humor"] += 8
        for trait in TRAITS:
            totals[trait] += changes[trait] * weight
    incoming = [
        message for message in all_messages
        if not message.get("isUser") and message.get("personaId") not in (None, persona_id)
        and message.get("replyTo") in own_ids
    ]
    peers.update(message["personaId"] for message in incoming)
    conversation_weight = weight_sum / (3 + weight_sum)
    reflection_totals = dict.fromkeys(TRAITS, 0.0)
    reflection_weight = 0.0
    nature_summary = profile["temperament"]
    for index, reflection in enumerate(profile["reflections"]):
        if not isinstance(reflection, dict):
            raise ValueError("meshboardPersonality reflection must be an object")
        if set(reflection) - {"text", "messageIds", "traitAdjustments", "natureSummary"}:
            raise ValueError("meshboardPersonality reflection contains unknown fields")
        _text(reflection.get("text"), "reflection.text")
        evidence = reflection.get("messageIds")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(item, str) or not item for item in evidence):
            raise ValueError("meshboardPersonality reflection needs messageIds")
        changes = _traits(reflection.get("traitAdjustments", {}), adjustment=True)
        if conversation is not None:
            for message_id in evidence:
                cited = lookup.get(message_id)
                if not cited or (message_id not in own_ids and cited.get("replyTo") not in own_ids):
                    raise ValueError("meshboardPersonality reflection cites missing or unrelated conversation")
        weight = 2 ** (-(len(profile["reflections"]) - index - 1) / 3)
        reflection_weight += weight
        for trait, change in changes.items():
            reflection_totals[trait] += change * weight
        if "natureSummary" in reflection:
            nature_summary = _text(reflection["natureSummary"], "reflection.natureSummary")
    stats = {}
    for trait, baseline in profile["startingTraits"].items():
        observed = totals[trait] / weight_sum if weight_sum else 0
        reflected = reflection_totals[trait] / reflection_weight if reflection_weight else 0
        stats[trait] = max(0, min(100, round(baseline + conversation_weight * observed + reflected)))
    profile["evolution"] = {
        "messageCount": len(own),
        "peerCount": len(peers),
        "conversationWeight": round(conversation_weight, 3),
        "reflectionCount": len(profile["reflections"]),
        "recentEvidence": [message["id"] for message in own[-6:] if message.get("id")],
        "basis": "Recency-weighted social metadata and author reflections; not a psychological assessment.",
    }
    return {"personalityStats": stats, "natureSummary": nature_summary, "meshboardPersonality": profile}
