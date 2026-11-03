"""Speech-first beat edits: only explicitly expendable, silent boundary handles."""
from __future__ import annotations

import math
import threading
from pathlib import Path

from .models import Clip, Cue
from .workflow_models import WorkflowCut, WorkflowPlan


def compile_style(
    plan: WorkflowPlan, cut: WorkflowCut, segments: list[Clip], cues: list[Cue],
    cancel: threading.Event,
) -> tuple[list[Clip], list[dict], dict[int, tuple[int, int]], list[dict]]:
    from . import media
    from .montage import detect_silences

    style = cut.stylized
    if style is None:
        return segments, [], {}, []
    if style.boundaries and (
        cut.trim_silence or len(segments) != len(cut.segments)
        or any(abs(s.start - original.start) > 1e-7 or abs(s.end - original.end) > 1e-7
               for s, original in zip(segments, cut.segments))
    ):
        raise ValueError("Beat handles require trim_silence=false and unchanged authored segments; "
                         "reconcile exclusions/BRB into the plan first.")
    result = [s.model_copy(deep=True) for s in segments]
    frames = [math.floor((s.end - s.start) * 30 + 1e-7) for s in result]
    transitions: dict[int, tuple[int, int]] = {}
    removed: list[dict] = []
    report: list[dict] = []
    evidence = [e for e in plan.evidence + cut.evidence if e.kind != "brb"]

    def require_safe(start: float, end: float) -> None:
        media._check_cancel(cancel)
        if any(c.start < end + 0.08 and c.end > start - 0.08 for c in cues):
            raise ValueError("A beat trim/transition overlaps a caption or its speech safety margin.")
        if any(start - 0.1 <= e.time <= end + 0.1 for e in evidence):
            raise ValueError("A beat trim/transition overlaps protected visual evidence.")
        if plan.media.has_audio:
            quiet = detect_silences(Path(plan.source), start, end, cancel,
                                    threshold_db=-35, min_duration=min(0.02, (end - start) / 2))
            covered = math.fsum(max(0, min(b, end) - max(a, start)) for a, b in quiet)
            if covered < end - start - 1 / 48000:
                raise ValueError("A beat trim/transition handle is not silent; retain the original cut.")

    period = 60 / style.music.bpm
    offset = style.music.beat_offset_seconds
    for boundary in sorted(style.boundaries, key=lambda b: b.segment_index):
        index = boundary.segment_index
        if index >= len(result) - 1:
            raise ValueError("Beat boundaries must identify an internal join, not the final segment.")
        clip, incoming = result[index], result[index + 1]
        if clip.results_zoom or clip.correction is not None:
            raise ValueError("Beat edits cannot shorten results or editor-correction segments.")
        old_frames = frames[index]
        old_join = sum(frames[:index + 1])
        minimum = old_join - math.floor(boundary.safe_tail_seconds * 30 + 1e-7)
        beat = math.floor((old_join / 30 - offset) / period + 1e-9)
        target = round((offset + beat * period) * 30)
        if target > old_join:
            beat -= 1
            target = round((offset + beat * period) * 30)
        aligned = beat >= 0 and minimum <= target <= old_join
        if aligned and target < old_join:
            count = old_frames - (old_join - target)
            if count < 15:
                raise ValueError("A beat edit must retain at least half a second in each segment.")
            end = clip.start + count / 30
            prior_end = clip.start + old_frames / 30
            require_safe(end, prior_end)
            removed.append({"start": end, "end": prior_end, "reason": "explicit silent beat tail",
                            "safety_note": boundary.safety_note})
            clip.end, frames[index] = end, count
        if boundary.transition == "dip":
            fade = style.transition_frames
            if (incoming.results_zoom or incoming.correction is not None
                    or min(frames[index], frames[index + 1]) < 2 * fade + 1):
                raise ValueError("A dip needs sufficient clear handles and cannot hide results/corrections.")
            end = clip.start + frames[index] / 30
            require_safe(end - fade / 30, end)
            require_safe(incoming.start, incoming.start + fade / 30)
            transitions[index] = (transitions.get(index, (0, 0))[0], fade)
            transitions[index + 1] = (fade, transitions.get(index + 1, (0, 0))[1])
        join = sum(frames[:index + 1])
        report.append({
            "segment_index": index, "output_frame": join, "output_seconds": join / 30,
            "aligned": aligned, "removed_frames": old_frames - frames[index],
            "beat_error_seconds": join / 30 - (offset + beat * period) if aligned else None,
            "transition": boundary.transition, "safety_note": boundary.safety_note,
            "note": "Frame-quantized authored beat grid." if aligned else
                    "No beat inside the approved handle; original cut retained.",
        })
    return result, removed, transitions, report
