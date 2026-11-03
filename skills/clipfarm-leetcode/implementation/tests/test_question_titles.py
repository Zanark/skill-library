import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from clipfarm import media, question_titles, thumbnails
from clipfarm.models import Clip, Cue, Region
from clipfarm.workflow_models import WorkflowCut


@pytest.fixture
def consolas(monkeypatch):
    from clipfarm import solution_artwork

    path = Path(os.environ.get("CLIPFARM_TEST_CONSOLAS", str(
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "consola.ttf"
    )))
    if not path.is_file():
        pytest.skip("A permitted local Consolas font is required.")
    monkeypatch.setattr(solution_artwork, "_default_consolas", lambda: path)


@pytest.mark.parametrize("title", [
    "Design a Parking Reservation System", "Design a Rate Limiter",
    "1401. Circle and Rectangle Overlapping", "W" * 120,
    r"Literal {\pos(0,0)} and \N text",
])
def test_full_heading_fits_reserved_space_without_dropped_characters(title, consolas):
    layout = question_titles.title_layout(title)
    assert "".join("".join(layout["lines"]).split()) == "".join(title.split())
    assert 40 <= layout["font_size"] <= 72 and len(layout["lines"]) <= 3
    assert layout["bounds"][3] < 1920 * 0.16
    assert layout["font"]["family"] == "Consolas"
    assert len(layout["font"]["sha256"]) == 64


@pytest.mark.parametrize("title", [" ", "Bad\nTitle", "Bad\tTitle", "\x00Title", "x" * 121])
def test_question_title_rejects_blank_controls_and_oversize(title):
    with pytest.raises(ValueError):
        WorkflowCut(id="cut", title="Topic", question_title=title, category="explanation",
                    rationale="Fixture", segments=[{"start": 0, "end": 1}])


def test_header_is_persistent_separate_from_speech_and_escaped(consolas):
    clip = Clip(start=10, end=20, layout="leetcode", camera_mode="absent",
                content_region=Region(x=0, y=0, w=1, h=1),
                question_title=r"Literal {\pos(0,0)} title")
    ass = media._ass([Cue(start=3, end=4, text="Actual speech")], clip)
    assert "Style: Question,Consolas," in ass
    assert "Dialogue: 1,0:00:00.00,0:00:10.00,Question" in ass
    assert r"\{\pos" not in ass
    assert "Actual speech" in ass
    assert "Style: Question,Consolas," in media._ass([], clip)
    assert clip.question_title not in media._srt([Cue(start=3, end=4, text="Actual speech")])


def test_missing_consolas_is_not_silently_replaced(monkeypatch):
    def missing(_):
        raise media.MediaError("Consolas is required")
    monkeypatch.setattr(question_titles, "_load_font", missing)
    with pytest.raises(media.MediaError, match="Consolas"):
        question_titles.title_layout("Design a Rate Limiter")


def test_legacy_question_cover_remains_compatible(tmp_path, monkeypatch, consolas):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"Local fixture")
    monkeypatch.setattr(thumbnails, "_extract_region", lambda *_: Image.new("RGB", (640, 360), "#073642"))
    result = thumbnails.render_thumbnail(
        source, 0, Region(x=0, y=0, w=1, h=1), "Design a Parking Reservation System",
        tmp_path / "thumbnail.jpg", camera_mode="absent", font_family="Consolas",
    )
    assert result["layout"]["font"].startswith("Consolas")
    assert " ".join(result["layout"]["title_lines"]) == "Design a Parking Reservation System"
    assert result["layout"]["title_bounds"][3] < result["layout"]["content_bounds"][1]


@pytest.mark.parametrize("camera", [True, False])
@pytest.mark.parametrize(("problem", "topic"), [
    ("Design a Parking Reservation System", "Separate Read Traffic From Writes"),
    ("217. Contains Duplicate", "Why a Set Fits"),
    ("W" * 120, "M" * 240),
])
def test_problem_topic_cover_separates_complete_text_and_optional_camera(
    tmp_path, monkeypatch, consolas, camera, problem, topic,
):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"Untouched local source")
    shot = Image.new("RGB", (640, 360), "#db2518")
    calls = []

    def extract(*args):
        calls.append(args)
        assert camera, "A camera-free cover must not extract diagram/code footage."
        return shot.copy()

    monkeypatch.setattr(thumbnails, "_extract_region", extract)
    result = thumbnails.render_thumbnail(
        source, 2.5 if camera else None, Region(x=0, y=0, w=1, h=1) if camera else None,
        problem, tmp_path / "thumbnail.jpg", topic=topic,
        camera_mode="required" if camera else "absent",
    )
    assert result["title"] == problem and result["topic"] == topic
    assert result["renderer"] == ("problem-topic-camera-3" if camera else "problem-topic-camera-1")
    assert result["shot_kind"] == ("camera" if camera else "none")
    layout = result["layout"]
    for key, text in (("problem", problem), ("topic", topic)):
        block = layout[key]
        assert block["font"] == "Consolas Regular"
        assert "".join("".join(block["lines"]).split()) == "".join(text.split())
        assert block["font_size"] >= 40
        if camera:
            assert block["font_size"] <= (64 if key == "problem" else 68)
        x0, y0, x1, y1 = block["area"]
        for left, top, right, bottom in block["line_bounds"]:
            assert x0 <= left < right <= x1 and y0 <= top < bottom <= y1
    first = layout["separators"][0]
    assert layout["problem"]["area"][3] < first[1] < first[3] < layout["topic"]["area"][1]
    assert len(layout["separators"]) == (2 if camera else 1)
    assert len(calls) == (1 if camera else 0)
    if camera:
        second = layout["separators"][1]
        assert layout["topic"]["area"][3] < second[1] < second[3] < layout["camera_bounds"][1]
        assert layout["camera_fit"] == "contain"
        assert abs((layout["camera_bounds"][1] + layout["camera_bounds"][3]) / 2 - 1104) <= 0.5
    else:
        assert result["source_time"] is None
        assert "camera_region" not in result and "content_region" not in result
        assert not any(key.startswith(("content_", "camera_")) for key in layout)
    with Image.open(tmp_path / "thumbnail.jpg") as image:
        assert image.size == (1080, 1920) and image.format == "JPEG"
        if camera:
            left, top, right, bottom = layout["camera_bounds"]
            for x, y in ((left + 3, top + 3), (right - 3, bottom - 3)):
                assert max(abs(a - b) for a, b in zip(image.getpixel((x, y)), (219, 37, 24))) < 12
    assert source.read_bytes() == b"Untouched local source"


@pytest.mark.parametrize("size", [(640, 360), (200, 480), (800, 140)])
def test_compact_camera_is_centered_with_frost_shadow_and_accent_border(size, consolas):
    from clipfarm.solution_artwork import _load_font

    shot = Image.new("RGB", size, "#efc030")
    ImageDraw.Draw(shot).rectangle([0, 0, size[0] // 2, size[1]], fill="#227799")
    font, _ = _load_font(None)
    problem = thumbnails._fit_title("3622. Check Divisibility by Digit Sum and Product",
                                    base_font=font, max_size=64, height_limit=270)
    topic = thumbnails._fit_title("Extract a Digit With n % 10",
                                  base_font=font, max_size=68, height_limit=270)
    image, layout = thumbnails._compose_problem_topic(shot, problem, topic)
    x0, y0, x1, y1 = layout["camera_bounds"]
    assert abs((y0 + y1) / 2 / 1920 - 0.575) < 0.001
    assert 0.39 < y0 / 1920 < 0.58 and y1 / 1920 < 0.76
    assert abs((x1 - x0) * size[1] / size[0] - (y1 - y0)) <= 1
    card = layout["camera_card"]["bounds"]
    assert layout["separators"][1][3] < card[1]
    assert image.getpixel((card[0], (y0 + y1) // 2)) == (69, 97, 106)
    assert layout["camera_card"]["border_color"] == "#45616a"
    assert image.getpixel((540, 398)) == (205, 92, 92)
    assert image.getpixel((540, 740)) == (205, 92, 92)
    for fx, fy in ((0.02, 0.02), (0.98, 0.98)):
        assert image.getpixel((x0 + int((x1 - x0) * fx), y0 + int((y1 - y0) * fy))) == shot.getpixel(
            (int(size[0] * fx), int(size[1] * fy)))
    assert image.getpixel((50, 1800)) == thumbnails._backdrop(shot, grain=True).getpixel((50, 1800))
    assert image.getpixel((50, 1800)) != thumbnails._backdrop().getpixel((50, 1800))
    shadow_point = (540, card[3] + 20)
    assert sum(image.getpixel(shadow_point)) < sum(thumbnails._backdrop(shot).getpixel(shadow_point))


def test_camera_grain_is_subtle_repeatable_and_not_added_to_legacy_or_text_only():
    import numpy as np

    shot = Image.new("RGB", (400, 300), "#779999")
    original = np.asarray(thumbnails._backdrop(shot), dtype=int)
    grain = np.asarray(thumbnails._backdrop(shot, grain=True), dtype=int)
    np.testing.assert_array_equal(grain, np.asarray(thumbnails._backdrop(shot, grain=True)))
    delta = grain - original
    assert np.abs(delta).max() <= 4
    assert 1 < delta.std() < 1.4
    np.testing.assert_array_equal(delta[:, :, 0], delta[:, :, 1])
    assert thumbnails._backdrop().tobytes() == thumbnails._backdrop(grain=True).tobytes()

@pytest.mark.parametrize("topic", ["", " ", "Question", "Bad\nTopic", "x" * 241])
def test_invalid_or_repeated_cover_topic_fails_explicitly(tmp_path, topic):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="topic"):
        thumbnails.render_thumbnail(source, None, None, "Question", output,
                                    camera_mode="absent", topic=topic)
    assert not output.exists()


def test_text_only_cover_rejects_fabricated_frame_provenance(tmp_path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"source")
    with pytest.raises(media.MediaError, match="must not claim"):
        thumbnails.render_thumbnail(
            source, 0, Region(x=0, y=0, w=1, h=1), "Question", tmp_path / "thumbnail.jpg",
            camera_mode="absent", topic="Specific topic",
        )
