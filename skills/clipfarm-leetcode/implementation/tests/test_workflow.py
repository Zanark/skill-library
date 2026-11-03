import json
import hashlib
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from clipfarm import montage, workflow
from clipfarm.models import Cue, MediaInfo, Region
from clipfarm.workflow_models import DeliverySession, TimeRange, VisualEvidence, WorkflowCut, WorkflowPlan, WorkflowProfile, WorkflowSegment


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "ROOT", tmp_path)

    def thumbnail(source, at, region, title, output, *, camera_mode="required",
                  font_family="default", topic=None):
        output.write_bytes(b"camera thumbnail fixture")
        return {"width": 1080, "height": 1920, "title": title}

    monkeypatch.setattr(workflow, "render_thumbnail", thumbnail)
    source = tmp_path / "[ LeetCode ] example.mp4"
    source.write_bytes(b"source fixture")
    transcript = tmp_path / "captions.txt"
    transcript.write_text("00:00:01.000 A useful setup.\n00:00:04.000 A complete payoff.\n", encoding="utf-8")
    info = MediaInfo(duration=30, width=1280, height=720, fps=30)
    monkeypatch.setattr(workflow, "probe", lambda _: info)
    path = workflow.prepare(source, transcript, "example", tmp_path / "runs")
    plan = workflow.load_plan(path)
    plan.profile = WorkflowProfile(
        face_region=Region(x=0, y=0.8, w=0.2, h=0.2),
        code_region=Region(x=0.5, y=0.1, w=0.5, h=0.5),
        results_region=Region(x=0, y=0.1, w=0.45, h=0.4),
    )
    plan.reviewed_entire_transcript = True
    plan.editorial_notes = "Read every cue and its context; the selected joke preserves its setup and payoff."
    plan.cuts = [WorkflowCut(
        id="example-cut", title="A useful clip", category="funny", rationale="Clear setup and payoff.",
        segments=[WorkflowSegment(start=1, end=5), WorkflowSegment(start=8, end=12)],
        trim_silence=False, coherence_review="The selected setup leads to its actual payoff without changing meaning.",
    )]
    workflow.write_json(path, plan.model_dump())
    return path, plan


def test_workflow_cli_from_another_directory(tmp_path):
    result = subprocess.run([sys.executable, "-m", "clipfarm", "workflow", "--help"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "review-transcribe" in result.stdout and "publish" in result.stdout


@pytest.mark.parametrize("name", ["[LeetCode] a.mp4", "[ LeetCode ] a.mp4", "b [leetcode].mkv"])
def test_filename_routing(name):
    assert workflow.workflow_for(Path(name)) == "leetcode"


@pytest.mark.parametrize("name", ["leetcode.mp4", "[System Design] a.mp4", "[leet code].mp4"])
def test_unregistered_names_are_not_silently_routed(name):
    with pytest.raises(ValueError, match="filename"):
        workflow.workflow_for(Path(name))


def test_future_workflow_not_implemented():
    with pytest.raises(ValueError, match="not implemented"):
        workflow.workflow_for(Path("[LeetCode] a.mp4"), "unsupported")


def test_system_design_routing_is_explicit_not_a_filename_rewrite():
    source = Path("Design a Rate Limiter _ System Design Interview.mp4")
    assert workflow.workflow_for(source, "system-design") == "system-design"
    with pytest.raises(ValueError, match="filename"):
        workflow.workflow_for(source)


@pytest.fixture
def system_design(prepared):
    path, plan = prepared
    source = Path(plan.source)
    plan.source = str(source.rename(source.with_name("Design a Rate Limiter _ System Design Interview.mp4")))
    plan.workflow = "system-design"
    plan.profile.results_region = None
    plan.cuts[0].category = "explanation"
    plan.cuts[0].title = "Why rate limiting protects a service"
    workflow.write_json(path, plan.model_dump())
    return path, plan


def test_system_design_models_reject_unknown_workflows_and_horizontal(system_design):
    _, plan = system_design
    data = plan.model_dump()
    with pytest.raises(ValueError, match="vertical output only"):
        WorkflowPlan.model_validate({**data, "output_format": "horizontal"})
    with pytest.raises(ValueError, match="workflow"):
        WorkflowPlan.model_validate({**data, "workflow": "unknown"})
    plan.output_format = "horizontal"
    assert any("vertical output only" in error for error in workflow.validate_plan(plan))


@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_system_design_uses_explicit_segment_diagrams_and_camera_policy(system_design, camera_mode):
    _, plan = system_design
    face = plan.profile.face_region
    diagram = plan.profile.code_region
    plan.profile = WorkflowProfile(camera_mode=camera_mode)
    assert any("content_region" in error for error in workflow.validate_plan(plan))
    for segment in plan.cuts[0].segments:
        segment.content_region = diagram
    if camera_mode == "required":
        assert any("face_region" in error for error in workflow.validate_plan(plan))
        for segment in plan.cuts[0].segments:
            segment.face_region = face
    assert workflow.validate_plan(plan) == []
    compiled, _ = workflow.compile_segments(plan, plan.cuts[0], threading.Event())
    assert all(s.content_region == diagram and s.camera_mode == camera_mode for s in compiled)
    assert all(s.face_region == (face if camera_mode == "required" else None) for s in compiled)
    assert all(s.layout == "leetcode" and not s.results_zoom for s in compiled)
    plan.reviewed_entire_transcript = False
    plan.cuts[0].coherence_review = ""
    assert any("entire transcript" in error for error in workflow.validate_plan(plan))
    assert any("coherence" in error for error in workflow.validate_plan(plan))


@pytest.mark.parametrize("category", ["submission", "solution"])
def test_system_design_does_not_accept_leetcode_categories(system_design, category):
    _, plan = system_design
    plan.cuts[0].category = category
    assert any("explanation or funny" in error for error in workflow.validate_plan(plan))


def test_system_design_does_not_require_or_invent_submission_evidence(system_design):
    _, plan = system_design
    assert workflow.validate_plan(plan) == []
    assert workflow.review_checks(plan, plan.cuts[0]) == {
        "coherent", "useful_content", "captions_reviewed", "visuals_reviewed", "brb_reviewed",
    }
    plan.cuts[0].segments[0].view = "results"
    assert any("not submission/runtime-results" in error for error in workflow.validate_plan(plan))
    plan.cuts[0].segments[0].view = "code"
    plan.cuts[0].evidence = [VisualEvidence(
        kind="results", time=2, image="not-real.png", description="Not a System Design result.", runtime_ms=0,
    )]
    assert any("not submission/runtime-results" in error for error in workflow.validate_plan(plan))


def test_legacy_system_design_allows_individually_authored_a_b_and_combined_variants(system_design):
    _, plan = system_design
    plan.clip_policy = None
    template = plan.cuts[0]
    plan.cuts = [
        template.model_copy(update={"id": "topic-a", "title": "Topic A", "segments": [template.segments[0]]}),
        template.model_copy(update={"id": "topic-b", "title": "Topic B", "segments": [template.segments[1]]}),
        template.model_copy(update={"id": "topics-a-b", "title": "Topics A and B"}),
    ]
    assert workflow.validate_plan(plan) == []
    assert len({workflow.cut_signature(plan, cut) for cut in plan.cuts}) == 3
    assert len(workflow.compile_segments(plan, plan.cuts[2], threading.Event())[0]) == 2


def test_prepare_preserves_cues_and_refuses_overwrite(prepared):
    path, plan = prepared
    assert len(workflow.load_cues(path)) == 2
    assert workflow.load_cues(path)[0].start == 1
    assert "A complete payoff" in (path.parent / "source-transcript.txt").read_text()
    with pytest.raises(ValueError, match="already"):
        workflow.prepare(Path(plan.source), Path(plan.transcript), plan.run_id, path.parent.parent)


def test_stale_inputs_and_caption_snapshots_fail(prepared):
    path, plan = prepared
    cues = path.parent / "source-cues.json"
    original = cues.read_bytes()
    cues.write_text("[]")
    with pytest.raises(ValueError, match="snapshot changed"):
        workflow.load_cues(path)
    cues.write_bytes(original)
    Path(plan.transcript).write_text("modified")
    with pytest.raises(ValueError, match="Input changed"):
        workflow.load_plan(path)


def test_review_is_not_assumed(prepared):
    _, plan = prepared
    assert workflow.validate_plan(plan) == []
    plan.reviewed_entire_transcript = False
    plan.cuts[0].coherence_review = ""
    errors = workflow.validate_plan(plan)
    assert any("entire transcript" in e for e in errors)
    assert any("coherence" in e for e in errors)


def test_animated_results_invalidate_only_results_render_signatures(prepared):
    _, plan = prepared
    cut = plan.cuts[0]

    def previous_signature():
        payload = {
            "renderer_schema": 2, "workflow": plan.workflow, "source": plan.source_sha256,
            "transcript": plan.transcript_sha256, "cues": plan.cues_sha256,
            "profile": plan.profile.model_dump(),
            "exclusions": [r.model_dump() for r in plan.exclusions], "cut": cut.model_dump(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    assert workflow.cut_signature(plan, cut) == previous_signature()
    cut.segments[-1].view = "results"
    assert workflow.cut_signature(plan, cut) != previous_signature()


@pytest.mark.parametrize("view,schema", [("code", 2), ("results", 3)])
def test_camera_mode_default_does_not_change_old_profile_or_signature(prepared, view, schema):
    _, plan = prepared
    cut = plan.cuts[0]
    cut.segments[-1].view = view
    legacy_profile = {
        "face_region": plan.profile.face_region.model_dump(),
        "code_region": plan.profile.code_region.model_dump(),
        "results_region": plan.profile.results_region.model_dump(),
        "subtitle_y": 0.82, "caption_style": "clean",
    }
    payload = {
        "renderer_schema": schema, "workflow": plan.workflow, "source": plan.source_sha256,
        "transcript": plan.transcript_sha256, "cues": plan.cues_sha256,
        "profile": legacy_profile, "exclusions": [], "cut": cut.model_dump(),
    }
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    for profile in (legacy_profile, {**legacy_profile, "camera_mode": "required"}):
        plan.profile = WorkflowProfile.model_validate(profile)
        assert plan.profile.model_dump() == legacy_profile
        assert json.loads(plan.model_dump_json())["profile"] == legacy_profile
        assert workflow.cut_signature(plan, cut) == expected
    plan.profile = WorkflowProfile.model_validate({
        **legacy_profile, "camera_mode": "absent", "face_region": None,
    })
    assert workflow.cut_signature(plan, cut) != expected
    assert json.loads(plan.model_dump_json())["profile"]["camera_mode"] == "absent"
    assert WorkflowPlan.model_validate_json(plan.model_dump_json()) == plan


def test_no_camera_is_authored_not_inferred_and_still_requires_content(prepared):
    _, plan = prepared
    plan.profile.face_region = None
    assert any("avatar" in e for e in workflow.validate_plan(plan))
    with pytest.raises(ValueError, match="explicit avatar"):
        workflow.compile_segments(plan, plan.cuts[0], threading.Event())
    plan.profile.camera_mode = "absent"
    assert workflow.validate_plan(plan) == []
    plan.profile.code_region = None
    assert workflow.validate_plan(plan)
    with pytest.raises(ValueError):
        workflow.compile_segments(plan, plan.cuts[0], threading.Event())


def test_camera_free_profile_rejects_contradictory_or_automatic_declarations(prepared):
    _, plan = prepared
    with pytest.raises(ValueError, match="absent camera"):
        WorkflowProfile(camera_mode="absent", face_region=plan.profile.face_region)
    with pytest.raises(ValueError):
        WorkflowProfile(camera_mode="auto")
    data = plan.model_dump()
    data["profile"].update(camera_mode="absent", face_region=None)
    data["cuts"][0]["segments"][1]["face_region"] = plan.profile.face_region.model_dump()
    with pytest.raises(ValueError, match="segment face_region"):
        WorkflowPlan.model_validate(data)
    plan.profile.camera_mode = "absent"
    assert any("without a face_region" in e for e in workflow.validate_plan(plan))
    plan.profile.face_region = None
    plan.cuts[0].segments[0].face_region = Region(x=0, y=0, w=0.1, h=0.1)
    assert any("segment face_region" in e for e in workflow.validate_plan(plan))
    plan.cuts[0].segments[0].face_region = None
    plan.output_format = "horizontal"
    with pytest.raises(ValueError, match="only for vertical"):
        WorkflowPlan.model_validate(plan.model_dump())


@pytest.fixture
def camera_free(prepared):
    path, plan = prepared
    plan.profile = WorkflowProfile(
        camera_mode="absent", code_region=plan.profile.code_region,
        results_region=plan.profile.results_region,
    )
    workflow.write_json(path, plan.model_dump())
    return path, plan


def test_camera_free_compile_keeps_overrides_and_results(camera_free):
    _, plan = camera_free
    cut = plan.cuts[0]
    diagram = Region(x=0.1, y=0.1, w=0.4, h=0.5)
    cut.segments[0].content_region = diagram
    cut.segments[1].view = "results"
    segments, _ = workflow.compile_segments(plan, cut, threading.Event())
    assert [s.content_region for s in segments] == [diagram, plan.profile.results_region]
    assert all(s.camera_mode == "absent" and s.face_region is None and s.subtitle_y == 0.82 for s in segments)
    assert [s.results_zoom for s in segments] == [False, True]
    plan.profile.results_region = None
    assert any("verified results-region" in e for e in workflow.validate_plan(plan))


def test_subtraction_handles_overlaps_and_edges():
    assert workflow.subtract_ranges(0, 10, [(2, 4), (3, 6), (8, 12)]) == [(0, 2), (6, 8)]
    assert workflow.subtract_ranges(2, 3, [(0, 5)]) == []
    assert workflow.subtract_ranges(0, 1, [(1, 2)]) == [(0, 1)]
    with pytest.raises(ValueError):
        workflow.subtract_ranges(0, 10, [(3, 2)])


def test_compile_retains_guards_and_never_keeps_brb(prepared, monkeypatch):
    _, plan = prepared
    plan.exclusions = [TimeRange(start=2, end=3, reason="BRB")]
    cut = plan.cuts[0]
    cut.trim_silence = True
    monkeypatch.setattr(montage, "detect_silences",
                        lambda source, start, end, cancel, **_: [(3.2, 4.2)] if start == 3 else [])
    segments, removed = workflow.compile_segments(plan, cut, threading.Event())
    expected = [(1, 2), (3, 3.32), (4.08, 5), (8, 12)]
    assert len(segments) == len(expected)
    for segment, bounds in zip(segments, expected):
        assert (segment.start, segment.end) == pytest.approx(bounds)
    assert all(s.layout == "leetcode" and s.subtitle_y == 0.82 for s in segments)
    assert any(r["reason"] == "silence interior" for r in removed)


def test_submission_requires_real_evidence_in_the_results_view(prepared, tmp_path):
    _, plan = prepared
    cut = plan.cuts[0]
    cut.category = "submission"
    assert any("runtime-results" in error for error in workflow.validate_plan(plan))
    image = tmp_path / "evidence.png"
    image.write_bytes(b"image fixture")
    cut.evidence = [
        VisualEvidence(kind="submission", time=2, image=str(image), description="Submit action", verified_by="test"),
        VisualEvidence(kind="results", time=9, image=str(image), description="Accepted 15ms",
                       verified_by="test", runtime_ms=15),
    ]
    assert any("required view" in error for error in workflow.validate_plan(plan))
    cut.segments[1].view = "results"
    assert not workflow.validate_plan(plan)
    plan.exclusions = [TimeRange(start=8, end=10)]
    with pytest.raises(ValueError, match="required results"):
        workflow.compile_segments(plan, cut, threading.Event())


def fake_draft(path, plan):
    cut = plan.cuts[0]
    signature = workflow.cut_signature(plan, cut)
    directory = path.parent / "drafts" / cut.id / signature[:12]
    directory.mkdir(parents=True)
    names = {"video": "clip.mp4", "subtitles": "clip.srt",
             "transcript": "clip.transcript.txt", "source_map": "clip.source-map.json"}
    segments, _ = workflow.compile_segments(plan, cut, threading.Event())
    draft = {"workflow": plan.workflow, "signature": signature, "title": cut.title, "category": cut.category,
             "duration": sum(s.end - s.start for s in segments), "removed": [],
             "effective_segments": [s.model_dump() for s in segments],
             "visual_report": {"coverage": {"step": 0.5}}}
    for key, name in names.items():
        artifact = directory / name
        artifact.write_bytes(f"{key} fixture".encode())
        draft[key] = str(artifact)
    elapsed = 0
    spans = []
    for index, segment in enumerate(segments):
        duration = segment.end - segment.start
        spans.append({
            "index": index, "source_start": segment.start, "source_end": segment.end,
            "output_start": elapsed, "output_end": elapsed + duration,
        })
        elapsed += duration
    workflow.write_json(Path(draft["source_map"]), {"version": 1, "fps": 30, "duration": elapsed, "segments": spans})
    draft["artifact_sha256"] = {key: workflow.fingerprint(Path(draft[key])) for key in names}
    draft["video_sha256"] = draft["artifact_sha256"]["video"]
    workflow.write_json(directory / "draft.json", draft)
    workflow.write_json(directory.parent / "latest.json", {"draft": str(directory / "draft.json")})
    return directory, draft


def approve(directory, draft, cut):
    asr = directory / "review-asr.txt"
    asr.write_text("A useful setup. A complete payoff.")
    transcript_hash = workflow.fingerprint(asr)
    workflow.write_json(directory / "review-asr.json", {
        "workflow": draft["workflow"], "video_sha256": draft["video_sha256"],
        "transcript_sha256": transcript_hash, "model": "base",
    })
    workflow.write_json(directory / "review.json", {
        "workflow": draft["workflow"], "cut_id": cut.id, "verdict": "approve", "reviewer": "test",
        "video_sha256": draft["video_sha256"], "transcript_sha256": transcript_hash,
        "checks": dict.fromkeys(["coherent", "useful_content", "captions_reviewed", "visuals_reviewed", "brb_reviewed"], True),
        "notes": "Read both generated transcripts and inspected the retained visual evidence. "
                 "The setup and payoff remain intelligible; this fixture tests publication gates, not real footage.",
    })


@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_system_design_draft_asr_review_publish_and_gallery(system_design, monkeypatch, camera_mode):
    from clipfarm import transcribe, workflow_vision

    path, plan = system_design
    if camera_mode == "absent":
        plan.profile = WorkflowProfile(camera_mode="absent", code_region=plan.profile.code_region)
        workflow.write_json(path, plan.model_dump())
    cut = plan.cuts[0]
    monkeypatch.setattr(workflow_vision, "scan_intervals", lambda *a, **k: {
        "samples": [{"at": 2}], "brb_ranges": [],
        "coverage": {"status": "completed", "requested_samples_complete": True, "step": 0.5},
    })

    def render(source, info, segments, cues, output, preview, progress, cancel):
        assert str(source) == plan.source
        assert all(s.content_region == plan.profile.code_region for s in segments)
        assert all(s.camera_mode == camera_mode and not s.results_zoom for s in segments)
        spans = []
        elapsed = 0
        for index, segment in enumerate(segments):
            duration = segment.end - segment.start
            spans.append({
                "index": index, "source_start": segment.start, "source_end": segment.end,
                "output_start": elapsed, "output_end": elapsed + duration,
            })
            elapsed += duration
        for suffix in (".mp4", ".srt", ".transcript.txt"):
            output.with_suffix(suffix).write_text("Synthetic fixture, not encoded media.", encoding="utf-8")
        workflow.write_json(output.with_suffix(".source-map.json"), {
            "version": 1, "fps": 30, "duration": elapsed, "segments": spans,
        })
        return spans

    monkeypatch.setattr(montage, "render_montage", render)
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(duration=8, width=1080, height=1920, fps=30))
    draft_path = workflow.draft_cut(path, cut.id)
    draft = workflow.read_json(draft_path)
    assert draft["workflow"] == "system-design"
    assert workflow.draft_cut(path, cut.id) == draft_path
    monkeypatch.setattr(transcribe, "transcribe", lambda *a: [Cue(start=0, end=2, text="Rate limiting protects a service.")])
    audio_transcript = workflow.transcribe_draft(path, cut.id)
    asr = workflow.read_json(draft_path.parent / "review-asr.json")
    assert asr["workflow"] == "system-design"
    assert asr["transcript_sha256"] == workflow.fingerprint(audio_transcript)
    review_path = draft_path.parent / "review.json"
    review = workflow.read_json(review_path)
    assert review["workflow"] == "system-design"
    assert review["verdict"] == "pending" and not any(review["checks"].values())
    with pytest.raises(ValueError, match="approval"):
        workflow.publish(path, cut.id)
    review.update(verdict="approve", reviewer="test",
                  notes="Synthetic test fixture: independently checked the source and output transcripts, "
                        "usefulness, retained diagram/camera framing, captions and all joins. Not actual media approval.")
    review["checks"] = dict.fromkeys(review["checks"], True)
    for check in workflow.review_checks(plan, cut):
        review["checks"][check] = False
        workflow.write_json(review_path, review)
        with pytest.raises(ValueError, match="Not all"):
            workflow.publish(path, cut.id)
        review["checks"][check] = True
    workflow.write_json(review_path, review)
    final = workflow.publish(path, cut.id)
    manifest = workflow.read_json(final / "manifest.json")
    assert manifest["workflow"] == "system-design" and manifest["category"] == "explanation"
    assert manifest["source"] == plan.source
    gallery = (final.parent / "index.html").read_text(encoding="utf-8")
    assert "ClipFarm / System Design" in gallery and "Reviewed System Design clips" in gallery
    assert "LeetCode" not in gallery and "leetcode" not in gallery
    assert workflow.publish(path, cut.id) == final


@pytest.mark.parametrize("record_name", ["draft.json", "review-asr.json", "review.json"])
@pytest.mark.parametrize("record_workflow", [None, "leetcode"])
def test_system_design_rejects_mislabeled_or_missing_artifact_workflow(system_design, record_name, record_workflow):
    path, plan = system_design
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    record_path = directory / record_name
    record = workflow.read_json(record_path)
    if record_workflow is None:
        record.pop("workflow")
    else:
        record["workflow"] = record_workflow
    workflow.write_json(record_path, record)
    with pytest.raises(ValueError, match="different workflow"):
        workflow.publish(path, plan.cuts[0].id)
    assert not (path.parent / "final").exists()


def test_old_leetcode_artifacts_without_workflow_metadata_still_publish(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    for name in ("draft.json", "review-asr.json", "review.json"):
        record_path = directory / name
        record = workflow.read_json(record_path)
        record.pop("workflow")
        workflow.write_json(record_path, record)
    final = workflow.publish(path, plan.cuts[0].id)
    for folder in (final, path.parent / "final" / plan.cuts[0].id):
        manifest_path = folder / "manifest.json"
        manifest = workflow.read_json(manifest_path)
        manifest.pop("workflow")
        workflow.write_json(manifest_path, manifest)
    assert workflow.publish(path, plan.cuts[0].id) == final
    assert "ClipFarm / LeetCode" in (final.parent / "index.html").read_text(encoding="utf-8")


def test_workflow_change_invalidates_existing_render_and_approval(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    plan.workflow = "system-design"
    workflow.write_json(path, plan.model_dump())
    with pytest.raises(ValueError, match="plan changed"):
        workflow.publish(path, plan.cuts[0].id)


def test_question_titles_are_explicit_versioned_and_legacy_compatible(prepared, monkeypatch):
    path, plan = prepared
    cut = plan.cuts[0]
    monkeypatch.setattr(workflow, "title_layout", lambda text: {"text": text, "font": {"sha256": "a" * 64}})
    before = workflow.cut_signature(plan, cut)
    assert "show_question_title" not in plan.profile.model_dump()
    assert "question_title" not in cut.model_dump()
    plan.profile.show_question_title = True
    assert any("Question titles" in error for error in workflow.validate_plan(plan))
    cut.problem = "217. Contains Duplicate"
    assert workflow.validate_plan(plan) == []
    assert workflow.resolved_question_title(plan, cut) == cut.problem
    clips, _ = workflow.compile_segments(plan, cut, threading.Event())
    assert all(c.question_title == cut.problem for c in clips)
    assert "question_title_reviewed" in workflow.review_checks(plan, cut)
    titled = workflow.cut_signature(plan, cut)
    assert titled != before
    monkeypatch.setattr(workflow, "title_layout", lambda text: {"text": text, "font": {"sha256": "b" * 64}})
    assert workflow.cut_signature(plan, cut) != titled
    plan.profile.show_question_title = False
    cut.problem = ""
    assert workflow.cut_signature(plan, cut) == before


@pytest.mark.parametrize("kind", ["leetcode", "system-design"])
@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_two_level_cover_binding_does_not_change_video_signature(prepared, monkeypatch, kind, camera_mode):
    path, plan = prepared
    plan.workflow = kind
    plan.profile.show_question_title = True
    plan.profile.camera_mode = camera_mode
    if camera_mode == "absent":
        plan.profile.face_region = None
    cut = plan.cuts[0]
    cut.question_title = "Design a Rate Limiter" if kind == "system-design" else "217. Contains Duplicate"
    monkeypatch.setattr(workflow, "title_layout", lambda text: {"text": text, "font": {"sha256": "a" * 64}})
    directory, draft = fake_draft(path, plan)
    signature = workflow.cut_signature(plan, cut)
    if camera_mode == "absent":
        monkeypatch.setattr(workflow, "thumbnail_frame", lambda *_args, **_kwargs: pytest.fail("No camera shot"))
    workflow.ensure_thumbnail(directory, plan, cut, draft)
    metadata = directory / "thumbnail.json"
    record = workflow.read_json(metadata)
    assert record["title"] == cut.question_title and record["topic"] == cut.title
    assert record["renderer"] == (
        "problem-topic-camera-1" if camera_mode == "absent" else "problem-topic-camera-3"
    )
    assert record["shot_kind"] == ("none" if camera_mode == "absent" else "camera")
    assert record["schema_version"] == 2
    assert workflow.cut_signature(plan, cut) == signature
    assert workflow.fingerprint(Path(draft["video"])) == draft["video_sha256"]
    workflow.ensure_thumbnail(directory, plan, cut, draft)
    if camera_mode == "absent":
        assert record["source_time"] is None and record["span_index"] is None
        assert "camera_region" not in record and "content_region" not in record
    stale_renderer = "problem-topic-camera-1" if camera_mode == "required" else "question-only-old"
    for field, value in (("topic", "Wrong focus"), ("renderer", stale_renderer)):
        workflow.write_json(metadata, {**record, field: value})
        with pytest.raises(ValueError, match="Thumbnail changed"):
            workflow.ensure_thumbnail(directory, plan, cut, draft)
    workflow.write_json(metadata, record)


def test_system_design_question_cover_and_header_require_fresh_approval(system_design, monkeypatch):
    path, plan = system_design
    cut = plan.cuts[0]
    plan.profile.show_question_title = True
    cut.problem = "Rate limiter - source-qualified interview sketch"
    assert any("Supply question_title" in error for error in workflow.validate_plan(plan))
    cut.question_title = "Design a Rate Limiter"
    monkeypatch.setattr(workflow, "title_layout", lambda text: {"text": text, "font": {"sha256": "a" * 64}})
    workflow.write_json(path, plan.model_dump())
    directory, draft = fake_draft(path, plan)
    draft["question_heading"] = workflow.title_layout(cut.question_title)
    workflow.write_json(directory / "draft.json", draft)
    approve(directory, draft, cut)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, cut.id)
    review_path = directory / "review.json"
    review = workflow.read_json(review_path)
    review["checks"]["question_title_reviewed"] = True
    workflow.write_json(review_path, review)
    calls = []

    def cover(source, at, region, title, output, **options):
        calls.append((title, options))
        output.write_bytes(b"Consolas problem-and-topic fixture")
        return {"title": title}

    monkeypatch.setattr(workflow, "render_thumbnail", cover)
    final = workflow.publish(path, cut.id)
    assert calls == [("Design a Rate Limiter", {"font_family": "Consolas", "topic": cut.title})]
    assert workflow.read_json(final / "thumbnail.json")["title"] == cut.question_title
    assert workflow.read_json(final / "thumbnail.json")["topic"] == cut.title
    manifest = workflow.read_json(final / "manifest.json")
    assert manifest["title"] == cut.title
    assert manifest["question_heading"]["text"] == cut.question_title
    draft["question_heading"]["text"] = "Wrong question"
    workflow.write_json(directory / "draft.json", draft)
    with pytest.raises(ValueError, match="Question-heading provenance"):
        workflow.latest_draft(path, cut.id)


def test_gallery_labels_mixed_legacy_and_system_design_bundles(tmp_path):
    for cut_id, workflow_id in (("legacy", None), ("design", "system-design")):
        item = {"cut_id": cut_id, "title": "<Reviewed title>", "category": "explanation",
                "duration": 12, "review_notes": "<review notes>"}
        if workflow_id:
            item["workflow"] = workflow_id
        workflow.write_json(tmp_path / cut_id / "manifest.json", item)
    gallery = workflow._write_gallery(tmp_path).read_text(encoding="utf-8")
    assert "ClipFarm / Reviewed clips" in gallery
    assert "LeetCode &middot; explanation" in gallery and "System Design &middot; explanation" in gallery
    assert "&lt;Reviewed title&gt;" in gallery and "<Reviewed title>" not in gallery


def test_publish_requires_approval_and_preserves_provenance(prepared, tmp_path, monkeypatch):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    review_path = directory / "review.json"
    review = workflow.read_json(review_path)
    review["checks"]["coherent"] = False
    workflow.write_json(review_path, review)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, plan.cuts[0].id)
    assert not (path.parent / "final").exists()
    assert not (tmp_path / "results").exists()
    review["checks"]["coherent"] = True
    workflow.write_json(review_path, review)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    final = workflow.publish(path, plan.cuts[0].id)
    assert final == workflow.results_directory(plan) / plan.cuts[0].id
    archive = path.parent / "final" / plan.cuts[0].id
    for artifact in archive.iterdir():
        assert (final / artifact.name).read_bytes() == artifact.read_bytes()
    assert (final / "clip.mp4").read_bytes() == Path(draft["video"]).read_bytes()
    assert (final / "transcript.audio.txt").is_file()
    assert (final.parent / "index.html").is_file()
    assert workflow.read_json(final / "manifest.json")["source_sha256"] == plan.source_sha256
    thumbnail = workflow.read_json(final / "thumbnail.json")
    assert thumbnail["title"] == plan.cuts[0].title
    assert thumbnail["video_sha256"] == draft["video_sha256"]
    assert thumbnail["source_sha256"] == plan.source_sha256
    assert thumbnail["sha256"] == workflow.fingerprint(final / "thumbnail.jpg")
    gallery = (final.parent / "index.html").read_text(encoding="utf-8")
    assert 'poster="example-cut/thumbnail.jpg"' in gallery
    assert 'download="example-cut-thumbnail.jpg">Thumbnail' in gallery
    monkeypatch.setattr(workflow, "render_thumbnail", lambda *a: pytest.fail("Reuse the existing thumbnail"))
    assert workflow.publish(path, plan.cuts[0].id) == final


def test_posting_text_backfills_without_rerendering_or_overwriting_conflicts(prepared):
    from clipfarm.posting import PostingRecord

    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    delivered = workflow.publish(path, plan.cuts[0].id)
    original = {p.name: workflow.fingerprint(p) for p in delivered.iterdir()}
    signature = workflow.cut_signature(plan, plan.cuts[0])
    private = path.parent / "final" / plan.cuts[0].id
    record = PostingRecord(
        caption="A scoped explanation.\n\n#LeetCode", alt_text="A title and a camera image.",
        reviewed_by="Fixture posting editor", video_sha256=draft["video_sha256"],
        thumbnail_sha256=workflow.fingerprint(private / "thumbnail.jpg"),
    )
    workflow.write_json(private / "posting.json", record.model_dump())
    assert workflow.publish(path, plan.cuts[0].id) == delivered
    assert workflow.cut_signature(plan, plan.cuts[0]) == signature
    assert all(workflow.fingerprint(delivered / name) == sha for name, sha in original.items())
    assert (delivered / "posting.json").read_bytes() == (private / "posting.json").read_bytes()
    (delivered / "posting.json").write_text("Do not overwrite my changes", encoding="utf-8")
    with pytest.raises(ValueError, match="Different or incomplete results"):
        workflow.publish(path, plan.cuts[0].id)


def test_music_recommendation_backfills_without_changing_media_or_approval(prepared):
    from clipfarm.music_recommendations import RECOMMENDATION_FILE, MusicRecommendation

    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    delivered = workflow.publish(path, plan.cuts[0].id)
    original = {p.name: workflow.fingerprint(p) for p in delivered.iterdir()}
    signature = workflow.cut_signature(plan, plan.cuts[0])
    private = path.parent / "final" / plan.cuts[0].id
    record = MusicRecommendation(
        song="A Walk", artist="Tycho", version="Original Dive album version",
        reference_url="https://music.example.org/a-walk", fit_reason="A brighter mood for the actual payoff.",
        mix_guidance="Keep the voice prominent; audition in the app.",
        video_sha256=draft["video_sha256"], recommended_by="Fixture editor",
        recommended_at="2026-09-27T03:19:32+05:30",
    )
    workflow.write_json(private / RECOMMENDATION_FILE, record.model_dump(mode="json"))
    assert workflow.publish(path, plan.cuts[0].id) == delivered
    assert workflow.publish(path, plan.cuts[0].id) == delivered
    assert workflow.cut_signature(plan, plan.cuts[0]) == signature
    assert all(workflow.fingerprint(delivered / name) == sha for name, sha in original.items())
    assert (delivered / RECOMMENDATION_FILE).read_bytes() == (private / RECOMMENDATION_FILE).read_bytes()
    assert "Suggested music - add it yourself" in (delivered.parent / "index.html").read_text(encoding="utf-8")
    assert not (delivered / "music.json").exists()
    (delivered / RECOMMENDATION_FILE).write_text("Preserve my changed recommendation", encoding="utf-8")
    with pytest.raises(ValueError, match="Different or incomplete results"):
        workflow.publish(path, plan.cuts[0].id)
    assert (delivered / RECOMMENDATION_FILE).read_text(encoding="utf-8") == "Preserve my changed recommendation"


def test_music_recommendation_rejects_wrong_video_before_backfill(prepared):
    from clipfarm.music_recommendations import RECOMMENDATION_FILE, MusicRecommendation

    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    delivered = workflow.publish(path, plan.cuts[0].id)
    original = {p.name: workflow.fingerprint(p) for p in delivered.iterdir()}
    private = path.parent / "final" / plan.cuts[0].id
    record = MusicRecommendation(
        song="Resonance", artist="HOME", version="Original Odyssey album version",
        reference_url="https://music.example.org/resonance", fit_reason="Warm ambient mood.",
        mix_guidance="Keep speech clear.", video_sha256="0" * 64,
        recommended_by="Fixture editor", recommended_at="2026-09-27T03:19:32+05:30",
    )
    workflow.write_json(private / RECOMMENDATION_FILE, record.model_dump(mode="json"))
    with pytest.raises(ValueError, match="different video"):
        workflow.publish(path, plan.cuts[0].id)
    assert {p.name: workflow.fingerprint(p) for p in delivered.iterdir()} == original


@pytest.mark.parametrize("name", [
    "clip.mp4", "clip.srt", "review.json", "manifest.json", "thumbnail.jpg", "thumbnail.json",
])
def test_publish_preserves_conflicting_results(prepared, name):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    final = workflow.publish(path, plan.cuts[0].id)
    (final / name).write_bytes(b"user-modified delivery")
    with pytest.raises(ValueError, match="Different or incomplete results"):
        workflow.publish(path, plan.cuts[0].id)
    assert (final / name).read_bytes() == b"user-modified delivery"
    assert (path.parent / "final" / plan.cuts[0].id / name).read_bytes() != b"user-modified delivery"


def test_results_copy_failure_preserves_archive_and_can_resume(prepared, tmp_path, monkeypatch):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    original_copy = workflow.shutil.copy2

    def fail_delivery(source, destination):
        if Path(destination).is_relative_to(tmp_path / "results") and Path(source).name == "clip.srt":
            raise OSError("Simulated results disk failure")
        return original_copy(source, destination)

    monkeypatch.setattr(workflow.shutil, "copy2", fail_delivery)
    with pytest.raises(OSError, match="results disk failure"):
        workflow.publish(path, plan.cuts[0].id)
    assert not list(workflow.results_directory(plan).iterdir())
    archive = path.parent / "final" / plan.cuts[0].id
    assert (archive / "clip.mp4").read_bytes() == Path(draft["video"]).read_bytes()
    monkeypatch.setattr(workflow.shutil, "copy2", original_copy)
    final = workflow.publish(path, plan.cuts[0].id)
    assert (final / "clip.mp4").read_bytes() == (archive / "clip.mp4").read_bytes()
    assert (final.parent / "index.html").is_file()


def test_thumbnail_backfills_legacy_bundles_without_changing_published_files(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    final = workflow.publish(path, plan.cuts[0].id)
    archive = path.parent / "final" / plan.cuts[0].id
    original = {p.name: p.read_bytes() for p in final.iterdir()}
    for folder in (archive, final):
        for name in workflow.THUMBNAIL_FILES:
            (folder / name).unlink()
    assert workflow.publish(path, plan.cuts[0].id) == final
    for name, value in original.items():
        assert (final / name).read_bytes() == value
        assert (archive / name).read_bytes() == value


def test_session_gallery_accumulates_sources_and_disambiguates_cut_folders(prepared, tmp_path):
    path, plan = prepared
    plan.delivery = DeliverySession(requested_at="2026-09-25T23:41:12.327Z", notice="Music is not included.")
    workflow.write_json(path, plan.model_dump())
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    first = workflow.publish(path, plan.cuts[0].id)
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    other = plan.model_copy(deep=True)
    other.run_id = "another-source"
    other.cuts[0].title = "Another useful clip"
    other_path = tmp_path / "runs" / other.run_id / "plan.json"
    workflow.write_json(other_path, other.model_dump())
    workflow.shutil.copy2(path.parent / "source-cues.json", other_path.parent / "source-cues.json")
    directory, draft = fake_draft(other_path, other)
    approve(directory, draft, other.cuts[0])
    second = workflow.publish(other_path, other.cuts[0].id)
    assert first != second and first.parent == second.parent
    assert first.parent.name == "session_20260926_051112_327000"
    assert second.name.startswith("example-cut--")
    assert {p.name: p.read_bytes() for p in first.iterdir()} == before
    assert workflow.publish(path, plan.cuts[0].id) == first
    assert workflow.publish(other_path, other.cuts[0].id) == second
    gallery_path = first.parent / "index.html"
    assert list(first.parent.rglob("index.html")) == [gallery_path]
    gallery = gallery_path.read_text(encoding="utf-8")
    assert gallery.count("<article ") == 2
    for folder in (first, second):
        assert f'src="{folder.name}/clip.mp4"' in gallery
        assert f'poster="{folder.name}/thumbnail.jpg"' in gallery
    assert "2026-09-26T05:11:12.327000+05:30" in gallery
    assert "Music is not included." in gallery
    assert not (path.parent / "final" / "index.html").exists()


def test_binding_delivery_keeps_legacy_render_signatures_and_original_backup(prepared):
    path, plan = prepared
    plan.delivery = None
    workflow.write_json(path, plan.model_dump())
    original = path.read_bytes()
    assert "delivery" not in workflow.read_json(path)
    assert workflow.results_directory(plan).name == plan.run_id
    before = workflow.cut_signature(plan, plan.cuts[0])
    assert workflow.main(["session", "--plan", str(path), "--requested-at", "2026-09-25T23:41:12.327Z"]) == 0
    rebound = workflow.load_plan(path)
    assert workflow.cut_signature(rebound, rebound.cuts[0]) == before
    assert rebound.delivery.timestamp_source == "prompt"
    backups = list(path.parent.glob("plan.before-delivery-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    workflow.bind_delivery_session([path], "2026-09-26T05:11:12.327+05:30")
    assert list(path.parent.glob("plan.before-delivery-*.json")) == backups


def test_legacy_plan_still_delivers_without_inventing_prompt_timestamp(prepared):
    path, plan = prepared
    plan.delivery = None
    workflow.write_json(path, plan.model_dump())
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    final = workflow.publish(path, plan.cuts[0].id)
    assert final == workflow.ROOT / "results" / plan.run_id / plan.cuts[0].id
    assert not (final.parent / "session.json").exists()


def test_session_metadata_and_publication_reservation_cannot_be_overwritten(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    final = workflow.publish(path, plan.cuts[0].id)
    lock = final.parent / ".publishing.lock"
    lock.write_text("another publisher", encoding="utf-8")
    with pytest.raises(ValueError, match="already reserved"):
        workflow.publish(path, plan.cuts[0].id)
    assert lock.read_text(encoding="utf-8") == "another publisher"
    lock.unlink()
    metadata = final.parent / "session.json"
    changed = workflow.read_json(metadata)
    changed["notice"] = "Preserve this user notice."
    workflow.write_json(metadata, changed)
    with pytest.raises(ValueError, match="Different delivery session metadata"):
        workflow.publish(path, plan.cuts[0].id)
    assert workflow.read_json(metadata) == changed
    assert not lock.exists()


def test_thumbnail_backfill_copy_failure_preserves_existing_results(prepared, monkeypatch):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    final = workflow.publish(path, plan.cuts[0].id)
    for name in workflow.THUMBNAIL_FILES:
        (final / name).unlink()
    original = {p.name: p.read_bytes() for p in final.iterdir()}
    copy = workflow.shutil.copy2

    def fail_metadata(source, target):
        if Path(source).name == "thumbnail.json":
            raise OSError("Thumbnail metadata copy failed")
        return copy(source, target)

    monkeypatch.setattr(workflow.shutil, "copy2", fail_metadata)
    with pytest.raises(OSError, match="metadata copy failed"):
        workflow.publish(path, plan.cuts[0].id)
    assert {p.name: p.read_bytes() for p in final.iterdir()} == original
    assert not final.with_name(final.name + ".publishing").exists()
    monkeypatch.setattr(workflow.shutil, "copy2", copy)
    workflow.publish(path, plan.cuts[0].id)
    assert all((final / name).is_file() for name in workflow.THUMBNAIL_FILES)


def test_thumbnail_uses_only_retained_spans_and_segment_camera_overrides(prepared):
    path, plan = prepared
    plan.exclusions = [TimeRange(start=2, end=3, reason="BRB")]
    plan.cuts[0].segments[1].face_region = Region(x=0.3, y=0.2, w=0.2, h=0.3)
    _, draft = fake_draft(path, plan)
    seen = set()
    for seed in range(30):
        candidate = {**draft, "signature": str(seed)}
        first = workflow.thumbnail_frame(candidate)
        assert workflow.thumbnail_frame(candidate) == first
        index, at, region = first
        span = workflow.read_json(Path(draft["source_map"]))["segments"][index]
        assert span["source_start"] < at < span["source_end"]
        assert not 2 <= at < 3
        assert region.model_dump() == draft["effective_segments"][index]["face_region"]
        seen.add(index)
    assert seen == {0, 1, 2}


def test_camera_free_thumbnails_use_retained_content_overrides_only(camera_free):
    path, plan = camera_free
    plan.exclusions = [TimeRange(start=2, end=3, reason="BRB")]
    plan.cuts[0].segments[1].content_region = Region(x=0.3, y=0.2, w=0.2, h=0.3)
    _, draft = fake_draft(path, plan)
    with pytest.raises(ValueError, match="declared camera mode"):
        workflow.thumbnail_frame(draft)
    seen = set()
    for seed in range(30):
        candidate = {**draft, "signature": str(seed)}
        first = workflow.thumbnail_frame(candidate, camera_mode="absent")
        assert workflow.thumbnail_frame(candidate, camera_mode="absent") == first
        index, at, region = first
        span = workflow.read_json(Path(draft["source_map"]))["segments"][index]
        assert span["source_start"] < at < span["source_end"] and not 2 <= at < 3
        assert region.model_dump() == draft["effective_segments"][index]["content_region"]
        seen.add(index)
    assert seen == {0, 1, 2}


def test_camera_free_publication_records_truthful_cover_and_keeps_review_gates(camera_free, monkeypatch):
    from PIL import Image
    from clipfarm import thumbnails

    path, plan = camera_free
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    review_path = directory / "review.json"
    review = workflow.read_json(review_path)
    review["checks"]["visuals_reviewed"] = False
    workflow.write_json(review_path, review)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, plan.cuts[0].id)
    assert not (path.parent / "final").exists()
    review["checks"]["visuals_reviewed"] = True
    workflow.write_json(review_path, review)
    monkeypatch.setattr(workflow, "render_thumbnail", thumbnails.render_thumbnail)
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: Image.new("RGB", (600, 650), "blue"))
    final = workflow.publish(path, plan.cuts[0].id)
    record = workflow.read_json(final / "thumbnail.json")
    assert record["camera_mode"] == "absent" and record["shot_kind"] == "content"
    assert "camera_region" not in record
    assert record["content_region"] == plan.profile.code_region.model_dump()
    assert record["video_sha256"] == draft["video_sha256"]
    assert record["signature"] == draft["signature"]
    assert record["sha256"] == workflow.fingerprint(final / "thumbnail.jpg")
    assert " ".join(record["layout"]["title_lines"]) == plan.cuts[0].title
    assert not any(key.startswith("camera_") for key in record["layout"])
    manifest = workflow.read_json(final / "manifest.json")
    assert manifest["camera_mode"] == "absent"
    assert all(s["camera_mode"] == "absent" and s["face_region"] is None for s in manifest["effective_segments"])
    monkeypatch.setattr(workflow, "render_thumbnail", lambda *a, **k: pytest.fail("Reuse identical thumbnail"))
    assert workflow.publish(path, plan.cuts[0].id) == final


@pytest.mark.parametrize("alteration", ["camera_mode", "shot_kind", "camera_region", "content_region",
                                         "source_time", "span_index", "layout"])
def test_camera_free_publish_rejects_false_or_changed_thumbnail_provenance(camera_free, alteration):
    path, plan = camera_free
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    workflow.publish(path, plan.cuts[0].id)
    metadata = path.parent / "final" / plan.cuts[0].id / "thumbnail.json"
    record = workflow.read_json(metadata)
    record[alteration] = {
        "camera_mode": "required", "shot_kind": "camera", "camera_region": plan.profile.code_region.model_dump(),
        "content_region": None, "source_time": 20, "span_index": 99, "layout": {"camera_fit": "contain"},
    }[alteration]
    workflow.write_json(metadata, record)
    with pytest.raises(ValueError, match="Thumbnail changed"):
        workflow.publish(path, plan.cuts[0].id)
    assert workflow.read_json(metadata) == record


def test_camera_absence_edit_cannot_reuse_a_camera_present_approval(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    plan.profile = WorkflowProfile(camera_mode="absent", code_region=plan.profile.code_region)
    workflow.write_json(path, plan.model_dump())
    with pytest.raises(ValueError, match="plan changed"):
        workflow.publish(path, plan.cuts[0].id)
    assert not (path.parent / "final").exists()


def test_thumbnail_refuses_mismatched_source_map(prepared):
    path, plan = prepared
    _, draft = fake_draft(path, plan)
    mapping = workflow.read_json(Path(draft["source_map"]))
    mapping["segments"][0]["index"] = 10
    workflow.write_json(Path(draft["source_map"]), mapping)
    with pytest.raises(ValueError, match="do not match"):
        workflow.thumbnail_frame(draft)


def test_thumbnail_failure_leaves_no_partial_publication(prepared, tmp_path, monkeypatch):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])

    def fail(*args):
        raise workflow.MediaError("No camera frame decoded")

    monkeypatch.setattr(workflow, "render_thumbnail", fail)
    with pytest.raises(workflow.MediaError, match="No camera frame"):
        workflow.publish(path, plan.cuts[0].id)
    assert not list((path.parent / "final").iterdir())
    assert not (tmp_path / "results").exists()


def test_altered_archived_thumbnail_is_preserved_and_rejected(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    workflow.publish(path, plan.cuts[0].id)
    image = path.parent / "final" / plan.cuts[0].id / "thumbnail.jpg"
    image.write_bytes(b"altered camera frame")
    with pytest.raises(ValueError, match="Thumbnail changed"):
        workflow.publish(path, plan.cuts[0].id)
    assert image.read_bytes() == b"altered camera frame"


def test_changed_sidecar_invalidates_render_review(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    Path(draft["subtitles"]).write_text("different captions")
    with pytest.raises(ValueError, match="subtitles artifact changed"):
        workflow.publish(path, plan.cuts[0].id)


def test_changed_plan_invalidates_render_review(prepared):
    path, plan = prepared
    fake_draft(path, plan)
    plan.cuts[0].segments[0].end = 4.9
    workflow.write_json(path, plan.model_dump())
    with pytest.raises(ValueError, match="plan changed"):
        workflow.latest_draft(path, plan.cuts[0].id)


def test_independent_asr_does_not_auto_approve(prepared, monkeypatch):
    from clipfarm import transcribe

    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    monkeypatch.setattr(transcribe, "transcribe", lambda *args: [Cue(start=0, end=2, text="Actual output words.")])
    text = workflow.transcribe_draft(path, plan.cuts[0].id)
    assert "Actual output words" in text.read_text()
    review = json.loads((directory / "review.json").read_text())
    assert review["verdict"] == "pending" and not any(review["checks"].values())
    assert workflow.fingerprint(text) == review["transcript_sha256"]
    with pytest.raises(ValueError, match="approval"):
        workflow.publish(path, plan.cuts[0].id)


def test_draft_inspection_subtracts_discovered_brb_and_records_artifacts(prepared, monkeypatch):
    from clipfarm import workflow_vision

    path, plan = prepared
    observed = {}

    def scan(source, intervals, directory, **kwargs):
        observed["inspection"] = intervals
        assert kwargs["step"] == 0.5
        return {"samples": [{"at": 2, "brb": True}],
                "coverage": {"step": 0.5, "status": "completed", "requested_samples_complete": True},
                "brb_ranges": [{"start": 2, "end": 3, "reason": "visible BRB"}]}

    def render(source, info, segments, cues, output, preview, progress, cancel):
        observed["render"] = [(s.start, s.end) for s in segments]
        assert len(cues) == 2 and not preview
        for suffix in (".mp4", ".srt", ".transcript.txt", ".source-map.json"):
            output.with_suffix(suffix).write_text(f"rendered {suffix}")
        return [object()] * len(segments)

    monkeypatch.setattr(workflow_vision, "scan_intervals", scan)
    monkeypatch.setattr(montage, "render_montage", render)
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(
        duration=7, width=1080, height=1920, fps=30))
    draft_path = workflow.draft_cut(path, plan.cuts[0].id)
    assert observed["inspection"] == [(1, 5), (8, 12)]
    assert observed["render"] == [(1, 2), (3, 5), (8, 12)]
    draft = workflow.read_json(draft_path)
    assert draft["status"] == "draft"
    assert len(draft["artifact_sha256"]) == 4
    assert draft["detected_brb"][0]["start"] == 2
    assert not (path.parent / "final").exists()
    monkeypatch.setattr(workflow_vision, "scan_intervals", lambda *a, **k: pytest.fail("Valid draft must resume"))
    assert workflow.draft_cut(path, plan.cuts[0].id) == draft_path


def test_draft_never_renders_when_visual_coverage_is_empty(prepared, monkeypatch):
    from clipfarm import workflow_vision

    path, plan = prepared
    monkeypatch.setattr(workflow_vision, "scan_intervals", lambda *a, **k: {"samples": [], "brb_ranges": []})
    monkeypatch.setattr(montage, "render_montage", lambda *a, **k: pytest.fail("No uninspected render"))
    with pytest.raises(ValueError, match="no evidence"):
        workflow.draft_cut(path, plan.cuts[0].id)


def test_caption_crop_changes_do_not_repeat_transcript_words():
    from clipfarm import media
    from clipfarm.models import Clip

    source = [Cue(id="original", start=0, end=3, text="Accepted. Yay.")]
    output = []
    previous = None
    for index in range(3):
        clip = Clip(start=index, end=index + 1)
        local = media._clip_cues(source, clip, 1)
        span = montage.MontageSpan(index=index, source_start=index, source_end=index + 1,
                                   output_start=index, output_end=index + 1)
        previous = montage._append_mapped_cues(output, local, span, previous)
    assert len(output) == 1
    assert (output[0].start, output[0].end, output[0].text) == (0, 3, "Accepted. Yay.")
    replay = montage.MontageSpan(index=3, source_start=0, source_end=1, output_start=3, output_end=4)
    montage._append_mapped_cues(output, media._clip_cues(source, Clip(start=0, end=1), 1), replay, previous)
    assert len(output) == 2, "A deliberate replay must retain its repeated speech."


def test_visual_cache_tracks_source_and_sampling_not_layout(prepared, monkeypatch, tmp_path):
    from clipfarm import workflow_vision

    path, plan = prepared
    segments, _ = workflow.compile_segments(plan, plan.cuts[0], threading.Event())
    evidence = tmp_path / "contact.jpg"
    evidence.write_bytes(b"contact fixture")
    scans = []

    def scan(source, intervals, directory, **kwargs):
        scans.append(intervals)
        return {"samples": [{"time": 1, "image": str(evidence)}], "contact_sheets": [str(evidence)],
                "coverage": {"status": "completed", "requested_samples_complete": True}}

    monkeypatch.setattr(workflow_vision, "scan_intervals", scan)
    for step in (0.5, 0.5, 0.25):
        workflow.cached_visual_report(path, plan, segments, tmp_path, step, threading.Event())
    assert len(scans) == 2
    before = workflow.visual_cache_key(plan, [(1, 5)], 0.5)
    plan.profile.subtitle_y = 0.84
    assert workflow.visual_cache_key(plan, [(1, 5)], 0.5) == before
    plan.source_sha256 = "f" * 64
    assert workflow.visual_cache_key(plan, [(1, 5)], 0.5) != before
