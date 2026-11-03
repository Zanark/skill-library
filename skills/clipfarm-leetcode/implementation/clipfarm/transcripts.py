from __future__ import annotations

import bisect
import html
import json
import re

from .models import Clip, Cue

TIMING = re.compile(
    r"(?P<start>(?:\d+:)?\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*"
    r"(?P<end>(?:\d+:)?\d{2}:\d{2}[.,]\d{1,3})(?:\s+.*)?$"
)
START_LINE = re.compile(
    r"^(?P<start>(?:\d+:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?)(?:[ \t]+(?P<text>.*))?$"
)
HOOKS = re.compile(
    r"\b(?:why|how|secret|mistake|instead|never|lesson|learned|imagine|"
    r"here's|turns out|the truth|the problem|the trick|what if)\b", re.I
)


def timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2])
    hours = int(parts[-3]) if len(parts) == 3 else 0
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds


def clean_text(value: str) -> str:
    # Remove subtitle markup, not arbitrary angle-bracketed spoken text.
    value = re.sub(r"</?(?:b|i|u|font|c|v|lang|ruby|rt)(?:[ .][^>]*)?>", "", value,
                   flags=re.I)
    value = re.sub(r"<\d{2}:\d{2}(?::\d{2})?\.\d{3}>", "", value)
    return " ".join(html.unescape(value).split())


def _start_only_cues(content: str, duration: float) -> list[Cue]:
    entries: list[tuple[float, list[str]]] = []
    for line_number, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line or (not entries and line.startswith("#")):
            continue
        match = START_LINE.fullmatch(line)
        if match:
            start = timestamp(match["start"])
            if entries and start <= entries[-1][0]:
                raise ValueError(f"Line {line_number}: transcript timestamps must strictly increase.")
            if start >= duration:
                raise ValueError(f"Line {line_number}: timestamp is beyond the video's duration.")
            entries.append((start, [match["text"]] if match["text"] else []))
        elif not entries:
            raise ValueError(f"Line {line_number}: text appears before the first transcript timestamp.")
        elif re.match(r"^\d+:\d", line):
            raise ValueError(f"Line {line_number}: invalid transcript timestamp.")
        else:
            entries[-1][1].append(line)
    cues: list[Cue] = []
    for index, (start, lines) in enumerate(entries):
        text = clean_text(" ".join(lines))
        if not text:
            raise ValueError(f"Timestamp {start:g}s has no caption text.")
        next_start = entries[index + 1][0] if index + 1 < len(entries) else duration
        # Start-only exports omit silence/end markers. Do not hold a short line
        # through a long break or for the entire remaining video.
        maximum_span = max(8.0, len(text.split()) / 2.0)
        cues.append(Cue(start=start, end=min(next_start, start + maximum_span), text=text))
    return cues


def parse_transcript(content: str, filename: str, duration: float) -> tuple[list[Cue], str]:
    if len(content.encode("utf-8")) > 20 * 1024 * 1024:
        raise ValueError("Transcript exceeds 20 MB. Split it into a smaller subtitle file.")
    content = content.lstrip("\ufeff").strip()
    cues: list[Cue] = []
    start_only = False
    if filename.lower().endswith(".json") or content.startswith(("[", "{")):
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid transcript JSON: {exc.msg}") from exc
        if isinstance(data, dict):
            data = data.get("segments", data.get("cues"))
        if not isinstance(data, list):
            raise ValueError("JSON needs an array of {start, end, text}, or a segments/cues array.")
        for index, item in enumerate(data):
            if not isinstance(item, dict) or not {"start", "end", "text"} <= item.keys():
                raise ValueError(f"Transcript item {index + 1} needs start, end, and text.")
            if not isinstance(item["text"], str):
                raise ValueError(f"Transcript item {index + 1} text must be a string.")
            cues.append(Cue(start=item["start"], end=item["end"], text=clean_text(item["text"])))
    elif "-->" not in content and any(START_LINE.fullmatch(line.strip()) for line in content.splitlines()):
        start_only = True
        cues = _start_only_cues(content, duration)
    else:
        blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n"))
        for block in blocks:
            lines = block.strip().splitlines()
            if not lines:
                continue
            if lines[0].startswith(("NOTE", "STYLE", "REGION")):
                continue
            timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
            if timing_index is None:
                if lines[0].startswith("WEBVTT"):
                    continue
                raise ValueError(
                    "Use SRT, VTT, timed JSON, or TXT with timestamped lines. Plain text "
                    "without timestamps has no reliable alignment; transcribe it or add timestamps."
                )
            match = TIMING.fullmatch(lines[timing_index].strip())
            if not match:
                raise ValueError(f"Invalid subtitle timing: {lines[timing_index]}")
            text = clean_text(" ".join(lines[timing_index + 1:]))
            if text:
                cues.append(Cue(start=timestamp(match["start"]), end=timestamp(match["end"]), text=text))
    if not cues:
        raise ValueError("No nonempty timed captions found.")
    cues.sort(key=lambda c: (c.start, c.end))
    if cues[-1].start >= duration or any(c.start >= duration for c in cues):
        raise ValueError("Transcript contains captions beyond this video's duration. Check its timing.")
    if any(c.end > duration + 1 for c in cues):
        raise ValueError("Transcript extends beyond this video. Check that it belongs to the same edit.")
    for cue in cues:
        cue.end = min(cue.end, duration)
    # Rolling VTT captions often repeat the previous line. Drop exact overlapping repeats only.
    normalized: list[Cue] = []
    for cue in cues:
        if normalized and normalized[-1].text == cue.text and cue.start < normalized[-1].end:
            normalized[-1].end = max(normalized[-1].end, cue.end)
        else:
            normalized.append(cue)
    overlaps = sum(a.end > b.start + 0.05 for a, b in zip(normalized, normalized[1:]))
    note = f"Imported {len(normalized)} timed captions."
    if start_only:
        note += (
            " Start times come from the transcript. End times are inferred from the next "
            "timestamp and a reading-time cap to avoid lingering across silence. "
            "Long caption bursts use proportional timing, not word-level audio alignment."
        )
    if overlaps:
        note += f" {overlaps} overlapping cue pairs: review rolling captions or simultaneous speakers."
    return normalized, note


def suggest_clips(
    cues: list[Cue], duration: float, minimum: float, maximum: float, count: int, keywords: str
) -> list[Clip]:
    if not cues:
        raise ValueError("Import a timed transcript or transcribe the video before suggesting clips.")
    if minimum > maximum:
        raise ValueError("Minimum clip length cannot exceed maximum.")
    if duration < minimum:
        minimum = duration
    ends = [c.end for c in cues]
    # Overlapping transcripts may have non-monotonic ends; searches use monotonic maxima.
    for i in range(1, len(ends)):
        ends[i] = max(ends[i], ends[i - 1])
    terms = {w.casefold() for w in re.findall(r"\w+", keywords)}
    candidates: list[tuple[float, float, float, str, str]] = []
    target = min(maximum, (minimum + maximum) / 2)
    for i, first in enumerate(cues):
        start = max(0.0, first.start - 0.12)
        if duration - start < minimum:
            continue
        lo = bisect.bisect_left(ends, start + minimum, lo=i)
        hi = bisect.bisect_right(ends, min(duration, start + maximum), lo=i)
        if lo >= hi:
            continue
        # Bounded endpoints keep suggestion cost linear for hours of subtitles.
        near = bisect.bisect_left(ends, start + target, lo=lo, hi=hi)
        choices = sorted({lo, hi - 1, max(lo, near - 1), min(hi - 1, near)})
        for j in choices:
            end = min(duration, cues[j].end + 0.15, start + maximum)
            if end - start < minimum:
                continue
            text = " ".join(c.text for c in cues[i:j + 1])
            words = set(re.findall(r"\w+", text.casefold()))
            matches = len(terms & words)
            if terms and not matches:
                continue
            clean_end = bool(re.search(r'[.!?]["\']?$', cues[j].text))
            hook = bool(HOOKS.search(first.text))
            gap_before = i == 0 or first.start - cues[i - 1].end > 0.7
            gap_after = j == len(cues) - 1 or cues[j + 1].start - cues[j].end > 0.7
            length = end - start
            score = matches * 4 + hook * 2 + clean_end * 1.5 + gap_before + gap_after
            score -= abs(length - target) / max(target, 1)
            # Reject long dead-air spans even when the endpoint lengths happen to match.
            speech = sum(min(c.end, end) - max(c.start, start) for c in cues[i:j + 1])
            if speech / length < 0.35:
                continue
            title = first.text[:100].rstrip()
            reason = "Transcript heuristic: "
            reason += ", ".join(
                [s for flag, s in [(hook, "opening hook"), (clean_end, "sentence ending"),
                                  (gap_before or gap_after, "speech boundary"),
                                  (matches > 0, "keyword match")] if flag]
            ) or "balanced duration"
            candidates.append((score, start, end, title, reason + ". Review context before posting."))
    candidates.sort(key=lambda c: (-c[0], c[1]))
    selected: list[Clip] = []
    for _, start, end, title, reason in candidates:
        if any(max(0, min(end, c.end) - max(start, c.start)) >
               min(end - start, c.end - c.start) * 0.15 for c in selected):
            continue
        selected.append(Clip(title=title, start=round(start, 3), end=round(end, 3), reason=reason))
        if len(selected) >= count:
            break
    if not selected:
        raise ValueError("No matching spoken sections fit these lengths. Lower the minimum or change keywords.")
    return sorted(selected, key=lambda c: c.start)
