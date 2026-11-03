"""Reproducible media stages; semantic edit decisions belong to the invoking editor."""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.metadata
import json
import math
import os
import random
import re
import shutil
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .explorer import (
    EXPORT_FOLDER_CSS, SESSION_NAME, add_explorer_button,
    export_folder_field, export_folder_sort_key,
)
from .horizontal_models import HorizontalRenderSegment
from .media import CancelledError, MediaError, probe
from .models import Clip, Cue, Region, validate_question_title
from .music_recommendations import RECOMMENDATION_FILE, MusicRecommendation, recommendation_fields
from .posting import POSTING_CSS, POSTING_FILE, POSTING_SCRIPT, PostingRecord, PostingText, posting_fields, suggested_posting
from .question_titles import title_layout
from .editorial_corrections import correction_layout
from .solution_artwork import artwork_inputs, render_solution_thumbnail
from .thumbnails import render_thumbnail
from .transcripts import parse_transcript
from .workflow_models import DeliverySession, SAFE_ID_PATTERN, TimeRange, WorkflowCut, WorkflowPlan, WorkflowProfile
from .workflow_vision import VisionError

ROOT = Path(__file__).resolve().parents[1]
LEETCODE_NAME = re.compile(r"\[\s*leetcode\s*\]", re.IGNORECASE)
MAX_SECONDS = 180.0
THUMBNAIL_FILES = ("thumbnail.jpg", "thumbnail.json")
HORIZONTAL_ARTIFACTS = ("thumbnail", "thumbnail_metadata", "credits")
MUSIC_ARTIFACTS = ("music_record", "music_instructions")
MUSIC_FILES = ("music.json", "music-instructions.txt")
HORIZONTAL_CHECKS = {
    "complete_solve_reviewed", "original_layout_preserved", "silent_work_preserved",
    "subtitle_space_reviewed", "thumbnail_reviewed", "complexity_verified",
    "meme_rights_verified", "intro_fade_reviewed",
}


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def workflow_for(source: Path, requested: str | None = None) -> str:
    if requested == "system-design":
        return requested
    if requested not in (None, "leetcode"):
        raise ValueError(f"Workflow {requested!r} is not implemented.")
    if not LEETCODE_NAME.search(source.name):
        raise ValueError("The LeetCode workflow requires [LeetCode] or [ LeetCode ] in the video filename. "
                         "For System Design, explicitly select --workflow system-design.")
    return "leetcode"


def clock(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, fraction = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02}.{fraction:03}"


def transcript_text(cues: list[Cue]) -> str:
    return "\n".join(f"[{clock(c.start)} - {clock(c.end)}] {c.text}" for c in cues) + "\n"


def prepare(
    source: Path, transcript: Path | None = None, run_id: str | None = None, root: Path | None = None,
    *, model_name: str = "small", language: str | None = None, cancel: threading.Event | None = None,
    output_format: Literal["vertical", "horizontal"] = "vertical",
    workflow: str | None = None,
    session_timestamp: str | None = None, session_notice: str = "",
) -> Path:
    delivery = DeliverySession.model_validate({
        "requested_at": session_timestamp if session_timestamp is not None else datetime.now(timezone.utc),
        "timestamp_source": "prompt" if session_timestamp is not None else "cli",
        "notice": session_notice,
    })
    if output_format not in ("vertical", "horizontal"):
        raise ValueError("Output format must be vertical or horizontal.")
    source = source.expanduser().resolve()
    workflow = workflow_for(source, workflow)
    if workflow == "system-design" and output_format != "vertical":
        raise ValueError("System Design currently supports vertical output only.")
    if run_id is not None and not re.fullmatch(SAFE_ID_PATTERN, run_id):
        raise ValueError("Use a run ID of 1-80 lowercase letters, digits or hyphens, starting with a letter or digit.")
    data_root = root or Path(os.environ.get("CLIPFARM_DATA_DIR", str(ROOT / ".clipfarm"))) / "workflow-runs"
    data_root = data_root.expanduser().resolve()
    if run_id is not None and (data_root / run_id / "plan.json").exists():
        raise ValueError(f"Run already has a plan: {data_root / run_id / 'plan.json'}. Resume it instead of replacing it.")
    info = probe(source)
    if output_format == "horizontal" and info.width <= info.height:
        raise ValueError("Horizontal complete solves require a landscape source; no reframing is applied.")
    source_hash = fingerprint(source)
    prefix = f"{workflow}-horizontal" if output_format == "horizontal" else workflow
    run_id = run_id or f"{prefix}-{datetime.now():%Y%m%d-%H%M%S-%f}-{source_hash[:6]}"
    directory = data_root / run_id
    plan_path = directory / "plan.json"
    if plan_path.exists():
        raise ValueError(f"Run already has a plan: {plan_path}. Resume it instead of replacing it.")
    request_path = directory / "delivery-request.json"
    request_binding = {"source_sha256": source_hash, "workflow": workflow, "output_format": output_format}
    if request_path.exists():
        saved = read_json(request_path)
        if any(saved.get(key) != value for key, value in request_binding.items()):
            raise ValueError("The interrupted run belongs to different inputs. Use a new run ID.")
        previous = DeliverySession.model_validate(saved["delivery"])
        if ((session_timestamp is not None and delivery != previous)
                or (session_notice and session_notice != previous.notice)):
            raise ValueError("The interrupted run belongs to a different delivery session. Resume with its original options.")
        delivery = previous
    else:
        write_json(request_path, {**request_binding, "delivery": delivery.model_dump(mode="json")})
    generation = None
    if transcript is None:
        from .source_transcripts import generate

        progress(0, f"Generating source transcript in {directory}. "
                 f"If interrupted, repeat prepare with --run-id {run_id} and the same options.")
        cues, generation = generate(
            source, info, source_sha256=source_hash, directory=directory / "source-asr",
            model_name=model_name, language=language, progress=progress,
            cancel=cancel if cancel is not None else threading.Event(),
        )
        if not cues:
            raise MediaError("No speech detected; no workflow plan was created.")
        if fingerprint(source) != source_hash:
            raise ValueError("Source video changed during transcription. Prepare a new run.")
        note = generation["timing_note"]
        directory.mkdir(parents=True, exist_ok=True)
        transcript = directory / "transcript_granular.txt"
        transcript.write_text(
            "# ClipFarm local speech transcript\n"
            f"# Model: {model_name}; language hint: {language or 'auto'}\n"
            f"# {note}\n\n"
            + "\n".join(f"{clock(cue.start)} {cue.text}" for cue in cues) + "\n",
            encoding="utf-8",
        )
        write_json(directory / "transcript_granular.json", {
            "source_sha256": source_hash, "transcription": generation,
            "cues": [cue.model_dump() for cue in cues],
        })
    else:
        transcript = transcript.expanduser().resolve()
        cues, note = parse_transcript(transcript.read_text(encoding="utf-8-sig"), transcript.name, info.duration)
    transcript_hash = fingerprint(transcript)
    plan = WorkflowPlan(
        run_id=run_id, workflow=workflow, source=str(source), source_sha256=source_hash, delivery=delivery,
        transcript=str(transcript), transcript_sha256=transcript_hash, media=info, output_format=output_format,
        profile=WorkflowProfile(show_question_title=output_format == "vertical"),
        clip_policy="coverage-first-v1" if output_format == "vertical" else None,
    )
    directory.mkdir(parents=True, exist_ok=True)
    write_json(directory / "source-cues.json", [c.model_dump() for c in cues])
    plan.cues_sha256 = fingerprint(directory / "source-cues.json")
    (directory / "source-transcript.txt").write_text(
        f"{source.name}\nDuration: {clock(info.duration)}\n{note}\n\n{transcript_text(cues)}",
        encoding="utf-8",
    )
    write_json(directory / "input-provenance.json", {
        "workflow": workflow, "source": str(source), "source_sha256": source_hash,
        "output_format": output_format,
        "delivery": delivery.model_dump(mode="json"),
        "transcript": str(transcript), "transcript_sha256": transcript_hash,
        "transcript_origin": "generated_local" if generation is not None else "provided",
        "source_transcription": generation,
        "cue_count": len(cues), "timing_note": note,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    write_json(plan_path, plan.model_dump())
    return plan_path


def load_plan(path: Path, verify_inputs: bool = True) -> WorkflowPlan:
    plan = WorkflowPlan.model_validate(read_json(path))
    workflow_for(Path(plan.source), plan.workflow)
    if verify_inputs:
        for filename, expected in ((plan.source, plan.source_sha256), (plan.transcript, plan.transcript_sha256)):
            if fingerprint(Path(filename)) != expected:
                raise ValueError(f"Input changed since preparation: {filename}. Prepare a new run.")
    return plan


def load_cues(plan_path: Path) -> list[Cue]:
    plan = load_plan(plan_path, verify_inputs=False)
    path = plan_path.parent / "source-cues.json"
    if fingerprint(path) != plan.cues_sha256:
        raise ValueError("Prepared caption snapshot changed. Reconcile it explicitly before rendering.")
    return [Cue.model_validate(c) for c in read_json(path)]


def validate_plan(plan: WorkflowPlan, require_cuts: bool = True) -> list[str]:
    errors: list[str] = []
    try:
        workflow_for(Path(plan.source), plan.workflow)
    except ValueError as exc:
        errors.append(str(exc))
    system_design = plan.workflow == "system-design"
    if system_design and plan.output_format != "vertical":
        errors.append("System Design currently supports vertical output only.")
    if not plan.cues_sha256:
        errors.append("The prepared caption snapshot needs a SHA-256 fingerprint.")
    if not plan.reviewed_entire_transcript or len(plan.editorial_notes.strip()) < 40:
        errors.append("The entire transcript needs a substantive editorial coverage review.")
    horizontal = plan.output_format == "horizontal"
    if plan.clip_policy == "coverage-first-v1":
        limit = max(1, math.floor(plan.media.duration / 120))
        if sum(c.category != "funny" for c in plan.cuts) > limit:
            errors.append(f"Coverage-first policy permits at most {limit} core clips (5 per 10 source minutes).")
        if sum(c.category == "funny" for c in plan.cuts) > 2:
            errors.append("Coverage-first policy permits at most 2 genuine humor bonuses per source.")
    if horizontal and plan.profile.show_question_title:
        errors.append("Persistent question headers are vertical-only; horizontal layout is unchanged.")
    no_camera = plan.profile.camera_mode == "absent"
    if no_camera and (horizontal or plan.profile.face_region is not None):
        errors.append("An absent camera requires a vertical profile without a face_region.")
    if not horizontal and not system_design and (
        not plan.profile.code_region or (not no_camera and not plan.profile.face_region)
    ):
        errors.append("Visually verified avatar and code-pane regions are required.")
    if require_cuts and not plan.cuts:
        errors.append("No editorial cuts have been selected.")
    for cut in plan.cuts:
        if cut.stylized is not None:
            from .music import inputs as music_inputs

            try:
                music_inputs(cut.stylized)
                if horizontal:
                    raise ValueError("Stylized finishing is vertical-only.")
                if cut.stylized.boundaries and cut.trim_silence:
                    raise ValueError("Explicit beat handles require trim_silence=false.")
                if any(b.segment_index >= len(cut.segments) - 1 for b in cut.stylized.boundaries):
                    raise ValueError("Beat boundaries must identify internal authored joins.")
            except (ValueError, OSError, MediaError) as exc:
                errors.append(f"{cut.id}: {exc}")
        for segment in cut.segments:
            if segment.correction is not None:
                if horizontal or plan.profile.subtitle_y < 0.82:
                    errors.append(f"{cut.id}: corrections need vertical layout and subtitle_y >= 0.82.")
                try:
                    correction_layout(segment.correction.text)
                except (ValueError, MediaError) as exc:
                    errors.append(f"{cut.id}: {exc}")
        try:
            heading = resolved_question_title(plan, cut)
            if heading is not None:
                title_layout(heading)
        except (ValueError, MediaError) as exc:
            errors.append(f"{cut.id}: {exc}")
        if len(cut.coherence_review.strip()) < 30:
            errors.append(f"{cut.id}: read its proposed transcript and record a coherence review.")
        if system_design:
            if cut.category not in ("explanation", "funny"):
                errors.append(f"{cut.id}: System Design supports explanation or funny cuts, not LeetCode submissions/solutions.")
            if any(s.view != "code" for s in cut.segments) or any(
                e.kind in ("submission", "results") or e.runtime_ms is not None for e in cut.evidence
            ):
                errors.append(f"{cut.id}: System Design uses reviewed diagrams/code, not submission/runtime-results views or evidence.")
            for segment in cut.segments:
                if not (segment.content_region or plan.profile.code_region):
                    errors.append(f"{cut.id}: each System Design segment needs an explicit reviewed diagram/code content_region.")
                if not no_camera and not (segment.face_region or plan.profile.face_region):
                    errors.append(f"{cut.id}: each System Design segment needs an explicit reviewed face_region or declared absent camera.")
        if horizontal:
            errors.extend(validate_horizontal_cut(plan, cut))
            continue
        if cut.horizontal is not None or cut.category == "solution" or any(
            s.subtitle_region is not None or s.trim_silence is not None for s in cut.segments
        ):
            errors.append(f"{cut.id}: horizontal options require an explicitly horizontal plan.")
        if len(cut.title) > 120:
            errors.append(f"{cut.id}: vertical titles are limited to 120 characters.")
        length = sum(s.end - s.start for s in cut.segments)
        if length > MAX_SECONDS and not cut.trim_silence:
            errors.append(f"{cut.id}: {length:.1f}s exceeds the shared 180-second limit.")
        if cut.category == "submission":
            submissions = [e for e in cut.evidence if e.kind == "submission" and e.verified_by]
            results = [e for e in cut.evidence if e.kind == "results" and e.verified_by and e.runtime_ms is not None]
            if not submissions or not results:
                errors.append(f"{cut.id}: needs visually verified submission and runtime-results evidence.")
            for evidence in submissions + results:
                if not Path(evidence.image).is_file():
                    errors.append(f"{cut.id}: evidence image is missing: {evidence.image}")
                required_view = "results" if evidence.kind == "results" else None
                if not any(s.start <= evidence.time < s.end and (required_view is None or s.view == required_view)
                           for s in cut.segments):
                    errors.append(f"{cut.id}: evidence at {evidence.time:g}s is not in the required view.")
        for segment in cut.segments:
            if no_camera and segment.face_region is not None:
                errors.append(f"{cut.id}: an absent camera cannot have a segment face_region.")
            if segment.view == "results" and not (segment.content_region or plan.profile.results_region):
                errors.append(f"{cut.id}: a results segment needs a verified results-region crop.")
    return errors


def validate_horizontal_cut(plan: WorkflowPlan, cut: WorkflowCut) -> list[str]:
    errors: list[str] = []
    options = cut.horizontal
    if cut.category != "solution" or options is None:
        return [f"{cut.id}: horizontal mode requires category 'solution' and complete horizontal options."]
    if plan.media.width <= plan.media.height:
        errors.append(f"{cut.id}: horizontal mode requires the original landscape layout.")
    if len(options.coverage_review.strip()) < 60:
        errors.append(f"{cut.id}: record a complete chapter/important-work coverage review.")
    if len(options.subtitle_review.strip()) < 40:
        errors.append(f"{cut.id}: record a visual review of bottom empty subtitle space in every scene.")
    if cut.title != f"{options.artwork.problem_number}. {options.artwork.problem_title}":
        errors.append(f"{cut.id}: use the exact numbered problem title for the cut and thumbnail.")
    if any(a.end > b.start for a, b in zip(cut.segments, cut.segments[1:])):
        errors.append(f"{cut.id}: complete solves must be chronological, with no overlapping source segments.")
    if any(s.start < options.chapter.start or s.end > options.chapter.end for s in cut.segments):
        errors.append(f"{cut.id}: every retained segment must belong to the reviewed problem chapter.")
    if any(r.start < options.chapter.start or r.end > options.chapter.end for r in options.preserve_ranges):
        errors.append(f"{cut.id}: protected silent work must belong to the reviewed problem chapter.")
    for protected in options.preserve_ranges:
        covered = math.fsum(max(0, min(s.end, protected.end) - max(s.start, protected.start))
                            for s in cut.segments)
        if covered < protected.end - protected.start - 1e-7:
            errors.append(f"{cut.id}: selected segments omit declared protected silent work.")
    if any(s.face_region is not None or s.content_region is not None for s in cut.segments):
        errors.append(f"{cut.id}: horizontal segments cannot crop or rearrange the original feeds.")
    if sum(math.floor((s.end - s.start) * 30 + 1e-7) for s in cut.segments) < 120:
        errors.append(f"{cut.id}: retain at least four seconds of footage for the four-second dissolve.")
    complexity = options.artwork.complexity
    if complexity.source_kind == "stream" and (
        complexity.source_time is None
        or not options.chapter.start <= complexity.source_time < options.chapter.end
    ):
        errors.append(f"{cut.id}: stream-stated complexity needs a timestamp in this problem chapter.")
    try:
        artwork_inputs(options.artwork)
    except (ValueError, OSError, MediaError) as exc:
        errors.append(f"{cut.id}: invalid thumbnail inputs: {exc}")
    verified = [e for e in cut.evidence if e.verified_by.strip() and len(e.description.strip()) >= 12]
    for kind in ("introduction", "implementation", "completion"):
        candidates = [e for e in verified if e.kind == kind]
        if not candidates:
            errors.append(f"{cut.id}: needs verified {kind} evidence for a complete solve.")
        required_segments = (
            [cut.segments[0]] if kind == "introduction" else
            [cut.segments[-1]] if kind == "completion" else cut.segments
        )
        for item in candidates:
            if not any(s.start <= item.time < s.end for s in required_segments):
                errors.append(f"{cut.id}: {kind} evidence must be in its retained {'opening/ending' if kind != 'implementation' else 'work'} segment.")
    for item in cut.evidence:
        if not Path(item.image).is_file():
            errors.append(f"{cut.id}: evidence image is missing: {item.image}")
        if item.kind != "brb" and not any(s.start <= item.time < s.end for s in cut.segments):
            errors.append(f"{cut.id}: {item.kind} evidence is outside the selected footage.")
        if item.kind in ("submission", "results") and not item.verified_by.strip():
            errors.append(f"{cut.id}: submission/results evidence needs a named visual verifier.")
    regions = {json.dumps((s.subtitle_region or options.subtitle_region).model_dump(), sort_keys=True)
               for s in cut.segments}
    for region in regions:
        if not any(
            item.kind == "subtitle_space" and any(
                s.start <= item.time < s.end
                and json.dumps((s.subtitle_region or options.subtitle_region).model_dump(), sort_keys=True) == region
                for s in cut.segments
            )
            for item in verified
        ):
            errors.append(f"{cut.id}: every subtitle rectangle needs retained, verified subtitle_space image evidence.")
    return errors


def subtract_ranges(start: float, end: float, exclusions: list[tuple[float, float]]) -> list[tuple[float, float]]:
    remaining = [(start, end)]
    for left, right in sorted(exclusions):
        if right <= left:
            raise ValueError("Invalid exclusion interval.")
        next_ranges = []
        for a, b in remaining:
            if right <= a or left >= b:
                next_ranges.append((a, b))
                continue
            if a < left:
                next_ranges.append((a, min(left, b)))
            if b > right:
                next_ranges.append((max(right, a), b))
        remaining = next_ranges
    return [(a, b) for a, b in remaining if b - a >= 0.1]


def resolved_question_title(plan: WorkflowPlan, cut: WorkflowCut) -> str | None:
    if not plan.profile.show_question_title:
        return None
    if plan.output_format != "vertical":
        raise ValueError("Persistent question headers are vertical-only.")
    if plan.workflow == "system-design" and cut.question_title is None:
        raise ValueError("Supply question_title with the actual design question, not the clip headline.")
    return validate_question_title(cut.question_title if cut.question_title is not None else cut.problem)


def cut_signature(plan: WorkflowPlan, cut: WorkflowCut) -> str:
    payload = {
        "renderer_schema": 3 if any(segment.view == "results" for segment in cut.segments) else 2,
        "workflow": plan.workflow, "source": plan.source_sha256,
        "transcript": plan.transcript_sha256, "cues": plan.cues_sha256, "profile": plan.profile.model_dump(),
        "exclusions": [r.model_dump() for r in plan.exclusions], "cut": cut.model_dump(),
    }
    if plan.output_format == "horizontal":
        if cut.horizontal is None:
            raise ValueError("Horizontal draft is missing its solution artwork and editing options.")
        payload.update(
            renderer_schema="horizontal-2", output_format="horizontal", media=plan.media.model_dump(),
            artwork_inputs=artwork_inputs(cut.horizontal.artwork),
            evidence_sha256={e.image: fingerprint(Path(e.image)) for e in cut.evidence},
        )
    elif plan.profile.camera_mode == "absent":
        payload["renderer_schema"] = "vertical-no-camera-1"
    heading = resolved_question_title(plan, cut)
    if heading is not None:
        payload["question_heading"] = title_layout(heading)
    if any(segment.correction for segment in cut.segments):
        payload["editorial_corrections"] = [
            correction_layout(segment.correction.text) if segment.correction else None
            for segment in cut.segments
        ]
    if cut.stylized is not None:
        from .music import inputs as music_inputs

        payload["stylized_inputs"] = music_inputs(cut.stylized)
        payload["stylized_renderer"] = "speech-first-1"
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def compile_segments(
    plan: WorkflowPlan, cut: WorkflowCut, cancel: threading.Event,
    extra_exclusions: list[TimeRange] | None = None,
) -> tuple[list[Clip] | list[HorizontalRenderSegment], list[dict]]:
    from .montage import detect_silences

    if plan.output_format == "horizontal":
        return compile_horizontal_segments(plan, cut, cancel, extra_exclusions)
    exclusions = [(r.start, r.end) for r in plan.exclusions + (extra_exclusions or [])]
    compiled: list[Clip] = []
    removed: list[dict] = []
    for segment in cut.segments:
        visible = subtract_ranges(segment.start, segment.end, exclusions)
        if visible != [(segment.start, segment.end)]:
            removed.append({"start": segment.start, "end": segment.end, "reason": "BRB/excluded ranges",
                            "retained": visible})
        for start, end in visible:
            pauses = []
            if cut.trim_silence:
                silences = detect_silences(Path(plan.source), start, end, cancel,
                                           threshold_db=-35, min_duration=0.6)
                pauses = [(a + 0.12, b - 0.12) for a, b in silences if b - a > 0.6]
                removed.extend({"start": a, "end": b, "reason": "silence interior"} for a, b in pauses)
            for left, right in subtract_ranges(start, end, pauses):
                region = segment.content_region or (
                    plan.profile.results_region if segment.view == "results" else plan.profile.code_region
                )
                compiled.append(Clip(
                    start=left, end=right, title=cut.title, layout="leetcode",
                    camera_mode=plan.profile.camera_mode,
                    face_region=segment.face_region or plan.profile.face_region,
                    content_region=region, captions=True, caption_style=plan.profile.caption_style,
                    subtitle_y=plan.profile.subtitle_y, results_zoom=segment.view == "results",
                    question_title=resolved_question_title(plan, cut),
                    correction=segment.correction,
                ))
    if not compiled:
        raise ValueError(f"{cut.id}: no content remains after exclusions and silence removal.")
    if sum(c.end - c.start for c in compiled) > MAX_SECONDS:
        raise ValueError(f"{cut.id}: retained content exceeds 180 seconds. Edit it further; do not speed it up.")
    if cut.category == "submission":
        for evidence in cut.evidence:
            if evidence.kind in ("submission", "results") and not any(
                c.start <= evidence.time < c.end and (evidence.kind != "results" or c.results_zoom)
                for c in compiled
            ):
                raise ValueError(f"{cut.id}: trimming removed required {evidence.kind} evidence.")
    return compiled, removed


def compile_horizontal_segments(
    plan: WorkflowPlan, cut: WorkflowCut, cancel: threading.Event,
    extra_exclusions: list[TimeRange] | None = None,
) -> tuple[list[HorizontalRenderSegment], list[dict]]:
    from .montage import detect_silences

    options = cut.horizontal
    if options is None:
        raise ValueError("Horizontal editing options are required.")
    exclusions = [(r.start, r.end) for r in plan.exclusions + (extra_exclusions or [])]
    protected = [(r.start, r.end) for r in options.preserve_ranges]
    protected.extend((max(0, e.time - 0.5), min(plan.media.duration, e.time + 1.0))
                     for e in cut.evidence if e.kind != "brb")
    compiled: list[HorizontalRenderSegment] = []
    removed: list[dict] = []
    for segment in cut.segments:
        visible = subtract_ranges(segment.start, segment.end, exclusions)
        if visible != [(segment.start, segment.end)]:
            removed.append({"start": segment.start, "end": segment.end, "reason": "BRB/excluded ranges",
                            "retained": visible})
        for start, end in visible:
            pauses: list[tuple[float, float]] = []
            trim = cut.trim_silence if segment.trim_silence is None else segment.trim_silence
            if trim:
                for a, b in detect_silences(Path(plan.source), start, end, cancel,
                                            threshold_db=-35, min_duration=0.6):
                    if b - a > 0.6:
                        pauses.extend(subtract_ranges(a + 0.12, b - 0.12, protected))
                removed.extend({"start": a, "end": b, "reason": "silence interior"} for a, b in pauses)
            for left, right in subtract_ranges(start, end, pauses):
                compiled.append(HorizontalRenderSegment(
                    start=left, end=right, subtitle_region=segment.subtitle_region or options.subtitle_region,
                    reason=segment.reason,
                ))
    if sum(math.floor((c.end - c.start) * 30 + 1e-7) for c in compiled) < 120:
        raise ValueError(f"{cut.id}: fewer than four seconds remain after exclusions/silence trimming.")
    for required in options.preserve_ranges:
        covered = math.fsum(max(0, min(c.end, required.end) - max(c.start, required.start))
                            for c in compiled)
        if covered < required.end - required.start - 1e-7:
            raise ValueError(f"{cut.id}: exclusions removed protected silent work; reconcile the conflicting ranges.")
    for item in cut.evidence:
        if item.kind != "brb" and not any(
            c.start <= item.time < c.start + math.floor((c.end - c.start) * 30 + 1e-7) / 30
            for c in compiled
        ):
            raise ValueError(f"{cut.id}: trimming removed required {item.kind} evidence.")
    return compiled, removed


def require_valid(plan: WorkflowPlan) -> None:
    errors = validate_plan(plan)
    if errors:
        raise ValueError("\n".join(errors))


def verify_draft(draft: dict) -> None:
    keys = ("video", "subtitles", "transcript", "source_map")
    if draft.get("output_format") == "horizontal":
        keys += HORIZONTAL_ARTIFACTS
    if draft.get("stylized") is not None:
        keys += MUSIC_ARTIFACTS
    for key in keys:
        if fingerprint(Path(draft[key])) != draft["artifact_sha256"][key]:
            raise ValueError(f"The rendered {key} artifact changed after this draft.")
    if draft.get("output_format") == "horizontal":
        verify_horizontal_cover_binding(draft)
    if draft.get("stylized") is not None:
        record = read_json(Path(draft["music_record"]))
        if (record.get("signature") != draft["signature"]
                or record.get("video_sha256") != draft["video_sha256"]
                or record.get("settings") != draft["stylized"]
                or record.get("preview") != (draft.get("status") == "preview")
                or record.get("audio_embedded") != (draft["stylized"]["music"]["route"] == "embedded")):
            raise ValueError("Music provenance does not match the rendered draft.")


def verify_workflow_record(plan: WorkflowPlan, record: dict, description: str) -> None:
    # Artifacts predating explicit workflow metadata were exclusively LeetCode.
    if record.get("workflow", "leetcode") != plan.workflow:
        raise ValueError(f"{description} belongs to a different workflow.")


def verify_horizontal_cover_binding(draft: dict) -> None:
    expected = draft["artifact_sha256"]["thumbnail"]
    intro = read_json(Path(draft["source_map"])).get("synthetic_intro", {})
    metadata = read_json(Path(draft["thumbnail_metadata"]))
    if intro.get("thumbnail_sha256") != expected or metadata.get("sha256") != expected:
        raise ValueError("The horizontal intro and delivered thumbnail are not bound to the same JPEG.")
    if metadata.get("credits_sha256") != draft["artifact_sha256"]["credits"]:
        raise ValueError("The horizontal artwork credits do not match the encoded cover's provenance.")


def visual_cache_key(plan: WorkflowPlan, intervals: list[tuple[float, float]], step: float) -> str:
    versions = {}
    for name in ("rapidocr", "onnxruntime", "opencv-python", "imageio-ffmpeg"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    payload = {
        "source_sha256": plan.source_sha256, "intervals": intervals, "step": step,
        "vision_code_sha256": fingerprint(Path(__file__).with_name("workflow_vision.py")),
        "versions": versions,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def cached_visual_report(plan_path: Path, plan: WorkflowPlan, segments: list[Clip] | list[HorizontalRenderSegment], directory: Path,
                         step: float, cancel: threading.Event) -> dict:
    intervals = [(segment.start, segment.end) for segment in segments]
    return _cached_interval_report(plan_path, plan, intervals, directory, step, cancel)


def horizontal_scan_batches(intervals: list[tuple[float, float]], step: float) -> list[list[tuple[float, float]]]:
    if not math.isfinite(step) or step <= 0:
        raise ValueError("Visual sampling step must be finite and positive.")
    budget = 4000
    span = min(600, (budget - 2) * step)
    batches: list[list[tuple[float, float]]] = []
    batch: list[tuple[float, float]] = []
    count = 0
    for start, end in intervals:
        while start < end:
            right = min(end, start + span)
            if right <= start:
                raise ValueError("Visual sampling step is too small for these source timestamps.")
            samples = math.ceil((right - start) / step - 1e-8) + 2
            if batch and count + samples > budget:
                batches.append(batch)
                batch, count = [], 0
            batch.append((start, right))
            count += samples
            start = right
    if batch:
        batches.append(batch)
    return batches


def _cached_interval_report(plan_path: Path, plan: WorkflowPlan, intervals: list[tuple[float, float]],
                            directory: Path, step: float, cancel: threading.Event) -> dict:
    from .workflow_vision import scan_intervals

    key = visual_cache_key(plan, intervals, step)
    cache = plan_path.parent / "visual-cache" / f"{key}.json"
    if cache.is_file():
        record = read_json(cache)
        report = record["report"]
        evidence_paths = report.get("contact_sheets", []) + [
            sample["image"] for sample in report.get("samples", []) if sample.get("image")
        ]
        coverage = report.get("coverage", {})
        if (record.get("key") == key and record.get("source_sha256") == plan.source_sha256
                and coverage.get("status") == "completed" and coverage.get("requested_samples_complete") is True
                and report.get("samples") and evidence_paths and all(Path(p).is_file() for p in evidence_paths)):
            progress(0, "Reusing complete source inspection; source, intervals, OCR versions and code are unchanged.")
            return report
        progress(0, "Stored inspection is incomplete or its evidence is missing; rescanning.")
    batches = horizontal_scan_batches(intervals, step) if plan.output_format == "horizontal" else [intervals]
    if len(batches) <= 1:
        report = scan_intervals(Path(plan.source), intervals, directory / "vision",
                                step=step, progress=progress, cancel=cancel)
    else:
        reports = []
        for index, batch in enumerate(batches):
            if cancel.is_set():
                raise CancelledError("Horizontal visual inspection cancelled; incomplete coverage is not reusable.")
            progress(index / len(batches), f"Inspecting long-form batch {index + 1}/{len(batches)}")
            item = _cached_interval_report(plan_path, plan, batch, directory / f"scan-{index:04d}", step, cancel)
            if (not item.get("samples") or item.get("coverage", {}).get("status") != "completed"
                    or item["coverage"].get("requested_samples_complete") is not True):
                raise ValueError("A horizontal visual-inspection batch is incomplete; refusing an uninspected draft.")
            reports.append(item)
        samples = [sample for item in reports for sample in item["samples"]]
        report = {
            "source": plan.source, "duration": plan.media.duration, "step": step,
            "samples": samples, "brb_ranges": [r for item in reports for r in item.get("brb_ranges", [])],
            "contact_sheets": [p for item in reports for p in item.get("contact_sheets", [])],
            "warnings": sorted({text for item in reports for text in item.get("warnings", [])}),
            "coverage": {
                "status": "completed", "requested_samples_complete": True, "step": step,
                "requested_intervals": [list(interval) for interval in intervals], "batch_count": len(reports),
                "requested_samples": sum(item["coverage"].get("requested_samples", len(item["samples"]))
                                         for item in reports),
                "completed_samples": len(samples), "continuous_coverage": False, "certified_clean": False,
                "max_planned_sample_gap_seconds": step, "timestamp_kind": "requested_seek_seconds",
            },
        }
        write_json(directory / "vision" / "report.json", report)
    if (report.get("coverage", {}).get("status") == "completed"
            and report.get("coverage", {}).get("requested_samples_complete") is True):
        write_json(cache, {"key": key, "source_sha256": plan.source_sha256, "report": report})
    return report


def prepare_horizontal_cover(directory: Path, plan: WorkflowPlan, cut: WorkflowCut, signature: str) -> dict[str, str]:
    if cut.horizontal is None:
        raise ValueError("Horizontal thumbnail options are required.")
    paths = {"thumbnail": directory / "thumbnail.jpg", "thumbnail_metadata": directory / "thumbnail.json",
             "credits": directory / "credits.txt"}
    binding = {"signature": signature, "source_sha256": plan.source_sha256, "title": cut.title}
    if any(path.exists() for path in paths.values()):
        if not all(path.is_file() for path in paths.values()):
            raise ValueError("Incomplete horizontal cover; preserve and inspect the draft directory before retrying.")
        record = read_json(paths["thumbnail_metadata"])
        if (any(record.get(key) != value for key, value in binding.items())
                or record.get("sha256") != fingerprint(paths["thumbnail"])
                or record.get("credits_sha256") != fingerprint(paths["credits"])):
            raise ValueError("Horizontal cover changed; preserve it and use a new draft.")
        return {key: str(path.resolve()) for key, path in paths.items()}
    staging = directory / ".cover.publishing"
    if staging.exists():
        raise ValueError(f"Interrupted cover exists at {staging}; inspect it before retrying.")
    staging.mkdir()
    added: list[Path] = []
    complete = False
    try:
        spec = cut.horizontal.artwork
        details = render_solution_thumbnail(spec, staging / "thumbnail.jpg",
                                            width=plan.media.width, height=plan.media.height)
        complexity, meme = spec.complexity, spec.meme
        technique = f"Data structure / algorithm: {spec.technique}\n" if spec.technique else ""
        (staging / "credits.txt").write_text(
            f"{cut.title}\n\n{technique}Time complexity: {complexity.notation}\n"
            f"Basis: {'Stream stated' if complexity.source_kind == 'stream' else 'Researched best-known, not a claim about the demonstrated implementation'}\n"
            f"Evidence: {complexity.evidence}\n"
            f"Source: {complexity.source_url or f'Local stream at {clock(complexity.source_time or 0)}'}\n\n"
            f"Meme source: {meme.source_url or 'Local supplied/original artwork'}\n"
            f"Rights: {meme.rights}\n{meme.rights_note}\nAttribution: {meme.attribution or 'None required by the supplied rights declaration'}\n"
            f"Topic relevance: {meme.topic}\nSearch query: {meme.search_query or 'Not from web search'}\n\n"
            "Keep any required attribution in the platform description when posting.\n",
            encoding="utf-8",
        )
        write_json(staging / "thumbnail.json", {
            **details, **binding, "schema_version": 2, "output_format": "horizontal",
            "sha256": fingerprint(staging / "thumbnail.jpg"),
            "credits_sha256": fingerprint(staging / "credits.txt"),
        })
        for path in paths.values():
            (staging / path.name).rename(path)
            added.append(path)
        complete = True
    finally:
        if not complete:
            for path in added:
                path.unlink()
        shutil.rmtree(staging)
    return {key: str(path.resolve()) for key, path in paths.items()}


def draft_cut(
    plan_path: Path, cut_id: str, *, scan_step: float = 0.5,
    cancel: threading.Event | None = None, preview: bool = False,
) -> Path:
    from .montage import render_montage

    cancel = cancel or threading.Event()
    plan = load_plan(plan_path)
    require_valid(plan)
    cut = next((c for c in plan.cuts if c.id == cut_id), None)
    if cut is None:
        raise ValueError(f"Unknown cut: {cut_id}")
    if preview and (cut.stylized is None or plan.output_format != "vertical"):
        raise ValueError("Workflow preview requires an explicitly opted-in vertical stylized cut.")
    if not 0 < scan_step <= 1:
        raise ValueError("Draft BRB inspection must sample at least once per second.")
    if plan.output_format == "horizontal" and scan_step < 1 / plan.media.fps:
        raise ValueError("Horizontal visual sampling cannot exceed the source frame rate.")
    signature = cut_signature(plan, cut)
    heading = resolved_question_title(plan, cut)
    directory = plan_path.parent / ("previews" if preview else "drafts") / cut.id / signature[:12]
    draft_path = directory / ("preview.json" if preview else "draft.json")
    if draft_path.is_file():
        draft = read_json(draft_path)
        if draft["signature"] == signature:
            verify_workflow_record(plan, draft, "Draft")
            expected_style = cut.stylized.model_dump(mode="json") if cut.stylized is not None else None
            if (draft.get("stylized") != expected_style
                    or (draft.get("status") == "preview") != preview):
                raise ValueError("Cached draft settings or preview status do not match this request.")
            verify_draft(draft)
            if heading is not None and draft.get("question_heading") != title_layout(heading):
                raise ValueError("Question-heading provenance does not match this draft.")
            if not preview:
                write_json(plan_path.parent / "drafts" / cut.id / "latest.json", {"draft": str(draft_path.resolve())})
            return draft_path
        raise ValueError("Existing draft artifacts changed. Do not reuse or overwrite a reviewed draft.")
    directory.mkdir(parents=True, exist_ok=True)
    segments, removed = compile_segments(plan, cut, cancel)
    report = cached_visual_report(plan_path, plan, segments, directory, scan_step, cancel)
    if not isinstance(report.get("samples"), list) or not report["samples"]:
        raise ValueError("Visual scan returned no evidence; refusing an uninspected draft.")
    coverage = report.get("coverage", {})
    if coverage.get("status") != "completed" or coverage.get("requested_samples_complete") is not True:
        raise ValueError("Visual scan coverage is incomplete; refusing an uninspected draft.")
    discovered = [TimeRange(start=r["start"], end=r["end"], reason=r.get("reason", "BRB"))
                  for r in report.get("brb_ranges", [])]
    if discovered:
        segments, removed = compile_segments(plan, cut, cancel, discovered)
    output = directory / f"{cut.id}.mp4"
    source_cues = load_cues(plan_path)
    cues = cut.source_cues if cut.source_cues is not None else source_cues
    transitions, beat_report = {}, []
    if cut.stylized is not None:
        from .stylized import compile_style

        segments, beat_removed, transitions, beat_report = compile_style(
            plan, cut, [Clip.model_validate(s.model_dump()) for s in segments], cues, cancel,
        )
        removed.extend(beat_removed)
    cover = {}
    cover_hashes = {}
    if plan.output_format == "horizontal":
        from .horizontal import render_horizontal

        if cut.horizontal is None:
            raise ValueError("Horizontal editing options are required.")
        cover = prepare_horizontal_cover(directory, plan, cut, signature)
        cover_hashes = {key: fingerprint(Path(filename)) for key, filename in cover.items()}
        horizontal_segments = [HorizontalRenderSegment.model_validate(s.model_dump()) for s in segments]
        mapping = render_horizontal(
            Path(plan.source), plan.media, horizontal_segments, cues, output, Path(cover["thumbnail"]),
            progress, cancel, intro_hold=cut.horizontal.intro_hold_seconds,
        )
        if any(fingerprint(Path(cover[key])) != digest for key, digest in cover_hashes.items()):
            raise ValueError("The horizontal cover or provenance changed during rendering; preserve and inspect this draft.")
    else:
        vertical_segments = [Clip.model_validate(s.model_dump()) for s in segments]
        finishing = ({"stylized": cut.stylized, "transitions": transitions}
                     if cut.stylized is not None else {})
        mapping = render_montage(Path(plan.source), plan.media, vertical_segments, cues,
                                 output, preview, progress, cancel, **finishing)
    info = probe(output)
    expected_canvas = (plan.media.width, plan.media.height) if plan.output_format == "horizontal" else (1080, 1920)
    if preview:
        expected_canvas = (360, 640)
    if ((info.width, info.height) != expected_canvas
            or (plan.output_format == "vertical" and info.duration > MAX_SECONDS + 0.05)):
        raise ValueError("Final canvas/duration verification failed.")
    if (plan.output_format == "horizontal" or heading is not None
            or cut.stylized is not None
            or any(s.correction for s in cut.segments)) and cut_signature(plan, cut) != signature:
        raise ValueError("Artwork/title/evidence changed during rendering; this render cannot be reviewed.")
    draft = {
        "schema_version": 1, "workflow": plan.workflow, "run_id": plan.run_id, "cut_id": cut.id, "title": cut.title,
        "category": cut.category, "signature": signature, "source_sha256": plan.source_sha256,
        "video": str(output.resolve()), "video_sha256": fingerprint(output),
        "subtitles": str(output.with_suffix(".srt").resolve()),
        "transcript": str(output.with_suffix(".transcript.txt").resolve()),
        "source_map": str(output.with_suffix(".source-map.json").resolve()),
        "duration": info.duration, "effective_segments": [s.model_dump() for s in segments],
        "removed": removed, "detected_brb": [r.model_dump() for r in discovered],
        "visual_report": report, "created_at": datetime.now(timezone.utc).isoformat(),
        "span_count": len(mapping), "status": "preview" if preview else "draft",
        **cover,
    }
    if plan.output_format == "horizontal":
        draft.update(output_format="horizontal", width=info.width, height=info.height)
    if heading is not None:
        draft["question_heading"] = title_layout(heading)
    if cut.stylized is not None:
        from .music import inputs as music_inputs, instructions

        record_path, instructions_path = (directory / name for name in MUSIC_FILES)
        settings = cut.stylized.model_dump(mode="json")
        write_json(record_path, {
            "schema_version": 1, "renderer": "speech-first-1",
            "settings": settings, "inputs": music_inputs(cut.stylized),
            "signature": signature, "video_sha256": draft["video_sha256"],
            "duration": mapping[-1].output_end, "boundaries": beat_report,
            "transitions": {str(k): list(v) for k, v in transitions.items()},
            "preview": preview, "audio_embedded": cut.stylized.music.route == "embedded",
        })
        instructions_path.write_text(instructions(cut.stylized, mapping[-1].output_end), encoding="utf-8")
        draft.update(stylized=settings, music_record=str(record_path.resolve()),
                     music_instructions=str(instructions_path.resolve()))
    draft["artifact_sha256"] = {
        key: fingerprint(Path(draft[key]))
        for key in ("video", "subtitles", "transcript", "source_map")
    }
    draft["artifact_sha256"].update(cover_hashes)
    if cut.stylized is not None:
        draft["artifact_sha256"].update({key: fingerprint(Path(draft[key])) for key in MUSIC_ARTIFACTS})
    if plan.output_format == "horizontal":
        verify_horizontal_cover_binding(draft)
    write_json(draft_path, draft)
    if not preview:
        write_json(plan_path.parent / "drafts" / cut.id / "latest.json", {"draft": str(draft_path.resolve())})
    return draft_path


def latest_draft(plan_path: Path, cut_id: str) -> tuple[WorkflowPlan, WorkflowCut, Path, dict]:
    plan = load_plan(plan_path)
    cut = next((c for c in plan.cuts if c.id == cut_id), None)
    if cut is None:
        raise ValueError(f"Unknown cut: {cut_id}")
    pointer = read_json(plan_path.parent / "drafts" / cut.id / "latest.json")
    path = Path(pointer["draft"]).resolve()
    if not path.is_relative_to((plan_path.parent / "drafts" / cut.id).resolve()):
        raise ValueError("Draft pointer must remain in its cut directory.")
    draft = read_json(path)
    if draft.get("status") == "preview":
        raise ValueError("A preview is not a full-resolution draft and cannot be reviewed/published.")
    if cut.stylized is not None and draft.get("stylized") != cut.stylized.model_dump(mode="json"):
        raise ValueError("Stylized settings are missing or changed in this draft.")
    if draft["signature"] != cut_signature(plan, cut):
        raise ValueError("The edit plan changed after this draft. Render it again.")
    heading = resolved_question_title(plan, cut)
    if heading is not None and draft.get("question_heading") != title_layout(heading):
        raise ValueError("Question-heading provenance does not match this draft.")
    verify_workflow_record(plan, draft, "Draft")
    verify_draft(draft)
    return plan, cut, path, draft


def transcribe_draft(plan_path: Path, cut_id: str, model: str = "base", language: str | None = None) -> Path:
    from .transcribe import transcribe

    plan, cut, draft_path, draft = latest_draft(plan_path, cut_id)
    directory = draft_path.parent
    transcript_path = directory / "review-asr.txt"
    metadata_path = directory / "review-asr.json"
    if metadata_path.is_file():
        metadata = read_json(metadata_path)
        if (metadata["video_sha256"] == draft["video_sha256"] and metadata["model"] == model
                and metadata.get("language") == language
                and metadata.get("workflow", "leetcode") == plan.workflow
                and transcript_path.is_file() and metadata["transcript_sha256"] == fingerprint(transcript_path)):
            return transcript_path
    video = Path(draft["video"])
    options = {"language": language} if language else {}
    cues = transcribe(video, probe(video), model, progress, threading.Event(), **options)
    transcript_path.write_text(transcript_text(cues), encoding="utf-8")
    write_json(metadata_path, {
        "workflow": plan.workflow, "video_sha256": draft["video_sha256"], "model": model, "language": language,
        "transcript_sha256": fingerprint(transcript_path),
        "cues": [c.model_dump() for c in cues],
    })
    checks = dict.fromkeys(sorted(review_checks(plan, cut)), False)
    review = directory / "review.json"
    if not review.exists():
        write_json(review, {
            "workflow": plan.workflow, "cut_id": cut.id, "video_sha256": draft["video_sha256"],
            "transcript_sha256": fingerprint(transcript_path), "verdict": "pending",
            "reviewer": "", "checks": checks, "notes": "",
            "warning": "Read the ASR and source transcripts and inspect the video before approving. "
                       "OCR sampling and ASR are fallible; this is not human approval.",
            **({"thumbnail_sha256": draft["artifact_sha256"]["thumbnail"]}
               if plan.output_format == "horizontal" else {}),
            **({"music_sha256": {name: draft["artifact_sha256"][key]
                                for key, name in zip(MUSIC_ARTIFACTS, MUSIC_FILES)}}
               if cut.stylized is not None else {}),
        })
    return transcript_path


def review_checks(plan: WorkflowPlan, cut: WorkflowCut) -> set[str]:
    required = {"coherent", "useful_content", "captions_reviewed", "visuals_reviewed", "brb_reviewed"}
    if plan.output_format == "horizontal":
        required.update(HORIZONTAL_CHECKS)
        if any(e.kind == "submission" for e in cut.evidence):
            required.add("submission_visible")
        if any(e.kind == "results" and e.runtime_ms is not None for e in cut.evidence):
            required.add("runtime_verified")
    elif cut.category == "submission":
        required.update({"submission_visible", "runtime_verified", "results_zoom_reviewed"})
    if resolved_question_title(plan, cut) is not None:
        required.add("question_title_reviewed")
    if any(segment.correction for segment in cut.segments):
        required.add("corrections_reviewed")
    if cut.stylized is not None:
        required.update({"music_rights_reviewed", "beat_edits_reviewed",
                         "transitions_reviewed", "music_mix_reviewed"})
        if cut.stylized.music.route == "instagram":
            required.add("instagram_handoff_reviewed")
        if cut.stylized.music.trend is not None:
            required.add("trend_evidence_reviewed")
    return required


def publish(plan_path: Path, cut_id: str) -> Path:
    plan, cut, draft_path, draft = latest_draft(plan_path, cut_id)
    require_valid(plan)
    review = read_json(draft_path.parent / "review.json")
    verify_workflow_record(plan, review, "Review")
    if review.get("cut_id") != cut.id:
        raise ValueError("Review belongs to a different cut.")
    if not isinstance(review.get("scope_note", ""), str):
        raise ValueError("Review scope_note must be text.")
    asr_path = draft_path.parent / "review-asr.txt"
    if review.get("verdict") != "approve" or not review.get("reviewer") or len(review.get("notes", "").strip()) < 80:
        raise ValueError("A substantive, explicit editorial approval is required before publishing.")
    if review.get("video_sha256") != draft["video_sha256"]:
        raise ValueError("Review belongs to a different render.")
    if review.get("transcript_sha256") != fingerprint(asr_path):
        raise ValueError("The independently generated transcript changed after review.")
    asr_metadata = read_json(draft_path.parent / "review-asr.json")
    verify_workflow_record(plan, asr_metadata, "Audio-transcript provenance")
    if (asr_metadata["video_sha256"] != draft["video_sha256"]
            or asr_metadata["transcript_sha256"] != review["transcript_sha256"]):
        raise ValueError("Audio-transcript provenance does not match this review.")
    required = review_checks(plan, cut)
    if (plan.output_format == "horizontal"
            and review.get("thumbnail_sha256") != draft["artifact_sha256"]["thumbnail"]):
        raise ValueError("The horizontal thumbnail/intro does not match the reviewed image.")
    if cut.stylized is not None and review.get("music_sha256") != {
        name: draft["artifact_sha256"][key] for key, name in zip(MUSIC_ARTIFACTS, MUSIC_FILES)
    }:
        raise ValueError("Music settings, evidence or instructions do not match this review.")
    checks = review.get("checks", {})
    if any(checks.get(key) is not True for key in required):
        raise ValueError("Not all category-specific editorial/visual checks are approved.")
    destination = plan_path.parent / "final" / cut.id
    if destination.exists():
        existing = read_json(destination / "manifest.json")
        verify_workflow_record(plan, existing, "Published manifest")
        if (existing["video_sha256"] == draft["video_sha256"]
                and fingerprint(destination / "clip.mp4") == draft["video_sha256"]):
            if cut.stylized is not None and (
                existing.get("signature") != draft["signature"]
                or existing.get("stylized") != draft["stylized"]
            ):
                raise ValueError("A different music handoff already exists. Preserve it and use a new cut ID.")
            ensure_thumbnail(destination, plan, cut, draft)
            if plan.delivery is None:
                write_gallery(plan_path.parent)
            return _deliver_final(destination, plan.run_id, plan.delivery)
        raise ValueError("A different final version already exists. Preserve it and use a new cut ID.")
    staging = destination.with_name(destination.name + ".publishing")
    if staging.exists():
        raise ValueError(f"Interrupted publication exists at {staging}; inspect it before retrying.")
    staging.mkdir(parents=True)
    complete = False
    try:
        files = {
            Path(draft["video"]): "clip.mp4", Path(draft["subtitles"]): "clip.srt",
            Path(draft["transcript"]): "transcript.source.txt",
            Path(draft["source_map"]): "source-map.json",
            asr_path: "transcript.audio.txt", draft_path.parent / "review.json": "review.json",
        }
        for source, name in files.items():
            shutil.copy2(source, staging / name)
        if cut.stylized is not None:
            for key, name in zip(MUSIC_ARTIFACTS, MUSIC_FILES):
                shutil.copy2(Path(draft[key]), staging / name)
        manifest = {
            "workflow": plan.workflow, "run_id": plan.run_id, "cut_id": cut.id, "title": cut.title, "category": cut.category,
            "duration": draft["duration"], "video_sha256": draft["video_sha256"],
            "source_sha256": plan.source_sha256, "transcript_sha256": plan.transcript_sha256,
            "source": plan.source, "signature": draft["signature"], "reviewer": review["reviewer"],
            "review_notes": review["notes"], "evidence": [e.model_dump() for e in cut.evidence],
            "scope_note": review.get("scope_note", ""), "effective_segments": draft["effective_segments"],
            "audio_transcription": {"model": asr_metadata["model"], "language": asr_metadata.get("language"),
                                    "sha256": asr_metadata["transcript_sha256"]},
            "removed": draft["removed"], "visual_coverage": draft["visual_report"].get("coverage", {}),
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        if plan.output_format == "horizontal":
            manifest.update(output_format="horizontal", width=draft["width"], height=draft["height"],
                            thumbnail_sha256=draft["artifact_sha256"]["thumbnail"],
                            horizontal=cut.horizontal.model_dump() if cut.horizontal else None,
                            artifact_sha256=draft["artifact_sha256"])
        elif plan.profile.camera_mode == "absent":
            manifest["camera_mode"] = "absent"
        if resolved_question_title(plan, cut) is not None:
            manifest["question_heading"] = draft["question_heading"]
        if cut.stylized is not None:
            manifest.update(stylized=draft["stylized"], music_sha256={
                name: draft["artifact_sha256"][key] for key, name in zip(MUSIC_ARTIFACTS, MUSIC_FILES)
            })
        write_json(staging / "manifest.json", manifest)
        ensure_thumbnail(staging, plan, cut, draft)
        staging.rename(destination)
        complete = True
    finally:
        if not complete:
            shutil.rmtree(staging)
    if plan.delivery is None:
        write_gallery(plan_path.parent)
    return _deliver_final(destination, plan.run_id, plan.delivery)


def thumbnail_frame(draft: dict, *, camera_mode: str = "required") -> tuple[int, float, Region]:
    from .montage import MontageSpan

    if camera_mode not in ("required", "absent"):
        raise ValueError("Thumbnail camera_mode must be 'required' or explicitly 'absent'.")
    region_key = "content_region" if camera_mode == "absent" else "face_region"
    segments = [Clip.model_validate(value) for value in draft["effective_segments"]]
    spans = [MontageSpan.model_validate(value) for value in read_json(Path(draft["source_map"]))["segments"]]
    if not spans or len(spans) != len(segments):
        raise ValueError("Thumbnail selection requires the rendered source map and matching crop segments.")
    for index, span in enumerate(spans):
        segment = segments[index]
        if (span.index != index or abs(span.source_start - segment.start) > 0.0001
                or span.source_end > segment.end + 0.0001 or getattr(segment, region_key) is None
                or segment.camera_mode != camera_mode):
            raise ValueError("Thumbnail source spans do not match their declared camera mode and crop regions.")
    # Stable randomness keeps retries from silently choosing a different picture.
    rng = random.Random("thumbnail:" + draft["signature"])
    span = rng.choices(spans, weights=[s.source_end - s.source_start for s in spans])[0]
    margin = min(0.15, (span.source_end - span.source_start) / 4)
    at = rng.uniform(span.source_start + margin, span.source_end - margin)
    region = getattr(segments[span.index], region_key)
    if region is None:
        raise ValueError("A thumbnail needs an explicitly selected source crop.")
    return span.index, at, region


def ensure_thumbnail(directory: Path, plan: WorkflowPlan, cut: WorkflowCut, draft: dict) -> None:
    if plan.output_format == "horizontal":
        verify_horizontal_cover_binding(draft)
        for key, name in zip(HORIZONTAL_ARTIFACTS, (*THUMBNAIL_FILES, "credits.txt")):
            target = directory / name
            expected = draft["artifact_sha256"][key]
            if target.exists():
                if not target.is_file() or fingerprint(target) != expected:
                    raise ValueError(f"Thumbnail/credits changed or belong to a different horizontal draft: {directory}")
            else:
                shutil.copy2(Path(draft[key]), target)
                if fingerprint(target) != expected:
                    raise MediaError(f"Copied horizontal artwork does not match the reviewed draft: {name}")
        return
    image = directory / THUMBNAIL_FILES[0]
    metadata = directory / THUMBNAIL_FILES[1]
    question = resolved_question_title(plan, cut)
    question_cover = question is not None
    cover_title = question if question is not None else cut.title
    binding = {
        "signature": draft["signature"], "video_sha256": draft["video_sha256"],
        "source_sha256": plan.source_sha256, "title": cover_title,
    }
    if question_cover:
        from .thumbnails import problem_topic_renderer

        binding.update(question_heading=title_layout(question), topic=cut.title,
                       renderer=problem_topic_renderer(plan.profile.camera_mode))
    no_camera = plan.profile.camera_mode == "absent"
    text_only = no_camera and question_cover
    index, at, region = None, None, None
    if text_only:
        binding.update(camera_mode="absent", shot_kind="none", span_index=None, source_time=None)
    elif no_camera:
        index, at, region = thumbnail_frame(draft, camera_mode="absent")
        binding.update(camera_mode="absent", shot_kind="content", span_index=index,
                       source_time=at, content_region=region.model_dump())
    elif question_cover:
        index, at, region = thumbnail_frame(draft)
        binding.update(camera_mode="required", shot_kind="camera", span_index=index,
                       source_time=at, camera_region=region.model_dump())
    if image.exists() or metadata.exists():
        if not image.is_file() or not metadata.is_file():
            raise ValueError(f"Incomplete thumbnail at {directory}; preserve and inspect it before retrying.")
        record = read_json(metadata)
        if (any(record.get(key) != value for key, value in binding.items())
                or record.get("sha256") != fingerprint(image)
                or (text_only and ("content_region" in record or any(
                    key.startswith("content_") for key in record.get("layout", {})
                )))
                or (no_camera and ("camera_region" in record or any(
                    key.startswith("camera_") for key in record.get("layout", {})
                )))):
            raise ValueError(f"Thumbnail changed or belongs to a different clip: {directory}")
        return
    if not no_camera and not question_cover:
        index, at, region = thumbnail_frame(draft)
    staging = directory / ".thumbnail.publishing"
    if staging.exists():
        raise ValueError(f"Interrupted thumbnail exists at {staging}; inspect it before retrying.")
    staging.mkdir()
    added: list[Path] = []
    complete = False
    try:
        options = {"camera_mode": "absent"} if no_camera else {}
        if question_cover:
            options["font_family"] = "Consolas"
            options["topic"] = cut.title
        details = render_thumbnail(Path(plan.source), at, region, cover_title, staging / image.name, **options)
        write_json(staging / metadata.name, {
            **details, **binding, "schema_version": 2 if question_cover else 1, "span_index": index,
            "source_time": at,
            **({("content_region" if no_camera else "camera_region"): region.model_dump()}
               if region is not None else {}),
            "selection": ("Explicitly absent camera: text-only cover; no source frame selected." if text_only else
                          "Reproducible random timestamp from retained footage, avoiding cut edges."),
            "sha256": fingerprint(staging / image.name),
        })
        for target in (image, metadata):
            (staging / target.name).rename(target)
            added.append(target)
        complete = True
    finally:
        if not complete:
            for target in added:
                target.unlink()
        shutil.rmtree(staging)


def results_directory(plan: WorkflowPlan) -> Path:
    return ROOT / "results" / (plan.delivery.directory_name if plan.delivery is not None else plan.run_id)


def bind_delivery_session(plan_paths: list[Path], timestamp: str, notice: str = "") -> Path:
    if not plan_paths:
        raise ValueError("At least one existing plan is required for a delivery session.")
    delivery = DeliverySession.model_validate({"requested_at": timestamp, "notice": notice})
    updates = []
    for path in plan_paths:
        original = read_json(path)
        plan = WorkflowPlan.model_validate(original)
        if plan.delivery == delivery:
            continue
        backup = path.with_name(f"{path.stem}.before-delivery-{fingerprint(path)[:12]}.json")
        if backup.exists() and fingerprint(backup) != fingerprint(path):
            raise ValueError(f"Conflicting delivery backup exists: {backup}")
        updates.append((path, backup, original))
    for path, backup, original in updates:
        if not backup.exists():
            shutil.copy2(path, backup)
        original["delivery"] = delivery.model_dump(mode="json")
        write_json(path, original)
    return ROOT / "results" / delivery.directory_name


def _delivery_destination(archive: Path, run_id: str, delivery: DeliverySession | None) -> Path:
    directory = ROOT / "results" / (delivery.directory_name if delivery is not None else run_id)
    destination = directory / archive.name
    if delivery is not None:
        metadata = directory / "session.json"
        if metadata.exists() and DeliverySession.model_validate(read_json(metadata)) != delivery:
            raise ValueError(f"Different delivery session metadata already exists at {directory}; existing files were preserved.")
        if destination.exists():
            manifest_path = destination / "manifest.json"
            if not manifest_path.is_file():
                raise ValueError(f"Different or incomplete results already exist at {destination}.")
            try:
                existing = read_json(manifest_path)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Different or incomplete results already exist at {destination}.") from exc
            if (not isinstance(existing, dict) or existing.get("cut_id") != archive.name
                    or not isinstance(existing.get("run_id"), str)
                    or not re.fullmatch(SAFE_ID_PATTERN, existing["run_id"])):
                raise ValueError(f"Different or incomplete results already exist at {destination}.")
            if existing.get("run_id") != run_id:
                suffix = hashlib.sha256(f"{run_id}:{archive.name}".encode("utf-8")).hexdigest()[:12]
                destination = directory / f"{archive.name[:60]}--{suffix}"
                if destination.exists():
                    manifest_path = destination / "manifest.json"
                    if not manifest_path.is_file() or read_json(manifest_path).get("run_id") != run_id:
                        raise ValueError(f"Different or incomplete results already exist at {destination}.")
    return destination


def _deliver_final(archive: Path, run_id: str, delivery: DeliverySession | None = None) -> Path:
    if delivery is None:
        return _copy_final(archive, run_id, delivery)
    directory = ROOT / "results" / delivery.directory_name
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".publishing.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError as exc:
        raise ValueError(f"Session publication is already reserved at {lock}. Retry after it finishes; inspect stale locks.") from exc
    try:
        return _copy_final(archive, run_id, delivery)
    finally:
        lock.unlink()


def _copy_final(archive: Path, run_id: str, delivery: DeliverySession | None) -> Path:
    identity = read_json(archive / "manifest.json")
    if identity.get("run_id") != run_id or identity.get("cut_id") != archive.name:
        raise ValueError("Published bundle identity does not match the requested run and cut.")
    destination = _delivery_destination(archive, run_id, delivery)
    names = (
        "clip.mp4", "clip.srt", "transcript.source.txt", "transcript.audio.txt",
        "source-map.json", "review.json", "manifest.json",
    ) + THUMBNAIL_FILES
    if read_json(archive / "manifest.json").get("output_format") == "horizontal":
        names += ("credits.txt",)
    if read_json(archive / "manifest.json").get("stylized") is not None:
        music_delivery_text(archive, read_json(archive / "manifest.json"))
        names += MUSIC_FILES
    if (archive / POSTING_FILE).exists():
        gallery_posting(archive, read_json(archive / "manifest.json"))
        names += (POSTING_FILE,)
    if (archive / RECOMMENDATION_FILE).exists():
        gallery_music_recommendation(archive, identity)
        names += (RECOMMENDATION_FILE,)
    expected = {name: fingerprint(archive / name) for name in names}
    missing = list(names)
    if destination.exists():
        missing = []
        for name, digest in expected.items():
            target = destination / name
            if not target.exists() and name in (*THUMBNAIL_FILES, POSTING_FILE, RECOMMENDATION_FILE):
                missing.append(name)
            elif not target.is_file() or fingerprint(target) != digest:
                raise ValueError(
                    f"Different or incomplete results already exist at {destination}. "
                    "Existing files were preserved; move that bundle aside before retrying."
                )
    if missing:
        staging = destination.with_name(destination.name + ".publishing")
        if staging.exists():
            raise ValueError(f"Interrupted results copy exists at {staging}; inspect it before retrying.")
        staging.mkdir(parents=True)
        complete = False
        try:
            for name in missing:
                shutil.copy2(archive / name, staging / name)
                if fingerprint(staging / name) != expected[name]:
                    raise MediaError(f"Results copy does not match the approved bundle: {name}")
            if destination.exists():
                for name in missing:
                    (staging / name).rename(destination / name)
                staging.rmdir()
            else:
                staging.rename(destination)
            complete = True
        finally:
            if not complete:
                shutil.rmtree(staging)
    if delivery is not None:
        write_json(destination.parent / "session.json", delivery.model_dump(mode="json"))
    _write_gallery(destination.parent)
    return destination


def write_gallery(directory: Path) -> Path:
    return _write_gallery(directory / "final")


def gallery_posting(directory: Path, item: dict) -> tuple[PostingText, bool]:
    authored = directory / POSTING_FILE
    if authored.exists():
        record = PostingRecord.model_validate(read_json(authored))
        if (record.video_sha256 != item.get("video_sha256")
                or record.video_sha256 != fingerprint(directory / "clip.mp4")
                or record.thumbnail_sha256 != fingerprint(directory / "thumbnail.jpg")):
            raise ValueError(f"Posting text belongs to different video/thumbnail bytes: {directory}")
        return record, True
    metadata = directory / "thumbnail.json"
    return suggested_posting(item, read_json(metadata) if metadata.exists() else None), False


def music_delivery_text(directory: Path, item: dict) -> str:
    if item.get("stylized") is None:
        return ""
    for name in MUSIC_FILES:
        if fingerprint(directory / name) != item["music_sha256"][name]:
            raise ValueError("Published music instructions/provenance changed; preserve and inspect this bundle.")
    record = read_json(directory / MUSIC_FILES[0])
    if (record.get("settings") != item["stylized"] or record.get("video_sha256") != item["video_sha256"]
            or record.get("signature") != item["signature"] or record.get("preview") is not False
            or record.get("audio_embedded") != (item["stylized"]["music"]["route"] == "embedded")
            or fingerprint(directory / "clip.mp4") != item["video_sha256"]):
        raise ValueError("Published music handoff belongs to different video bytes or settings.")
    return (directory / MUSIC_FILES[1]).read_text(encoding="utf-8")


def gallery_music_recommendation(directory: Path, item: dict) -> MusicRecommendation | None:
    path = directory / RECOMMENDATION_FILE
    if not path.exists():
        return None
    if item.get("stylized") is not None:
        raise ValueError("Music suggestions cannot replace or accompany an existing stylized music handoff.")
    record = MusicRecommendation.model_validate(read_json(path))
    if (record.video_sha256 != item.get("video_sha256")
            or record.video_sha256 != fingerprint(directory / "clip.mp4")):
        raise ValueError(f"Music recommendation belongs to different video bytes: {directory}")
    return record


def _write_gallery(directory: Path) -> Path:
    cards = []
    labels = {"leetcode": "LeetCode", "system-design": "System Design"}
    workflows = set()
    for manifest_path in sorted(
        directory.glob("*/manifest.json"), key=lambda path: export_folder_sort_key(path.parent),
    ):
        if manifest_path.parent.name.endswith(".publishing"):
            continue
        item = read_json(manifest_path)
        workflow = item.get("workflow", "leetcode")
        workflows.add(workflow)
        label = html.escape(labels.get(workflow, "Unknown workflow"))
        name = html.escape(manifest_path.parent.name, quote=True)
        horizontal = item.get("output_format") == "horizontal"
        orientation = ' class="horizontal"' if horizontal else ""
        dimensions = ""
        if horizontal:
            width, height = int(item["width"]), int(item["height"])
            if width <= height or height <= 0:
                raise ValueError("Horizontal gallery dimensions must be positive and landscape.")
            dimensions = f' width="{width}" height="{height}"'
        has_thumbnail = (manifest_path.parent / THUMBNAIL_FILES[0]).is_file()
        poster = f' poster="{name}/thumbnail.jpg"' if has_thumbnail else ""
        thumbnail_link = (
            f'<a href="{name}/thumbnail.jpg" download="{name}-thumbnail.jpg">Thumbnail</a> &middot; '
            if has_thumbnail else ""
        )
        credits_link = (f'<p><a href="{name}/credits.txt">Complexity sources / meme credits</a></p>'
                        if horizontal else "")
        copy, authored = gallery_posting(manifest_path.parent, item)
        posting = posting_fields(copy, str(manifest_path.parent), authored=authored)
        suggestion = gallery_music_recommendation(manifest_path.parent, item)
        recommendation = (
            recommendation_fields(suggestion, str(manifest_path.parent), manifest_path.parent.name, item["duration"])
            if suggestion is not None else ""
        )
        music_text = music_delivery_text(manifest_path.parent, item)
        music_note = (
            f'<section class="posting-text"><h3>Music / platform handoff</h3>'
            f'<textarea readonly rows="9" aria-label="Music credits and posting instructions">'
            f'{html.escape(music_text)}</textarea><p><a href="{name}/music-instructions.txt" download>'
            f'Music instructions / required credits</a> &middot; '
            f'<a href="{name}/music.json">Music and beat provenance</a></p></section>'
            if music_text else ""
        )
        cards.append(
            f'<article data-cut="{name}"{orientation}><h2>{html.escape(item["title"])}</h2>'
            f'{export_folder_field(manifest_path.parent, directory)}'
            f'<p>{label} &middot; {html.escape(item["category"])} &middot; {item["duration"]:.1f}s</p>'
            f'<p>{html.escape(item.get("scope_note", ""))}</p>'
            f'<video controls preload="metadata"{poster}{dimensions} src="{name}/clip.mp4"></video>'
            f'<p><a href="{name}/clip.mp4" download="{name}.mp4">MP4</a> &middot; '
            f'{thumbnail_link}'
            f'<a href="{name}/clip.srt" download="{name}.srt">SRT</a> &middot; '
            f'<a href="{name}/transcript.audio.txt">Audio transcript</a> &middot; '
            f'<a href="{name}/review.json">Review</a></p>{credits_link}{recommendation}{posting}{music_note}'
            f'<details><summary>Editorial review</summary><p>{html.escape(item["review_notes"])}</p></details></article>'
        )
    label = labels.get(next(iter(workflows)), "Reviewed clips") if len(workflows) == 1 else "Reviewed clips"
    title = f"Reviewed {label} clips" if label != "Reviewed clips" else label
    session_details = ""
    if (directory / "session.json").exists():
        session = DeliverySession.model_validate(read_json(directory / "session.json"))
        basis = "Creation prompt" if session.timestamp_source == "prompt" else "CLI request (chat timestamp not supplied)"
        session_details = (
            f'<p>{basis}: <time>{html.escape(session.requested_at.isoformat())}</time> &middot; '
            f'{len(cards)} clips</p>'
            + (f'<p class="session-notice">{html.escape(session.notice)}</p>' if session.notice else "")
        )
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>ClipFarm - {title}</title><style>'
        '*{box-sizing:border-box}body{margin:0;padding:clamp(16px,3vw,40px);background:#002b36;color:#eee8d5;font:15px system-ui}'
        'h1{border-bottom:2px solid #cd5c5c;padding-bottom:20px;font-size:28px;font-weight:600}'
        'h2{font-size:19px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:24px}'
        'article{min-width:0;padding:24px;background:#073642;border:1px solid #31535e;border-radius:8px}'
        'video{width:100%;max-height:70vh;aspect-ratio:9/16;object-fit:contain;background:#000}'
        'article.horizontal{grid-column:1/-1}.horizontal video{width:auto;max-width:100%;height:auto;aspect-ratio:auto;display:block;margin:auto}'
        'a{color:#f0a3a3}p{line-height:1.6}'
        'summary{cursor:pointer;color:#a3b4b6}:focus-visible{outline:2px solid #cd5c5c;outline-offset:4px}'
        f'{POSTING_CSS}{EXPORT_FOLDER_CSS}</style><h1>ClipFarm / {label}</h1>'
        f'{session_details}'
        '<p>Reviewed local exports. Review records identify automated/Copilot evidence, not user approval.</p>'
        '<main>' + "".join(cards) + f"</main>{POSTING_SCRIPT}</html>"
    )
    if SESSION_NAME.fullmatch(directory.name):
        document = add_explorer_button(document, directory.name)
    path = directory / "index.html"
    temporary = path.with_suffix(".html.tmp")
    temporary.write_text(document, encoding="utf-8")
    temporary.replace(path)
    return path


def progress(value: float, message: str) -> None:
    print(f"{value * 100:5.1f}% {message}", flush=True)


def select_cuts(plan: WorkflowPlan, requested: str | None) -> list[WorkflowCut]:
    if requested:
        selected = [c for c in plan.cuts if c.id == requested]
        if not selected:
            raise ValueError(f"Unknown cut: {requested}")
        return selected
    if not plan.cuts:
        raise ValueError("No cuts in this plan.")
    return plan.cuts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clipfarm workflow", description="ClipFarm evidence-driven editorial workflow stages")
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare", help="Snapshot inputs for a full Copilot editorial review")
    preparation.add_argument("--video", type=Path, required=True)
    preparation.add_argument("--workflow", choices=["leetcode", "system-design"],
                             help="Explicit workflow; otherwise only tagged LeetCode filenames are routed")
    preparation.add_argument("--transcript", type=Path, help="Optional timed transcript; otherwise generate one locally")
    preparation.add_argument("--model", choices=["tiny", "base", "small"], default="small",
                             help="Source speech model when no transcript is supplied (default: small)")
    preparation.add_argument("--language", help="Optional source language code, e.g. en; otherwise detect it")
    preparation.add_argument("--format", dest="output_format", choices=["vertical", "horizontal"], default="vertical",
                             help="Opt in to full-frame, long-form horizontal solution videos; vertical remains default")
    preparation.add_argument("--run-id")
    preparation.add_argument("--root", type=Path)
    preparation.add_argument("--session-timestamp",
                             help="Timezone-aware ISO timestamp of the creation prompt; reuse for EVERY source in that request")
    preparation.add_argument("--session-notice", default="", help="Shared delivery notice, e.g. an unmet music request")
    session = commands.add_parser("session", help="Bind existing plans to one creation prompt without changing media signatures")
    session.add_argument("--plan", type=Path, action="append", required=True)
    session.add_argument("--requested-at", required=True, help="Original timezone-aware creation-prompt timestamp")
    session.add_argument("--notice", default="")
    commands.add_parser("music-schema", help="Print the opt-in speech-first music settings JSON schema")
    styling = commands.add_parser("style", help="Explicitly apply reviewed music settings to ONE cut")
    styling.add_argument("--plan", type=Path, required=True)
    styling.add_argument("--cut", required=True)
    styling.add_argument("--settings", type=Path, required=True)
    for name in ("validate", "inspect", "preview", "draft", "review-transcribe", "publish"):
        command = commands.add_parser(name)
        command.add_argument("--plan", type=Path, required=True)
        if name in ("preview", "draft", "review-transcribe", "publish"):
            command.add_argument("--cut")
        if name == "inspect":
            command.add_argument("--start", type=float, default=0)
            command.add_argument("--end", type=float)
            command.add_argument("--step", type=float, default=60)
        if name in ("preview", "draft"):
            command.add_argument("--scan-step", type=float, default=0.5)
        if name == "review-transcribe":
            command.add_argument("--model", choices=["tiny", "base", "small"], default="base")
            command.add_argument("--language", help="Optional language code, e.g. en, for short/misdetected clips")
    args = parser.parse_args(argv)
    try:
        if args.command == "music-schema":
            from .music_models import StylizedEdit

            print(json.dumps(StylizedEdit.model_json_schema(), indent=2))
            return 0
        if args.command == "prepare":
            format_option = {"output_format": args.output_format} if args.output_format != "vertical" else {}
            if args.workflow is not None:
                format_option["workflow"] = args.workflow
            if args.session_timestamp is not None:
                format_option["session_timestamp"] = args.session_timestamp
            if args.session_notice:
                format_option["session_notice"] = args.session_notice
            print(prepare(args.video, args.transcript, args.run_id, args.root,
                          model_name=args.model, language=args.language, **format_option))
            return 0
        if args.command == "session":
            print(bind_delivery_session([path.resolve() for path in args.plan], args.requested_at, args.notice))
            return 0
        plan_path = args.plan.resolve()
        plan = load_plan(plan_path)
        if args.command == "style":
            from .music_models import StylizedEdit

            cut = select_cuts(plan, args.cut)[0]
            cut.stylized = StylizedEdit.model_validate(read_json(args.settings.resolve()))
            require_valid(plan)
            backup = plan_path.with_name(f"{plan_path.stem}.before-style-{fingerprint(plan_path)[:12]}.json")
            if not backup.exists():
                with backup.open("xb") as stream:
                    stream.write(plan_path.read_bytes())
            elif fingerprint(backup) != fingerprint(plan_path):
                raise ValueError("Conflicting style backup exists; preserve it and inspect before retrying.")
            write_json(plan_path, plan.model_dump())
            print(f"Opted in {cut.id}. Original plan: {backup}. Preview/draft and fresh review are required.")
        elif args.command == "validate":
            require_valid(plan)
            print(f"Plan is structurally valid: {len(plan.cuts)} cuts. Editorial approval is separate.")
        elif args.command == "inspect":
            from .workflow_vision import scan_intervals

            output = plan_path.parent / "inspections" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            report = scan_intervals(Path(plan.source), [(args.start, plan.media.duration if args.end is None else args.end)],
                                    output, step=args.step, progress=progress, cancel=threading.Event())
            print(json.dumps({"directory": str(output), "coverage": report.get("coverage"),
                              "brb_ranges": report.get("brb_ranges")}, indent=2))
        else:
            for cut in select_cuts(plan, args.cut):
                if args.command == "preview":
                    print(draft_cut(plan_path, cut.id, scan_step=args.scan_step, preview=True))
                elif args.command == "draft":
                    print(draft_cut(plan_path, cut.id, scan_step=args.scan_step))
                elif args.command == "review-transcribe":
                    print(transcribe_draft(plan_path, cut.id, args.model, args.language))
                elif args.command == "publish":
                    print(publish(plan_path, cut.id))
        return 0
    except (KeyboardInterrupt, CancelledError):
        print("ClipFarm workflow cancelled; no unreviewed result was published.", file=sys.stderr)
        return 130
    except (ValueError, OSError, MediaError, VisionError) as exc:
        print(f"ClipFarm workflow: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
