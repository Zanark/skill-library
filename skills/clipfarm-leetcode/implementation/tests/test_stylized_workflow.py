"""Workflow gates use synthetic media; no test result constitutes editorial approval."""

import hashlib
import html
import json
import wave
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest

from clipfarm import montage, music, transcribe, workflow, workflow_vision
from clipfarm.models import Cue, MediaInfo
from clipfarm.music_models import StylizedEdit
from clipfarm.workflow_models import WorkflowCut, WorkflowPlan
from test_workflow import approve, fake_draft, prepared


BASE_CHECKS = {
    "coherent", "useful_content", "captions_reviewed", "visuals_reviewed", "brb_reviewed",
}
MUSIC_CHECKS = {
    "music_rights_reviewed", "beat_edits_reviewed", "transitions_reviewed", "music_mix_reviewed",
}
ATTRIBUTION = (
    'Fixture Composition by A & B, "Original Mix"\n'
    "CC BY 4.0 - https://example.org/License#MixedCase\n"
    "  Required notice: preserve capitalization and spacing.  "
)


@pytest.fixture
def native_settings():
    return {
        "preset": "speech-first",
        "music": {
            "route": "instagram",
            "title": "Fixture music",
            "artist": "Fixture author",
            "track_url": "https://www.instagram.com/reels/audio/123/",
            "start_seconds": 0,
            "bpm": 120,
            "beat_offset_seconds": 0,
            "beat_review": "Measured first beat and steady timing for this fixture.",
            "native_checked_at": datetime.now(timezone.utc).isoformat(),
            "region": "IN",
            "account_context": "Personal organic Reel",
        },
        "boundaries": [],
    }


@pytest.fixture
def embedded_settings(tmp_path, native_settings):
    track = tmp_path / "original-fixture.wav"
    with wave.open(str(track), "wb") as audio:
        audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 8000 * 10)
    proof = tmp_path / "permission.txt"
    proof.write_text(
        "Synthetic test permission for the generated silent fixture; not real music clearance.",
        encoding="utf-8",
    )
    settings = deepcopy(native_settings)
    spec = settings["music"]
    for key in ("native_checked_at", "region", "account_context"):
        spec.pop(key)
    spec.update(
        route="embedded", track_url="https://example.org/original-fixture",
        file=str(track), sha256=workflow.fingerprint(track),
        rights={
            "scope": "Original generated test audio",
            "usage": "Organic test video exports",
            "territory": "Worldwide",
            "checked_by": "Synthetic test fixture",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "permission_note": "Original silent test audio generated only for this automated test.",
            "platforms": ["instagram", "youtube"],
            "attribution_required": True,
            "attribution": ATTRIBUTION,
            "proof_file": str(proof),
            "proof_sha256": workflow.fingerprint(proof),
        },
    )
    return settings


@pytest.fixture
def pipeline(prepared, monkeypatch):
    """Exercise real workflow persistence while replacing OCR, encoding and ASR."""
    _, plan = prepared
    observed = {"renders": [], "transcriptions": [], "scans": []}
    outputs = {}

    def scan(source, intervals, directory, **kwargs):
        directory.mkdir(parents=True, exist_ok=True)
        evidence = directory / "synthetic-frame.jpg"
        evidence.write_bytes(b"Synthetic scan evidence; not an inspected frame.")
        observed["scans"].append(intervals)
        return {
            "samples": [{"at": intervals[0][0], "image": str(evidence)}],
            "brb_ranges": [],
            "coverage": {
                "status": "completed", "requested_samples_complete": True, "step": kwargs["step"],
            },
        }

    def render(source, info, segments, cues, output, preview, progress, cancel, **kwargs):
        observed["renders"].append({
            "source": source, "segments": segments, "cues": cues,
            "output": output, "preview": preview, "kwargs": kwargs,
        })
        spans = []
        elapsed = 0
        for index, segment in enumerate(segments):
            duration = segment.end - segment.start
            spans.append(montage.MontageSpan(
                index=index, source_start=segment.start, source_end=segment.end,
                output_start=elapsed, output_end=elapsed + duration,
            ))
            elapsed += duration
        style = kwargs.get("stylized")
        output.write_bytes(b"Synthetic media, not an encode.\n" + json.dumps({
            "preview": preview,
            "style": style.model_dump(mode="json") if style is not None and style.music.route == "embedded" else None,
            "segments": [s.model_dump() for s in spans],
        }, sort_keys=True).encode())
        output.with_suffix(".srt").write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nA useful setup.\n", encoding="utf-8",
        )
        output.with_suffix(".transcript.txt").write_text(
            "A useful setup. A complete payoff.", encoding="utf-8",
        )
        workflow.write_json(output.with_suffix(".source-map.json"), {
            "version": 1, "fps": 30, "duration": elapsed,
            "segments": [s.model_dump() for s in spans],
        })
        width, height = (360, 640) if preview else (1080, 1920)
        outputs[output.resolve()] = MediaInfo(
            duration=elapsed, width=width, height=height, fps=30, has_audio=True,
        )
        return spans

    def recognize(video, info, model, progress, cancel, **kwargs):
        observed["transcriptions"].append((video, model, kwargs))
        return [Cue(start=0, end=2, text="A useful setup. A complete payoff.")]

    monkeypatch.setattr(workflow_vision, "scan_intervals", scan)
    monkeypatch.setattr(montage, "render_montage", render)
    monkeypatch.setattr(workflow, "probe", lambda p: outputs.get(Path(p).resolve(), plan.media))
    monkeypatch.setattr(transcribe, "transcribe", recognize)
    return observed


def _set_style(prepared, settings):
    path, plan = prepared
    plan.cuts[0].stylized = StylizedEdit.model_validate(settings)
    workflow.write_json(path, plan.model_dump())
    return path, plan, plan.cuts[0]


def _draft(prepared, settings):
    path, plan, cut = _set_style(prepared, settings)
    draft_path = workflow.draft_cut(path, cut.id)
    return path, plan, cut, draft_path, workflow.read_json(draft_path)


def _approve_fixture(plan_path, cut, draft_path):
    workflow.transcribe_draft(plan_path, cut.id)
    review_path = draft_path.parent / "review.json"
    review = workflow.read_json(review_path)
    if cut.stylized is not None:
        draft = workflow.read_json(draft_path)
        assert review["music_sha256"] == {
            "music.json": draft["artifact_sha256"]["music_record"],
            "music-instructions.txt": draft["artifact_sha256"]["music_instructions"],
        }
    else:
        assert "music_sha256" not in review
    review.update(
        verdict="approve", reviewer="Synthetic test fixture",
        notes="Synthetic fixture explicitly exercises each review gate, hash binding and publication "
              "boundary. No real footage has been viewed, heard, approved or uploaded by this test.",
    )
    review["checks"] = dict.fromkeys(review["checks"], True)
    workflow.write_json(review_path, review)
    return review


def _style_cli(path, cut_id, settings):
    settings_path = path.parent / "requested-style.json"
    workflow.write_json(settings_path, settings)
    return workflow.main([
        "style", "--plan", str(path), "--cut", cut_id, "--settings", str(settings_path),
    ])


@pytest.mark.parametrize("view,schema", [("code", 2), ("results", 3)])
@pytest.mark.parametrize("explicit_none", [False, True])
def test_absent_style_preserves_legacy_serialization_and_signature(prepared, view, schema, explicit_none):
    _, plan = prepared
    cut = plan.cuts[0]
    cut.segments[-1].view = view
    legacy_cut = cut.model_dump()
    assert "stylized" not in legacy_cut
    incoming = {**legacy_cut, **({"stylized": None} if explicit_none else {})}
    cut = WorkflowCut.model_validate(incoming)
    plan.cuts[0] = cut
    assert cut.model_dump() == legacy_cut
    assert json.loads(cut.model_dump_json()) == legacy_cut
    assert "stylized" not in json.loads(plan.model_dump_json())["cuts"][0]
    legacy_payload = {
        "renderer_schema": schema, "workflow": plan.workflow, "source": plan.source_sha256,
        "transcript": plan.transcript_sha256, "cues": plan.cues_sha256,
        "profile": plan.profile.model_dump(), "exclusions": [], "cut": legacy_cut,
    }
    expected = hashlib.sha256(json.dumps(legacy_payload, sort_keys=True).encode()).hexdigest()
    assert workflow.cut_signature(plan, cut) == expected
    assert workflow.review_checks(plan, cut) == BASE_CHECKS


@pytest.mark.parametrize("route", ["instagram", "embedded"])
def test_style_roundtrips_without_enabling_other_cuts(prepared, native_settings, embedded_settings, route):
    path, plan = prepared
    sibling = plan.cuts[0].model_copy(deep=True, update={"id": "untouched-cut"})
    plan.cuts.append(sibling)
    sibling_signature = workflow.cut_signature(plan, sibling)
    settings = native_settings if route == "instagram" else embedded_settings
    _, _, cut = _set_style(prepared, settings)
    expected = StylizedEdit.model_validate(settings).model_dump(mode="json")
    assert cut.model_dump()["stylized"] == expected
    assert json.loads(plan.model_dump_json())["cuts"][0]["stylized"] == expected
    assert WorkflowPlan.model_validate_json(plan.model_dump_json()) == plan
    restored = workflow.load_plan(path)
    assert restored == plan
    assert restored.cuts[1].stylized is None
    assert workflow.cut_signature(restored, restored.cuts[1]) == sibling_signature
    if route == "embedded":
        assert restored.cuts[0].stylized.music.rights.attribution == ATTRIBUTION


def test_music_schema_cli_is_json_and_exposes_both_routes(capsys):
    assert workflow.main(["music-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema == StylizedEdit.model_json_schema()
    assert schema["properties"]["preset"]["const"] == "speech-first"
    assert set(schema["$defs"]["MusicSpec"]["properties"]["route"]["enum"]) == {"embedded", "instagram"}


def test_style_cli_changes_one_cut_and_keeps_exact_backups(prepared, native_settings, capsys):
    path, plan = prepared
    plan.cuts.append(plan.cuts[0].model_copy(deep=True, update={"id": "untouched-cut"}))
    workflow.write_json(path, plan.model_dump())
    before = path.read_bytes()
    before_data = workflow.read_json(path)
    untouched_signature = workflow.cut_signature(plan, plan.cuts[1])
    old_signature = workflow.cut_signature(plan, plan.cuts[0])
    assert _style_cli(path, plan.cuts[0].id, native_settings) == 0
    assert "fresh review" in capsys.readouterr().out
    backup = path.with_name(f"{path.stem}.before-style-{hashlib.sha256(before).hexdigest()[:12]}.json")
    assert backup.read_bytes() == before
    styled = workflow.load_plan(path)
    actual = workflow.read_json(path)
    assert actual["cuts"][0].pop("stylized") == StylizedEdit.model_validate(native_settings).model_dump(mode="json")
    assert actual == before_data
    assert workflow.cut_signature(styled, styled.cuts[0]) != old_signature
    assert workflow.cut_signature(styled, styled.cuts[1]) == untouched_signature
    assert not (path.parent / "drafts").exists()
    assert not (path.parent / "previews").exists()
    first_style = path.read_bytes()
    revised = deepcopy(native_settings)
    revised["music"]["track_url"] = "https://www.instagram.com/reels/audio/456/"
    assert _style_cli(path, plan.cuts[0].id, revised) == 0
    second_backup = path.with_name(
        f"{path.stem}.before-style-{hashlib.sha256(first_style).hexdigest()[:12]}.json",
    )
    assert second_backup.read_bytes() == first_style
    assert backup.read_bytes() == before
    assert workflow.load_plan(path).cuts[1].stylized is None


@pytest.mark.parametrize("failure", ["invalid-settings", "unknown-cut", "unreviewed-plan", "changed-source"])
def test_style_cli_failure_preserves_plan_without_backup(prepared, native_settings, failure, capsys):
    path, plan = prepared
    cut_id = plan.cuts[0].id
    if failure == "invalid-settings":
        native_settings["music"]["file"] = str(path.parent / "platform-track.wav")
    elif failure == "unknown-cut":
        cut_id = "does-not-exist"
    elif failure == "unreviewed-plan":
        plan.reviewed_entire_transcript = False
        workflow.write_json(path, plan.model_dump())
    else:
        Path(plan.source).write_bytes(b"Changed source, not the prepared media.")
    before = path.read_bytes()
    assert _style_cli(path, cut_id, native_settings) == 2
    assert "ClipFarm workflow:" in capsys.readouterr().err
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.before-style-*.json"))


def test_style_cli_preserves_a_conflicting_backup(prepared, native_settings, capsys):
    path, plan = prepared
    before = path.read_bytes()
    backup = path.with_name(f"{path.stem}.before-style-{workflow.fingerprint(path)[:12]}.json")
    backup.write_bytes(b"Conflicting backup must not be replaced.")
    assert _style_cli(path, plan.cuts[0].id, native_settings) == 2
    assert "Conflicting style backup" in capsys.readouterr().err
    assert path.read_bytes() == before
    assert backup.read_bytes() == b"Conflicting backup must not be replaced."


def test_horizontal_styling_is_rejected_by_model_and_workflow(prepared, native_settings, capsys):
    path, plan, _ = _set_style(prepared, native_settings)
    with pytest.raises(ValueError, match="vertical-only"):
        WorkflowPlan.model_validate({**plan.model_dump(), "output_format": "horizontal", "clip_policy": None})
    plan.output_format = "horizontal"
    assert any("vertical-only" in error for error in workflow.validate_plan(plan))
    workflow.write_json(path, plan.model_dump())
    before = path.read_bytes()
    assert _style_cli(path, plan.cuts[0].id, native_settings) == 2
    assert "vertical-only" in capsys.readouterr().err
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.before-style-*.json"))


def test_unstyled_render_and_publication_do_not_call_music_or_add_fields(prepared, pipeline, monkeypatch):
    path, plan = prepared
    cut = plan.cuts[0]
    signature = workflow.cut_signature(plan, cut)
    monkeypatch.setattr(music, "inputs", lambda *a: pytest.fail("No implicit music validation"))
    monkeypatch.setattr(music, "instructions", lambda *a: pytest.fail("No implicit music handoff"))
    draft_path = workflow.draft_cut(path, cut.id)
    draft = workflow.read_json(draft_path)
    assert draft["signature"] == signature
    assert pipeline["renders"][0]["kwargs"] == {}
    assert pipeline["renders"][0]["preview"] is False
    assert not {"stylized", "music_record", "music_instructions"} & draft.keys()
    assert set(draft["artifact_sha256"]) == {"video", "subtitles", "transcript", "source_map"}
    _approve_fixture(path, cut, draft_path)
    final = workflow.publish(path, cut.id)
    assert not {"stylized", "music_sha256"} & workflow.read_json(final / "manifest.json").keys()
    assert not list(final.glob("music*"))
    assert "Music / platform handoff" not in (final.parent / "index.html").read_text(encoding="utf-8")
    assert workflow.cut_signature(workflow.load_plan(path), cut) == signature


def test_legacy_draft_without_style_still_publishes(prepared):
    path, plan = prepared
    directory, draft = fake_draft(path, plan)
    approve(directory, draft, plan.cuts[0])
    before = (directory / "draft.json").read_bytes()
    final = workflow.publish(path, plan.cuts[0].id)
    assert workflow.fingerprint(final / "clip.mp4") == draft["video_sha256"]
    assert (directory / "draft.json").read_bytes() == before
    assert not list(final.glob("music*"))


@pytest.mark.parametrize("route", ["instagram", "embedded"])
@pytest.mark.parametrize("workflow_name", ["leetcode", "system-design"])
def test_styled_draft_asr_review_gates_and_hash_bound_publication(
    prepared, pipeline, native_settings, embedded_settings, route, workflow_name,
):
    path, plan = prepared
    plan.workflow = workflow_name
    settings = native_settings if route == "instagram" else embedded_settings
    path, plan, cut, draft_path, draft = _draft(prepared, settings)
    assert draft["workflow"] == workflow_name and draft["status"] == "draft"
    assert not (draft_path.parent / "review.json").exists()
    rendered = pipeline["renders"][0]
    assert rendered["preview"] is False
    assert workflow.probe(Path(draft["video"])).width == 1080
    assert workflow.probe(Path(draft["video"])).height == 1920
    assert rendered["kwargs"] == {"stylized": cut.stylized, "transitions": {}}
    assert [(s.start, s.end) for s in rendered["segments"]] == [(1, 5), (8, 12)]
    record = workflow.read_json(Path(draft["music_record"]))
    assert record["settings"] == cut.stylized.model_dump(mode="json")
    assert record["signature"] == draft["signature"]
    assert record["video_sha256"] == draft["video_sha256"]
    assert record["duration"] == draft["duration"] == 8
    assert record["audio_embedded"] is (route == "embedded")
    assert record["preview"] is False
    assert record["boundaries"] == [] and record["transitions"] == {}
    if route == "instagram":
        assert record["inputs"]["assets"] == {}
        assert rendered["kwargs"]["stylized"].music.file is None
    else:
        assert record["inputs"]["assets"]["track"]["sha256"] == settings["music"]["sha256"]
        assert record["inputs"]["assets"]["proof"]["sha256"] == settings["music"]["rights"]["proof_sha256"]
    workflow.verify_draft(draft)
    assert workflow.draft_cut(path, cut.id) == draft_path
    assert len(pipeline["renders"]) == 1
    output_asr = workflow.transcribe_draft(path, cut.id, model="small", language="en")
    assert pipeline["transcriptions"] == [(Path(draft["video"]), "small", {"language": "en"})]
    assert workflow.transcribe_draft(path, cut.id, model="small", language="en") == output_asr
    assert len(pipeline["transcriptions"]) == 1
    review_path = draft_path.parent / "review.json"
    review = workflow.read_json(review_path)
    expected_checks = BASE_CHECKS | MUSIC_CHECKS
    if route == "instagram":
        expected_checks |= {"instagram_handoff_reviewed"}
    assert set(review["checks"]) == expected_checks
    assert review["verdict"] == "pending"
    assert all(value is False for value in review["checks"].values())
    assert review["video_sha256"] == draft["video_sha256"]
    assert review["transcript_sha256"] == workflow.fingerprint(output_asr)
    assert review["music_sha256"] == {
        "music.json": draft["artifact_sha256"]["music_record"],
        "music-instructions.txt": draft["artifact_sha256"]["music_instructions"],
    }
    with pytest.raises(ValueError, match="approval"):
        workflow.publish(path, cut.id)
    review.update(
        verdict="approve", reviewer="Synthetic test fixture",
        notes="This synthetic fixture exercises explicit music and editorial approval gates. "
              "It is not a real media review, direct listening, user approval or platform publication.",
    )
    review["checks"] = dict.fromkeys(expected_checks, True)
    for check in sorted(MUSIC_CHECKS | ({"instagram_handoff_reviewed"} if route == "instagram" else set())):
        review["checks"][check] = False
        workflow.write_json(review_path, review)
        with pytest.raises(ValueError, match="Not all"):
            workflow.publish(path, cut.id)
        assert not (path.parent / "final").exists()
        review["checks"][check] = True
    workflow.write_json(review_path, review)
    final = workflow.publish(path, cut.id)
    assert final == workflow.ROOT / "results" / plan.run_id / cut.id
    manifest = workflow.read_json(final / "manifest.json")
    assert manifest["workflow"] == workflow_name
    assert manifest["stylized"] == record["settings"]
    assert manifest["music_sha256"] == {
        "music.json": draft["artifact_sha256"]["music_record"],
        "music-instructions.txt": draft["artifact_sha256"]["music_instructions"],
    }
    assert manifest["music_sha256"] == review["music_sha256"]
    for name, key in (("music.json", "music_record"), ("music-instructions.txt", "music_instructions")):
        assert (final / name).read_bytes() == Path(draft[key]).read_bytes()
        assert (path.parent / "final" / cut.id / name).read_bytes() == Path(draft[key]).read_bytes()
        assert workflow.fingerprint(final / name) == manifest["music_sha256"][name]
    instructions = (final / "music-instructions.txt").read_text(encoding="utf-8")
    if route == "instagram":
        assert "original audio only" in instructions
        assert "local preview cannot audition" in instructions
        assert "Do not transfer Instagram library audio rights to YouTube" in instructions
    else:
        assert ATTRIBUTION in instructions
        assert workflow.read_json(final / "music.json")["settings"]["music"]["rights"]["attribution"] == ATTRIBUTION
    assert workflow.music_delivery_text(final, manifest) == instructions
    gallery = (final.parent / "index.html").read_text(encoding="utf-8")
    assert "Music / platform handoff" in gallery
    assert f'{cut.id}/music-instructions.txt' in gallery and f'{cut.id}/music.json' in gallery
    assert html.escape(instructions) in gallery
    assert "Fixture music" not in (final / "clip.srt").read_text(encoding="utf-8")
    assert workflow.publish(path, cut.id) == final


@pytest.mark.parametrize("route", ["instagram", "embedded"])
@pytest.mark.parametrize("alteration", ["missing", "wrong-record", "wrong-instructions", "extra"])
def test_publish_requires_the_exact_reviewed_music_binding(
    prepared, pipeline, native_settings, embedded_settings, route, alteration,
):
    settings = native_settings if route == "instagram" else embedded_settings
    path, _, cut, draft_path, draft = _draft(prepared, settings)
    review = _approve_fixture(path, cut, draft_path)
    if alteration == "missing":
        review.pop("music_sha256")
    elif alteration == "wrong-record":
        review["music_sha256"]["music.json"] = "0" * 64
    elif alteration == "wrong-instructions":
        review["music_sha256"]["music-instructions.txt"] = "0" * 64
    else:
        review["music_sha256"]["unreviewed-extra.txt"] = "0" * 64
    workflow.write_json(draft_path.parent / "review.json", review)
    workflow.verify_draft(draft)
    with pytest.raises(ValueError, match="Music settings, evidence or instructions do not match this review"):
        workflow.publish(path, cut.id)
    assert not (path.parent / "final").exists()
    assert not (workflow.ROOT / "results").exists()


@pytest.mark.parametrize("change", ["track", "native-evidence"])
def test_old_approval_cannot_follow_changed_native_handoff_with_identical_video(
    prepared, pipeline, native_settings, change,
):
    path, plan, cut, old_path, old_draft = _draft(prepared, native_settings)
    old_review = _approve_fixture(path, cut, old_path)
    if change == "track":
        cut.stylized.music.track_url = "https://www.instagram.com/reels/audio/456/"
    else:
        cut.stylized.music.native_checked_at -= timedelta(minutes=1)
    workflow.write_json(path, plan.model_dump())
    new_path = workflow.draft_cut(path, cut.id)
    new_draft = workflow.read_json(new_path)
    assert new_draft["signature"] != old_draft["signature"]
    assert new_draft["video_sha256"] == old_draft["video_sha256"]
    workflow.transcribe_draft(path, cut.id)
    review_path = new_path.parent / "review.json"
    pending = workflow.read_json(review_path)
    assert pending["verdict"] == "pending"
    assert pending["video_sha256"] == old_review["video_sha256"]
    assert pending["transcript_sha256"] == old_review["transcript_sha256"]
    assert pending["music_sha256"] != old_review["music_sha256"]
    workflow.write_json(review_path, old_review)
    with pytest.raises(ValueError, match="Music settings, evidence or instructions do not match this review"):
        workflow.publish(path, cut.id)
    assert not (path.parent / "final").exists()
    assert workflow.read_json(old_path.parent / "review.json") == old_review
    workflow.write_json(review_path, pending)
    approved = _approve_fixture(path, cut, new_path)
    final = workflow.publish(path, cut.id)
    assert workflow.read_json(final / "manifest.json")["music_sha256"] == approved["music_sha256"]
    assert workflow.read_json(final / "music.json")["settings"] == cut.stylized.model_dump(mode="json")


def test_trend_evidence_adds_a_separate_pending_review_gate(prepared, pipeline, native_settings):
    native_settings["music"]["trend"] = {
        "observed_at": datetime.now(timezone.utc).isoformat(), "region": "IN",
        "url": "https://example.org/dated-regional-observation",
        "note": "Synthetic dated regional fixture, not a real claim of current popularity.",
    }
    path, plan, cut, draft_path, _ = _draft(prepared, native_settings)
    workflow.transcribe_draft(path, cut.id)
    review = workflow.read_json(draft_path.parent / "review.json")
    assert review["checks"]["trend_evidence_reviewed"] is False
    assert workflow.review_checks(plan, cut) == BASE_CHECKS | MUSIC_CHECKS | {
        "instagram_handoff_reviewed", "trend_evidence_reviewed",
    }
    review = _approve_fixture(path, cut, draft_path)
    review["checks"]["trend_evidence_reviewed"] = False
    workflow.write_json(draft_path.parent / "review.json", review)
    with pytest.raises(ValueError, match="Not all"):
        workflow.publish(path, cut.id)


@pytest.mark.parametrize("key", ["music_record", "music_instructions"])
def test_tampered_draft_music_sidecars_cannot_be_reused_or_published(
    prepared, pipeline, native_settings, key,
):
    path, _, cut, draft_path, draft = _draft(prepared, native_settings)
    _approve_fixture(path, cut, draft_path)
    target = Path(draft[key])
    target.write_bytes(target.read_bytes() + b"\nTampered sidecar.")
    for action in (workflow.latest_draft, workflow.draft_cut, workflow.transcribe_draft, workflow.publish):
        with pytest.raises(ValueError, match="artifact changed"):
            action(path, cut.id)
    assert len(pipeline["renders"]) == 1
    assert not (path.parent / "final").exists()


@pytest.mark.parametrize("field", ["signature", "video_sha256", "settings", "preview", "audio_embedded"])
def test_rehashed_music_record_still_needs_draft_binding(prepared, pipeline, native_settings, field):
    path, _, cut, draft_path, draft = _draft(prepared, native_settings)
    record_path = Path(draft["music_record"])
    record = workflow.read_json(record_path)
    if field == "settings":
        record["settings"]["music"]["title"] = "A different track"
    elif field in {"preview", "audio_embedded"}:
        record[field] = True
    else:
        record[field] = "0" * 64
    workflow.write_json(record_path, record)
    draft["artifact_sha256"]["music_record"] = workflow.fingerprint(record_path)
    workflow.write_json(draft_path, draft)
    with pytest.raises(ValueError, match="Music provenance"):
        workflow.latest_draft(path, cut.id)


@pytest.mark.parametrize("alteration", ["missing", "changed"])
def test_draft_settings_must_match_current_opt_in(prepared, pipeline, native_settings, alteration):
    path, _, cut, draft_path, draft = _draft(prepared, native_settings)
    if alteration == "missing":
        draft.pop("stylized")
    else:
        draft["stylized"]["music"]["track_url"] = "https://www.instagram.com/reels/audio/999/"
    workflow.write_json(draft_path, draft)
    with pytest.raises(ValueError, match="Stylized settings"):
        workflow.latest_draft(path, cut.id)
    with pytest.raises(ValueError, match="settings"):
        workflow.draft_cut(path, cut.id)


@pytest.mark.parametrize("asset", ["track", "proof"])
def test_changed_local_asset_bytes_fail_before_reuse(prepared, pipeline, embedded_settings, asset):
    path, _, cut, draft_path, draft = _draft(prepared, embedded_settings)
    _approve_fixture(path, cut, draft_path)
    filename = embedded_settings["music"]["file"] if asset == "track" else embedded_settings["music"]["rights"]["proof_file"]
    target = Path(filename)
    target.write_bytes(target.read_bytes() + b"Changed after rights and track review.")
    for action in (workflow.latest_draft, workflow.draft_cut, workflow.publish):
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            action(path, cut.id)
    assert workflow.fingerprint(Path(draft["video"])) == draft["video_sha256"]
    assert len(pipeline["renders"]) == 1
    assert not (path.parent / "final").exists()


@pytest.mark.parametrize("change", ["track", "native-evidence", "rights-evidence", "proof-bytes"])
def test_changed_settings_or_evidence_require_new_draft_and_review(
    prepared, pipeline, native_settings, embedded_settings, change,
):
    settings = embedded_settings if change in {"rights-evidence", "proof-bytes"} else native_settings
    path, plan, cut, old_path, old = _draft(prepared, settings)
    _approve_fixture(path, cut, old_path)
    old_review = (old_path.parent / "review.json").read_bytes()
    spec = cut.stylized.music
    if change == "track":
        spec.track_url = "https://www.instagram.com/reels/audio/456/"
    elif change == "native-evidence":
        spec.native_checked_at -= timedelta(minutes=1)
    elif change == "rights-evidence":
        spec.rights.checked_at -= timedelta(minutes=1)
    else:
        proof = Path(spec.rights.proof_file)
        proof.write_text("Updated synthetic permission scope, explicitly requiring a new review.", encoding="utf-8")
        spec.rights.proof_sha256 = workflow.fingerprint(proof)
    workflow.write_json(path, plan.model_dump())
    assert workflow.cut_signature(plan, cut) != old["signature"]
    with pytest.raises(ValueError, match="settings.*changed|plan changed"):
        workflow.publish(path, cut.id)
    new_path = workflow.draft_cut(path, cut.id)
    assert new_path != old_path and len(pipeline["renders"]) == 2
    assert (old_path.parent / "review.json").read_bytes() == old_review
    assert workflow.fingerprint(Path(old["video"])) == old["video_sha256"]
    assert not (new_path.parent / "review.json").exists()
    workflow.transcribe_draft(path, cut.id)
    review = workflow.read_json(new_path.parent / "review.json")
    assert review["verdict"] == "pending"
    assert all(value is False for value in review["checks"].values())
    with pytest.raises(ValueError, match="approval"):
        workflow.publish(path, cut.id)


@pytest.mark.parametrize("change", ["track", "native-evidence"])
def test_identical_native_audio_video_cannot_reuse_an_old_published_music_handoff(
    prepared, pipeline, native_settings, change,
):
    path, plan, cut, old_path, old = _draft(prepared, native_settings)
    _approve_fixture(path, cut, old_path)
    final = workflow.publish(path, cut.id)
    before = {file.name: file.read_bytes() for file in final.iterdir() if file.is_file()}
    if change == "track":
        cut.stylized.music.track_url = "https://www.instagram.com/reels/audio/456/"
    else:
        cut.stylized.music.native_checked_at -= timedelta(minutes=1)
    workflow.write_json(path, plan.model_dump())
    new_path = workflow.draft_cut(path, cut.id)
    new = workflow.read_json(new_path)
    assert new["signature"] != old["signature"]
    assert new["video_sha256"] == old["video_sha256"]
    _approve_fixture(path, cut, new_path)
    with pytest.raises(ValueError, match="different music handoff"):
        workflow.publish(path, cut.id)
    assert {file.name: file.read_bytes() for file in final.iterdir() if file.is_file()} == before


def test_an_approved_native_draft_is_not_reusable_after_availability_expires(
    prepared, pipeline, native_settings, monkeypatch,
):
    from clipfarm import music_models

    path, _, cut, draft_path, _ = _draft(prepared, native_settings)
    _approve_fixture(path, cut, draft_path)
    later = datetime.now(timezone.utc) + timedelta(days=8)

    class LaterDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return later.astimezone(tz) if tz is not None else later.replace(tzinfo=None)

    monkeypatch.setattr(music_models, "datetime", LaterDatetime)
    for action in (workflow.latest_draft, workflow.draft_cut, workflow.publish):
        with pytest.raises(ValueError, match="stale"):
            action(path, cut.id)
    assert len(pipeline["renders"]) == 1
    assert not (path.parent / "final").exists()


@pytest.mark.parametrize("evidence", ["native-future", "native-stale", "trend-future", "trend-stale", "rights-future"])
def test_workflow_validates_evidence_freshness_at_use(
    prepared, pipeline, native_settings, embedded_settings, evidence, capsys,
):
    settings = embedded_settings if evidence == "rights-future" else native_settings
    timestamp = datetime.now(timezone.utc) + timedelta(days=1 if evidence.endswith("future") else -8)
    if evidence.startswith("native"):
        settings["music"]["native_checked_at"] = timestamp.isoformat()
    elif evidence.startswith("trend"):
        settings["music"]["trend"] = {
            "observed_at": timestamp.isoformat(), "region": "IN", "url": "https://example.org/trend",
            "note": "A dated synthetic observation with enough detail to test freshness.",
        }
    else:
        settings["music"]["rights"]["checked_at"] = timestamp.isoformat()
    path, plan, cut = _set_style(prepared, settings)
    expected = "future" if evidence.endswith("future") else "stale"
    assert workflow.load_plan(path).cuts[0].stylized is not None
    assert any(expected in error for error in workflow.validate_plan(plan))
    assert workflow.main(["validate", "--plan", str(path)]) == 2
    assert expected in capsys.readouterr().err
    with pytest.raises(ValueError, match=expected):
        workflow.draft_cut(path, cut.id)
    assert pipeline["renders"] == []


@pytest.mark.parametrize("name", ["music.json", "music-instructions.txt"])
def test_public_music_sidecar_conflicts_are_preserved_and_gallery_rejected(
    prepared, pipeline, native_settings, name,
):
    path, _, cut, draft_path, _ = _draft(prepared, native_settings)
    _approve_fixture(path, cut, draft_path)
    final = workflow.publish(path, cut.id)
    original_gallery = (final.parent / "index.html").read_bytes()
    target = final / name
    changed = target.read_bytes() + b"\nChanged public handoff."
    target.write_bytes(changed)
    with pytest.raises(ValueError, match="music instructions/provenance changed"):
        workflow._write_gallery(final.parent)
    assert (final.parent / "index.html").read_bytes() == original_gallery
    with pytest.raises(ValueError, match="Different or incomplete results"):
        workflow.publish(path, cut.id)
    assert target.read_bytes() == changed
    assert (path.parent / "final" / cut.id / name).read_bytes() != changed


class _MusicTextarea(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.parts = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "textarea":
            self.inside = dict(attrs).get("aria-label") == "Music credits and posting instructions"

    def handle_endtag(self, tag):
        if tag == "textarea":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)


@pytest.mark.parametrize("route", ["instagram", "embedded"])
def test_gallery_handoff_escapes_markup_without_changing_copyable_text(
    prepared, pipeline, native_settings, embedded_settings, route,
):
    settings = native_settings if route == "instagram" else embedded_settings
    payload = '</textarea><img src=x onerror="fixture()"><script>fixture()</script>'
    settings["music"]["title"] = payload
    settings["music"]["artist"] = 'A & B "Quoted Artist"'
    path, _, cut, draft_path, _ = _draft(prepared, settings)
    _approve_fixture(path, cut, draft_path)
    final = workflow.publish(path, cut.id)
    instructions = (final / "music-instructions.txt").read_text(encoding="utf-8")
    gallery = (final.parent / "index.html").read_text(encoding="utf-8")
    assert payload in instructions and payload not in gallery
    assert html.escape(payload) in gallery
    parsed = _MusicTextarea()
    parsed.feed(gallery)
    assert "".join(parsed.parts) == instructions
    assert "img" not in parsed.tags
    assert '<textarea readonly rows="9"' in gallery
    if route == "embedded":
        assert ATTRIBUTION in "".join(parsed.parts)


def test_preview_is_reusable_isolated_and_never_approval(prepared, pipeline, native_settings, capsys):
    path, plan, cut = _set_style(prepared, native_settings)
    signature = workflow.cut_signature(plan, cut)
    expected = path.parent / "previews" / cut.id / signature[:12] / "preview.json"
    assert workflow.main(["preview", "--plan", str(path), "--cut", cut.id]) == 0
    assert str(expected) in capsys.readouterr().out
    preview = workflow.read_json(expected)
    assert preview["status"] == "preview" and preview["signature"] == signature
    assert workflow.probe(Path(preview["video"])).width == 360
    assert workflow.probe(Path(preview["video"])).height == 640
    assert workflow.read_json(Path(preview["music_record"]))["preview"] is True
    assert pipeline["renders"][0]["preview"] is True
    assert not (path.parent / "drafts").exists()
    assert not (expected.parent / "review.json").exists()
    assert workflow.draft_cut(path, cut.id, preview=True) == expected
    assert len(pipeline["renders"]) == 1
    for command in ("review-transcribe", "publish"):
        assert workflow.main([command, "--plan", str(path), "--cut", cut.id]) == 2
    assert pipeline["transcriptions"] == []
    assert not (path.parent / "final").exists()
    assert not (workflow.ROOT / "results").exists()
    full_path = workflow.draft_cut(path, cut.id)
    assert full_path != expected and len(pipeline["renders"]) == 2
    assert pipeline["renders"][1]["preview"] is False
    full = workflow.read_json(full_path)
    assert full["status"] == "draft" and full["video_sha256"] != preview["video_sha256"]
    assert not (full_path.parent / "review.json").exists()
    _approve_fixture(path, cut, full_path)
    pointer = full_path.parent.parent / "latest.json"
    before_pointer = pointer.read_bytes()
    before_review = (full_path.parent / "review.json").read_bytes()
    assert workflow.draft_cut(path, cut.id, preview=True) == expected
    assert pointer.read_bytes() == before_pointer
    assert (full_path.parent / "review.json").read_bytes() == before_review
    final = workflow.publish(path, cut.id)
    assert workflow.fingerprint(final / "clip.mp4") == full["video_sha256"]
    assert workflow.read_json(final / "music.json")["preview"] is False


@pytest.mark.parametrize("placement", ["outside-cut", "inside-cut"])
def test_preview_cannot_be_promoted_by_repointing_latest(prepared, pipeline, native_settings, placement):
    path, _, cut = _set_style(prepared, native_settings)
    preview_path = workflow.draft_cut(path, cut.id, preview=True)
    cut_directory = path.parent / "drafts" / cut.id
    cut_directory.mkdir(parents=True)
    if placement == "inside-cut":
        copied = cut_directory / "copied-preview.json"
        copied.write_bytes(preview_path.read_bytes())
        preview_path = copied
    workflow.write_json(cut_directory / "latest.json", {"draft": str(preview_path)})
    for action in (workflow.latest_draft, workflow.transcribe_draft, workflow.publish):
        with pytest.raises(ValueError, match="preview|Draft pointer"):
            action(path, cut.id)
    assert pipeline["transcriptions"] == []
    assert not (path.parent / "final").exists()


@pytest.mark.parametrize("alteration", ["missing-style", "changed-status", "changed-sidecar"])
def test_preview_cache_rejects_changed_style_status_or_handoff(
    prepared, pipeline, native_settings, alteration,
):
    path, _, cut = _set_style(prepared, native_settings)
    preview_path = workflow.draft_cut(path, cut.id, preview=True)
    preview = workflow.read_json(preview_path)
    if alteration == "missing-style":
        preview.pop("stylized")
    elif alteration == "changed-status":
        preview["status"] = "draft"
    else:
        Path(preview["music_instructions"]).write_text("Altered native handoff.", encoding="utf-8")
    workflow.write_json(preview_path, preview)
    with pytest.raises(ValueError, match="settings|preview status|artifact changed"):
        workflow.draft_cut(path, cut.id, preview=True)
    assert len(pipeline["renders"]) == 1
    assert not (path.parent / "drafts").exists()


def test_preview_without_explicit_style_is_rejected(prepared, pipeline, capsys):
    path, plan = prepared
    assert workflow.main(["preview", "--plan", str(path), "--cut", plan.cuts[0].id]) == 2
    assert "explicitly opted-in" in capsys.readouterr().err
    assert pipeline["renders"] == []
    assert not (path.parent / "previews").exists()
    assert workflow.load_plan(path).cuts[0].stylized is None


@pytest.mark.parametrize("preview", [False, True])
def test_wrong_canvas_does_not_get_a_draft_or_preview_receipt(
    prepared, pipeline, native_settings, monkeypatch, preview,
):
    path, _, cut = _set_style(prepared, native_settings)
    width, height = (1080, 1920) if preview else (360, 640)
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(duration=8, width=width, height=height, fps=30))
    with pytest.raises(ValueError, match="canvas/duration"):
        workflow.draft_cut(path, cut.id, preview=preview)
    root = path.parent / ("previews" if preview else "drafts")
    assert not list(root.rglob("preview.json" if preview else "draft.json"))
    assert not list(root.rglob("review.json"))
    assert not (path.parent / "drafts" / cut.id / "latest.json").exists()
