from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest

from clipfarm import media
from clipfarm.models import Analysis, Clip, Cue, Region, TrackPoint


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    return tmp_path_factory.mktemp("media")


def ffmpeg(*arguments):
    result = subprocess.run(
        [media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *map(str, arguments)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    return result


def read_image(path):
    return cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)


def preview_frame(path, at):
    result = ffmpeg("-ss", at, "-protocol_whitelist", "file,pipe", "-i", path,
                    "-map", "0:v:0", "-frames:v", "1", "-an", "-pix_fmt", "rgb24",
                    "-f", "rawvideo", "pipe:1")
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(640, 360, 3)


@pytest.fixture(scope="module")
def sources(workspace):
    landscape = workspace / "source with spaces café.mp4"
    silent = workspace / "silent.mp4"
    portrait = workspace / "portrait.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=2.5",
           "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=2.5",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", landscape)
    ffmpeg("-f", "lavfi", "-i",
           "color=red:size=320x180:rate=30:duration=2,drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,1)'",
           "-c:v", "libx264", "-preset", "ultrafast", "-g", "60", "-an", silent)
    ffmpeg("-display_rotation:v:0", "90", "-i", landscape, "-c", "copy", portrait)
    return landscape, silent, portrait


@pytest.fixture(scope="module")
def scene_source(workspace):
    source = workspace / "actual scene cut.mp4"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=red:size=640x360:rate=30:duration=2,"
        "drawbox=x=214:y=0:w=212:h=ih:color=green:t=fill,"
        "drawbox=x=426:y=0:w=214:h=ih:color=blue:t=fill,"
        "drawbox=x=0:y=0:w=214:h=ih:color=cyan:t=fill:enable='gte(t,1)',"
        "drawbox=x=214:y=0:w=212:h=ih:color=magenta:t=fill:enable='gte(t,1)',"
        "drawbox=x=426:y=0:w=214:h=ih:color=yellow:t=fill:enable='gte(t,1)'",
        "-c:v", "libx264", "-preset", "ultrafast", "-an", source,
    )
    return source


def test_bundled_ffmpeg_supports_required_encoder_and_subtitles():
    assert media._capabilities(media.ffmpeg_exe()) == (True, True)


def test_analysis_worker_allows_process_to_exit(sources):
    script = """
from pathlib import Path
import sys
import threading
from clipfarm.media import analyze, probe
from clipfarm.models import Clip
source = Path(sys.argv[1])
info = probe(source)
def run():
    analyze(source, info, Clip(start=0, end=2), lambda *_: None, threading.Event())
worker = threading.Thread(target=run)
worker.start()
worker.join()
print("worker finished", flush=True)
"""
    result = subprocess.run([sys.executable, "-c", script, str(sources[0])],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "worker finished" in result.stdout


def test_probe_rotation_and_thumbnail_paths(sources, workspace):
    landscape, silent, portrait = sources
    assert media.probe(landscape).has_audio
    assert not media.probe(silent).has_audio
    rotated = media.probe(portrait)
    assert (rotated.width, rotated.height) == (360, 640)
    thumb = workspace / "thumb with spaces café.jpg"
    media.thumbnail(portrait, thumb, 0.4)
    image = read_image(thumb)
    assert image is not None and image.shape[0] > image.shape[1]


@pytest.mark.parametrize("layout", ["fit", "manual", "split", "follow"])
def test_real_preview_layouts_audio_trim_and_caption_sidecar(layout, sources, workspace):
    source = sources[0]
    info = media.probe(source)
    face = Region(x=0.1, y=0.1, w=0.25, h=0.5)
    analysis = Analysis(layout="follow", confidence=1, message="Synthetic test track", face_region=face,
                        track=[TrackPoint(time=0, x=0.1, y=0.1, w=0.15, h=0.3),
                               TrackPoint(time=0.5, x=0.55, y=0.1, w=0.15, h=0.3),
                               TrackPoint(time=1, x=0.2, y=0.1, w=0.15, h=0.3, cut=True)])
    clip = Clip(start=0.5, end=1.9, layout=layout, face_region=face, analysis=analysis,
                content_region=Region(x=0.2, y=0, w=0.8, h=1), caption_style="punchy")
    cues = [Cue(start=0, end=0.5, text="not included"),
            Cue(start=0.2, end=0.8, text="café literal {\\pos(0,0)}"),
            Cue(start=0.8, end=2.4, text="Readable captions without any translated words.")]
    output = workspace / f"job {layout} café" / "preview result.mp4"
    progress = []
    returned = media.render(source, info, clip, cues, output, True,
                            lambda fraction, _: progress.append(fraction), threading.Event())
    result = media.probe(output)
    assert (returned is not None) == (layout == "follow")
    assert (result.width, result.height, result.fps) == (360, 640, 30)
    assert result.has_audio and result.video_codec == "h264"
    assert result.duration == pytest.approx(1.4, abs=0.09)
    sidecar = output.with_suffix(".srt").read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:00,300" in sidecar
    # Long captions retain their source burst boundary rather than compressing all
    # words into the shortened clip.
    assert "00:00:00,300 --> 00:00:01,309" in sidecar
    assert "00:00:01,309 --> 00:00:01,400" in sidecar
    assert "not included" not in sidecar and r"{\pos(0,0)}" in sidecar
    assert progress[-1] == 1
    assert sorted(p.name for p in output.parent.iterdir()) == ["preview result.mp4", "preview result.srt"]
    metadata = subprocess.run(
        [media.ffmpeg_exe(), "-hide_banner", "-i", str(output), "-t", "0.01", "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
    ).stderr.decode("utf-8", errors="replace")
    assert "48000 Hz" in metadata and "yuv420p" in metadata
    payload = output.read_bytes()
    assert payload.find(b"moov") < payload.find(b"mdat")


def test_full_export_silent_accurate_seek_and_srt_without_burn(sources, workspace):
    source = sources[1]
    output = workspace / "full export" / "result.mp4"
    media.render(
        source, media.probe(source), Clip(start=0.8, end=1.4, layout="manual", captions=False),
        [Cue(start=0.9, end=1.2, text="Sidecar only")], output, False, lambda *_: None, threading.Event(),
    )
    info = media.probe(output)
    assert (info.width, info.height, info.fps) == (1080, 1920, 30)
    assert not info.has_audio and info.duration == pytest.approx(0.6, abs=0.05)
    assert "00:00:00,100 --> 00:00:00,400" in output.with_suffix(".srt").read_text()
    first, later = workspace / "first.png", workspace / "later.png"
    media.thumbnail(output, first, 0)
    media.thumbnail(output, later, 0.3)
    first_pixel = read_image(first).mean(axis=(0, 1))
    later_pixel = read_image(later).mean(axis=(0, 1))
    assert first_pixel[2] > 200 and first_pixel[0] < 30
    assert later_pixel[0] > 200 and later_pixel[2] < 30


def test_portrait_preserves_rotation_and_no_sidecar_when_no_cues(sources, workspace):
    source = sources[2]
    info = media.probe(source)
    output = workspace / "portrait render" / "preview.mp4"
    media.render(source, info, Clip(start=0, end=0.5, layout="fit"), [], output, True,
                 lambda *_: None, threading.Event())
    result = media.probe(output)
    assert (result.width, result.height) == (360, 640)
    assert not output.with_suffix(".srt").exists()


def test_sampled_analysis_is_clip_local_and_conservative(sources):
    source = sources[1]
    info = media.probe(source)
    progress = []
    result = media.analyze(source, info, Clip(start=0.6, end=1.6),
                           lambda fraction, _: progress.append(fraction), threading.Event())
    assert result.layout == "fit"
    assert all(0 <= point.time <= 1 for point in result.track)
    assert progress[0] == 0 and progress[-1] == 1
    frames = list(media._sample_frames(source, info, Clip(start=0.5, end=1.5), threading.Event()))
    assert len(frames) == 2
    assert frames[0][0] == 0
    assert frames[0][1][:, :, 0].mean() > 200


def test_real_follow_pixels_move_and_jump_instead_of_panning_across_cut(scene_source, workspace):
    track = [
        TrackPoint(time=0, x=0.1, y=0.2, w=0.1, h=0.15),
        TrackPoint(time=0.5, x=0.45, y=0.2, w=0.1, h=0.15),
        TrackPoint(time=1, x=0.8, y=0.2, w=0.1, h=0.15, cut=True),
        TrackPoint(time=1.5, x=0.8, y=0.2, w=0.1, h=0.15),
    ]
    analysis = Analysis(layout="follow", confidence=1, message="Known synthetic face positions", track=track)
    output = workspace / "follow cut pixels" / "preview.mp4"
    media.render(scene_source, media.probe(scene_source),
                 Clip(start=0, end=2, layout="follow", captions=False, analysis=analysis),
                 [], output, True, lambda *_: None, threading.Event())
    expected = [
        (0.05, (255, 0, 0)),
        (0.6, (0, 128, 0)),
        (0.9, (0, 128, 0)),
        (1.1, (255, 255, 0)),
    ]
    for at, color in expected:
        pixel = preview_frame(output, at)[320, 180].astype(int)
        assert np.max(np.abs(pixel - np.array(color))) < 12, (at, pixel, color)


def test_real_scene_change_resets_analysis_track(scene_source, monkeypatch):
    class DeterministicDetector:
        """Known boxes isolate real scene detection from Haar's photographic training."""

        calls = 0

        def empty(self):
            return False

        def detectMultiScale(self, *_args, **_kwargs):
            self.calls += 1
            return [(60 if self.calls <= 2 else 330, 45, 70, 70)]

    monkeypatch.setattr(media.cv2, "CascadeClassifier", lambda _: DeterministicDetector())
    analysis = media.analyze(scene_source, media.probe(scene_source), Clip(start=0, end=2),
                             lambda *_: None, threading.Event())
    assert analysis.layout == "follow"
    cut = next(point for point in analysis.track if point.cut)
    assert cut.time == 1
    assert cut.x == pytest.approx(330 / 480)


def test_real_split_uses_both_regions_and_contains_screen_edges(workspace):
    source = workspace / "split screen edge markers.mp4"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=red:size=640x360:rate=30:duration=1,"
        "drawbox=x=320:y=0:w=320:h=ih:color=blue:t=fill,"
        "drawbox=x=320:y=0:w=320:h=30:color=yellow:t=fill,"
        "drawbox=x=320:y=330:w=320:h=30:color=cyan:t=fill",
        "-c:v", "libx264", "-preset", "ultrafast", "-an", source,
    )
    output = workspace / "split pixel evidence" / "preview.mp4"
    clip = Clip(start=0, end=1, layout="split", captions=False,
                face_region=Region(x=0, y=0, w=0.25, h=1),
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    media.render(source, media.probe(source), clip, [], output, True,
                 lambda *_: None, threading.Event())
    frame = preview_frame(output, 0.1)
    for y, color in [(109, (255, 0, 0)), (278, (0, 0, 255)),
                     (197, (255, 255, 0)), (359, (0, 255, 255))]:
        pixel = frame[y, 180].astype(int)
        assert np.max(np.abs(pixel - np.array(color))) < 12, (y, pixel, color)


def test_cancel_cleans_partial_artifacts(sources, workspace):
    source = sources[0]
    output = workspace / "cancel job" / "preview.mp4"
    cancel = threading.Event()

    def progress(fraction, _):
        if fraction > 0:
            cancel.set()

    with pytest.raises(media.CancelledError):
        media.render(source, media.probe(source), Clip(start=0, end=2.4, layout="fit"),
                     [Cue(start=0, end=2, text="cancel")], output, False, progress, cancel)
    assert not output.exists() and not output.with_suffix(".srt").exists()
    assert not list(output.parent.iterdir())


def test_invalid_media_and_missing_split_region_fail_without_outputs(sources, workspace):
    invalid = workspace / "broken.mp4"
    invalid.write_bytes(b"not a video")
    with pytest.raises(media.MediaError, match="FFmpeg"):
        media.probe(invalid)
    output = workspace / "bad job" / "preview.mp4"
    with pytest.raises(media.MediaError, match="FFmpeg"):
        media.render(invalid, media.probe(sources[0]), Clip(start=0, end=0.5, layout="fit"),
                     [], output, True, lambda *_: None, threading.Event())
    assert not output.exists() and not list(output.parent.iterdir())
    source = sources[1]
    with pytest.raises(media.MediaError, match="face region"):
        media.render(source, media.probe(source), Clip(start=0, end=1, layout="split"),
                     [], output, True, lambda *_: None, threading.Event())


def test_square_pixel_normalization(sources, workspace):
    anamorphic = workspace / "anamorphic.mp4"
    ffmpeg("-i", sources[1], "-vf", "setsar=2", "-c:v", "libx264",
           "-preset", "ultrafast", "-an", anamorphic)
    info = media.probe(anamorphic)
    assert (info.width, info.height) == (640, 180)
    rotated = workspace / "anamorphic rotated.mp4"
    ffmpeg("-display_rotation:v:0", "90", "-i", anamorphic, "-c", "copy", rotated)
    info = media.probe(rotated)
    assert (info.width, info.height) == (180, 640)


def test_variable_frame_rate_becomes_stable_thirty(workspace):
    source = workspace / "variable cadence.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=2",
           "-vf", "select='if(lt(t,1),not(mod(n,2)),1)'", "-fps_mode", "vfr",
           "-c:v", "libx264", "-preset", "ultrafast", "-an", source)
    output = workspace / "vfr job" / "preview.mp4"
    media.render(source, media.probe(source), Clip(start=0.25, end=1.75, layout="fit"),
                 [], output, True, lambda *_: None, threading.Event())
    assert media.probe(output).fps == 30
    result = ffmpeg("-i", output, "-an", "-vf", "showinfo", "-f", "null", "-")
    assert result.returncode == 0


def test_ass_commands_in_transcript_cannot_reposition_caption(workspace):
    source = workspace / "black.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=black:size=320x180:rate=30:duration=1",
           "-c:v", "libx264", "-preset", "ultrafast", source)
    output = workspace / "escaped caption" / "preview.mp4"
    media.render(
        source, media.probe(source), Clip(start=0, end=1, layout="manual"),
        [Cue(start=0, end=1, text=r"{\pos(10,10)} Test\Ntext")],
        output, True, lambda *_: None, threading.Event(),
    )
    image_path = workspace / "caption pixels.png"
    media.thumbnail(output, image_path, 0.1)
    gray = cv2.cvtColor(read_image(image_path), cv2.COLOR_BGR2GRAY)
    ys, _ = np.where(gray > 150)
    assert len(ys) > 20
    assert ys.min() > gray.shape[0] * 0.45
    assert ys.max() < gray.shape[0] * 0.66


def test_very_wide_caption_letters_stay_inside_horizontal_safe_zone(workspace):
    source = workspace / "black wide text.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=black:size=320x180:rate=30:duration=1",
           "-c:v", "libx264", "-preset", "ultrafast", source)
    output = workspace / "wide caption" / "preview.mp4"
    media.render(source, media.probe(source), Clip(start=0, end=1, layout="manual"),
                 [Cue(start=0, end=1, text="W" * 48)], output, True,
                 lambda *_: None, threading.Event())
    image_path = workspace / "wide caption pixels.png"
    media.thumbnail(output, image_path, 0.1)
    gray = cv2.cvtColor(read_image(image_path), cv2.COLOR_BGR2GRAY)
    _, xs = np.where(gray > 150)
    assert len(xs) > 20
    assert xs.min() >= gray.shape[1] * 0.06
    assert xs.max() <= gray.shape[1] * 0.86


def test_source_playlists_are_not_accepted(workspace):
    playlist = workspace / "playlist.m3u8"
    playlist.write_text("#EXTM3U\n")
    with pytest.raises(media.MediaError, match="ordinary local video"):
        media.probe(playlist)


@pytest.mark.parametrize("results_zoom", [False, True])
@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_leetcode_reference_regions_full_roi_and_below_code_caption(workspace, monkeypatch, results_zoom, camera_mode):
    source = workspace / f"leetcode reference {results_zoom} {camera_mode}.mp4"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=lime:size=640x360:rate=30:duration=1,"
        "drawbox=x=0:y=0:w=160:h=90:color=red:t=fill,"
        "drawbox=x=320:y=0:w=320:h=ih:color=blue:t=fill,"
        "drawbox=x=320:y=0:w=320:h=24:color=yellow:t=fill,"
        "drawbox=x=320:y=336:w=320:h=24:color=cyan:t=fill",
        "-c:v", "libx264", "-preset", "ultrafast", "-an", source,
    )
    clip = Clip(start=0, end=1, layout="leetcode", results_zoom=results_zoom, camera_mode=camera_mode,
                face_region=Region(x=0, y=0, w=0.25, h=0.25) if camera_mode == "required" else None,
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    monkeypatch.setattr(media, "analyze", lambda *_: pytest.fail("A cardboard avatar must not trigger Haar"))
    output = workspace / f"leetcode job {results_zoom} {camera_mode}" / "preview.mp4"
    media.render(source, media.probe(source), clip, [Cue(start=0, end=1, text="Readable code caption")],
                 output, True, lambda *_: None, threading.Event())
    frame = preview_frame(output, 0.9 if results_zoom else 0.1)
    if camera_mode == "required":
        np.testing.assert_allclose(frame[112, 180].astype(int), (255, 0, 0), atol=12)
    else:
        np.testing.assert_allclose(frame[112, 180].astype(int), (0, 0, 255), atol=12)
    top, bottom = (211, 473) if camera_mode == "required" else (60, 444)
    np.testing.assert_allclose(frame[(top + bottom) // 2, 180].astype(int), (0, 0, 255), atol=12)
    np.testing.assert_allclose(frame[top + 5, 180].astype(int), (255, 255, 0), atol=12)
    np.testing.assert_allclose(frame[bottom - 5, 180].astype(int), (0, 255, 255), atol=12)
    # The website/problem area is lime; the editor panel contains only the supplied blue ROI.
    assert frame[(top + bottom) // 2, 170, 1] < 20
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    lower = gray[480:, :]
    ys, _ = np.where(lower > 235)
    assert len(ys) > 30 and ys.min() + 480 >= 500
    assert ys.max() + 480 < 580
    assert np.count_nonzero(lower[25:65, 80:280] < 45) > 300


@pytest.mark.parametrize("camera_mode", ["required", "absent"])
@pytest.mark.parametrize("captions", [False, True])
@pytest.mark.parametrize("results_zoom", [False, True])
def test_question_header_survives_silence_without_covering_feeds_or_captions(workspace, camera_mode, captions, results_zoom):
    from clipfarm.solution_artwork import _default_consolas

    try:
        font = _default_consolas()
    except media.MediaError:
        pytest.skip("Requires genuine local Consolas")
    if not font.is_file():
        pytest.skip("Requires genuine local Consolas")
    source = workspace / f"title source {camera_mode} {captions}.mp4"
    ffmpeg("-f", "lavfi", "-i",
           "color=black:size=640x360:rate=30:duration=1,"
           "drawbox=x=0:y=0:w=160:h=90:color=red:t=fill,"
           "drawbox=x=320:y=0:w=320:h=ih:color=blue:t=fill,"
           "drawbox=x=320:y=0:w=320:h=24:color=yellow:t=fill,"
           "drawbox=x=320:y=336:w=320:h=24:color=cyan:t=fill",
           "-c:v", "libx264", "-preset", "ultrafast", "-an", source)
    clip = Clip(start=0, end=1, layout="leetcode", camera_mode=camera_mode, captions=captions,
                results_zoom=results_zoom,
                question_title="Design a Parking Reservation System",
                face_region=Region(x=0, y=0, w=0.25, h=0.25) if camera_mode == "required" else None,
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    output = workspace / f"header {camera_mode} {captions}.mp4"
    media.render(source, media.probe(source), clip, [Cue(start=0, end=0.4, text="Actual speech")],
                 output, True, lambda *_: None, threading.Event())
    for at in (0.1, 0.9):
        frame = preview_frame(output, at)
        white = np.all(frame > 220, axis=2)
        assert np.count_nonzero(white[10:86]) > 100
        assert not white[90:100].any()
        yellow = (frame[:, :, 0] > 220) & (frame[:, :, 1] > 220) & (frame[:, :, 2] < 35)
        cyan = (frame[:, :, 0] < 35) & (frame[:, :, 1] > 220) & (frame[:, :, 2] > 220)
        assert np.count_nonzero(yellow) > 100 and np.count_nonzero(cyan) > 100
        assert np.where(yellow)[0].min() >= 102
        assert np.where(cyan)[0].max() < 480
        if captions and at < 0.4:
            assert np.count_nonzero(white[500:580]) > 40
        else:
            assert not white[500:580].any()
    assert "Design a Parking" not in output.with_suffix(".srt").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def results_source(workspace):
    source = workspace / "results animation markers.mp4"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=lime:size=640x360:rate=30:duration=3,"
        "drawbox=x=0:y=0:w=160:h=90:color=red:t=fill,"
        "drawbox=x=0:y=0:w=16:h=90:color=white:t=fill,"
        "drawbox=x=144:y=0:w=16:h=90:color=orange:t=fill,"
        "drawbox=x=320:y=0:w=320:h=ih:color=blue:t=fill,"
        "drawbox=x=320:y=0:w=320:h=24:color=yellow:t=fill,"
        "drawbox=x=320:y=336:w=320:h=24:color=cyan:t=fill,"
        "drawbox=x=320:y=24:w=16:h=312:color=magenta:t=fill,"
        "drawbox=x=624:y=24:w=16:h=312:color=magenta:t=fill",
        "-c:v", "libx264", "-preset", "ultrafast", "-an", source,
    )
    return source


@pytest.mark.parametrize("captions", [True, False])
def test_editor_correction_renders_separately_and_survives_silent_montage(sources, workspace, captions):
    from clipfarm.models import EditorialCorrection
    from clipfarm.montage import render_montage

    source = sources[1]
    note = EditorialCorrection(text="Fixed and sliding windows are different.",
                               sources=["https://learn.microsoft.com/en-us/aspnet/core/performance/rate-limit"])
    clip = Clip(start=0, end=0.9, layout="leetcode", camera_mode="absent",
                content_region=Region(x=0, y=0, w=1, h=1), correction=note,
                question_title="Design a Rate Limiter", captions=captions)
    cues = [Cue(start=0, end=0.9, text="Original speech")]
    for renderer in ("direct", "montage"):
        path = workspace / f"correction-{captions}-{renderer}" / "clip.mp4"
        if renderer == "direct":
            media.render(source, media.probe(source), clip, cues, path, True,
                         lambda *_: None, threading.Event())
        else:
            render_montage(source, media.probe(source), [clip], cues, path, True,
                           lambda *_: None, threading.Event())
        image = preview_frame(path, 0.3)
        cream = (image[:, :, 0] > 185) & (image[:, :, 1] > 175) & (image[:, :, 2] > 150)
        assert cream[432:493].sum() > 100
        assert cream[:90].sum() > 100
        assert cream[510:585].any() == captions
        assert not cream[494:505].any()
        if path.with_suffix(".srt").exists():
            assert "CORRECTION" not in path.with_suffix(".srt").read_text(encoding="utf-8")


def _result_clip(duration, *, results_zoom=True, camera_mode="required"):
    return Clip(start=0, end=duration, layout="leetcode", results_zoom=results_zoom, camera_mode=camera_mode,
                face_region=Region(x=0, y=0, w=0.25, h=0.25) if camera_mode == "required" else None,
                content_region=Region(x=0.5, y=0, w=0.5, h=1))


def _central_blue_widths(rows):
    blue = (rows[:, :, 2] > 190) & (rows[:, :, 0] < 50) & (rows[:, :, 1] < 50)
    middle = rows.shape[1] // 2
    assert blue[:, middle].all()
    assert (~blue[:, :middle]).any(axis=1).all() and (~blue[:, middle:]).any(axis=1).all()
    return np.argmax(~blue[:, :middle][:, ::-1], axis=1) + np.argmax(~blue[:, middle:], axis=1)


@pytest.mark.parametrize("preview", [True, False], ids=["preview", "1080p"])
@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_results_scale_smoothly_and_dim_without_touching_camera_or_subtitles(results_source, workspace, preview, camera_mode):
    width, height = (360, 640) if preview else (1080, 1920)
    source_info = media.probe(results_source)
    output = workspace / f"animated results {width} {camera_mode}" / "result.mp4"
    cue = Cue(start=0, end=3, text="Focus stays readable")
    media.render(results_source, source_info, _result_clip(3, camera_mode=camera_mode), [cue], output, preview,
                 lambda *_: None, threading.Event())
    info = media.probe(output)
    assert (info.width, info.height, info.fps, info.has_audio) == (width, height, 30, False)
    assert info.duration == pytest.approx(3, abs=1 / 30)
    baseline = workspace / f"normal content {width} {camera_mode}" / "result.mp4"
    media.render(results_source, source_info, _result_clip(3, results_zoom=False, camera_mode=camera_mode), [cue],
                 baseline, preview, lambda *_: None, threading.Event())
    assert info.duration == media.probe(baseline).duration
    # Every frame's center scanline detects real scale motion, not a fade or a crop jump.
    pane_y, pane_height = (0.33, 0.41) if camera_mode == "required" else (0.05, 0.69)
    center_y = int(height * (pane_y + pane_height / 2)) // 2 * 2
    rows = np.frombuffer(ffmpeg(
        "-i", output, "-an", "-vf", f"crop=iw:2:0:{center_y}", "-pix_fmt", "rgb24",
        "-f", "rawvideo", "pipe:1",
    ).stdout, dtype=np.uint8).reshape(-1, 2, width, 3)
    widths = _central_blue_widths(rows[:, 0])
    normal_rows = ffmpeg(
        "-i", baseline, "-an", "-vf", f"crop=iw:2:0:{center_y}", "-pix_fmt", "rgb24",
        "-f", "rawvideo", "pipe:1",
    ).stdout
    # The existing direct renderer may round its EOF down one frame; focus adds/removes none.
    assert len(widths) == len(normal_rows) // (2 * width * 3) >= 89
    assert widths[0] < widths[15] < widths[30] < widths[45] < widths[60]
    assert widths[-1] / widths[0] == pytest.approx(1 / 0.68, rel=0.04)
    assert np.min(np.diff(widths)) >= -2
    assert np.max(np.diff(widths)) <= width * 0.025
    assert np.ptp(widths[60:]) <= 2

    frames = np.frombuffer(ffmpeg(
        "-i", output, "-an", "-vf", f"select='eq(n,0)+eq(n,30)+eq(n,60)+eq(n,{len(widths) - 1})'",
        "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ).stdout, dtype=np.uint8).reshape(-1, height, width, 3)
    assert len(frames) == 4
    normal = np.frombuffer(ffmpeg(
        "-i", baseline, "-an", "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ).stdout, dtype=np.uint8).reshape(height, width, 3)
    camera = (slice(int(height * 0.055), int(height * 0.295)),
              slice(int(width * 0.11), int(width * 0.89)))
    reference = normal[camera].astype(float)
    for frame in frames:
        if camera_mode == "required":
            assert np.mean(np.abs(frame[camera].astype(float) - reference)) < 3
            np.testing.assert_allclose(frame[int(height * 0.17), width // 2], (255, 0, 0), atol=12)
        else:
            np.testing.assert_allclose(frame[center_y, width // 2], (0, 0, 255), atol=12)
        # All four colored ROI edges survive throughout the contained zoom.
        band = frame[int(height * pane_y):int(height * 0.74)].astype(int)
        for color in [(255, 255, 0), (0, 255, 255), (255, 0, 255)]:
            assert np.count_nonzero(np.max(np.abs(band - color), axis=2) < 25) > width
        magenta = np.max(np.abs(band - (255, 0, 255)), axis=2) < 25
        assert magenta[:, :width // 2].sum() > width / 2
        assert magenta[:, width // 2:].sum() > width / 2
        subtitles = frame[int(height * 0.78):int(height * 0.90), int(width * 0.1):int(width * 0.9)]
        assert np.count_nonzero(np.min(subtitles, axis=2) > 235) > width / 2
        assert np.count_nonzero(np.max(subtitles, axis=2) < 45) > width
    # A fixed background-only patch smoothly reaches 70% black; color ratios stay intact.
    background = frames[:, int(height * 0.93):int(height * 0.97), int(width * 0.4):int(width * 0.6)]
    brightness = background.mean(axis=(1, 2, 3))
    assert brightness[0] > brightness[1] > brightness[2]
    assert brightness[2] == pytest.approx(brightness[3], abs=2)
    assert brightness[3] / brightness[0] == pytest.approx(0.30, abs=0.04)
    white_masks = [np.min(frame[int(height * 0.78):int(height * 0.90)], axis=2) > 235 for frame in frames]
    assert min(mask.sum() for mask in white_masks) / max(mask.sum() for mask in white_masks) > 0.90


@pytest.mark.parametrize("count", [1, 2, 6])
def test_short_results_reach_final_size_without_added_frames(results_source, workspace, count):
    output = workspace / f"short results {count}" / "result.mp4"
    media.render(results_source, media.probe(results_source), _result_clip(count / 30), [], output, True,
                 lambda *_: None, threading.Event())
    frames = np.frombuffer(ffmpeg(
        "-i", output, "-an", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ).stdout, dtype=np.uint8).reshape(-1, 640, 360, 3)
    assert len(frames) == count
    widths = _central_blue_widths(frames[:, 342])
    assert 202 <= widths[-1] <= 214
    if count > 1:
        assert widths[0] < widths[-1] * 0.75
    if count > 2:
        assert widths[0] < widths[count // 2] < widths[-1]
