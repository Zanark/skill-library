from __future__ import annotations

import threading
from pathlib import Path

import pytest

from clipfarm import media
from clipfarm.models import Analysis, Clip, Cue, MediaInfo, Region, TrackPoint


def info(width=1920, height=1080):
    return MediaInfo(duration=10, width=width, height=height, fps=30, has_audio=False)


def test_probe_uses_decoded_display_dimensions_and_input_audio():
    log = """Input #0, mov, from 'portrait.mp4':
  Duration: 00:01:02.34, start: 0.000000, bitrate: 600 kb/s
  Stream #0:0: Video: h264 (High), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 29.97 fps, 30 tbr
  Stream #0:1: Audio: aac, 44100 Hz, stereo
Output #0, null, to 'pipe:':
  Stream #0:0: Video: wrapped_avframe, yuv420p, 1080x1920 [SAR 1:1 DAR 9:16], 29.97 fps
"""
    result = media._parse_probe(log)
    assert (result.width, result.height) == (1080, 1920)
    assert result.duration == pytest.approx(62.34)
    assert result.fps == 29.97
    assert result.has_audio and result.video_codec == "h264"


def test_invalid_probe_is_not_success():
    with pytest.raises(media.MediaError, match="finite video"):
        media._parse_probe("Duration: N/A\nVideo: png")


def test_bad_ffmpeg_override_is_actionable(monkeypatch):
    monkeypatch.setenv("FFMPEG_BINARY", r"Z:\does-not-exist\ffmpeg.exe")
    with pytest.raises(media.MediaError, match="FFMPEG_BINARY"):
        media.ffmpeg_exe()


def test_duration_is_bounded_by_actual_source():
    assert media._duration(info(), Clip(start=9, end=10.05)) == 1
    with pytest.raises(media.MediaError):
        media._duration(info(), Clip(start=9, end=11))


def test_clip_cues_clamps_and_excludes_boundaries():
    cues = [
        Cue(start=0, end=3, text="before"),
        Cue(start=2, end=4, text="cross start"),
        Cue(start=4, end=8, text="cross end"),
        Cue(start=6, end=7, text="after"),
    ]
    selected = media._clip_cues(cues, Clip(start=3, end=6), 3)
    assert [(c.start, c.end, c.text) for c in selected] == [
        (0, 1, "cross start"), (1, 3, "cross end"),
    ]
    assert "00:00:00,000 --> 00:00:01,000" in media._srt(selected)
    assert "before" not in media._srt(selected)
    assert media._srt_time(59.9996) == "00:01:00,000"


def test_caption_bursts_do_not_drop_words_or_change_case():
    text = "These Exact Words should remain in the same order, with punctuation. " * 6
    cue = Cue(start=2, end=14, text=text)
    bursts = media._caption_bursts(cue, 28)
    assert len(bursts) > 1
    assert " ".join(part for _, _, part in bursts).split() == cue.text.split()
    assert bursts[0][0] == 2 and bursts[-1][1] == 14
    for start, end, part in bursts:
        assert start < end
        assert len(part.splitlines()) <= 2
        assert max(map(len, part.splitlines())) <= 28
    assert all(a[1] == b[0] for a, b in zip(bursts, bursts[1:]))


@pytest.mark.parametrize("style,width", [("clean", 24), ("punchy", 20)])
def test_partial_long_caption_preserves_source_burst_phase(style, width):
    cue = Cue(start=10, end=70, text=" ".join(f"word{i:02}" for i in range(70)))
    bursts = media._caption_bursts(cue, width)
    begin, end, text = bursts[4]
    clip = Clip(start=begin + 0.1, end=end - 0.1, caption_style=style)
    selected = media._clip_cues([cue], clip, clip.end - clip.start)
    assert len(selected) == 1
    assert selected[0].text == text
    assert selected[0].start == 0
    assert selected[0].end == pytest.approx(clip.end - clip.start)
    assert "word00" not in selected[0].text


def test_caption_wrapping_accounts_for_wide_unicode_and_letters():
    wide = "字幕漢字" * 10
    lines = media._caption_lines(wide, 24)
    assert "".join(lines) == wide and max(map(len, lines)) <= 12
    wide = "W" * 48
    lines = media._caption_lines(wide, 24)
    assert "".join(lines) == wide and max(map(len, lines)) <= 13


def test_short_detected_face_is_available_for_an_editable_manual_split():
    result = media._choose_analysis(
        [media._Observation(0, Region(x=0.3, y=0.2, w=0.2, h=0.3))], info(), 0.4,
    )
    assert result.layout == "fit" and result.face_region is not None


def test_ass_escapes_untrusted_text_and_keeps_unicode():
    text = "{\\pos(0,0)} café \\N\nDialogue: 0,evil"
    escaped = media._ass_escape(text)
    assert r"{\pos" not in escaped
    assert r"\{\\pos" not in escaped
    assert "\\\u2060N" in escaped
    assert "café" in escaped
    assert "\n" not in escaped
    script = media._ass([Cue(start=0, end=2, text=text)], Clip(start=0, end=2))
    assert "NOT word-accurate" in script
    assert r"\pos(497," in script
    assert r"{\pos(0,0)}" not in script


def test_caption_position_respects_full_two_line_safe_zone():
    for style in ("clean", "punchy"):
        script = media._ass([Cue(start=0, end=1, text="caption")],
                            Clip(start=0, end=1, subtitle_y=0.63, caption_style=style))
        import re

        y = int(re.search(r"\\pos\(497,(\d+)\)", script)[1])
        font_size = 56 if style == "clean" else 64
        assert y + font_size * 1.5 <= 1920 * 0.65 + 1


def test_track_deadband_smoothing_and_cut_reset():
    observations = [
        media._Observation(0, Region(x=0.1, y=0.2, w=0.15, h=0.3)),
        media._Observation(0.5, Region(x=0.105, y=0.2, w=0.15, h=0.3)),
        media._Observation(1, Region(x=0.3, y=0.2, w=0.15, h=0.3)),
        media._Observation(1.5, Region(x=0.7, y=0.2, w=0.15, h=0.3), cut=True),
    ]
    track = media._smooth_track(observations)
    assert track[1].x == track[0].x
    assert 0.1 < track[2].x < 0.3
    assert track[3].x == 0.7 and track[3].cut
    commands = media._track_commands(track, info(), *media._crop_size(info(), track))
    before_cut = commands.splitlines()[2]
    assert "*(t-" not in before_cut
    assert "*(t-" in commands.splitlines()[1]
    assert "1.500000 crop@subject" in commands


def test_cut_without_face_is_carried_forward():
    track = media._smooth_track([
        media._Observation(0, Region(x=0.1, y=0.1, w=0.2, h=0.2)),
        media._Observation(0.5, None, cut=True),
        media._Observation(1, Region(x=0.7, y=0.1, w=0.2, h=0.2)),
    ])
    assert track[-1].cut and track[-1].x == 0.7


def test_heuristic_follows_only_sustained_unambiguous_face():
    face = Region(x=0.4, y=0.2, w=0.15, h=0.3)
    observations = [media._Observation(n / 2, face) for n in range(6)]
    assert media._choose_analysis(observations, info(), 3).layout == "follow"
    observations[2].ambiguous = True
    assert media._choose_analysis(observations, info(), 3).layout == "fit"
    observations[2].ambiguous = False
    assert media._choose_analysis(observations, info(720, 1280), 3).layout == "fit"


def test_corner_split_needs_persistence_and_screen_detail():
    face = Region(x=0.83, y=0.06, w=0.10, h=0.14)
    observations = [media._Observation(n / 2, face, detail=0.1) for n in range(8)]
    result = media._choose_analysis(observations, info(), 4)
    assert result.layout == "split" and result.face_region is not None
    assert any("heuristic" in warning.lower() for warning in result.warnings)
    for observation in observations:
        observation.detail = 0
    assert media._choose_analysis(observations, info(), 4).layout != "split"


def test_padded_faces_and_crop_coordinates_stay_inside_source():
    for x, y in ((0, 0), (0.8, 0.8), (0.4, 0.3)):
        face = Region(x=x, y=y, w=0.2, h=0.2)
        padded = media._padded_face(face)
        assert padded.x + padded.w <= 1 and padded.y + padded.h <= 1
        width, height = media._crop_size(info())
        cx, cy = media._crop_xy(TrackPoint(time=0, **face.model_dump()), info(), width, height)
        assert 0 <= cx <= info().width - width
        assert 0 <= cy <= info().height - height


def test_split_contains_content_instead_of_filling_by_crop():
    clip = Clip(start=0, end=1, layout="split",
                face_region=Region(x=0.8, y=0, w=0.2, h=0.3),
                content_region=Region(x=0, y=0, w=0.8, h=1))
    graph = media._filter_graph(info(), clip, "split", 1080, 1920,
                                clip.face_region, [], "captions_123.ass", None)
    assert "[screen]crop=1536:1080:0:0,scale=" in graph
    assert graph.count("force_original_aspect_ratio=decrease") == 2
    assert "gblur=" in graph
    assert "ass=filename=captions_123.ass" in graph
    assert "safe-zone" not in graph


def test_cancelled_render_does_not_spawn(monkeypatch):
    monkeypatch.setattr(media, "_source", lambda value: Path(value))
    monkeypatch.setattr(media, "_capabilities", lambda _: pytest.fail("must not start a probe"))
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(media.CancelledError):
        media.render(Path("source.mp4"), info(), Clip(start=0, end=1), [],
                     Path("output.mp4"), True, lambda *_: None, cancel)


def test_follow_without_usable_track_fails_actionably():
    with pytest.raises(media.MediaError, match="usable face track"):
        media._track_commands([], info(), 606, 1080)


def test_leetcode_model_requires_regions_and_has_distinct_caption_limits():
    regions = dict(face_region=Region(x=0, y=0, w=0.2, h=0.2),
                   content_region=Region(x=0.5, y=0, w=0.5, h=1))
    clip = Clip(start=0, end=1, layout="leetcode", **regions)
    assert clip.subtitle_y == 0.82 and not clip.results_zoom
    assert Clip(start=0, end=1, layout="leetcode", subtitle_y=0.88, **regions).subtitle_y == 0.88
    for arguments in [dict(layout="leetcode"), dict(layout="leetcode", subtitle_y=0.7, **regions),
                      dict(layout="fit", subtitle_y=0.82), dict(layout="split", subtitle_y=0.64)]:
        with pytest.raises(ValueError):
            Clip(start=0, end=1, **arguments)


def test_camera_absence_is_explicit_and_roundtrips_without_changing_legacy_clips():
    content = Region(x=0.5, y=0, w=0.5, h=1)
    clip = Clip(start=0, end=1, layout="leetcode", camera_mode="absent", content_region=content)
    assert clip.face_region is None and clip.subtitle_y == 0.82
    assert Clip.model_validate_json(clip.model_dump_json()) == clip
    assert clip.model_dump()["camera_mode"] == "absent"
    default = Clip(start=0, end=1)
    assert "camera_mode" not in default.model_dump()
    assert "camera_mode" not in default.model_dump_json()
    assert "camera_mode" not in default.model_dump(include={"camera_mode"})
    for arguments in [
        {"layout": "leetcode", "content_region": content},
        {"layout": "leetcode", "camera_mode": "absent"},
        {"layout": "leetcode", "camera_mode": "absent", "content_region": content, "face_region": content},
        {"layout": "fit", "camera_mode": "absent", "content_region": content},
        {"layout": "leetcode", "camera_mode": "auto", "content_region": content},
    ]:
        with pytest.raises(ValueError):
            Clip(start=0, end=1, **arguments)


@pytest.mark.parametrize("results", [False, True])
def test_camera_free_graph_uses_one_contained_content_feed_and_lower_captions(results, monkeypatch):
    clip = Clip(start=0, end=3, layout="leetcode", camera_mode="absent", results_zoom=results,
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    monkeypatch.setattr(media, "analyze", lambda *_: pytest.fail("Never infer camera absence"))
    assert media._prepare_layout(Path("unused.mp4"), info(), clip, lambda *_: None,
                                 threading.Event()) == ("leetcode", None, [], None)
    graph = media._filter_graph(info(), clip, "leetcode", 1080, 1920, None, [], "captions.ass", None)
    assert "[base]split=2[back][screen]" in graph
    assert "[avatar]" not in graph and "[face]" not in graph
    assert "[screen]crop=960:1080:960:0,scale=" in graph
    assert "[background][editor]overlay=(W-w)/2:96.0000+(1324-h)/2" in graph
    assert graph.endswith("[composed]ass=filename=captions.ass,setsar=1,format=yuv420p[outv]")
    if results:
        assert "0.68+0.32*" in graph and "eval=frame" in graph
        assert "[undimmed][black]blend=" in graph
        assert graph.index("[undimmed][black]") < graph.index("[background][editor]")
    else:
        assert "scale=1026:1324:force_original_aspect_ratio=decrease" in graph
        assert "blend=" not in graph
    script = media._ass([Cue(start=0, end=3, text="Code without a camera")], clip)
    assert r"\pos(540,1574)" in script and "&H20181818" in script
    clip.face_region = clip.content_region
    with pytest.raises(media.MediaError, match="absent camera"):
        media._prepare_layout(Path("unused.mp4"), info(), clip, lambda *_: None, threading.Event())
    with pytest.raises(media.MediaError, match="absent camera"):
        media._filter_graph(info(), clip, "leetcode", 1080, 1920, None, [], None, None)


def test_leetcode_captions_are_centered_below_editor_with_dark_box():
    clip = Clip(start=0, end=1, layout="leetcode",
                face_region=Region(x=0, y=0, w=0.2, h=0.2),
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    script = media._ass([Cue(start=0, end=1, text="Reference caption")], clip)
    assert r"\pos(540,1574)" in script
    assert ",3,8,0,5,54,54,0,1" in script
    assert "&H20181818" in script
    with pytest.raises(media.MediaError, match="not automatic face detection"):
        media.analyze(Path("unused.mp4"), info(), clip, lambda *_: None, threading.Event())


def test_results_graph_animates_only_explicit_roi_and_background():
    clip = Clip(start=2, end=5, layout="leetcode", results_zoom=True,
                face_region=Region(x=0, y=0, w=0.25, h=0.25),
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    graph = media._filter_graph(info(), clip, "leetcode", 360, 640, clip.face_region, [],
                                "captions.ass", None, results_elapsed=0.4, results_duration=3)
    assert "[screen]crop=960:1080:960:0,scale=w=" in graph
    assert "0.68+0.32*" in graph and "eval=frame:flags=lanczos,setsar=1[editor]" in graph
    assert "(t+0.400000000000)/1.900000000000" in graph
    assert "(T+0.400000000000)/1.900000000000" in graph
    assert "blend=all_expr='A+(B-A)*0.70*" in graph
    assert "[face]crop=480:270:0:0,scale=288:160:" in graph
    assert "overlay=(W-w)/2:32.0000+(160-h)/2" in graph
    assert "overlay=(W-w)/2:211.2000+(262-h)/2" in graph
    assert graph.index("[undimmed][black]") < graph.index("[background][avatar]")
    assert graph.index("[layer][editor]") < graph.index("[composed]ass=filename=captions.ass")
    assert "zoompan" not in graph and "tpad" not in graph


def test_normal_leetcode_graph_ignores_results_timing():
    clip = Clip(start=0, end=3, layout="leetcode",
                face_region=Region(x=0, y=0, w=0.25, h=0.25),
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    args = (info(), clip, "leetcode", 360, 640, clip.face_region, [], None, None)
    graph = media._filter_graph(*args)
    assert graph == media._filter_graph(*args, results_elapsed=2, results_duration=8,
                                        results_dim_elapsed=4, results_dim_duration=12)
    assert "eval=frame" not in graph and "blend=" not in graph
    assert "[face]crop=480:270:0:0,scale=288:160:" in graph
    assert "[screen]crop=960:1080:960:0,scale=342:262:" in graph
    assert "[background][avatar]overlay=(W-w)/2:32.0000+(160-h)/2" in graph
    assert "[layer][editor]overlay=(W-w)/2:211.2000+(262-h)/2" in graph


def test_results_graph_keeps_dim_clock_while_new_roi_zoom_restarts():
    clip = Clip(start=0, end=0.4, layout="leetcode", results_zoom=True,
                face_region=Region(x=0, y=0, w=0.25, h=0.25),
                content_region=Region(x=0.55, y=0, w=0.45, h=1))
    graph = media._filter_graph(info(), clip, "leetcode", 360, 640, clip.face_region, [], None, None,
                                results_elapsed=0, results_duration=0.4,
                                results_dim_elapsed=2.4, results_dim_duration=2.8)
    assert "(t+0.000000000000)/0.320000000000" in graph
    assert "(T+2.400000000000)/1.900000000000" in graph


@pytest.mark.parametrize("duration,ramp", [(3, 1.9), (1, 0.8), (0.2, 0.16), (2 / 30, 1 / 30)])
def test_results_animation_duration_reaches_hold_without_extending_clip(duration, ramp):
    assert f"/{ramp:.12f},0,1)" in media._results_ease(0, duration)
    assert media._results_ease(0, 1 / 30) == "1"


@pytest.mark.parametrize("elapsed,duration", [(-1, 1), (0, 0), (float("nan"), 1), (0, float("inf"))])
def test_results_animation_rejects_invalid_timing(elapsed, duration):
    with pytest.raises(media.MediaError, match="animation timing"):
        media._results_ease(elapsed, duration)
