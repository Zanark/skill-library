from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw, ImageFont

from clipfarm import media, thumbnails
from clipfarm.models import Region


TITLES = [
    "Contains Duplicate: From Problem to Accepted",
    "Contains Duplicate: Why a Set Fits",
    "Contains Duplicate: Accepted - 15 ms",
    "A Packed House: Two Viewers",
    "Public Stream. Private Face.",
    "The Interview Strategy Plot Twist",
    "A",
    "W" * 120,
    "A thoughtful title with enough words to fill all one hundred and twenty characters without dropping any of its meaning!!",
]


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source with spaces café.mp4"
    path.write_bytes(b"untouched source")
    return path


@pytest.fixture
def region():
    return Region(x=0.5, y=0.25, w=0.25, h=0.5)


def quadrant_camera(size=(282, 158)):
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.rectangle((0, 0, width // 2, height // 2), fill=(240, 30, 40))
    draw.rectangle((width // 2, 0, width, height // 2), fill=(20, 210, 70))
    draw.rectangle((0, height // 2, width // 2, height), fill=(30, 60, 235))
    draw.rectangle((width // 2, height // 2, width, height), fill=(245, 225, 40))
    return image


@pytest.mark.parametrize("title", TITLES)
def test_title_wraps_without_omissions_and_stays_within_bounds(title):
    assert 1 <= len(title) <= 120
    fitted = thumbnails._fit_title(title)
    assert "".join("".join(fitted.lines).split()) == "".join(title.split())
    assert fitted.height <= thumbnails._TITLE_HEIGHT
    assert fitted.font.size >= 40
    assert all(thumbnails._width(line, fitted.font) <= thumbnails._TITLE_WIDTH
               for line in fitted.lines)
    if " " in title:
        assert " ".join(fitted.lines) == title


def test_unbroken_word_wraps_without_synthetic_hyphens():
    text = "W" * 120
    lines = thumbnails._wrap_title(text, thumbnails._font(), 900)
    assert len(lines) > 1
    assert "".join(lines) == text
    assert all(thumbnails._width(line, thumbnails._font()) <= 900 for line in lines)


@pytest.mark.parametrize("length", [2, 30, 56, 57, 84, 85, 119])
def test_wide_titles_fit_at_layout_thresholds(length):
    title = "W" * length
    fitted = thumbnails._fit_title(title)
    assert "".join(fitted.lines) == title
    assert fitted.height <= thumbnails._TITLE_HEIGHT
    assert all(thumbnails._width(line, fitted.font) <= thumbnails._TITLE_WIDTH
               for line in fitted.lines)


@pytest.mark.parametrize("title", TITLES[:6])
def test_portrait_jpeg_has_only_full_title_text(source, region, title, tmp_path, monkeypatch):
    calls = []
    texts = []
    camera = quadrant_camera()

    def extract(actual_source, at, actual_region):
        calls.append((actual_source, at, actual_region))
        return camera.copy()

    original_text = ImageDraw.ImageDraw.text

    def record_text(self, xy, text, *args, **kwargs):
        texts.append(text)
        return original_text(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(thumbnails, "_extract_region", extract)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record_text)
    output = tmp_path / "finished" / "thumbnail.jpg"
    result = thumbnails.render_thumbnail(source, 12.75, region, title, output)
    assert calls == [(source.resolve(), 12.75, region)]
    assert result["width"] == 1080 and result["height"] == 1920
    assert result["title"] == title and result["source_time"] == 12.75
    assert result["camera_region"] == region.model_dump()
    assert result["layout"]["title_lines"] == texts
    assert " ".join(texts) == title
    with Image.open(output) as image:
        assert image.format == "JPEG" and image.size == (1080, 1920)
        assert image.mode == "RGB"
    for left, top, right, bottom in result["layout"]["line_bounds"]:
        assert 0 <= left < right <= 1080
        assert 0 <= top < bottom <= result["layout"]["camera_bounds"][1] - 50
    assert sorted(path.name for path in output.parent.iterdir()) == ["thumbnail.jpg"]
    assert source.read_bytes() == b"untouched source"


@pytest.mark.parametrize("size", [(282, 158), (100, 280), (360, 80)])
def test_entire_camera_is_contained_without_chopping_corners(
    source, region, size, tmp_path, monkeypatch,
):
    camera = quadrant_camera(size)
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: camera.copy())
    output = tmp_path / "thumbnail.jpg"
    result = thumbnails.render_thumbnail(source, 0, region, "Public Stream. Private Face.", output)
    layout = result["layout"]
    left, top, right, bottom = layout["camera_bounds"]
    width, height = right - left, bottom - top
    assert width <= 948 and height <= 790
    assert abs(width * size[1] / size[0] - height) <= 1
    assert layout["camera_fit"] == "contain"
    assert layout["camera_native_size"] == list(size)
    assert left + right == 1080 or left + right == 1079
    with Image.open(output) as image:
        for fx, fy in [(0.02, 0.02), (0.98, 0.02), (0.02, 0.98), (0.98, 0.98)]:
            actual = image.getpixel((left + int(width * fx), top + int(height * fy)))
            expected = camera.getpixel((int(size[0] * fx), int(size[1] * fy)))
            assert max(abs(a - b) for a, b in zip(actual, expected)) < 12


@pytest.mark.parametrize("at", [-0.01, float("nan"), float("inf"), -float("inf"), None, True, "bad"])
def test_invalid_timestamp_does_not_write_output(source, region, at, tmp_path):
    output = tmp_path / "not-created" / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="finite, nonnegative"):
        thumbnails.render_thumbnail(source, at, region, "A title", output)
    assert not output.parent.exists()


@pytest.mark.parametrize("title", ["", " \t\n ", "A" * 121, None])
def test_empty_or_oversized_title_is_rejected(source, region, title, tmp_path):
    with pytest.raises(media.MediaError, match="title must"):
        thumbnails.render_thumbnail(source, 0, region, title, tmp_path / "thumbnail.jpg")


def test_source_overwrite_and_wrong_suffix_are_rejected(source, region, tmp_path):
    with pytest.raises(media.MediaError, match="overwrite its source"):
        thumbnails.render_thumbnail(source, 0, region, "A title", source)
    with pytest.raises(media.MediaError, match=r"\.jpg or \.jpeg"):
        thumbnails.render_thumbnail(source, 0, region, "A title", tmp_path / "thumbnail.png")
    alias = tmp_path / "source-alias.jpg"
    alias.hardlink_to(source)
    with pytest.raises(media.MediaError, match="overwrite its source"):
        thumbnails.render_thumbnail(source, 0, region, "A title", alias)
    assert source.read_bytes() == b"untouched source"


def test_missing_font_is_an_explicit_failure(source, region, tmp_path, monkeypatch):
    def unavailable(*_, **__):
        raise OSError("font unavailable")

    monkeypatch.setattr(ImageFont, "truetype", unavailable)
    output = tmp_path / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="installed bold TrueType font"):
        thumbnails.render_thumbnail(source, 0, region, "Do not silently omit this", output)
    assert not output.exists()


def test_missing_or_mutated_camera_region_is_rejected(source, region, tmp_path):
    output = tmp_path / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="explicit camera Region"):
        thumbnails.render_thumbnail(source, 0, None, "A title", output)
    region.x = 0.9
    with pytest.raises(media.MediaError, match="Invalid thumbnail camera region"):
        thumbnails.render_thumbnail(source, 0, region, "A title", output)
    assert not output.exists()


def test_success_replaces_output_only_after_complete_jpeg_encoding(
    source, region, tmp_path, monkeypatch,
):
    output = tmp_path / "thumbnail.jpg"
    output.write_bytes(b"previous thumbnail")
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: quadrant_camera())
    original_replace = thumbnails.os.replace
    partials = []

    def replace(partial, destination):
        assert destination == output.resolve()
        assert output.read_bytes() == b"previous thumbnail"
        assert partial.parent == output.parent and partial.suffix == ".jpg"
        assert partial != output
        with Image.open(partial) as image:
            image.load()
            assert image.format == "JPEG" and image.size == (1080, 1920)
        partials.append(partial)
        original_replace(partial, destination)

    monkeypatch.setattr(thumbnails.os, "replace", replace)
    thumbnails.render_thumbnail(source, 0, region, "A title", output)
    assert len(partials) == 1 and not partials[0].exists()
    assert output.read_bytes() != b"previous thumbnail"


@pytest.mark.parametrize("failure", ["extract", "encode", "replace"])
def test_failures_preserve_existing_output_and_clean_only_owned_temps(
    source, region, tmp_path, monkeypatch, failure,
):
    output = tmp_path / "thumbnail.jpg"
    output.write_bytes(b"previous thumbnail")
    unrelated = tmp_path / ".thumbnail.somebody-else.tmp.jpg"
    unrelated.write_bytes(b"not ours")
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: quadrant_camera())

    if failure == "extract":
        def fail_extract(*_):
            raise media.MediaError("decode failed")
        monkeypatch.setattr(thumbnails, "_extract_region", fail_extract)
    elif failure == "encode":
        def fail_save(self, handle, **_):
            handle.write(b"partial JPEG")
            raise OSError("encode failed")
        monkeypatch.setattr(Image.Image, "save", fail_save)
    else:
        def fail_replace(*_):
            raise OSError("replace failed")
        monkeypatch.setattr(thumbnails.os, "replace", fail_replace)

    with pytest.raises(media.MediaError, match="failed"):
        thumbnails.render_thumbnail(source, 0, region, "A full title", output)
    assert output.read_bytes() == b"previous thumbnail"
    assert unrelated.read_bytes() == b"not ours"
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted([
        source.name, output.name, unrelated.name,
    ])


@pytest.mark.parametrize("payload", [b"", b"not a PNG"])
def test_empty_and_invalid_frame_decode_are_not_success(source, region, payload, monkeypatch):
    monkeypatch.setattr(media, "_bounded", lambda *_args, **_kwargs: SimpleNamespace(stdout=payload))
    with pytest.raises(media.MediaError, match="frame"):
        thumbnails._extract_region(source, 0, region)


def test_ffmpeg_uses_native_exact_camera_crop_and_local_protocols(source, region, monkeypatch):
    payload = BytesIO()
    quadrant_camera().save(payload, format="PNG")
    commands = []

    def bounded(command):
        commands.append(command)
        return SimpleNamespace(stdout=payload.getvalue())

    monkeypatch.setattr(media, "_bounded", bounded)
    image = thumbnails._extract_region(source, 5.25, region)
    command = commands[0]
    assert image.size == (282, 158)
    assert command[command.index("-ss") + 1] == "5.250000"
    assert command[command.index("-protocol_whitelist") + 1] == "file,pipe"
    filters = command[command.index("-vf") + 1]
    assert filters.startswith(media._NORMALIZE + ",format=rgb24,crop=")
    assert "exact=1" in filters and "scale=480" not in filters
    assert command[-2:] == ["image2pipe", "pipe:1"]


def test_real_video_decode_retains_odd_crop_pixels_and_accurate_seek(tmp_path):
    source = tmp_path / "tiny camera café.mkv"
    media._bounded(
        media._base() + [
            "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            "color=magenta:size=160x100:rate=4:duration=2,"
            "format=rgb24,"
            "drawbox=x=81:y=23:w=41:h=29:color=red:t=fill,"
            "drawbox=x=81:y=23:w=41:h=29:color=blue:t=fill:enable='gte(t,1)'",
            "-an", "-c:v", "ffv1", "-pix_fmt", "bgr0", str(source),
        ],
    )
    region = Region(x=81 / 160, y=23 / 100, w=41 / 160, h=29 / 100)
    first = thumbnails._extract_region(source, 0.25, region)
    later = thumbnails._extract_region(source, 1.25, region)
    assert first.size == later.size == (41, 29)
    for image, color in [(first, (255, 0, 0)), (later, (0, 0, 255))]:
        assert image.getextrema() == tuple((channel, channel) for channel in color)
    output = tmp_path / "thumbnail.jpg"
    result = thumbnails.render_thumbnail(source, 1.25, region, "A Real Camera Crop", output)
    assert result["layout"]["camera_native_size"] == [41, 29]
    with Image.open(output) as image:
        assert image.size == (1080, 1920) and image.format == "JPEG"


@pytest.mark.parametrize("size", [(620, 640), (620, 250), (300, 600)])
def test_explicit_camera_free_thumbnail_preserves_full_title_and_relevant_content(
    source, region, tmp_path, monkeypatch, size,
):
    shot = quadrant_camera(size)
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: shot.copy())
    title = "Score of a String: Adjacent Differences"
    output = tmp_path / "thumbnail.jpg"
    result = thumbnails.render_thumbnail(source, 2.5, region, title, output, camera_mode="absent")
    assert result["camera_mode"] == "absent" and result["shot_kind"] == "content"
    assert result["content_region"] == region.model_dump()
    assert "camera_region" not in result
    layout = result["layout"]
    assert not any(key.startswith("camera_") for key in layout)
    assert " ".join(layout["title_lines"]) == title
    assert layout["content_native_size"] == list(size) and layout["content_fit"] == "contain"
    left, top, right, bottom = layout["content_bounds"]
    assert 0 <= left < right <= 1080 and layout["title_bounds"][3] < top < bottom <= 1920
    assert abs((right - left) * size[1] / size[0] - (bottom - top)) <= 1
    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        for fx, fy in [(0.02, 0.02), (0.98, 0.02), (0.02, 0.98), (0.98, 0.98)]:
            actual = image.getpixel((left + int((right - left) * fx), top + int((bottom - top) * fy)))
            expected = shot.getpixel((int(size[0] * fx), int(size[1] * fy)))
            assert max(abs(a - b) for a, b in zip(actual, expected)) < 12


def test_camera_free_thumbnail_never_falls_back_to_whole_source(source, tmp_path, region):
    output = tmp_path / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="explicit content Region"):
        thumbnails.render_thumbnail(source, 0, None, "A title", output, camera_mode="absent")
    with pytest.raises(media.MediaError, match="camera_mode"):
        thumbnails.render_thumbnail(source, 0, region, "A title", output, camera_mode="auto")
    assert not output.exists()
