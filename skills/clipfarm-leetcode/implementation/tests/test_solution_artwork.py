from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw, ImageFont
from pydantic import ValidationError

from clipfarm import media, solution_artwork as artwork
from clipfarm.solution_artwork import ComplexityEvidence, MemeAsset, SolutionArtworkSpec


@pytest.fixture
def workspace():
    path = Path(__file__).resolve().parents[1] / ".clipfarm" / "artwork-tests" / uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


@pytest.fixture(scope="module")
def consolas():
    supplied = os.environ.get("CLIPFARM_TEST_CONSOLAS")
    if supplied:
        path = Path(supplied)
    elif os.name == "nt":
        path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "consola.ttf"
    else:
        pytest.skip("Rendering needs a permitted local Consolas font.")
    try:
        font = ImageFont.truetype(str(path), size=32)
    except OSError:
        pytest.skip("Consolas is not installed; contract validation still runs.")
    if font.getname()[0] != "Consolas":
        pytest.skip("The test font is not genuine Consolas.")
    return path.resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_art(size=(240, 160)):
    image = Image.new("RGB", size, "#355f88")
    draw = ImageDraw.Draw(image)
    w, h = size
    draw.rectangle((0, 0, w // 2, h // 2), fill=(240, 30, 40))
    draw.rectangle((w // 2, 0, w, h // 2), fill=(20, 210, 70))
    draw.rectangle((0, h // 2, w // 2, h), fill=(30, 60, 235))
    draw.rectangle((w // 2, h // 2, w, h), fill=(245, 225, 40))
    draw.polygon([(w * .3, h * .5), (w * .3, h * .15), (w * .5, h * .4)], fill="white")
    draw.polygon([(w * .5, h * .4), (w * .7, h * .15), (w * .7, h * .5)], fill="white")
    draw.ellipse((w * .3, h * .3, w * .7, h * .8), fill="white")
    for x in [.43, .57]:
        draw.ellipse((w * x - 2, h * .5 - 2, w * x + 2, h * .5 + 2), fill="black")
    return image


def make_spec(workspace, font_path=None):
    path = workspace / "original cat.png"
    original_art().save(path)
    return SolutionArtworkSpec(
        problem_number=217,
        problem_title="Contains Duplicate",
        complexity=ComplexityEvidence(
            notation="O(n)", source_kind="stream", source_time=42.5,
            evidence="We visit each number once, so the total running time is O(n).",
        ),
        meme=MemeAsset(
            image=str(path), sha256=digest(path), rights="original",
            rights_note="Original geometric cat drawn solely for this test.",
            topic="The same cat appears twice, like a duplicated array value.",
            search_query="original cat duplicate joke",
        ),
        font_path=str(font_path) if font_path else None,
    )


@pytest.fixture
def spec(workspace, consolas):
    return make_spec(workspace, consolas)


def revise(spec, **changes):
    return SolutionArtworkSpec.model_validate({**spec.model_dump(), **changes})


@pytest.mark.parametrize("changes", [
    {"source_time": None},
    {"source_time": -0.1},
    {"source_time": float("inf")},
    {"source_time": float("nan")},
    {"evidence": ""},
    {"evidence": "   "},
    {"evidence": "O(n)"},
    {"evidence": "see link"},
    {"notation": "  "},
    {"source_kind": "guess"},
])
def test_stream_complexity_requires_timestamp_and_substantive_evidence(changes):
    data = {
        "notation": "O(n^2)", "source_kind": "stream", "source_time": 0,
        "evidence": "There are two nested loops over all n elements.",
    }
    with pytest.raises(ValidationError):
        ComplexityEvidence.model_validate({**data, **changes})


@pytest.mark.parametrize("url", [
    None, "", "leetcode.com/editorial", "file:///editorial", "ftp://example.com",
    "https://", "https://example.com:invalid", "https://exa mple.com",
    "https://user:password@example.com", "https://example.com\\not-a-path",
    "https://[not-an-ipv6-address]/", "https://%broken-host/",
])
def test_research_requires_valid_http_citation(url):
    with pytest.raises(ValidationError):
        ComplexityEvidence(
            notation="O(n log n)", source_kind="research", source_url=url,
            evidence="The cited editorial sorts the array before its linear sweep.",
        )


def test_evidence_and_notation_are_preserved_not_computed():
    notation = "O(n^2 + m log m), worst case; O(n) expected"
    quote = "  The cited analysis distinguishes expected and worst-case hash operations.  "
    complexity = ComplexityEvidence(
        notation=notation, source_kind="research", evidence=quote,
        source_url="https://example.org/editorial?section=complexity#proof",
    )
    assert complexity.notation == notation
    assert complexity.evidence == quote
    assert complexity.source_time is None


@pytest.mark.parametrize("changes", [
    {"rights": "found_on_google"}, {"rights": None}, {"rights_note": ""},
    {"rights_note": "  "}, {"topic": " "}, {"sha256": "A" * 64},
    {"sha256": "a" * 63}, {"rights": "licensed"}, {"source_url": "ftp://example.com"},
    {"attribution": "line one\nline two"},
])
def test_meme_requires_hash_rights_declaration_and_relevance(workspace, changes):
    data = make_spec(workspace).meme.model_dump()
    with pytest.raises(ValidationError):
        MemeAsset.model_validate({**data, **changes})


def test_rights_are_required_and_licensed_images_require_credit(workspace):
    data = make_spec(workspace).meme.model_dump()
    data.pop("rights")
    with pytest.raises(ValidationError, match="rights"):
        MemeAsset.model_validate(data)
    data.update(
        rights="licensed", attribution="Test author / CC BY 4.0",
        source_url="https://example.org/original-cat",
        rights_note="Test declaration of permission, not a real third-party artwork.",
    )
    asset = MemeAsset.model_validate(data)
    assert asset.rights == "licensed"
    assert asset.attribution == "Test author / CC BY 4.0"


@pytest.mark.parametrize("path", [
    "cat.png", "https://example.org/cat.png", "file:///cat.png",
    r"\\server\share\cat.png", "//server/share/cat.png",
    "/\\server\\share\\cat.png",
])
def test_image_and_explicit_font_must_be_absolute_local_paths(workspace, path):
    data = make_spec(workspace).model_dump()
    with pytest.raises(ValidationError, match="local"):
        MemeAsset.model_validate({**data["meme"], "image": path})
    with pytest.raises(ValidationError, match="local"):
        SolutionArtworkSpec.model_validate({**data, "font_path": path})


@pytest.mark.parametrize("changes", [
    {"problem_number": 0}, {"problem_number": -1}, {"problem_number": True},
    {"problem_number": 1.5}, {"problem_title": ""}, {"problem_title": " "},
    {"problem_title": "A" * 221}, {"problem_title": "Exact\nTitle"},
])
def test_problem_identity_is_required_without_silent_rewrites(workspace, changes):
    with pytest.raises(ValidationError):
        revise(make_spec(workspace), **changes)


def test_validation_preserves_exact_title_and_all_provenance(workspace):
    title = "  A Title With  Deliberately Repeated Spaces  "
    spec = revise(make_spec(workspace), problem_title=title)
    restored = SolutionArtworkSpec.model_validate_json(spec.model_dump_json())
    assert restored == spec
    assert restored.problem_title == title
    assert restored.meme.search_query == "original cat duplicate joke"


@pytest.mark.parametrize("size", [(320, 180), (1280, 720), (2560, 1440)])
def test_landscape_is_black_rgb_jpeg_with_white_title_and_green_complexity(
    spec, workspace, size,
):
    output = workspace / "finished" / "thumbnail.jpg"
    before = digest(Path(spec.meme.image))
    result = artwork.render_solution_thumbnail(spec, output, width=size[0], height=size[1])
    assert result["width"] == size[0] and result["height"] == size[1]
    assert result["title"] == "217. Contains Duplicate"
    assert result["text"] == {
        "title": "217. Contains Duplicate", "notation": "O(n)",
        "technique": "",
        "complexity_label": "", "source_label": "", "attribution": "",
    }
    assert result["font"]["family"] == "Consolas"
    assert result["font"]["monospaced"] is True
    assert result["renderer_version"] == artwork.RENDERER_VERSION
    assert json.loads(json.dumps(result)) == result
    layout = result["layout"]
    with Image.open(output) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB" and image.size == size
        assert image.getpixel((0, 0)) == (0, 0, 0)
        assert image.getpixel((size[0] - 1, size[1] - 1)) == (0, 0, 0)
        assert image.getpixel((size[0] // 2, size[1] - 10)) == (0, 0, 0)
        white = image.crop(layout["title_bounds"]).getcolors(size[0] * size[1])
        assert any(min(pixel) > 220 for _, pixel in white)
        green = image.crop(layout["notation_bounds"]).getcolors(size[0] * size[1])
        assert any(g > 150 and g > r * 1.7 and g > b * 1.3 for _, (r, g, b) in green)
    for name in ["title_bounds", "notation_bounds", "notation_circle_bounds", "meme_bounds"]:
        left, top, right, bottom = layout[name]
        assert 0 <= left < right <= size[0]
        assert 0 <= top < bottom <= size[1]
    assert layout["title_bounds"][3] < layout["notation_bounds"][1]
    assert layout["title_bounds"][3] < layout["meme_bounds"][1]
    assert layout["notation_bounds"][2] < layout["meme_bounds"][0]
    assert Path(spec.meme.image).is_file() and digest(Path(spec.meme.image)) == before
    assert sorted(path.name for path in output.parent.iterdir()) == ["thumbnail.jpg"]
    assert layout["technique_lines"] == [] and layout["technique_bounds"] is None


@pytest.mark.parametrize("technique", ["", " ", "Hash\nSet", "Hash\tMap", "X" * 121])
def test_technique_rejects_blank_control_and_overlong_text(workspace, technique):
    with pytest.raises(ValidationError):
        revise(make_spec(workspace), technique=technique)


@pytest.mark.parametrize("size", [(320, 180), (1280, 720), (2560, 1440)])
@pytest.mark.parametrize("title,technique", [
    ("Contains Duplicate", "Hash Set"),
    ("Circle and Rectangle Overlapping", "Geometry"),
    ("Contains Duplicate II", "Hash Map"),
    ("A long title with every word preserved " * 5, "Dynamic Programming / Binary Search"),
])
def test_technique_is_left_aligned_lime_consolas_exactly_three_pixels_smaller(
    spec, workspace, monkeypatch, size, title, technique,
):
    calls = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        calls.append((text, kwargs["font"], kwargs["fill"]))
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    spec = revise(spec, problem_title=title, technique=technique)
    output = workspace / "technique.jpg"
    result = artwork.render_solution_thumbnail(spec, output, width=size[0], height=size[1])
    layout = result["layout"]
    assert result["text"]["technique"] == result["spec"]["technique"] == technique
    assert "".join(layout["title_lines"]) == f"217. {title}"
    assert "".join(layout["technique_lines"]) == technique
    assert layout["technique_font_size"] == layout["title_font_size"] - 3
    assert layout["technique_color"] == "#dfff00"
    label_calls = calls[len(layout["title_lines"]):-1]
    assert [text for text, _, _ in label_calls] == layout["technique_lines"]
    for _, font, color in label_calls:
        assert font.getname()[0] == "Consolas"
        assert font.size == layout["title_font_size"] - 3
        assert color == "#dfff00"
    for left, top, right, bottom in layout["technique_line_bounds"]:
        assert left == layout["title_bounds"][0]
        assert layout["title_bounds"][3] < top < bottom <= layout["title_area"][3]
        assert right <= layout["title_area"][2]
    assert layout["technique_bounds"][3] < layout["meme_area"][1]
    assert layout["technique_bounds"][3] < layout["notation_bounds"][1]
    with Image.open(output) as image:
        colors = image.crop(layout["technique_bounds"]).getcolors(size[0] * size[1])
        assert any(g > 80 and g >= r > g * 0.65 and b < g * 0.2 for _, (r, g, b) in colors)
        if layout["technique_font_size"] >= 10:
            assert any(r > 170 and g > 210 and b < 60 for _, (r, g, b) in colors)


def test_technique_preserves_existing_title_ring_and_meme_geometry(spec, workspace):
    before = artwork.render_solution_thumbnail(spec, workspace / "before.jpg")["layout"]
    after = artwork.render_solution_thumbnail(
        revise(spec, technique="Hash Set"), workspace / "after.jpg",
    )["layout"]
    for key in [
        "title_bounds", "title_font_size", "notation_bounds", "notation_circle_bounds",
        "notation_circle_stroke", "meme_bounds", "meme_area",
    ]:
        assert before[key] == after[key]
    with Image.open(workspace / "before.jpg") as old, Image.open(workspace / "after.jpg") as new:
        assert old.crop((0, 280, 1280, 720)).tobytes() == new.crop((0, 280, 1280, 720)).tobytes()


def test_technique_is_fingerprinted_and_missing_glyphs_are_not_substituted(spec, workspace):
    changed = revise(spec, technique="Hash Set")
    assert artwork.artwork_inputs(changed) != artwork.artwork_inputs(spec)
    assert SolutionArtworkSpec.model_validate_json(changed.model_dump_json()) == changed
    output = workspace / "missing-glyph.jpg"
    with pytest.raises(media.MediaError, match="cannot render character"):
        artwork.render_solution_thumbnail(revise(spec, technique="\U0010ffff"), output)
    assert not output.exists()


def test_heading_reports_impossible_fit_without_omitting_the_technique(spec, consolas):
    font = ImageFont.truetype(str(consolas), size=64)
    with pytest.raises(media.MediaError, match="three-pixel font difference"):
        artwork._fit_heading("Exact title", "Hash Set", font, 1000, 1, 64, 18, 20)


@pytest.mark.parametrize("title", [
    "A very precise LeetCode problem title with every significant word preserved " * 2,
    "W" * 220,
    ("A  B   C " * 25)[:220],
])
@pytest.mark.parametrize("size", [(320, 180), (1280, 720)])
def test_long_title_is_drawn_in_full_with_exact_wrapping(spec, workspace, monkeypatch, title, size):
    spec = revise(spec, problem_title=title)
    seen = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        seen.append(text)
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    result = artwork.render_solution_thumbnail(
        spec, workspace / "long.jpg", width=size[0], height=size[1],
    )
    layout = result["layout"]
    assert result["title"] == f"217. {title}"
    assert "".join(layout["title_lines"]) == f"217. {title}"
    assert seen[:len(layout["title_lines"])] == layout["title_lines"]
    assert len(layout["title_lines"]) > 1
    for left, top, right, bottom in layout["title_line_bounds"]:
        assert layout["title_area"][0] <= left < right <= layout["title_area"][2]
        assert layout["title_area"][1] <= top < bottom <= layout["title_area"][3]


@pytest.mark.parametrize("notation", [
    "O(n^2)", "O(n log n)", "O(n + m)", "O(1)", "O(n log(n + m))", "O(2^n)",
])
def test_literal_complexity_is_never_simplified(spec, workspace, notation):
    complexity = {**spec.complexity.model_dump(), "notation": notation}
    result = artwork.render_solution_thumbnail(
        revise(spec, complexity=complexity), workspace / "literal.jpg",
    )
    assert result["complexity"]["notation"] == notation
    assert result["text"]["notation"] == notation
    assert "".join(result["layout"]["notation_lines"]) == notation


def test_research_basis_is_preserved_off_image(spec, workspace, monkeypatch):
    research = ComplexityEvidence(
        notation="O(n log n)", source_kind="research",
        evidence="The editorial states that sorting dominates this approach's runtime.",
        source_url="https://example.org/editorial",
    )
    seen = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        seen.append(text)
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    result = artwork.render_solution_thumbnail(
        revise(spec, complexity=research), workspace / "research.jpg",
    )
    assert result["text"]["complexity_label"] == ""
    assert result["layout"]["complexity_label_lines"] == []
    assert seen == ["217. Contains Duplicate", "(n log n)"]
    assert result["complexity"]["source_kind"] == "research"
    assert result["complexity"]["source_url"] == research.source_url
    assert result["complexity"]["source_time"] is None


@pytest.mark.parametrize("size", [(240, 160), (80, 360), (400, 80)])
def test_meme_is_contained_bottom_right_without_cropping_or_distortion(spec, workspace, size):
    image = original_art(size)
    path = Path(spec.meme.image)
    image.save(path)
    spec = revise(spec, meme={**spec.meme.model_dump(), "sha256": digest(path)})
    result = artwork.render_solution_thumbnail(spec, workspace / "contained.jpg")
    layout = result["layout"]
    left, top, right, bottom = layout["meme_bounds"]
    width, height = right - left, bottom - top
    assert layout["meme_native_size"] == list(size)
    assert layout["meme_fit"] == "contain"
    scale = min(
        (layout["meme_area"][2] - layout["meme_area"][0]) / size[0],
        (layout["meme_area"][3] - layout["meme_area"][1]) / size[1],
    )
    assert abs(width - size[0] * scale) <= .5
    assert abs(height - size[1] * scale) <= .5
    assert right == layout["meme_area"][2] and bottom == layout["meme_area"][3]
    with Image.open(workspace / "contained.jpg") as output:
        for fx, fy in [(0.03, 0.03), (0.97, 0.03), (0.03, 0.97), (0.97, 0.97)]:
            actual = output.getpixel((left + int(width * fx), top + int(height * fy)))
            expected = image.getpixel((int(size[0] * fx), int(size[1] * fy)))
            assert max(abs(a - b) for a, b in zip(actual, expected)) < 12


def test_licensed_attribution_is_preserved_off_image(spec, workspace):
    attribution = "Original test cat by ClipFarm tests / permission declared for this fixture."
    meme = {**spec.meme.model_dump(), "rights": "licensed", "attribution": attribution}
    result = artwork.render_solution_thumbnail(
        revise(spec, meme=meme), workspace / "credited.jpg", width=320, height=180,
    )
    layout = result["layout"]
    assert layout["attribution_lines"] == []
    assert result["text"]["attribution"] == ""
    assert layout["attribution_bounds"] is None
    assert result["meme"]["attribution"] == attribution
    assert result["meme"]["rights"] == "licensed"


@pytest.mark.parametrize("qualifier", ["average", "expected", "amortized", "worst-case", "best case"])
def test_only_formula_is_displayed_without_losing_qualifications(spec, workspace, qualifier):
    raw = f"O(n) {qualifier}"
    result = artwork.render_solution_thumbnail(
        revise(spec, complexity={**spec.complexity.model_dump(), "notation": raw}),
        workspace / "bare-notation.jpg",
    )
    assert result["text"]["notation"] == "O(n)"
    assert result["complexity"]["notation"] == raw
    assert result["complexity"]["display_notation"] == "O(n)"


def test_compound_analysis_needs_explicit_display_formula(spec, workspace):
    raw = "O(n) expected; O(n^2) worst case"
    complexity = {**spec.complexity.model_dump(), "notation": raw}
    with pytest.raises(media.MediaError, match="display_notation"):
        artwork.render_solution_thumbnail(revise(spec, complexity=complexity), workspace / "ambiguous.jpg")
    assert not (workspace / "ambiguous.jpg").exists()
    result = artwork.render_solution_thumbnail(
        revise(spec, complexity={**complexity, "display_notation": "O(n^2)"}),
        workspace / "explicit.jpg",
    )
    assert result["text"]["notation"] == "O(n^2)"
    assert result["complexity"]["notation"] == raw


@pytest.mark.parametrize("notation", ["O()", "O(n", "O(n))", "O(n) + O(m)", "Theta(n)", "0(n)"])
def test_invalid_or_ambiguous_display_is_not_silently_simplified(spec, notation):
    complexity = {**spec.complexity.model_dump(), "display_notation": notation}
    with pytest.raises(media.MediaError, match=r"one O"):
        artwork.artwork_inputs(revise(spec, complexity=complexity))


@pytest.mark.parametrize("size,expected_stroke", [((320, 180), 1), ((1280, 720), 5), ((2560, 1440), 10)])
def test_big_o_is_a_drawn_circular_ring_not_a_font_glyph(spec, workspace, monkeypatch, size, expected_stroke):
    seen = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        seen.append(text)
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    output = workspace / "circle.jpg"
    result = artwork.render_solution_thumbnail(spec, output, width=size[0], height=size[1])
    bounds = result["layout"]["notation_circle_bounds"]
    assert bounds[2] - bounds[0] == bounds[3] - bounds[1]
    assert bounds[2] - bounds[0] == round(size[1] * 0.30)
    assert (bounds[1] + bounds[3]) / 2 == pytest.approx(size[1] * 0.70, abs=1)
    assert result["layout"]["notation_o_style"] == "drawn_circle"
    stroke = result["layout"]["notation_circle_stroke"]
    assert stroke == expected_stroke
    assert "(n)" in seen and "O(n)" not in seen
    with Image.open(output) as image:
        ring = image.crop(bounds)
        diameter = ring.width
        center = ring.getpixel((diameter // 2, diameter // 2))
        assert max(center) < 30
        for point in [(diameter // 2, stroke // 2), (stroke // 2, diameter // 2)]:
            r, g, b = ring.getpixel(point)
            assert g > 120 and g > r * 1.7 and g > b * 1.3
        mask = Image.new("L", ring.size)
        pixels = ring.load()
        mask.putdata([
            255 if pixels[x, y][1] > 120 and pixels[x, y][1] > pixels[x, y][0] * 1.7 else 0
            for y in range(diameter) for x in range(diameter)
        ])
        left, top, right, bottom = mask.getbbox()
        assert right - left == bottom - top
        visible_stroke = sum(
            mask.getpixel((diameter // 2, y)) > 0 for y in range(diameter // 2)
        )
        assert visible_stroke == pytest.approx(expected_stroke, abs=1)


@pytest.mark.parametrize("notation", ["O(1)", "O(n)", "O(n^2)", "O(n log(n + m))"])
def test_large_circle_does_not_shrink_with_the_expression(spec, workspace, notation):
    result = artwork.render_solution_thumbnail(
        revise(spec, complexity={**spec.complexity.model_dump(), "notation": notation}),
        workspace / "large-circle.jpg",
    )
    circle = result["layout"]["notation_circle_bounds"]
    text = result["layout"]["notation_text_bounds"]
    assert circle == [48, 396, 264, 612]
    assert text[0] > circle[2]
    assert text[2] < result["layout"]["meme_area"][0]
    assert (text[1] + text[3]) / 2 == pytest.approx((circle[1] + circle[3]) / 2, abs=1)
    assert result["text"]["notation"] == notation


def test_transparency_composites_on_black_without_distorting_image(spec, workspace):
    path = Path(spec.meme.image)
    image = Image.new("RGBA", (160, 160), (255, 0, 255, 0))
    ImageDraw.Draw(image).rectangle((40, 40, 120, 120), fill=(255, 255, 255, 255))
    image.save(path)
    spec = revise(spec, meme={**spec.meme.model_dump(), "sha256": digest(path)})
    output = workspace / "transparent.jpg"
    result = artwork.render_solution_thumbnail(spec, output)
    left, top, right, bottom = result["layout"]["meme_bounds"]
    with Image.open(output) as composed:
        assert composed.getpixel((left + 12, top + 12)) == (0, 0, 0)
        assert min(composed.getpixel(((left + right) // 2, (top + bottom) // 2))) > 240


def test_exif_orientation_is_respected_before_containment(spec, workspace):
    image = original_art((120, 80))
    exif = Image.Exif()
    exif[274] = 6
    path = workspace / "rotated-cat.jpg"
    image.save(path, exif=exif)
    spec = revise(spec, meme={**spec.meme.model_dump(), "image": str(path), "sha256": digest(path)})
    inputs = artwork.artwork_inputs(spec)
    assert inputs["meme"]["native_size"] == [120, 80]
    assert inputs["meme"]["display_size"] == [80, 120]
    result = artwork.render_solution_thumbnail(spec, workspace / "oriented.jpg")
    assert result["layout"]["meme_native_size"] == [80, 120]


def test_input_fingerprints_are_deterministic_json_and_include_provenance(spec):
    before = artwork.artwork_inputs(spec)
    after = artwork.artwork_inputs(spec)
    assert before == after
    assert json.loads(json.dumps(before)) == before
    assert before["font"]["sha256"] == digest(Path(spec.font_path))
    assert before["meme"]["sha256"] == spec.meme.sha256
    assert before["meme"]["topic"] == spec.meme.topic
    assert before["meme"]["rights_note"] == spec.meme.rights_note
    assert before["meme"]["search_query"] == spec.meme.search_query
    assert before["complexity"]["evidence"] == spec.complexity.evidence
    assert before["spec"] == spec.model_dump(mode="json")


def test_tampered_asset_errors_until_editor_repins_new_bytes(spec):
    before = artwork.artwork_inputs(spec)
    path = Path(spec.meme.image)
    with path.open("ab") as handle:
        handle.write(b"changed local asset bytes")
    with pytest.raises(media.MediaError, match="SHA256"):
        artwork.artwork_inputs(spec)
    updated = revise(spec, meme={**spec.meme.model_dump(), "sha256": digest(path)})
    after = artwork.artwork_inputs(updated)
    assert after != before
    assert after["meme"]["sha256"] != before["meme"]["sha256"]


def test_changed_font_bytes_invalidate_fingerprint_without_touching_original(spec, workspace):
    original = Path(spec.font_path)
    original_hash = digest(original)
    copy = workspace / "permitted local Consolas.ttf"
    shutil.copyfile(original, copy)
    spec = revise(spec, font_path=str(copy))
    before = artwork.artwork_inputs(spec)
    with copy.open("ab") as handle:
        handle.write(b"font changed without changing its valid glyph tables")
    after = artwork.artwork_inputs(spec)
    assert before["font"]["sha256"] != after["font"]["sha256"]
    assert after["font"]["family"] == "Consolas"
    assert digest(original) == original_hash


def test_cache_inputs_change_when_editorial_evidence_or_rights_change(spec):
    before = artwork.artwork_inputs(spec)
    changed = revise(
        spec,
        meme={**spec.meme.model_dump(), "rights_note": "Updated explicit original-art declaration."},
        complexity={**spec.complexity.model_dump(), "source_time": 90},
    )
    assert artwork.artwork_inputs(changed) != before


def test_urls_are_citations_only_and_never_downloaded(spec, monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("Artwork must never use the network.")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    meme = {**spec.meme.model_dump(), "source_url": "https://example.org/cat"}
    assert artwork.artwork_inputs(revise(spec, meme=meme))["meme"]["source_url"] == meme["source_url"]


def test_default_font_is_real_windows_consolas(spec, consolas):
    if os.name != "nt":
        pytest.skip("Default font discovery is Windows-only.")
    result = artwork.artwork_inputs(revise(spec, font_path=None))
    assert Path(result["font"]["path"]).samefile(consolas)
    assert result["font"]["family"] == "Consolas"


def test_nonwindows_has_clear_error_instead_of_font_fallback(monkeypatch):
    monkeypatch.setattr(artwork, "os", SimpleNamespace(name="posix"))
    with pytest.raises(media.MediaError, match="Consolas.*font_path"):
        artwork._default_consolas()


def test_missing_font_fails_without_creating_output(workspace):
    spec = make_spec(workspace, workspace / "missing-consola.ttf")
    output = workspace / "not-created" / "thumbnail.jpg"
    with pytest.raises(media.MediaError, match="Consolas.*no substitute"):
        artwork.render_solution_thumbnail(spec, output)
    assert not output.parent.exists()


@pytest.mark.parametrize("family,proportional", [("Arial", False), ("Consolas", True)])
def test_font_identity_and_monospace_metrics_are_both_checked(workspace, monkeypatch, family, proportional):
    font_path = workspace / "not-necessarily-Consolas.ttf"
    font_path.write_bytes(b"fake font payload for the loader stub")
    spec = make_spec(workspace, font_path)
    calls = []

    class FakeFont:
        def getname(self):
            return family, "Regular"

        def getlength(self, char):
            return 16 if proportional and char == "W" else 8

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeFont()

    monkeypatch.setattr(ImageFont, "truetype", fake)
    with pytest.raises(media.MediaError, match="monospaced Consolas"):
        artwork.artwork_inputs(spec)
    assert len(calls) == 1


def test_corrupt_font_never_falls_back(workspace):
    font_path = workspace / "consola.ttf"
    font_path.write_bytes(b"this is not a font")
    with pytest.raises(media.MediaError, match="no substitute"):
        artwork.artwork_inputs(make_spec(workspace, font_path))


def test_missing_glyph_is_an_error_not_silent_replacement(spec, workspace):
    spec = revise(spec, problem_title="An unsupported character \U0010fffd")
    with pytest.raises(media.MediaError, match="cannot render character"):
        artwork.render_solution_thumbnail(spec, workspace / "unsupported.jpg")
    assert not (workspace / "unsupported.jpg").exists()


@pytest.mark.parametrize("payload", [b"", b"<svg/>", b"not an image"])
def test_matching_hash_does_not_make_unsupported_image_valid(workspace, payload):
    spec = make_spec(workspace)
    path = Path(spec.meme.image)
    path.write_bytes(payload)
    spec = revise(spec, meme={**spec.meme.model_dump(), "sha256": digest(path)})
    with pytest.raises(media.MediaError, match="decode"):
        artwork.artwork_inputs(spec)


def test_missing_image_is_a_clear_local_error(workspace):
    spec = make_spec(workspace)
    Path(spec.meme.image).unlink()
    with pytest.raises(media.MediaError, match="read Meme image"):
        artwork.artwork_inputs(spec)


def test_animation_is_not_silently_reduced_to_first_frame(workspace):
    spec = make_spec(workspace)
    image = Path(spec.meme.image)
    frames = [Image.new("RGB", (40, 40), color) for color in ("red", "blue")]
    frames[0].save(image, format="GIF", save_all=True, append_images=frames[1:], duration=100)
    spec = revise(spec, meme={**spec.meme.model_dump(), "sha256": digest(image)})
    with pytest.raises(media.MediaError, match="explicit still image"):
        artwork.artwork_inputs(spec)


def test_mutable_model_is_revalidated_before_cache_or_render(spec, workspace):
    spec.meme.rights_note = ""
    with pytest.raises(media.MediaError, match="Invalid solution artwork"):
        artwork.artwork_inputs(spec)
    with pytest.raises(media.MediaError, match="Invalid solution artwork"):
        artwork.render_solution_thumbnail(spec, workspace / "invalid.jpg")


def test_render_and_metadata_use_the_same_validated_snapshot(spec, workspace, monkeypatch):
    real_compose = artwork._compose

    def concurrent_edit(inputs, width, height):
        spec.complexity.notation = "O(n^9)"
        spec.meme.attribution = "A later edit, not present in the rendered image"
        return real_compose(inputs, width, height)

    monkeypatch.setattr(artwork, "_compose", concurrent_edit)
    result = artwork.render_solution_thumbnail(spec, workspace / "snapshot.jpg")
    assert result["text"]["notation"] == "O(n)"
    assert result["complexity"]["notation"] == "O(n)"
    assert result["text"]["attribution"] == ""
    assert "".join(result["layout"]["notation_lines"]) == "O(n)"


@pytest.mark.parametrize("size", [(319, 180), (320, 179), (180, 320), (720, 720), (True, 720), (1280.0, 720)])
def test_invalid_dimensions_never_write(spec, workspace, size):
    output = workspace / "invalid.jpg"
    with pytest.raises(media.MediaError, match="landscape dimensions"):
        artwork.render_solution_thumbnail(spec, output, width=size[0], height=size[1])
    assert not output.exists()


def test_sources_and_hardlink_aliases_cannot_be_overwritten(spec, workspace):
    installed_font = Path(spec.font_path)
    installed_hash = digest(installed_font)
    local_font = workspace / "permitted-Consolas.ttf"
    shutil.copyfile(installed_font, local_font)
    spec = revise(spec, font_path=str(local_font))
    paths = [Path(spec.meme.image), Path(spec.font_path)]
    hashes = [digest(path) for path in paths]
    for index, source in enumerate(paths):
        with pytest.raises(media.MediaError, match="cannot overwrite"):
            artwork.render_solution_thumbnail(spec, source)
        alias = workspace / f"source-alias-{index}.jpg"
        alias.hardlink_to(source)
        with pytest.raises(media.MediaError, match="cannot overwrite"):
            artwork.render_solution_thumbnail(spec, alias)
    assert [digest(path) for path in paths] == hashes
    assert digest(installed_font) == installed_hash


@pytest.mark.parametrize("output", ["cover.png", r"\\server\share\cover.jpg", "https://example.org/cover.jpg"])
def test_invalid_or_remote_output_rejected(spec, workspace, output):
    destination = workspace / output if output == "cover.png" else output
    with pytest.raises(media.MediaError, match=r"\.jpg or \.jpeg|local"):
        artwork.render_solution_thumbnail(spec, destination)


def test_complete_jpeg_is_written_before_atomic_replace(spec, workspace, monkeypatch):
    output = workspace / "thumbnail.jpg"
    output.write_bytes(b"previous thumbnail")
    real_replace = artwork.os.replace
    replacements = []

    def replace(partial, destination):
        assert destination == output
        assert output.read_bytes() == b"previous thumbnail"
        assert partial.parent == output.parent
        with Image.open(partial) as image:
            image.load()
            assert image.format == "JPEG" and image.size == (1280, 720)
        replacements.append(partial)
        real_replace(partial, destination)

    monkeypatch.setattr(artwork.os, "replace", replace)
    artwork.render_solution_thumbnail(spec, output)
    assert len(replacements) == 1
    assert not replacements[0].exists()
    assert output.read_bytes() != b"previous thumbnail"


@pytest.mark.parametrize("failure", ["encode", "replace"])
def test_failure_preserves_originals_old_output_and_unowned_files(
    spec, workspace, monkeypatch, failure,
):
    output = workspace / "thumbnail.jpg"
    output.write_bytes(b"previous thumbnail")
    unrelated = workspace / ".thumbnail.someone-else.tmp.jpg"
    unrelated.write_bytes(b"not owned by this render")
    before = {path.name: digest(path) for path in workspace.iterdir()}
    if failure == "encode":
        def fail_save(self, handle, **kwargs):
            handle.write(b"incomplete jpeg")
            raise OSError("encode failed")
        monkeypatch.setattr(Image.Image, "save", fail_save)
    else:
        def fail_replace(*args):
            raise OSError("replace failed")
        monkeypatch.setattr(artwork.os, "replace", fail_replace)
    with pytest.raises(media.MediaError, match="failed"):
        artwork.render_solution_thumbnail(spec, output)
    after = {path.name: digest(path) for path in workspace.iterdir()}
    assert after == before


def test_unowned_partial_collision_is_never_deleted(spec, workspace, monkeypatch):
    monkeypatch.setattr(artwork, "uuid4", lambda: SimpleNamespace(hex="collision"))
    unrelated = workspace / ".thumbnail.collision.tmp.jpg"
    unrelated.write_bytes(b"not owned by this render")
    with pytest.raises(media.MediaError, match="Could not write"):
        artwork.render_solution_thumbnail(spec, workspace / "thumbnail.jpg")
    assert unrelated.read_bytes() == b"not owned by this render"
    assert not (workspace / "thumbnail.jpg").exists()
