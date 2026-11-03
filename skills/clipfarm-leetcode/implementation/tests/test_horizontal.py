from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import threading
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from PIL import Image

from clipfarm import horizontal, media, montage
from clipfarm.horizontal_models import HorizontalRenderSegment, SubtitleRegion
from clipfarm.models import Cue, MediaInfo


def ffmpeg(*arguments):
    result = subprocess.run(
        [media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
         *map(str, arguments)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    return result.stdout


@pytest.fixture(scope="module")
def workspace():
    path = Path.cwd() / ".clipfarm" / f"horizontal-tests-{uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def segment(start=0, end=6, *, captions=False, region=None):
    return HorizontalRenderSegment(
        start=start, end=end, captions=captions,
        subtitle_region=region or SubtitleRegion(x=0.05, y=0.72, w=0.9, h=0.25),
    )


@pytest.fixture(scope="module")
def source(workspace):
    path = workspace / "source with spaces café.mov"
    ffmpeg(
        "-f", "lavfi", "-i",
        "color=blue:size=320x180:rate=30:duration=10,"
        "drawbox=x=0:y=0:w=16:h=ih:color=lime:t=fill,"
        "drawbox=x=304:y=0:w=16:h=ih:color=magenta:t=fill,"
        "drawbox=x=16:y=0:w=288:h=12:color=white:t=fill,"
        "drawbox=x=16:y=168:w=288:h=12:color=yellow:t=fill,"
        "drawbox=x=80:y=50:w=20:h=20:color=white:t=fill:enable='gte(t,3)'",
        "-f", "lavfi", "-i",
        "aevalsrc='0.25*sin(2*PI*if(lt(t,3),440,if(lt(t,6),880,1320))*t)':s=48000:d=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-bf", "0", "-c:a", "pcm_s16le", path,
    )
    return path


@pytest.fixture(scope="module")
def cover(workspace):
    path = workspace / "cover with spaces café.jpg"
    Image.new("RGB", (320, 180), (255, 0, 0)).save(path, quality=100, subsampling=0)
    return path


def render(source, cover, output, segments=None, cues=None, **kwargs):
    return horizontal.render_horizontal(
        source, media.probe(source), segments or [segment()], cues or [], output, cover,
        kwargs.pop("progress", lambda *_: None), kwargs.pop("cancel", threading.Event()), **kwargs,
    )


def frames(path):
    info = media.probe(path)
    return np.frombuffer(ffmpeg(
        "-i", path, "-map", "0:v:0", "-an", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1",
    ), dtype=np.uint8).reshape(-1, info.height, info.width, 3)


def audio(path):
    return np.frombuffer(ffmpeg(
        "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", "48000", "-f", "f32le", "pipe:1",
    ), dtype="<f4")


def tone(samples, begin, end):
    samples = samples[round(begin * 48000):round(end * 48000)]
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return np.fft.rfftfreq(len(samples), 1 / 48000)[np.argmax(spectrum)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("segments,hold,message", [
    ([], 1, "at least one"),
    ([segment(0, 3.999)], 1, "at least 4 seconds"),
    ([segment(0, 5), segment(4.9, 6)], 1, "chronological"),
    ([segment(5, 9), segment(1, 2)], 1, "chronological"),
    ([segment(0, 0.02), segment(1, 6)], 1, "one 30 fps"),
    ([segment(0, 10.001)], 1, "beyond the source"),
    ([segment()], -1, "frame grid"),
    ([segment()], 10.1, "frame grid"),
    ([segment()], 1.01, "frame grid"),
    ([segment()], float("nan"), "frame grid"),
])
def test_plan_rejects_bad_boundaries(segments, hold, message):
    with pytest.raises(media.MediaError, match=message):
        horizontal._frame_plan(MediaInfo(width=320, height=180, fps=30, duration=10), segments, hold)


def test_plan_native_dimensions_no_long_solve_limit():
    info = MediaInfo(width=1920, height=1080, fps=60, duration=10_000)
    assert horizontal._frame_plan(info, [segment(0, 5000.013)], 1 / 30) == ([150000], 1)
    for width, height in [(180, 320), (320, 320), (321, 180), (320, 179)]:
        with pytest.raises(media.MediaError, match="landscape"):
            horizontal._frame_plan(info.model_copy(update={"width": width, "height": height}), [segment()], 1)


def test_caption_geometry_literal_escaping_and_insufficient_space():
    info = MediaInfo(width=1920, height=1080, fps=30, duration=10)
    region = SubtitleRegion(x=0.2, y=0.78, w=0.6, h=0.2)
    text = r"café {\pos(0,0)} C:\new\path \N <literal>"
    layout = horizontal._caption_layout(info, region, text)
    left, top, right, bottom = layout.rectangle
    assert left >= region.x * info.width and right <= (region.x + region.w) * info.width
    assert layout.y - layout.padding >= top
    assert layout.y + len(layout.lines) * layout.line_height + layout.padding <= bottom
    assert all(horizontal.thumbnails._width(line, layout.font) + 2 * layout.padding <= right - left
               for line in layout.lines)
    cue = Cue(start=0.4, end=1.5, text=text)
    script = horizontal._ass([cue], info, region)
    assert "PlayResX: 1920\nPlayResY: 1080" in script
    assert r"{\pos(0,0)}" not in script and "\\\u2060N" in script
    assert "café" in script and r"\clip" not in script and "0:00:00.40" in script
    with pytest.raises(media.MediaError, match="readable size"):
        horizontal._caption_layout(
            info, SubtitleRegion(x=0, y=0.9, w=0.3, h=0.055), " ".join(["unabridged"] * 80),
        )


def test_source_bursts_precede_cut_and_region_changes():
    info = MediaInfo(width=320, height=180, fps=30, duration=20)
    cue = Cue(id="long", start=0, end=20, text=" ".join(f"term{i:02}" for i in range(40)))
    bursts = horizontal._source_bursts([cue])
    selected = bursts[3]
    clipped = horizontal._local_cues(
        bursts, selected.start + 0.01, selected.end - selected.start - 0.02, info,
        segment(0, 20, captions=True),
    )
    assert len(clipped) == 1 and clipped[0].id == selected.id
    assert " ".join(clipped[0].text.split()) == " ".join(selected.text.split())
    assert "term00" not in clipped[0].text


def test_display_wrap_preserves_the_canonical_identifier():
    info = MediaInfo(width=640, height=360, fps=30, duration=10)
    region = SubtitleRegion(x=0.1, y=0.7, w=0.3, h=0.3)
    text = "IdentifierWithoutSpaces" * 2
    layout = horizontal._caption_layout(info, region, text)
    assert len(layout.lines) > 1
    cue = Cue(start=0, end=2, text=text)
    script = horizontal._ass([cue], info, region)
    rendered = [line.partition(")}")[2] for line in script.splitlines() if line.startswith("Dialogue:")]
    assert rendered == [media._ass_escape(line) for line in layout.lines]
    assert "".join(rendered) == cue.text == text


@pytest.mark.parametrize("text", [
    "longestIncreasingSubsequenceLength",
    "Before " + "IdentifierWithoutSpaces" * 8 + " after",
    "Repeat Repeat café  \t MW@%\n" + "anotherIdentifierWithNoWordBoundaries" * 3,
    " ".join(f"term{i:02}" for i in range(40)),
])
def test_source_bursts_keep_original_tokens_without_artificial_spaces(text):
    cue = Cue(id="canonical", start=3, end=23, text=text)
    original = cue.model_dump()
    bursts = horizontal._source_bursts([cue])
    assert cue.model_dump() == original
    assert " ".join(burst.text for burst in bursts) == " ".join(text.split())
    assert bursts[0].start == cue.start and bursts[-1].end == cue.end
    assert all(a.end == b.start for a, b in zip(bursts, bursts[1:]))
    if text.startswith("term"):
        expected = media._caption_bursts(cue, width=24)
        assert [(burst.start, burst.end) for burst in bursts] == [(start, end) for start, end, _ in expected]


def test_identifier_remains_whole_when_the_selected_rectangle_is_wide():
    info = MediaInfo(width=320, height=180, fps=30, duration=10)
    text = "longestIncreasingSubsequenceLength"
    cue = Cue(start=0, end=8, text=text)
    assert "\n" in media._caption_bursts(cue, width=24)[0][2]
    bursts = horizontal._source_bursts([cue])
    local = horizontal._local_cues(bursts, 0, 4, info, segment(captions=True))
    assert len(local) == 1 and local[0].text == text
    region = segment().subtitle_region
    assert horizontal._caption_layout(info, region, local[0].text).lines == (text,)
    assert text in horizontal._ass(local, info, region)


def test_caption_overlap_fails_instead_of_overprinting_empty_region():
    info = MediaInfo(width=320, height=180, fps=30, duration=10)
    bursts = horizontal._source_bursts([
        Cue(start=0, end=2, text="first"), Cue(start=1, end=3, text="second"),
    ])
    with pytest.raises(media.MediaError, match="Overlapping"):
        horizontal._local_cues(bursts, 0, 4, info, segment(captions=True))


def test_exact_intro_dissolve_native_framing_audio_and_mapping(source, cover, workspace, monkeypatch):
    before = {path: digest(path) for path in (source, cover)}
    output = workspace / "intro" / "full solve.mp4"
    edits = [segment(0.2, 2.213), segment(3.1, 5.113), segment(6.2, 8.213)]
    progress = []
    commands = []
    run = media._run

    def record(command, *args, **kwargs):
        commands.append(command)
        return run(command, *args, **kwargs)

    monkeypatch.setattr(media, "_run", record)
    spans = render(source, cover, output, edits, progress=lambda value, _: progress.append(value))
    assert sum("aac" in command for command in commands) == 1
    assert sum("pcm_s16le" in command for command in commands) == 4
    assert not any("afade" in argument for command in commands for argument in command)
    assert progress[-1] == 1 and all(a <= b for a, b in zip(progress, progress[1:]))
    output_info = media.probe(output)
    assert (output_info.width, output_info.height, output_info.fps, output_info.video_codec) == (320, 180, 30, "h264")
    assert output_info.duration == pytest.approx(7, abs=1 / 30)
    video = frames(output)
    assert len(video) == 210
    original_cover = np.asarray(Image.open(cover).convert("RGB")).astype(float)
    assert np.abs(video[:30].astype(float) - original_cover).mean() < 3
    assert np.abs(video[30].astype(float) - original_cover).mean() < 3
    # Alpha 1 -> 0 spans exactly 120 body frames, including a source jump at t=3.
    for index in [30, 31, 60, 89, 90, 120, 149, 150, 180, 209]:
        alpha = max(0, 1 - (index / 30 - 1) / 4)
        expected = np.array([254 * alpha, 0, 254 * (1 - alpha)])
        pixel = video[index, 90:110, 160:180].mean(axis=(0, 1))
        assert np.max(np.abs(pixel - expected)) < 7, (index, pixel, expected)
    # Real video changes underneath the cover; this is not a still-to-still dissolve.
    assert video[60, 60, 90, 0] < video[100, 60, 90, 0]
    frame = video[180]
    for y, x, expected in [
        (90, 5, (0, 255, 0)), (90, 314, (255, 0, 255)),
        (5, 160, (255, 255, 255)), (174, 160, (255, 255, 0)),
    ]:
        assert np.max(np.abs(frame[y, x].astype(float) - expected)) < 10
    pcm = audio(output)
    assert abs(len(pcm) / 48000 - 7) < 1 / 30
    assert np.max(np.abs(pcm[:round(0.95 * 48000)])) < 0.001
    assert np.sqrt(np.mean(pcm[round(1.01 * 48000):round(1.06 * 48000)] ** 2)) > 0.1
    for index, span in enumerate(spans):
        assert span.source_start == edits[index].start
        assert span.source_end == pytest.approx(edits[index].start + 2)
        assert (span.output_start, span.output_end) == (1 + index * 2, 3 + index * 2)
        assert tone(pcm, span.output_start + 0.04, span.output_start + 0.3) == pytest.approx(
            [440, 880, 1320][index], abs=10,
        )
        if index:
            assert tone(pcm, span.output_start - 0.035, span.output_start - 0.005) == pytest.approx(
                [440, 880][index - 1], abs=35,
            )
            assert tone(pcm, span.output_start + 0.005, span.output_start + 0.035) == pytest.approx(
                [880, 1320][index - 1], abs=35,
            )
    mapping = json.loads(output.with_suffix(".source-map.json").read_text())
    assert mapping["version"] == 2 and mapping["duration"] == 7 and mapping["mode"] == "horizontal"
    assert mapping["segments"] == [span.model_dump() for span in spans]
    intro = mapping["synthetic_intro"]
    assert (intro["output_start"], intro["output_end"], intro["hold_frames"]) == (0, 1, 30)
    assert (intro["fade_start"], intro["fade_end"], intro["fade_seconds"]) == (1, 5, 4)
    assert (intro["source_video_start"], intro["source_audio_start"], intro["first_source_time"]) == (1, 1, 0.2)
    assert intro["thumbnail_sha256"] == digest(cover) and intro["audio_during_hold"] == "silence"
    assert {path: digest(path) for path in before} == before
    assert sorted(path.suffix for path in output.parent.iterdir()) == [".json", ".mp4", ".srt", ".txt"]
    content = output.read_bytes()
    assert content.index(b"moov") < content.index(b"mdat")


def test_captions_above_cover_dynamic_regions_srt_and_offsets(source, cover, workspace):
    left = SubtitleRegion(x=0.02, y=0.7, w=0.46, h=0.25)
    right = SubtitleRegion(x=0.52, y=0.7, w=0.46, h=0.25)
    edits = [segment(0, 2, captions=True, region=left), segment(3, 6, captions=True, region=right)]
    cues = [Cue(start=0, end=2, text="LEFT café"), Cue(start=3, end=5, text=r"RIGHT \N {x}")]
    output = workspace / "captions" / "full.mp4"
    spans = render(source, cover, output, edits, cues)
    video = frames(output)
    assert np.abs(video[29].astype(float) - np.asarray(Image.open(cover))).mean() < 3
    # White caption ink exists even on the first fully opaque body/cover frame.
    first = video[30]
    mask = (first[:, :, :3].min(axis=2) > 150)
    ys, xs = np.where(mask)
    assert len(xs) > 10 and xs.min() >= 320 * left.x and xs.max() < 320 * (left.x + left.w)
    assert ys.min() >= 180 * left.y and ys.max() < 180 * (left.y + left.h)
    changed = np.max(np.abs(first.astype(float) - np.asarray(Image.open(cover))), axis=2) > 40
    ys, xs = np.where(changed)
    assert xs.min() >= 320 * left.x and xs.max() < 320 * (left.x + left.w)
    assert ys.min() >= 180 * left.y and ys.max() < 180 * (left.y + left.h)
    second = video[96]
    mask = (second[:, :, :3].min(axis=2) > 180)
    mask[:120] = False
    ys, xs = np.where(mask)
    assert len(xs) > 10 and xs.min() >= 320 * right.x and xs.max() < 320 * (right.x + right.w)
    assert ys.min() >= 180 * right.y and ys.max() < 180 * (right.y + right.h)
    srt = output.with_suffix(".srt").read_text(encoding="utf-8")
    assert "00:00:01,000 --> 00:00:03,000" in srt and "00:00:03,000 --> 00:00:05,000" in srt
    assert "LEFT café" in srt and r"RIGHT \N {x}" in srt
    assert r"RIGHT \N {x}" in output.with_suffix(".transcript.txt").read_text(encoding="utf-8")
    mapping = json.loads(output.with_suffix(".source-map.json").read_text())
    assert [item["region"] for item in mapping["subtitle_regions"]] == [left.model_dump(), right.model_dump()]
    assert mapping["subtitle_regions"][1]["output_start"] == spans[1].output_start


@pytest.mark.parametrize("text", [
    "The same spoken phrase crosses this cut",
    "longestIncreasingSubsequenceLength",
])
def test_canonical_cue_crossing_different_rectangles_is_exported_once(
    source, cover, workspace, monkeypatch, text,
):
    wide = SubtitleRegion(x=0.03, y=0.72, w=0.92, h=0.25)
    narrow = SubtitleRegion(x=0.6, y=0.68, w=0.35, h=0.3)
    edits = [segment(0, 4, captions=True, region=wide), segment(4, 8, captions=True, region=narrow)]
    cue = Cue(id="continuous", start=0, end=8, text=text)
    output = workspace / f"canonical-{uuid4().hex}" / "full.mp4"
    scripts = []
    ass = horizontal._ass

    def record(cues, info, region):
        script = ass(cues, info, region)
        scripts.append((cues, script))
        return script

    monkeypatch.setattr(horizontal, "_ass", record)
    spans = render(source, cover, output, edits, [cue])
    assert [(span.output_start, span.output_end) for span in spans] == [(1, 5), (5, 9)]
    assert len(scripts) == 2
    assert [cues[0].text for cues, _ in scripts] == [text, text]
    assert scripts[0][1].count("Dialogue:") == 1
    assert scripts[1][1].count("Dialogue:") > 1
    for _, script in scripts:
        lines = [line.partition(")}")[2] for line in script.splitlines() if line.startswith("Dialogue:")]
        assert "".join(lines).replace(" ", "") == text.replace(" ", "")
    srt = output.with_suffix(".srt").read_text(encoding="utf-8")
    transcript = output.with_suffix(".transcript.txt").read_text(encoding="utf-8")
    assert srt.count(" --> ") == transcript.count(" --> ") == 1
    assert srt.count(text) == transcript.count(text) == 1
    assert "00:00:01,000 --> 00:00:09,000" in srt
    assert "00:00:01,000 --> 00:00:09,000" in transcript


def test_over_180_seconds_silent_source_zero_hold_and_bounded_parts(workspace, monkeypatch):
    source = workspace / "long silent.mp4"
    cover = workspace / "tiny cover.jpg"
    output = workspace / "long silent output" / "full.mp4"
    Image.new("RGB", (32, 18), "red").save(cover, quality=100)
    ffmpeg("-f", "lavfi", "-i", "color=blue:size=32x18:rate=30:duration=181.1",
           "-c:v", "libx264", "-preset", "ultrafast", "-bf", "0", "-an", source)
    measured_parts = []
    measure = montage._measure

    def record(path, duration, cancel):
        timing = measure(path, duration, cancel)
        if path.suffix == ".mov":
            measured_parts.append(timing.frames)
            assert timing.audio_start is None
        return timing

    monkeypatch.setattr(montage, "_measure", record)
    spans = render(source, cover, output, [segment(0, 181.013)], intro_hold=0)
    assert measured_parts == [1800, 1800, 1800, 30]
    info = media.probe(output)
    assert (info.width, info.height, info.has_audio) == (32, 18, False)
    assert info.duration == pytest.approx(181, abs=1 / 30)
    assert spans[0].output_start == 0 and spans[0].output_end == 181
    mapping = json.loads(output.with_suffix(".source-map.json").read_text())
    assert mapping["synthetic_intro"]["source_audio_start"] is None
    assert mapping["synthetic_intro"]["hold_frames"] == 0 and mapping["synthetic_intro"]["fade_end"] == 4
    assert output.with_suffix(".srt").read_text() == ""
    assert "No transcript cues" in output.with_suffix(".transcript.txt").read_text()


def test_normalized_sample_aspect_ratio_is_preserved(workspace):
    source = workspace / "anamorphic.mov"
    cover = workspace / "anamorphic.jpg"
    output = workspace / "normalized output" / "full.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=4",
           "-vf", "setsar=2", "-c:v", "libx264", "-preset", "ultrafast", "-an", source)
    info = media.probe(source)
    assert (info.width, info.height) == (320, 90)
    Image.new("RGB", (320, 90), "red").save(cover)
    render(source, cover, output, [segment(0, 4)], intro_hold=1 / 30)
    assert (media.probe(output).width, media.probe(output).height) == (320, 90)
    assert len(frames(output)) == 121


@pytest.mark.parametrize("hold", [0, 1 / 30, 10])
def test_configurable_hold_has_exact_frames_and_unfaded_audio_onset(workspace, hold):
    root = workspace / f"hold-{round(hold * 30)}"
    root.mkdir()
    source, cover, output = root / "source.mov", root / "cover.jpg", root / "full.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=blue:size=32x18:rate=30:duration=4.1",
           "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=4.1",
           "-c:v", "libx264", "-preset", "ultrafast", "-bf", "0", "-c:a", "pcm_s16le", source)
    Image.new("RGB", (32, 18), "red").save(cover, quality=100)
    spans = render(source, cover, output, [segment(0, 4.1)], intro_hold=hold)
    assert spans[0].output_start == hold
    video = frames(output)
    assert len(video) == 123 + round(hold * 30)
    assert np.max(np.abs(video[0, 8, 16].astype(float) - (254, 0, 0))) < 4
    assert np.max(np.abs(video[-1, 8, 16].astype(float) - (0, 0, 254))) < 4
    pcm = audio(output)
    if hold >= 1:
        assert np.max(np.abs(pcm[:round((hold - 0.05) * 48000)])) < 0.001
    begin, end = round((hold + 0.01) * 48000), round((hold + 0.1) * 48000)
    assert np.sqrt(np.mean(pcm[begin:end] ** 2)) > 0.06
    assert tone(pcm, hold + 0.01, hold + 0.1) == pytest.approx(880, abs=12)


def test_bounded_parts_share_one_burst_and_do_not_restart_the_fade(source, cover, workspace, monkeypatch):
    monkeypatch.setattr(horizontal, "_PART_FRAMES", 45)
    output = workspace / "internal boundaries" / "full.mp4"
    cue = Cue(start=0, end=6, text="Continuous caption")
    spans = render(source, cover, output, [segment(captions=True)], [cue], intro_hold=0)
    assert len(spans) == 1 and spans[0].output_end == 6
    srt = output.with_suffix(".srt").read_text()
    assert srt.count(" --> ") == 1 and srt.count("Continuous caption") == 1
    video = frames(output)
    for index in [44, 45, 89, 90, 119, 120, 135]:
        alpha = max(0, 1 - index / 120)
        expected = np.array([254 * alpha, 0, 254 * (1 - alpha)])
        assert np.max(np.abs(video[index, 90, 160].astype(float) - expected)) < 7
    pcm = audio(output)
    for boundary in [1.5, 3, 4.5]:
        window = pcm[round((boundary - 0.02) * 48000):round((boundary + 0.02) * 48000)]
        assert np.sqrt(np.mean(window ** 2)) > 0.1


def test_conflicting_cover_source_paths_and_bad_cover_are_rejected(source, cover, workspace):
    info = media.probe(source)
    before = digest(source), digest(cover)
    for output, image in [(source, cover), (workspace / "valid.mp4", source), (cover, cover)]:
        with pytest.raises(media.MediaError):
            horizontal.render_horizontal(source, info, [segment()], [], output, image,
                                         lambda *_: None, threading.Event())
    bad_cover = workspace / "wrong size.jpg"
    Image.new("RGB", (160, 90)).save(bad_cover)
    with pytest.raises(media.MediaError, match="native video dimensions"):
        render(source, bad_cover, workspace / "bad cover output" / "full.mp4")
    assert before == (digest(source), digest(cover))
    assert not (workspace / "bad cover output").exists()


def test_cancel_failure_and_publish_rollback_preserve_originals(source, cover, workspace, monkeypatch):
    output = workspace / "rollback" / "full.mp4"
    output.parent.mkdir()
    destinations = [output, output.with_suffix(".srt"), output.with_suffix(".source-map.json"),
                    output.with_suffix(".transcript.txt")]
    for index, path in enumerate(destinations):
        path.write_bytes(f"old artifact {index}".encode())
    before = {path: digest(path) for path in [source, cover, *destinations]}
    cancel = threading.Event()

    def progress(value, _):
        if value > 0.2:
            cancel.set()

    with pytest.raises(media.CancelledError):
        render(source, cover, output, progress=progress, cancel=cancel)
    assert {path: digest(path) for path in before} == before
    assert len(list(output.parent.iterdir())) == 4
    corrupt = workspace / "broken.mov"
    corrupt.write_bytes(b"broken")
    with pytest.raises(media.MediaError, match="FFmpeg"):
        horizontal.render_horizontal(
            corrupt, media.probe(source), [segment()], [], output, cover, lambda *_: None, threading.Event(),
        )
    assert {path: digest(path) for path in before} == before
    replace_file = montage.os.replace

    def fail_final(src, dst):
        if dst == output:
            raise OSError("simulated final replacement failure")
        return replace_file(src, dst)

    monkeypatch.setattr(montage.os, "replace", fail_final)
    with pytest.raises(media.MediaError, match="replacement failure"):
        render(source, cover, output)
    assert {path: digest(path) for path in before} == before
    assert len(list(output.parent.iterdir())) == 4


def test_pre_cancel_never_starts_owned_process(source, cover, workspace, monkeypatch):
    cancel = threading.Event()
    cancel.set()

    def unexpected(*_args, **_kwargs):
        pytest.fail("Pre-cancelled horizontal rendering launched FFmpeg")

    monkeypatch.setattr(media, "_run", unexpected)
    with pytest.raises(media.CancelledError):
        horizontal.render_horizontal(
            source, MediaInfo(width=320, height=180, fps=30, duration=10), [segment()], [],
            workspace / "pre-cancelled" / "full.mp4", cover, lambda *_: None, cancel,
        )
    assert not (workspace / "pre-cancelled").exists()


def test_final_timing_verification_failure_publishes_nothing(source, cover, workspace, monkeypatch):
    output = workspace / "bad verified timing" / "full.mp4"
    measure = montage._measure

    def wrong_frames(path, duration, cancel):
        timing = measure(path, duration, cancel)
        return replace(timing, frames=timing.frames - 1) if path.suffix == ".mp4" else timing

    monkeypatch.setattr(montage, "_measure", wrong_frames)
    with pytest.raises(media.MediaError, match="timing verification"):
        render(source, cover, output)
    assert not list(output.parent.iterdir())
