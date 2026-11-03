from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import numpy as np
import pytest

from clipfarm import media, montage
from clipfarm.models import Clip, Cue, MediaInfo, Region
from clipfarm.montage import MontageSpan, detect_silences, render_montage


def ffmpeg(*args):
    result = subprocess.run(
        [media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *map(str, args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    return result.stdout


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    return tmp_path_factory.mktemp("montage")


@pytest.fixture(scope="module")
def source(workspace):
    path = workspace / "ordered source with spaces café.mov"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=red:size=320x180:rate=30:duration=3,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=green:t=fill:enable='between(t,1,1.999)',"
        "drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,2)'",
        "-f", "lavfi", "-i",
        "aevalsrc='0.25*sin(2*PI*if(lt(t,1),440,if(lt(t,2),880,1320))*t)':s=48000:d=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-bf", "0", "-c:a", "pcm_s16le", path,
    )
    return path


def test_plan_rejects_empty_overlong_and_subframe_segments():
    info = MediaInfo(duration=1000, width=320, height=180, fps=30)
    for clips, message in [
        ([], "at least one"),
        ([Clip(start=0, end=100), Clip(start=200, end=300)], "180"),
        ([Clip(start=0, end=0.01)], "one 30 fps"),
    ]:
        with pytest.raises(media.MediaError, match=message):
            montage._frame_plan(info, clips)
    assert montage._frame_plan(info, [Clip(start=9, end=9.213)]) == [6]


def test_results_events_join_only_identical_regions_and_use_retained_frame_counts():
    info = MediaInfo(duration=10, width=640, height=360, fps=30)
    clip = Clip(start=0, end=0.213, layout="leetcode", results_zoom=True,
                face_region=Region(x=0, y=0, w=0.25, h=0.25),
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    changed_content = clip.model_copy(update={"content_region": Region(x=0.55, y=0, w=0.45, h=1)})
    changed_camera = clip.model_copy(update={"face_region": Region(x=0.1, y=0, w=0.25, h=0.25)})
    segments = [
        clip, clip.model_copy(update={"start": 2, "end": 2.313, "captions": False}),
        changed_content, changed_content, changed_camera,
        clip.model_copy(update={"results_zoom": False}), clip, Clip(start=0, end=0.1), clip,
    ]
    assert montage._results_events(segments, montage._frame_plan(info, segments)) == {
        0: 15, 2: 12, 4: 6, 6: 6, 8: 6,
    }
    assert montage._results_events(segments, montage._frame_plan(info, segments), split_on_roi=False) == {
        0: 33, 6: 6, 8: 6,
    }


def test_span_requires_ordered_positive_intervals():
    with pytest.raises(ValueError):
        MontageSpan(index=0, source_start=1, source_end=0.5, output_start=0, output_end=1)


def _tone(samples, begin, end):
    window = samples[round(begin * 48000):round(end * 48000)]
    bins = np.abs(np.fft.rfft(window * np.hanning(len(window))))
    return np.fft.rfftfreq(len(window), 1 / 48000)[np.argmax(bins)]


def test_twelve_reordered_cuts_keep_pixels_audio_and_sidecars_aligned(source, workspace):
    starts = [2.1, 0.2, 1.1] * 4
    clips = [Clip(start=start, end=start + 0.213, layout="manual") for start in starts]
    cues = [Cue(start=0, end=1, text="Red words"), Cue(start=1, end=2, text="Green words"),
            Cue(start=2, end=3, text="Blue words")]
    output = workspace / "twelve cuts café" / "final reel.mp4"
    progress = []
    spans = render_montage(source, media.probe(source), clips, cues, output, True,
                           lambda value, _: progress.append(value), threading.Event())
    assert len(spans) == 12 and progress[-1] == 1
    assert all(a <= b for a, b in zip(progress, progress[1:]))
    info = media.probe(output)
    assert (info.width, info.height, info.fps, info.video_codec) == (360, 640, 30, "h264")
    assert info.duration == pytest.approx(2.4, abs=1 / 30)
    for index, span in enumerate(spans):
        assert span.index == index
        assert span.source_start == starts[index]
        assert span.source_end == pytest.approx(starts[index] + 0.2)
        assert span.output_start == pytest.approx(index * 0.2)
        assert span.output_end == pytest.approx((index + 1) * 0.2)
        pixel = np.frombuffer(ffmpeg(
            "-ss", span.output_start + 0.1, "-protocol_whitelist", "file,pipe", "-i", output,
            "-map", "0:v:0", "-an", "-frames:v", "1", "-vf", "crop=2:2:iw/2:ih/2",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
        ), dtype=np.uint8).reshape(-1, 3).mean(axis=0)
        expected = [(0, 0, 255), (255, 0, 0), (0, 128, 0)][index % 3]
        assert np.max(np.abs(pixel - expected)) < 15
    pcm = np.frombuffer(ffmpeg(
        "-protocol_whitelist", "file,pipe", "-i", output, "-map", "0:a:0",
        "-ac", "1", "-ar", "48000", "-f", "f32le", "pipe:1",
    ), dtype="<f4")
    assert abs(len(pcm) / 48000 - spans[-1].output_end) <= 1 / 30
    frequencies = [1320, 440, 880] * 4
    for index, span in enumerate(spans):
        assert _tone(pcm, span.output_start + 0.04, span.output_end - 0.04) == pytest.approx(frequencies[index], abs=15)
        if index:
            boundary = span.output_start
            assert _tone(pcm, boundary - 0.032, boundary - 0.008) == pytest.approx(frequencies[index - 1], abs=30)
            assert _tone(pcm, boundary + 0.008, boundary + 0.032) == pytest.approx(frequencies[index], abs=30)
    srt = output.with_suffix(".srt").read_text(encoding="utf-8")
    assert srt.count(" --> ") == 12
    assert "00:00:02,200 --> 00:00:02,400" in srt
    assert srt.index("Blue words") < srt.index("Red words") < srt.index("Green words")
    transcript = output.with_suffix(".transcript.txt").read_text(encoding="utf-8")
    assert transcript.index("Blue words") < transcript.index("Red words") < transcript.index("Green words")
    mapping = json.loads(output.with_suffix(".source-map.json").read_text())
    assert mapping["segments"] == [span.model_dump() for span in spans]
    assert mapping["duration"] == 2.4 and mapping["fps"] == 30
    assert sorted(path.suffix for path in output.parent.iterdir()) == [".json", ".mp4", ".srt", ".txt"]
    binary = output.read_bytes()
    assert binary.index(b"moov") < binary.index(b"mdat")


def test_full_resolution_silent_montage_and_no_cues(workspace):
    source = workspace / "no audio.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=blue:size=320x180:rate=30:duration=1",
           "-c:v", "libx264", "-preset", "ultrafast", "-an", source)
    output = workspace / "silent reel" / "result.mp4"
    spans = render_montage(
        source, media.probe(source),
        [Clip(start=0.2, end=0.4, layout="fit"), Clip(start=0.6, end=0.8, layout="manual")],
        [], output, False, lambda *_: None, threading.Event(),
    )
    info = media.probe(output)
    assert (info.width, info.height) == (1080, 1920) and not info.has_audio
    assert spans[-1].output_end == pytest.approx(0.4)
    assert output.with_suffix(".srt").read_text() == ""
    assert "No transcript cues" in output.with_suffix(".transcript.txt").read_text()


def test_montage_keeps_original_long_cue_burst_phase(source, workspace):
    cue = Cue(start=0, end=3, text=" ".join(f"term{i:02}" for i in range(28)))
    begin, end, text = media._caption_bursts(cue, 24)[2]
    clip = Clip(start=begin + 0.01, end=end - 0.01, layout="fit", captions=False)
    output = workspace / "phase" / "result.mp4"
    render_montage(source, media.probe(source), [clip], [cue], output, True,
                   lambda *_: None, threading.Event())
    transcript = output.with_suffix(".transcript.txt").read_text()
    assert text in transcript and "term00" not in transcript


def test_cancelled_and_failed_montage_leave_no_partial_artifacts(source, workspace):
    info = media.probe(source)
    output = workspace / "cancelled" / "result.mp4"
    event = threading.Event()

    def progress(value, _):
        if value > 0.3:
            event.set()

    with pytest.raises(media.CancelledError):
        render_montage(source, info, [Clip(start=0, end=1, layout="fit")] * 3, [],
                       output, True, progress, event)
    assert not list(output.parent.iterdir())
    corrupt = workspace / "corrupt.mp4"
    corrupt.write_bytes(b"broken")
    with pytest.raises(media.MediaError, match="FFmpeg"):
        render_montage(corrupt, info, [Clip(start=0, end=0.5, layout="fit")], [],
                       output, True, lambda *_: None, threading.Event())
    assert not list(output.parent.iterdir())


def test_atomic_publish_restores_existing_sidecars_on_failure(workspace, monkeypatch):
    root = workspace / "publication"
    root.mkdir()
    stage = root / "staged"
    stage.mkdir()
    old = root / "result.srt"
    old.write_text("previous subtitles")
    output = root / "result.mp4"
    output.write_bytes(b"previous video")
    new_subtitles, new_video = stage / "new.srt", stage / "new.mp4"
    new_subtitles.write_text("new subtitles")
    new_video.write_bytes(b"new video")
    replace = montage.os.replace

    def fail_video(source, destination):
        if destination == output:
            raise OSError("simulated publication failure")
        replace(source, destination)

    monkeypatch.setattr(montage.os, "replace", fail_video)
    with pytest.raises(OSError):
        montage._publish([(new_subtitles, old), (new_video, output)], threading.Event())
    assert old.read_text() == "previous subtitles"
    assert output.read_bytes() == b"previous video"


def test_silence_detection_absolute_times_and_clamped_edges(workspace):
    source = workspace / "tone with silence.mov"
    ffmpeg(
        "-f", "lavfi", "-i", "color=red:size=160x90:rate=30:duration=3",
        "-f", "lavfi", "-i",
        "aevalsrc='if(lt(t,0.6)+between(t,1,1.8)+gte(t,2.4),0,0.3*sin(2*PI*440*t))':s=48000:d=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "pcm_s16le", source,
    )
    silence = detect_silences(source, 0.2, 2.8, threading.Event(), min_duration=0.3)
    assert len(silence) == 3
    for actual, expected in zip(silence, [(0.2, 0.6), (1, 1.8), (2.4, 2.8)]):
        assert actual == pytest.approx(expected, abs=0.002)


def test_silence_no_audio_is_explicit_and_decode_errors_raise(workspace, caplog):
    source = workspace / "silent source.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=black:size=160x90:rate=30:duration=1",
           "-c:v", "libx264", "-preset", "ultrafast", "-an", source)
    assert detect_silences(source, 0, 1, threading.Event()) == []
    assert "no audio" in caplog.text
    corrupt = workspace / "bad audio.mp4"
    corrupt.write_bytes(b"broken")
    with pytest.raises(media.MediaError):
        detect_silences(corrupt, 0, 1, threading.Event())
    event = threading.Event()
    event.set()
    with pytest.raises(media.CancelledError):
        detect_silences(source, 0, 1, event)
    with pytest.raises(media.MediaError):
        detect_silences(source, 0, 1, threading.Event(), threshold_db=float("nan"))


@pytest.mark.parametrize("part_duration", [0.4, 0.1], ids=["held-dimmer", "unfinished-dimmer"])
@pytest.mark.parametrize("camera_mode", ["required", "absent"])
def test_results_animation_continues_across_cuts_and_restarts_for_new_roi_or_normal_span(
    workspace, monkeypatch, part_duration, camera_mode,
):
    source = workspace / "results montage source.mov"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=lime:size=640x360:rate=30:duration=3,"
        "drawbox=x=0:y=0:w=160:h=90:color=red:t=fill,"
        "drawbox=x=320:y=0:w=320:h=ih:color=blue:t=fill,"
        "drawbox=x=320:y=0:w=16:h=ih:color=magenta:t=fill,"
        "drawbox=x=624:y=0:w=16:h=ih:color=magenta:t=fill",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast", "-bf", "0", "-c:a", "pcm_s16le", source,
    )
    base = Clip(start=0, end=0.413, layout="leetcode", results_zoom=True, camera_mode=camera_mode,
                face_region=Region(x=0, y=0, w=0.25, h=0.25) if camera_mode == "required" else None,
                content_region=Region(x=0.5, y=0, w=0.5, h=1))
    segments = [base.model_copy(update={"start": start, "end": start + part_duration + 0.013})
                for start in [0, 0.5, 1, 1.5, 2, 0.1]]
    segments += [
        base.model_copy(update={"end": 0.213, "content_region": Region(x=0.55, y=0, w=0.45, h=1)}),
        base.model_copy(update={"start": 1, "end": 1.213,
                                "content_region": Region(x=0.55, y=0, w=0.45, h=1)}),
        base.model_copy(update={"end": 0.213, "results_zoom": False}),
        base.model_copy(update={"end": 0.313}),
        base.model_copy(update={"start": 1, "end": 1.313}),
    ]
    timings = []
    render_part = montage._render_part

    def record_timing(*args, **kwargs):
        timings.append((kwargs["results_elapsed"], kwargs["results_duration"],
                        kwargs["results_dim_elapsed"], kwargs["results_dim_duration"]))
        return render_part(*args, **kwargs)

    monkeypatch.setattr(montage, "_render_part", record_timing)
    output = workspace / "results montage" / "result.mp4"
    spans = render_montage(source, media.probe(source), segments,
                           [Cue(start=0, end=3, text="Always readable")], output, True,
                           lambda *_: None, threading.Event())
    group_duration = part_duration * 6
    dim_duration = group_duration + 0.4
    expected = [(n * part_duration, group_duration, n * part_duration, dim_duration) for n in range(6)] + [
        (0, 0.4, group_duration, dim_duration), (0.2, 0.4, group_duration + 0.2, dim_duration),
        (0, None, 0, None), (0, 0.6, 0, 0.6), (0.3, 0.6, 0.3, 0.6),
    ]
    for actual, wanted in zip(timings, expected):
        for value, target in zip(actual, wanted):
            assert value == (None if target is None else pytest.approx(target))
    assert len(timings) == len(expected)
    assert spans[-1].output_end == pytest.approx(group_duration + 1.2)
    part_frames = round(part_duration * 30)
    group_frames = part_frames * 6
    reset = group_frames + 18
    center_y = 342 if camera_mode == "required" else 252
    rows = np.frombuffer(ffmpeg(
        "-i", output, "-an", "-vf", f"crop=iw:2:0:{center_y}", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ), dtype=np.uint8).reshape(-1, 2, 360, 3)
    blue = (rows[:, 0, :, 2] > 190) & (rows[:, 0, :, 0] < 50) & (rows[:, 0, :, 1] < 50)
    assert blue[:, 180].all()
    widths = np.argmax(~blue[:, :180][:, ::-1], axis=1) + np.argmax(~blue[:, 180:], axis=1)
    assert len(widths) == group_frames + 36
    assert np.min(np.diff(widths[np.arange(6) * part_frames])) > 0
    assert np.min(np.diff(widths[:group_frames])) >= -2
    assert np.ptp(widths[5 * part_frames:group_frames]) <= 2
    assert widths[group_frames] < widths[group_frames + 6] < widths[group_frames + 11]
    assert widths[reset] < widths[reset + 9] < widths[-1]
    assert widths[0] == pytest.approx(widths[reset], abs=2)
    assert np.ptp(widths[group_frames + 12:reset]) <= 2  # Normal content stays static.
    # Average a background-only patch so isolated codec quantization is not a flash.
    background = np.frombuffer(ffmpeg(
        "-i", output, "-an", "-vf", "crop=72:24:144:596", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ), dtype=np.uint8).reshape(-1, 24, 72, 3).mean(axis=(1, 2, 3))
    assert len(background) == group_frames + 36
    assert background[0] > background[2 * part_frames] > background[4 * part_frames] > background[5 * part_frames]
    assert np.max(np.diff(background[:group_frames + 12])) <= 2
    assert background[group_frames] <= background[group_frames - 1] + 2
    if part_duration == 0.4:
        assert np.ptp(background[group_frames - 1:group_frames + 12]) <= 2
    else:
        assert background[group_frames] > background[group_frames + 3] > background[group_frames + 11]
    assert background[reset] > background[reset + 9] > background[-1]
    assert background[0] == pytest.approx(background[reset], abs=2)
    assert np.ptp(background[group_frames + 12:reset]) <= 2
    info = media.probe(output)
    assert (info.width, info.height, info.fps, info.has_audio) == (360, 640, 30, True)
    pcm = np.frombuffer(ffmpeg("-i", output, "-map", "0:a:0", "-ac", "1", "-ar", "48000",
                               "-f", "f32le", "pipe:1"), dtype="<f4")
    assert abs(len(pcm) / 48000 - spans[-1].output_end) <= 1 / 30
    for span in spans:
        assert _tone(pcm, span.output_start + 0.04, span.output_end - 0.04) == pytest.approx(440, abs=15)
