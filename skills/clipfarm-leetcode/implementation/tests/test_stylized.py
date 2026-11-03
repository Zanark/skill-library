from datetime import datetime, timezone
import json
import subprocess
import threading

import cv2
import numpy as np
import pytest

from clipfarm import media, montage, workflow
from clipfarm.models import Clip, Cue, EditorialCorrection, MediaInfo, Region
from clipfarm.music_models import BeatBoundary, StylizedEdit
from clipfarm.stylized import compile_style
from clipfarm.workflow_models import VisualEvidence, WorkflowCut, WorkflowPlan, WorkflowProfile, WorkflowSegment


def native_style(**changes):
    value = {
        "music": {
            "route": "instagram", "title": "Original fixture", "artist": "ClipFarm test",
            "track_url": "https://www.instagram.com/reels/audio/123/",
            "bpm": 120, "beat_review": "Manually measured the steady grid in this original fixture.",
            "native_checked_at": datetime.now(timezone.utc).isoformat(),
            "region": "IN", "account_context": "Personal organic Reel",
        },
        "boundaries": [{"segment_index": 0, "safe_tail_seconds": 0.3,
                        "safety_note": "The tail is silent idle time with no meaningful visual work."}],
    }
    value.update(changes)
    return StylizedEdit.model_validate(value)


def edit():
    cut = WorkflowCut(
        id="test", title="Useful explanation", category="explanation",
        rationale="Preserve the complete explanation.", coherence_review="Read complete context and retained explanation.",
        trim_silence=False, segments=[WorkflowSegment(start=0, end=1.2), WorkflowSegment(start=2, end=3.2)],
        stylized=native_style(),
    )
    plan = WorkflowPlan(
        run_id="test", source="source.mp4", source_sha256="a" * 64, transcript="source.txt",
        transcript_sha256="b" * 64, reviewed_entire_transcript=True,
        media=MediaInfo(duration=4, width=320, height=180, fps=30, has_audio=False),
        profile=WorkflowProfile(camera_mode="absent", code_region=Region(x=0, y=0, w=1, h=1)),
        cuts=[cut],
    )
    segments, _ = workflow.compile_segments(plan, cut, threading.Event())
    return plan, cut, segments


def test_explicit_beats_only_remove_safe_tail_and_map_exact_frames():
    plan, cut, segments = edit()
    changed, removed, transitions, report = compile_style(plan, cut, segments, [], threading.Event())
    assert segments[0].end == 1.2
    assert changed[0].end == 1 and changed[1].start == 2
    assert removed[0]["start"] == 1 and removed[0]["end"] == 1.2
    assert report[0]["output_frame"] == 30 and report[0]["aligned"]
    assert report[0]["removed_frames"] == 6 and not transitions


def test_no_safe_beat_keeps_content_and_discloses_unaligned_join():
    plan, cut, segments = edit()
    cut.stylized.boundaries[0].safe_tail_seconds = 0.1
    result, removed, _, report = compile_style(plan, cut, segments, [], threading.Event())
    assert result == segments and not removed
    assert not report[0]["aligned"] and report[0]["output_frame"] == 36


@pytest.mark.parametrize("hazard", ["caption", "visual", "results", "correction", "silence_trim",
                                   "changed_segments", "last_join"])
def test_speech_first_refuses_unsafe_or_stale_handles(hazard):
    plan, cut, segments = edit()
    cues = []
    if hazard == "caption":
        cues = [Cue(start=0.9, end=1.15, text="Never cut this word.")]
    elif hazard == "visual":
        cut.evidence = [VisualEvidence(time=1.1, image="proof.png", description="Protected meaningful work",
                                      kind="layout", verified_by="test")]
    elif hazard == "results":
        segments[0].results_zoom = True
    elif hazard == "correction":
        segments[0].correction = EditorialCorrection(text="Keep this complete correction.",
                                                    sources=["https://example.org/reference"])
    elif hazard == "silence_trim":
        cut.trim_silence = True
    elif hazard == "changed_segments":
        segments[0].end = 1.1
    else:
        cut.stylized.boundaries[0].segment_index = 1
    with pytest.raises(ValueError):
        compile_style(plan, cut, segments, cues, threading.Event())


def test_audio_signal_must_be_silent_not_just_missing_captions(monkeypatch):
    plan, cut, segments = edit()
    plan.media.has_audio = True
    monkeypatch.setattr(montage, "detect_silences", lambda *a, **kw: [])
    with pytest.raises(ValueError, match="not silent"):
        compile_style(plan, cut, segments, [], threading.Event())
    monkeypatch.setattr(montage, "detect_silences", lambda src, start, end, *a, **kw: [(start, end)])
    assert compile_style(plan, cut, segments, [], threading.Event())[0][0].end == 1


def test_dip_respects_incoming_captions_and_preserves_heading_layer():
    plan, cut, segments = edit()
    cut.stylized.boundaries[0].transition = "dip"
    with pytest.raises(ValueError, match="caption"):
        compile_style(plan, cut, segments, [Cue(start=2, end=2.2, text="Immediate speech")], threading.Event())
    _, _, transitions, _ = compile_style(plan, cut, segments, [], threading.Event())
    assert transitions == {0: (0, 4), 1: (4, 0)}
    clip = segments[0]
    graph = media._filter_graph(plan.media, clip, "leetcode", 360, 640, None, [], "caption.ass", None,
                                fade_out_frames=4, retained_frames=30)
    assert graph.index("fade=t=out") < graph.index("ass=filename=caption.ass")
    assert "start_frame=26:nb_frames=4" in graph


def test_multiple_boundaries_use_updated_output_clock_and_frame_grid():
    plan, cut, segments = edit()
    third = WorkflowSegment(start=3.3, end=4.5)
    plan.media.duration = 5
    cut.segments.append(third)
    segments.append(segments[1].model_copy(update={"start": 3.3, "end": 4.5}))
    cut.stylized.boundaries.append(BeatBoundary(
        segment_index=1, safe_tail_seconds=0.3, safety_note="Silent idle tail, safe to shorten for the beat.",
    ))
    result, _, _, report = compile_style(plan, cut, segments, [], threading.Event())
    assert [r["output_frame"] for r in report] == [30, 60]
    assert result[1].end == 3


def test_style_absent_serialization_preserves_old_cuts():
    plan, cut, _ = edit()
    cut.stylized = None
    old_signature = workflow.cut_signature(plan, cut)
    assert "stylized" not in cut.model_dump()
    roundtrip = WorkflowPlan.model_validate(plan.model_dump())
    assert workflow.cut_signature(roundtrip, roundtrip.cuts[0]) == old_signature


def test_native_preview_uses_real_frames_maps_and_original_audio_only(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run([
        media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=red:size=320x180:rate=30:duration=4",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", "4", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(source),
    ], check=True, capture_output=True, timeout=30)
    plan, cut, segments = edit()
    plan.source, plan.media = str(source), media.probe(source)
    cut.stylized.boundaries[0].transition = "dip"
    changed, _, transitions, _ = compile_style(plan, cut, segments, [], threading.Event())
    output = tmp_path / "native-preview.mp4"
    spans = montage.render_montage(
        source, plan.media, changed, [], output, True, lambda *_: None, threading.Event(),
        stylized=cut.stylized, transitions=transitions,
    )
    assert spans[0].output_end == 1 and spans[1].output_end == 2.2
    info = media.probe(output)
    assert (info.width, info.height, info.has_audio) == (360, 640, True)
    record = json.loads(output.with_suffix(".source-map.json").read_text())
    assert record["segments"][0]["source_end"] == 1
    cap = cv2.VideoCapture(str(output))
    try:
        levels = []
        for frame in (10, 29, 30, 40):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            assert ok
            levels.append(float(image.mean()))
        assert levels[1] < levels[0] * 0.5
        assert levels[2] < levels[3] * 0.2
    finally:
        cap.release()
    assert not list(tmp_path.glob(".montage_*"))


@pytest.mark.parametrize("has_audio", [True, False])
def test_embedded_montage_keeps_timing_and_mixes_music_with_or_without_source_audio(tmp_path, has_audio):
    from test_montage import ffmpeg

    source, track, proof = tmp_path / "source.mp4", tmp_path / "track.wav", tmp_path / "permission.txt"
    source_args = ["-f", "lavfi", "-i", "color=red:size=320x180:rate=30:duration=4"]
    if has_audio:
        source_args += ["-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=4"]
    ffmpeg(*source_args, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", source)
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5",
           "-ac", "2", "-c:a", "pcm_s16le", track)
    proof.write_text("Original synthetic test tone generated locally; unrestricted fixture use.", encoding="utf-8")
    style = StylizedEdit.model_validate({
        "music": {
            "route": "embedded", "title": "Synthetic fixture", "artist": "ClipFarm tests",
            "file": str(track), "sha256": workflow.fingerprint(track), "bpm": 120,
            "start_seconds": 0.5,
            "beat_review": "Synthetic steady tone; no beat-boundary edits are requested.",
            "rights": {
                "scope": "Original synthetic fixture", "usage": "Unrestricted local tests",
                "territory": "Worldwide", "checked_by": "Automated fixture generator",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "permission_note": "Created in this test; no third-party recording or composition used.",
                "platforms": ["instagram", "youtube"], "attribution_required": False,
                "proof_file": str(proof), "proof_sha256": workflow.fingerprint(proof),
            },
        },
    })
    plan, cut, segments = edit()
    plan.source, plan.media, cut.stylized = str(source), media.probe(source), style
    if not has_audio:
        style.boundaries = native_style().boundaries
        style.boundaries[0].transition = "dip"
    changed, _, transitions, _ = compile_style(plan, cut, segments, [], threading.Event())
    output = tmp_path / "embedded.mp4"
    spans = montage.render_montage(
        source, plan.media, changed, [], output, not has_audio, lambda *_: None, threading.Event(),
        stylized=style, transitions=transitions,
    )
    duration = 2.4 if has_audio else 2.2
    assert spans[-1].output_end == duration
    info = media.probe(output)
    assert info.has_audio
    assert (info.width, info.height) == ((1080, 1920) if has_audio else (360, 640))
    samples = np.frombuffer(ffmpeg("-i", output, "-map", "0:a:0", "-ac", "1", "-ar", "48000",
                                  "-f", "f32le", "pipe:1"), dtype="<f4")
    assert abs(len(samples) / 48000 - duration) <= 1 / 30
    window = samples[round(0.65 * 48000):round(1.05 * 48000)]
    times = np.arange(len(window)) / 48000
    music_level = abs(np.mean(window * np.exp(-2j * np.pi * 440 * times)))
    voice_level = abs(np.mean(window * np.exp(-2j * np.pi * 1000 * times)))
    assert music_level > 0.0001
    assert voice_level > 5 * music_level if has_audio else voice_level < music_level / 10
    assert not list(tmp_path.glob(".montage_*"))


def test_music_evidence_change_during_render_prevents_publication(tmp_path, monkeypatch):
    from clipfarm import music
    from test_montage import ffmpeg

    source, output = tmp_path / "source.mp4", tmp_path / "unapproved.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=red:size=320x180:rate=30:duration=1",
           "-c:v", "libx264", "-preset", "ultrafast", source)
    bindings = iter([{"proof": "original"}, {"proof": "changed"}])
    monkeypatch.setattr(music, "inputs", lambda style: next(bindings))
    monkeypatch.setattr(music, "stage_track", lambda *args: None)
    with pytest.raises(media.MediaError, match="changed during rendering"):
        montage.render_montage(source, media.probe(source), [Clip(start=0, end=1)], [], output,
                               True, lambda *_: None, threading.Event(), stylized=native_style(boundaries=[]))
    assert not output.exists() and not output.with_suffix(".srt").exists()
    assert not list(tmp_path.glob(".montage_*"))


def test_renderer_cannot_apply_transitions_without_opt_in(tmp_path):
    with pytest.raises(media.MediaError, match="explicit stylized opt-in"):
        montage.render_montage(tmp_path / "not-needed.mp4",
                               MediaInfo(duration=1, width=320, height=180, fps=30),
                               [Clip(start=0, end=1)], [], tmp_path / "out.mp4",
                               True, lambda *_: None, threading.Event(), transitions={0: (4, 0)})
