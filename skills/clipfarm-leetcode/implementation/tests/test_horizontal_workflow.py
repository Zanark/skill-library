import hashlib
import json
import math
import threading
from pathlib import Path

import pytest
from PIL import Image

from clipfarm import montage, workflow
from clipfarm.horizontal_models import HorizontalRenderSegment, SubtitleRegion
from clipfarm.models import Cue, MediaInfo, Region
from clipfarm.workflow_models import (
    HorizontalOptions, TimeRange, VisualEvidence, WorkflowCut, WorkflowPlan, WorkflowSegment,
)


@pytest.fixture
def horizontal_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "ROOT", tmp_path)
    source = tmp_path / "[LeetCode] original.mp4"
    source.write_bytes(b"original source fixture")
    transcript = tmp_path / "provided.json"
    transcript.write_text('[{"start":21,"end":24,"text":"The full question."}]', encoding="utf-8")
    info = MediaInfo(duration=600, width=1280, height=720, fps=60)
    monkeypatch.setattr(workflow, "probe", lambda _: info)
    image = tmp_path / "original cat.png"
    Image.new("RGB", (100, 100), "orange").save(image)

    def artwork_inputs(spec):
        digest = workflow.fingerprint(Path(spec.meme.image))
        if digest != spec.meme.sha256:
            raise ValueError("Meme image fingerprint changed.")
        return {"meme_sha256": digest, "font_sha256": "font fixture"}

    monkeypatch.setattr(workflow, "artwork_inputs", artwork_inputs)
    path = workflow.prepare(source, transcript, "horizontal", tmp_path / "runs", output_format="horizontal")
    plan = workflow.load_plan(path)
    plan.reviewed_entire_transcript = True
    plan.editorial_notes = "Fixture review of the whole recording; retain this problem from introduction through completion."
    plan.cuts = [WorkflowCut(
        id="300-longest-increasing-subsequence", title="300. Longest Increasing Subsequence",
        category="solution", problem="Longest Increasing Subsequence",
        rationale="Preserve the complete chronological solve and omit a separate tangent.",
        segments=[WorkflowSegment(start=20, end=220), WorkflowSegment(start=240, end=450)],
        trim_silence=False,
        coherence_review="The question, full implementation, corrections and genuine completion remain in chronological order.",
        horizontal=HorizontalOptions(
            chapter=TimeRange(start=20, end=450),
            subtitle_region=SubtitleRegion(x=0.1, y=0.86, w=0.8, h=0.12),
            coverage_review="Fixture chapter review includes the problem introduction, important silent work, complete implementation and final outcome.",
            subtitle_review="Fixture images show a common empty bottom strip across the problem and implementation views.",
            artwork={
                "problem_number": 300, "problem_title": "Longest Increasing Subsequence",
                "complexity": {
                    "notation": "O(n^2)", "source_kind": "stream", "source_time": 50,
                    "evidence": "The speaker says the two nested loops take O(n^2) time.",
                },
                "meme": {
                    "image": str(image), "sha256": workflow.fingerprint(image), "rights": "original",
                    "rights_note": "Original geometric test fixture, no third-party imagery.",
                    "topic": "A test cat steadily climbs an increasing staircase.",
                },
            },
        ),
        evidence=[
            VisualEvidence(time=21, kind="introduction", image=str(image),
                           description="Question title and problem introduction visible.", verified_by="test"),
            VisualEvidence(time=80, kind="implementation", image=str(image),
                           description="The demonstrated algorithm is implemented here.", verified_by="test"),
            VisualEvidence(time=449, kind="completion", image=str(image),
                           description="The complete solution and successful outcome are visible.", verified_by="test"),
            VisualEvidence(time=21, kind="subtitle_space", image=str(image),
                           description="The bottom caption rectangle is clear of important content.", verified_by="test"),
        ],
    )]
    workflow.write_json(path, plan.model_dump())
    return path, plan


def save(path, plan):
    workflow.write_json(path, plan.model_dump())


def test_horizontal_is_explicit_and_long_form_without_vertical_crops(horizontal_plan):
    path, plan = horizontal_plan
    assert plan.output_format == "horizontal"
    assert plan.profile.face_region is None and plan.profile.code_region is None
    assert workflow.validate_plan(plan) == []
    segments, removed = workflow.compile_segments(plan, plan.cuts[0], threading.Event())
    assert all(isinstance(s, HorizontalRenderSegment) for s in segments)
    assert sum(s.end - s.start for s in segments) == 410
    assert removed == []
    assert workflow.load_plan(path).cuts[0].horizontal.artwork.complexity.source_kind == "stream"
    plan.output_format = "vertical"
    assert any("explicitly horizontal" in e for e in workflow.validate_plan(plan))


def test_cli_format_is_opt_in(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(workflow, "prepare", lambda *a, **k: calls.append(k) or tmp_path / "plan.json")
    assert workflow.main(["prepare", "--video", str(tmp_path / "[LeetCode] a.mp4"), "--format", "horizontal"]) == 0
    assert calls[0]["output_format"] == "horizontal"
    assert workflow.main(["prepare", "--video", str(tmp_path / "[LeetCode] b.mp4")]) == 0
    assert "output_format" not in calls[1]


def test_portrait_source_is_rejected_before_asr(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(duration=30, width=720, height=1280, fps=30))
    with pytest.raises(ValueError, match="landscape"):
        workflow.prepare(tmp_path / "[LeetCode] portrait.mp4", root=tmp_path, output_format="horizontal")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ["introduction", "implementation", "completion", "subtitle_space"])
def test_complete_solve_requires_actual_stage_and_caption_evidence(horizontal_plan, kind):
    _, plan = horizontal_plan
    plan.cuts[0].evidence = [e for e in plan.cuts[0].evidence if e.kind != kind]
    assert any(kind in e for e in workflow.validate_plan(plan))


def test_horizontal_rejects_reordered_cropped_and_unreviewed_footage(horizontal_plan):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    cut.segments.reverse()
    cut.segments[0].content_region = Region(x=0, y=0, w=0.5, h=0.5)
    cut.horizontal.coverage_review = ""
    cut.horizontal.subtitle_review = ""
    cut.title = "A misleading generic clip title"
    errors = workflow.validate_plan(plan)
    for word in ("chronological", "crop", "coverage", "subtitle", "exact numbered"):
        assert any(word in error for error in errors)


def test_each_changed_subtitle_rectangle_requires_evidence(horizontal_plan):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    cut.segments[1].subtitle_region = SubtitleRegion(x=0.2, y=0.8, w=0.6, h=0.18)
    assert any("every subtitle rectangle" in e for e in workflow.validate_plan(plan))
    cut.evidence.append(cut.evidence[-1].model_copy(update={"time": 300}))
    assert workflow.validate_plan(plan) == []


def test_silence_protects_visible_work_and_supports_segment_override(horizontal_plan, monkeypatch):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    cut.trim_silence = True
    cut.horizontal.preserve_ranges = [TimeRange(start=100, end=110, reason="Typing the important recurrence.")]
    cut.segments[1].trim_silence = False
    calls = []

    def pauses(source, start, end, *args, **kwargs):
        calls.append((start, end))
        return [(90, 120)]

    monkeypatch.setattr(montage, "detect_silences", pauses)
    segments, removed = workflow.compile_segments(plan, cut, threading.Event())
    assert calls == [(20, 220)]
    assert any(s.start == 100 and s.end == 110 for s in segments)
    assert (segments[-1].start, segments[-1].end) == (240, 450)
    assert len(removed) == 2
    assert all(not (r["start"] < 110 and r["end"] > 100) for r in removed)


def test_silent_completion_is_protected_but_brb_never_is(horizontal_plan, monkeypatch):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    cut.trim_silence = True
    monkeypatch.setattr(montage, "detect_silences",
                        lambda source, start, end, *a, **k: [(440, 450)] if start == 240 else [])
    segments, _ = workflow.compile_segments(plan, cut, threading.Event())
    assert any(s.start <= 449 < s.end for s in segments)
    with pytest.raises(ValueError, match="removed required completion"):
        workflow.compile_segments(plan, cut, threading.Event(), [TimeRange(start=448, end=450)])


def test_conflicting_exclusions_cannot_silently_erase_protected_work(horizontal_plan):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    cut.horizontal.preserve_ranges = [TimeRange(start=100, end=110)]
    with pytest.raises(ValueError, match="protected silent work"):
        workflow.compile_segments(plan, cut, threading.Event(), [TimeRange(start=104, end=106)])
    cut.horizontal.preserve_ranges = [TimeRange(start=220, end=240)]
    assert any("omit declared protected" in e for e in workflow.validate_plan(plan))


def test_source_and_chapter_bounds_and_frame_grid_are_explicit(horizontal_plan):
    _, plan = horizontal_plan
    document = plan.model_dump()
    document["cuts"][0]["horizontal"]["chapter"]["end"] = 601
    with pytest.raises(ValueError, match="beyond the source"):
        WorkflowPlan.model_validate(document)
    with pytest.raises(ValueError, match="whole 30 fps frames"):
        plan.cuts[0].horizontal.model_validate({
            **plan.cuts[0].horizontal.model_dump(), "intro_hold_seconds": 0.123,
        })
    with pytest.raises(ValueError, match="bottom empty space"):
        SubtitleRegion(x=0.1, y=0.1, w=0.8, h=0.1)


def test_vertical_signatures_preserve_the_pre_horizontal_payload(horizontal_plan):
    _, plan = horizontal_plan
    plan.output_format = "vertical"
    cut = WorkflowCut(
        id="legacy", title="Legacy vertical", category="funny", rationale="An existing faithful clip.",
        segments=[WorkflowSegment(start=1, end=3)], trim_silence=False,
    )
    legacy_cut = {
        "id": "legacy", "title": "Legacy vertical", "category": "funny",
        "problem": "", "rationale": "An existing faithful clip.",
        "segments": [{"start": 1.0, "end": 3.0, "reason": "", "view": "code",
                      "face_region": None, "content_region": None}],
        "trim_silence": False, "coherence_review": "", "evidence": [], "source_cues": None,
    }
    assert cut.model_dump() == legacy_cut
    for view, schema in (("code", 2), ("results", 3)):
        cut.segments[0].view = view
        legacy_cut["segments"][0]["view"] = view
        payload = {
            "renderer_schema": schema, "workflow": plan.workflow, "source": plan.source_sha256,
            "transcript": plan.transcript_sha256, "cues": plan.cues_sha256,
            "profile": plan.profile.model_dump(), "exclusions": [], "cut": legacy_cut,
        }
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        assert workflow.cut_signature(plan, cut) == expected


@pytest.fixture
def horizontal_draft(horizontal_plan, monkeypatch):
    from clipfarm import horizontal, transcribe, workflow_vision

    path, plan = horizontal_plan
    cut = plan.cuts[0]
    monkeypatch.setattr(workflow_vision, "scan_intervals", lambda *a, **k: {
        "samples": [{"at": 21}], "brb_ranges": [],
        "coverage": {"status": "completed", "requested_samples_complete": True, "step": 0.5},
    })

    def cover(spec, output, **dimensions):
        output.write_bytes(b"same reviewed cover for intro and delivery")
        return {**dimensions, "title": f"{spec.problem_number}. {spec.problem_title}"}

    def render(source, info, segments, cues, output, thumbnail, progress, cancel, *, intro_hold):
        assert isinstance(segments[0], HorizontalRenderSegment)
        assert cues[0].start == 21 and intro_hold == 1
        output.write_bytes(b"video with " + thumbnail.read_bytes())
        output.with_suffix(".srt").write_text("00:00:02,000 --> 00:00:05,000\nThe full question.")
        output.with_suffix(".transcript.txt").write_text("The full question.")
        workflow.write_json(output.with_suffix(".source-map.json"), {
            "version": 2, "segments": [],
            "synthetic_intro": {"thumbnail_sha256": workflow.fingerprint(thumbnail)},
        })
        return [object()] * len(segments)

    monkeypatch.setattr(workflow, "render_solution_thumbnail", cover)
    monkeypatch.setattr(horizontal, "render_horizontal", render)
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(duration=411, width=1280, height=720, fps=30))
    monkeypatch.setattr(transcribe, "transcribe", lambda *a, **k: [Cue(start=2, end=5, text="The full question.")])
    draft_path = workflow.draft_cut(path, cut.id)
    draft = workflow.read_json(draft_path)
    return path, plan, draft_path, draft


def approve_fixture(path, plan, draft_path, draft):
    workflow.transcribe_draft(path, plan.cuts[0].id)
    review_path = draft_path.parent / "review.json"
    review = workflow.read_json(review_path)
    review.update(
        verdict="approve", reviewer="test",
        notes="Synthetic test fixture approval for publication behavior only, not real editorial review, visual evidence or user approval.",
    )
    review["checks"] = dict.fromkeys(review["checks"], True)
    workflow.write_json(review_path, review)
    return review_path, review


def test_draft_binds_cover_and_review_never_auto_approves(horizontal_draft):
    path, plan, draft_path, draft = horizontal_draft
    assert draft["output_format"] == "horizontal" and draft["duration"] > 180
    assert len(draft["artifact_sha256"]) == 7
    assert Path(draft["thumbnail"]).read_bytes() in Path(draft["video"]).read_bytes()
    assert workflow.draft_cut(path, plan.cuts[0].id) == draft_path
    workflow.transcribe_draft(path, plan.cuts[0].id)
    review = workflow.read_json(draft_path.parent / "review.json")
    assert review["verdict"] == "pending" and not any(review["checks"].values())
    assert workflow.HORIZONTAL_CHECKS <= review["checks"].keys()
    assert "results_zoom_reviewed" not in review["checks"]
    assert review["thumbnail_sha256"] == draft["artifact_sha256"]["thumbnail"]
    with pytest.raises(ValueError, match="approval"):
        workflow.publish(path, plan.cuts[0].id)


def test_publish_uses_identical_intro_cover_and_landscape_gallery(horizontal_draft, monkeypatch):
    path, plan, draft_path, draft = horizontal_draft
    review_path, review = approve_fixture(path, plan, draft_path, draft)
    review["checks"]["complete_solve_reviewed"] = False
    workflow.write_json(review_path, review)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, plan.cuts[0].id)
    review["checks"]["complete_solve_reviewed"] = True
    review["thumbnail_sha256"] = "0" * 64
    workflow.write_json(review_path, review)
    with pytest.raises(ValueError, match="reviewed image"):
        workflow.publish(path, plan.cuts[0].id)
    review["thumbnail_sha256"] = draft["artifact_sha256"]["thumbnail"]
    workflow.write_json(review_path, review)
    monkeypatch.setattr(workflow, "render_solution_thumbnail", lambda *a, **k: pytest.fail("Never regenerate a reviewed cover"))
    delivered = workflow.publish(path, plan.cuts[0].id)
    for key, name in zip(workflow.HORIZONTAL_ARTIFACTS, ("thumbnail.jpg", "thumbnail.json", "credits.txt")):
        assert (delivered / name).read_bytes() == Path(draft[key]).read_bytes()
    manifest = workflow.read_json(delivered / "manifest.json")
    assert manifest["output_format"] == "horizontal"
    assert (manifest["width"], manifest["height"]) == (1280, 720)
    gallery = (delivered.parent / "index.html").read_text(encoding="utf-8")
    assert 'class="horizontal"' in gallery and 'width="1280" height="720"' in gallery
    assert "credits.txt" in gallery
    assert workflow.publish(path, plan.cuts[0].id) == delivered


@pytest.mark.parametrize("artifact", ["thumbnail", "thumbnail_metadata", "credits"])
def test_cover_sidecar_tampering_blocks_old_review(horizontal_draft, artifact):
    path, plan, _, draft = horizontal_draft
    target = Path(draft[artifact])
    target.write_bytes(b"changed after encoding")
    with pytest.raises(ValueError, match="artifact changed"):
        workflow.latest_draft(path, plan.cuts[0].id)
    assert target.read_bytes() == b"changed after encoding"


def test_evidence_and_meme_inputs_are_bound_to_the_draft(horizontal_draft):
    path, plan, _, _ = horizontal_draft
    target = Path(plan.cuts[0].horizontal.artwork.meme.image)
    target.write_bytes(b"changed local source")
    with pytest.raises(ValueError, match="fingerprint changed"):
        workflow.latest_draft(path, plan.cuts[0].id)


def test_changing_horizontal_settings_invalidates_approval(horizontal_draft):
    path, plan, _, _ = horizontal_draft
    plan.cuts[0].horizontal.intro_hold_seconds = 2
    save(path, plan)
    with pytest.raises(ValueError, match="plan changed"):
        workflow.latest_draft(path, plan.cuts[0].id)


def test_changing_display_notation_invalidates_old_draft(horizontal_draft):
    path, plan, _, _ = horizontal_draft
    plan.cuts[0].horizontal.artwork.complexity.display_notation = "O(n)"
    save(path, plan)
    with pytest.raises(ValueError, match="plan changed"):
        workflow.latest_draft(path, plan.cuts[0].id)


def test_changing_artwork_renderer_invalidates_old_draft(horizontal_draft, monkeypatch):
    path, plan, _, _ = horizontal_draft
    original = workflow.artwork_inputs
    monkeypatch.setattr(workflow, "artwork_inputs", lambda spec: {
        **original(spec), "renderer_version": "solution-artwork-test-revision",
    })
    with pytest.raises(ValueError, match="plan changed"):
        workflow.latest_draft(path, plan.cuts[0].id)


def test_changing_technique_invalidates_old_intro_and_approval(horizontal_draft):
    path, plan, _, draft = horizontal_draft
    plan.cuts[0].horizontal.artwork.technique = "Dynamic Programming"
    save(path, plan)
    assert workflow.load_plan(path).cuts[0].horizontal.artwork.technique == "Dynamic Programming"
    assert workflow.cut_signature(plan, plan.cuts[0]) != draft["signature"]
    with pytest.raises(ValueError, match="plan changed"):
        workflow.latest_draft(path, plan.cuts[0].id)
    with pytest.raises(ValueError, match="plan changed"):
        workflow.publish(path, plan.cuts[0].id)


def test_cover_credits_retain_qualifications_and_attribution(horizontal_plan, tmp_path, monkeypatch):
    _, plan = horizontal_plan
    cut = plan.cuts[0]
    spec = cut.horizontal.artwork
    spec.technique = "Dynamic Programming"
    spec.complexity.notation = "O(n^2) worst case"
    spec.complexity.display_notation = "O(n^2)"
    spec.meme.rights = "licensed"
    spec.meme.attribution = "Example artist, CC BY-SA 4.0"
    spec.meme.rights_note = "Licensed fixture; preserve the source attribution."

    def cover(spec, output, **dimensions):
        output.write_bytes(b"cover fixture")
        return dimensions

    monkeypatch.setattr(workflow, "render_solution_thumbnail", cover)
    directory = tmp_path / "cover"
    directory.mkdir()
    paths = workflow.prepare_horizontal_cover(directory, plan, cut, workflow.cut_signature(plan, cut))
    credits = Path(paths["credits"]).read_text(encoding="utf-8")
    assert "O(n^2) worst case" in credits
    assert "Data structure / algorithm: Dynamic Programming" in credits
    assert "Example artist, CC BY-SA 4.0" in credits
    assert "platform description" in credits


@pytest.mark.parametrize("name", ["thumbnail.jpg", "thumbnail.json", "credits.txt"])
def test_cover_and_provenance_are_pinned_before_encoding(horizontal_draft, monkeypatch, name):
    from clipfarm import horizontal

    path, plan, previous, _ = horizontal_draft
    plan.cuts[0].rationale += " New render fixture for a concurrent file change."
    save(path, plan)
    original_render = horizontal.render_horizontal

    def changed(*args, **kwargs):
        result = original_render(*args, **kwargs)
        (args[5].parent / name).write_bytes(b"concurrently replaced cover artifact")
        return result

    monkeypatch.setattr(horizontal, "render_horizontal", changed)
    with pytest.raises(ValueError, match="changed during rendering"):
        workflow.draft_cut(path, plan.cuts[0].id)
    assert workflow.read_json(previous.parent.parent / "latest.json")["draft"] == str(previous.resolve())


def test_intro_cover_binding_is_checked_even_when_individual_artifact_hashes_match(horizontal_draft):
    _, _, _, draft = horizontal_draft
    path = Path(draft["source_map"])
    mapping = workflow.read_json(path)
    mapping["synthetic_intro"]["thumbnail_sha256"] = "0" * 64
    workflow.write_json(path, mapping)
    draft["artifact_sha256"]["source_map"] = workflow.fingerprint(path)
    with pytest.raises(ValueError, match="same JPEG"):
        workflow.verify_draft(draft)


def test_multi_hour_inspection_uses_bounded_batches_and_resumes(horizontal_plan, monkeypatch, tmp_path):
    from clipfarm import workflow_vision

    path, plan = horizontal_plan
    plan.media.duration = 24_000
    region = plan.cuts[0].horizontal.subtitle_region
    segments = [HorizontalRenderSegment(start=0, end=22_000, subtitle_region=region)]
    calls = []
    image = plan.cuts[0].evidence[0].image

    def scan(source, intervals, directory, *, step, progress, cancel):
        calls.append(intervals)
        budget = sum(math.ceil((b - a) / step) + 2 for a, b in intervals)
        assert budget <= 4000
        return {
            "samples": [{"time": intervals[0][0], "image": image}],
            "brb_ranges": [], "contact_sheets": [], "warnings": ["Sampling is not exhaustive."],
            "coverage": {"status": "completed", "requested_samples_complete": True, "requested_samples": 1},
        }

    monkeypatch.setattr(workflow_vision, "scan_intervals", scan)
    report = workflow.cached_visual_report(path, plan, segments, tmp_path / "draft", 0.5, threading.Event())
    assert len(calls) > 1 and report["coverage"]["batch_count"] == len(calls)
    assert calls[0][0][0] == 0 and calls[-1][-1][1] == 22_000
    assert report["coverage"]["continuous_coverage"] is False
    assert report["coverage"]["certified_clean"] is False
    first_count = len(calls)
    assert workflow.cached_visual_report(path, plan, segments, tmp_path / "draft", 0.5, threading.Event()) == report
    assert len(calls) == first_count


def test_incomplete_long_form_batch_is_not_certified(horizontal_plan, monkeypatch, tmp_path):
    from clipfarm import workflow_vision

    path, plan = horizontal_plan
    plan.media.duration = 24_000
    segments = [HorizontalRenderSegment(start=0, end=22_000,
                                       subtitle_region=plan.cuts[0].horizontal.subtitle_region)]
    monkeypatch.setattr(workflow_vision, "scan_intervals", lambda *a, **k: {
        "samples": [{"time": 1}], "coverage": {"status": "failed", "requested_samples_complete": False},
    })
    with pytest.raises(ValueError, match="batch is incomplete"):
        workflow.cached_visual_report(path, plan, segments, tmp_path / "draft", 0.5, threading.Event())
    assert not (tmp_path / "draft" / "vision" / "report.json").exists()
