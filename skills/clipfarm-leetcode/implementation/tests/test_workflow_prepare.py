import sys
import threading
from types import SimpleNamespace

import pytest

from clipfarm import workflow
from clipfarm.media import CancelledError, MediaError
from clipfarm.models import Cue, MediaInfo
from clipfarm.transcripts import parse_transcript


@pytest.fixture
def video_only(tmp_path, monkeypatch):
    source = tmp_path / "[LeetCode] source.mp4"
    source.write_bytes(b"unchanged video fixture")
    monkeypatch.setattr(workflow, "probe", lambda _: MediaInfo(duration=30, width=1280, height=720, fps=30))
    cues = [
        Cue(start=1.24, end=1.88, text="Hello."),
        Cue(start=4.26, end=6.82, text="Don't forget to insert it."),
    ]
    metadata = {
        "engine": "faster-whisper", "model": "small", "language_hint": None,
        "word_timestamps": True, "timing_note": "ASR word estimates; review recognition and timing.",
    }
    calls = []

    def generate(video, info, **options):
        calls.append((video, info, options))
        return cues, metadata

    engine = SimpleNamespace(generate=generate)
    monkeypatch.setitem(sys.modules, "clipfarm.source_transcripts", engine)
    return source, tmp_path / "runs", cues, calls, engine


def test_video_alone_generates_importable_granular_transcripts_and_precise_snapshot(video_only):
    source, root, cues, calls, _ = video_only
    original = source.read_bytes()
    path = workflow.prepare(source, root=root, run_id="video-only")
    plan = workflow.load_plan(path)
    assert source.read_bytes() == original
    assert not plan.reviewed_entire_transcript and plan.cuts == []
    assert plan.profile.show_question_title
    assert calls[0][2]["model_name"] == "small"
    assert calls[0][2]["language"] is None
    assert calls[0][2]["source_sha256"] == workflow.fingerprint(source)
    assert calls[0][2]["directory"] == path.parent / "source-asr"
    text = (path.parent / "transcript_granular.txt").read_text(encoding="utf-8")
    assert "00:00:01.240 Hello." in text
    imported, _ = parse_transcript(text, "transcript_granular.txt", 30)
    assert [(c.start, c.text) for c in imported] == [(c.start, c.text) for c in cues]
    snapshot = workflow.load_cues(path)
    assert [c.end for c in snapshot] == [1.88, 6.82]
    assert imported[0].end != snapshot[0].end
    exact, _ = parse_transcript(
        (path.parent / "transcript_granular.json").read_text(encoding="utf-8"),
        "transcript_granular.json", 30,
    )
    assert [(c.start, c.end, c.text) for c in exact] == [(c.start, c.end, c.text) for c in cues]
    provenance = workflow.read_json(path.parent / "input-provenance.json")
    assert provenance["transcript_origin"] == "generated_local"
    assert provenance["source_transcription"]["word_timestamps"] is True
    assert plan.transcript_sha256 == workflow.fingerprint(path.parent / "transcript_granular.txt")


def test_supplied_transcript_skips_asr_and_stays_unchanged(video_only):
    source, root, _, calls, _ = video_only
    transcript = source.parent / "provided.txt"
    transcript.write_text("00:00:02.000 Supplied words.\n", encoding="utf-8")
    original = transcript.read_bytes()
    path = workflow.prepare(source, transcript, "provided", root)
    assert calls == []
    assert transcript.read_bytes() == original
    assert workflow.load_cues(path)[0].text == "Supplied words."
    assert not (path.parent / "transcript_granular.txt").exists()
    assert workflow.read_json(path.parent / "input-provenance.json")["transcript_origin"] == "provided"


@pytest.mark.parametrize("filename", [
    "Design a Parking Reservation System _ System Design Interview.mp4",
    "Design a Rate Limiter _ System Design Interview.mp4",
])
def test_system_design_prepare_keeps_original_filename_and_requires_opt_in(video_only, filename):
    source, root, _, calls, _ = video_only
    source = source.rename(source.with_name(filename))
    with pytest.raises(ValueError, match="--workflow system-design"):
        workflow.prepare(source, root=root)
    assert calls == [] and not root.exists()
    original = source.read_bytes()
    path = workflow.prepare(source, root=root, workflow="system-design")
    plan = workflow.load_plan(path)
    assert plan.workflow == "system-design" and plan.output_format == "vertical"
    assert plan.profile.show_question_title
    assert plan.source == str(source) and source.read_bytes() == original
    assert plan.run_id.startswith("system-design-")
    assert not plan.reviewed_entire_transcript and plan.cuts == []
    assert plan.profile.code_region is None and plan.profile.face_region is None
    assert workflow.read_json(path.parent / "input-provenance.json")["workflow"] == "system-design"
    assert len(workflow.load_cues(path)) == 2


def test_system_design_rejects_horizontal_before_probe_or_writes(video_only, monkeypatch):
    source, root, _, calls, _ = video_only
    monkeypatch.setattr(workflow, "probe", lambda _: pytest.fail("Must reject format before probing"))
    with pytest.raises(ValueError, match="vertical output only"):
        workflow.prepare(source, root=root, workflow="system-design", output_format="horizontal")
    assert calls == [] and not root.exists()


def test_system_design_cli_passes_explicit_workflow(video_only, monkeypatch):
    source, root, _, _, _ = video_only
    calls = []
    monkeypatch.setattr(workflow, "prepare", lambda *a, **k: calls.append(k) or root / "plan.json")
    assert workflow.main(["prepare", "--video", str(source), "--workflow", "system-design"]) == 0
    assert calls == [{"model_name": "small", "language": None, "workflow": "system-design"}]


def test_missing_supplied_transcript_does_not_silently_fall_back_to_asr(video_only):
    source, root, _, calls, _ = video_only
    with pytest.raises(FileNotFoundError):
        workflow.prepare(source, source.parent / "missing.txt", root=root)
    assert calls == []


def test_existing_plan_is_refused_before_probe_or_transcription(video_only, monkeypatch):
    source, root, _, calls, _ = video_only
    path = workflow.prepare(source, root=root, run_id="existing")
    original = path.read_bytes()
    monkeypatch.setattr(workflow, "probe", lambda _: pytest.fail("Must not probe an existing run"))
    with pytest.raises(ValueError, match="already has a plan"):
        workflow.prepare(source, root=root, run_id="existing")
    assert len(calls) == 1 and path.read_bytes() == original


@pytest.mark.parametrize("run_id", ["../escape", "..\\escape", "Uppercase", "", "a" * 81])
def test_invalid_run_id_is_refused_before_probe_or_writes(video_only, monkeypatch, run_id):
    source, root, _, calls, _ = video_only
    monkeypatch.setattr(workflow, "probe", lambda _: pytest.fail("Must reject ID first"))
    with pytest.raises(ValueError, match="run ID"):
        workflow.prepare(source, run_id=run_id, root=root)
    assert calls == [] and not root.exists()


def test_interrupted_prepare_can_resume_same_run_and_forwards_options(video_only):
    source, root, cues, calls, engine = video_only
    event = threading.Event()

    def interrupted(video, info, **options):
        checkpoint = options["directory"] / "checkpoint.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text("saved progress", encoding="utf-8")
        raise CancelledError("Interrupted source ASR")

    original = engine.generate
    engine.generate = interrupted
    with pytest.raises(CancelledError):
        workflow.prepare(source, root=root, run_id="resume", model_name="base", language="en", cancel=event)
    assert not (root / "resume" / "plan.json").exists()
    assert (root / "resume" / "source-asr" / "checkpoint.json").read_text() == "saved progress"
    engine.generate = original
    path = workflow.prepare(source, root=root, run_id="resume", model_name="base", language="en", cancel=event)
    assert len(workflow.load_cues(path)) == len(cues)
    assert calls[0][2]["model_name"] == "base" and calls[0][2]["language"] == "en"
    assert calls[0][2]["cancel"] is event
    saved = workflow.read_json(path.parent / "delivery-request.json")
    assert workflow.load_plan(path).delivery.model_dump(mode="json") == saved["delivery"]


def test_empty_generation_never_creates_plan(video_only):
    source, root, _, _, engine = video_only
    engine.generate = lambda *args, **kwargs: ([], {"timing_note": "No speech"})
    with pytest.raises(MediaError, match="No speech"):
        workflow.prepare(source, root=root, run_id="silent")
    assert not (root / "silent" / "plan.json").exists()


def test_source_mutation_during_asr_never_creates_plan(video_only):
    source, root, _, _, engine = video_only
    original = engine.generate

    def mutate(video, info, **options):
        result = original(video, info, **options)
        source.write_bytes(b"changed video")
        return result

    engine.generate = mutate
    with pytest.raises(ValueError, match="changed during transcription"):
        workflow.prepare(source, root=root, run_id="changed")
    assert not (root / "changed" / "plan.json").exists()


@pytest.mark.parametrize("options,model,language", [([], "small", None), (["--model", "base", "--language", "en"], "base", "en")])
def test_prepare_cli_only_requires_video(video_only, monkeypatch, options, model, language):
    source, root, _, _, _ = video_only
    calls = []

    def prepare(*args, **kwargs):
        calls.append((args, kwargs))
        return root / "plan.json"

    monkeypatch.setattr(workflow, "prepare", prepare)
    assert workflow.main(["prepare", "--video", str(source), *options]) == 0
    assert calls[0][0][:2] == (source, None)
    assert calls[0][1] == {"model_name": model, "language": language}


def test_creation_timestamp_is_shared_across_sources_and_not_preparation_time(video_only):
    source, root, _, _, _ = video_only
    timestamp = "2026-09-25T23:41:12.327Z"
    first = workflow.prepare(source, root=root, run_id="first-source", session_timestamp=timestamp)
    second = workflow.prepare(source, root=root, run_id="second-source",
                              session_timestamp="2026-09-26T05:11:12.327+05:30")
    a, b = workflow.load_plan(first), workflow.load_plan(second)
    assert a.delivery == b.delivery
    assert a.delivery.directory_name == "session_20260926_051112_327000"
    assert a.delivery.timestamp_source == "prompt"
    assert workflow.read_json(first.parent / "input-provenance.json")["delivery"] == a.delivery.model_dump(mode="json")


@pytest.mark.parametrize("timestamp", ["2026-09-26T05:11:12", "2026-09-26", "not-a-time", "1790403072", 1790403072])
def test_creation_timestamp_requires_timezone_before_media_work(video_only, timestamp, monkeypatch):
    source, root, _, calls, _ = video_only
    monkeypatch.setattr(workflow, "probe", lambda _: pytest.fail("Reject timestamp before probing"))
    with pytest.raises(ValueError):
        workflow.prepare(source, root=root, session_timestamp=timestamp)
    assert calls == [] and not root.exists()


def test_cli_supplies_original_prompt_timestamp(video_only, monkeypatch):
    source, root, _, _, _ = video_only
    calls = []
    monkeypatch.setattr(workflow, "prepare", lambda *a, **k: calls.append(k) or root / "plan.json")
    assert workflow.main(["prepare", "--video", str(source), "--session-timestamp",
                          "2026-09-25T23:41:12.327Z", "--session-notice", "Music pending."]) == 0
    assert calls[0]["session_timestamp"] == "2026-09-25T23:41:12.327Z"
    assert calls[0]["session_notice"] == "Music pending."


def test_interrupted_request_cannot_be_silently_reassigned(video_only):
    source, root, _, _, engine = video_only

    def interrupted(*args, **kwargs):
        raise CancelledError("Stopped")

    engine.generate = interrupted
    with pytest.raises(CancelledError):
        workflow.prepare(source, root=root, run_id="resume", session_timestamp="2026-09-25T23:41:12.327Z")
    with pytest.raises(ValueError, match="different delivery session"):
        workflow.prepare(source, root=root, run_id="resume", session_timestamp="2026-09-26T23:41:12.327Z")


@pytest.mark.parametrize("filename,content", [
    ("captions.txt", "00:00:01.000 Again.\n00:00:02.000 Again.\n"),
    ("captions.json", '[{"start":1,"end":2,"text":"Again."},{"start":2,"end":3,"text":"Again."}]'),
])
def test_import_keeps_adjacent_deliberate_repetitions(filename, content):
    cues, _ = parse_transcript(content, filename, 30)
    assert [cue.text for cue in cues] == ["Again.", "Again."]
