"""Evidence-bound, local-only landscape artwork for complete LeetCode solutions."""

from __future__ import annotations

import hashlib
import math
import os
import re
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PureWindowsPath
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont, ImageOps, __version__ as pillow_version
from pydantic import Field, HttpUrl, field_validator, model_validator

from . import media
from .models import Model
from .thumbnails import _width, _wrap_title

RENDERER_VERSION = "solution-artwork-v5"
_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF"}
_GREEN = "#36e16a"
_LIME_YELLOW = "#dfff00"


def _nonblank(value: str, label: str) -> str:
    if not value.strip():
        raise ValueError(f"{label} must not be blank.")
    return value


def _display_text(value: str, label: str) -> str:
    _nonblank(value, label)
    if any(ord(char) < 32 or ord(char) == 127 or char in "\u2028\u2029" for char in value):
        raise ValueError(f"{label} must be printable text without line breaks or controls.")
    return value


def _citation_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Source URL must be a valid http(s) citation URL.") from exc
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or any(char.isspace() or ord(char) < 32 for char in value)
        or "\\" in value or parsed.username is not None or parsed.password is not None
        or (port is not None and port < 1)
    ):
        raise ValueError("Source URL must be a valid http(s) citation URL.")
    try:
        HttpUrl(value)
    except ValueError as exc:
        raise ValueError("Source URL must be a valid http(s) citation URL.") from exc
    return value


def _local_path(value: str, label: str, *, absolute: bool = True) -> Path:
    if (
        value.startswith(("\\\\", "//")) or PureWindowsPath(value).drive.startswith("\\\\")
        or re.match(r"^[a-zA-Z][\w+.-]*://", value)
    ):
        raise ValueError(f"{label} must be a local file, not a URL or network share.")
    path = Path(value)
    if absolute and not path.is_absolute():
        raise ValueError(f"{label} must be an absolute local file path.")
    if not value.strip() or "\x00" in value:
        raise ValueError(f"{label} must be a local file path.")
    return path


class ComplexityEvidence(Model):
    notation: str
    display_notation: str | None = None
    source_kind: Literal["stream", "research"]
    evidence: str
    source_time: float | None = Field(default=None, ge=0)
    source_url: str | None = None

    @field_validator("notation")
    @classmethod
    def notation_text(cls, value: str) -> str:
        return _display_text(value, "Complexity notation")

    @field_validator("display_notation")
    @classmethod
    def cover_text(cls, value: str | None) -> str | None:
        return _display_text(value, "Display notation") if value is not None else None

    @field_validator("evidence")
    @classmethod
    def substantive_evidence(cls, value: str) -> str:
        if len(re.sub(r"\s+", "", value)) < 12 or len(value.split()) < 3:
            raise ValueError("Complexity evidence requires a substantive quote or cited reason.")
        return value

    @field_validator("source_url")
    @classmethod
    def citation(cls, value: str | None) -> str | None:
        return _citation_url(value) if value is not None else None

    @model_validator(mode="after")
    def source_evidence(self) -> ComplexityEvidence:
        if self.source_kind == "stream" and self.source_time is None:
            raise ValueError("Stream complexity requires a nonnegative source_time and quote.")
        if self.source_kind == "research" and self.source_url is None:
            raise ValueError("Research complexity requires an http(s) source_url and cited reason.")
        return self


class MemeAsset(Model):
    image: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str | None = None
    rights: Literal["user_provided", "licensed", "public_domain", "original"]
    rights_note: str
    attribution: str = ""
    topic: str
    search_query: str = ""

    @field_validator("image")
    @classmethod
    def local_image(cls, value: str) -> str:
        _local_path(value, "Meme image")
        return value

    @field_validator("source_url")
    @classmethod
    def citation(cls, value: str | None) -> str | None:
        return _citation_url(value) if value is not None else None

    @field_validator("rights_note", "topic")
    @classmethod
    def declaration(cls, value: str) -> str:
        return _nonblank(value, "Rights declaration and topic relevance")

    @field_validator("attribution")
    @classmethod
    def credit(cls, value: str) -> str:
        return _display_text(value, "Attribution") if value else value

    @model_validator(mode="after")
    def licensed_credit(self) -> MemeAsset:
        if self.rights == "licensed" and not self.attribution.strip():
            raise ValueError("Licensed meme images require attribution.")
        return self


class SolutionArtworkSpec(Model):
    problem_number: int = Field(gt=0, strict=True)
    problem_title: str = Field(min_length=1, max_length=220)
    technique: str | None = Field(default=None, min_length=1, max_length=120)
    complexity: ComplexityEvidence
    meme: MemeAsset
    font_path: str | None = None

    @field_validator("problem_title")
    @classmethod
    def exact_title(cls, value: str) -> str:
        return _display_text(value, "Problem title")

    @field_validator("technique")
    @classmethod
    def technique_text(cls, value: str | None) -> str | None:
        return _display_text(value, "Data structure / algorithm") if value is not None else None

    @field_validator("font_path")
    @classmethod
    def local_font(cls, value: str | None) -> str | None:
        if value is not None:
            _local_path(value, "Consolas font")
        return value


def _read_local(value: str, label: str) -> tuple[Path, bytes]:
    try:
        path = _local_path(value, label).resolve()
        _local_path(str(path), label)
        if not path.is_file():
            raise ValueError(f"{label} is not a readable local file: {path}")
        return path, path.read_bytes()
    except (OSError, ValueError) as exc:
        raise media.MediaError(f"Could not read {label}: {exc}") from exc


def _default_consolas() -> Path:
    if os.name != "nt":
        raise media.MediaError(
            "Consolas is required. Supply font_path to a permitted local Consolas font; "
            "there is no font fallback or bundled proprietary font."
        )
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "consola.ttf"


def _load_font(font_path: str | None) -> tuple[ImageFont.FreeTypeFont, dict]:
    candidate = font_path if font_path is not None else str(_default_consolas())
    try:
        path, data = _read_local(candidate, "Consolas font")
        font = ImageFont.truetype(BytesIO(data), size=64)
        family, style = font.getname()
        advances = [font.getlength(char) for char in "iMW0 ."]
        if family.casefold() != "consolas" or max(advances) - min(advances) > 0.01:
            raise ValueError("The supplied font must actually be the monospaced Consolas family.")
    except (OSError, ValueError, media.MediaError) as exc:
        raise media.MediaError(
            f"Consolas is required; no substitute font will be used. {exc}"
        ) from exc
    return font, {
        "path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
        "family": family, "style": style, "monospaced": True,
    }


def _require_glyphs(font: ImageFont.FreeTypeFont, text: str) -> None:
    missing = font.getmask("\U0010ffff")
    missing_signature = (missing.size, bytes(missing))
    for char in sorted(set(text)):
        if char.isspace():
            continue
        mask = font.getmask(char)
        if (mask.size, bytes(mask)) == missing_signature:
            raise media.MediaError(
                f"Consolas cannot render character U+{ord(char):04X}; "
                "the exact artwork text will not be silently replaced."
            )


def _cover_notation(complexity: ComplexityEvidence) -> str:
    value = (complexity.display_notation or complexity.notation).strip()
    opening = re.match(r"O\s*\(", value)
    if opening:
        depth = 1
        start = opening.end()
        for index in range(start, len(value)):
            if value[index] == "(":
                depth += 1
            elif value[index] == ")":
                depth -= 1
                if depth == 0:
                    qualifier = value[index + 1:].strip(" ,;").casefold().replace("-", " ")
                    if value[start:index].strip() and qualifier in {
                        "", "average", "average case", "expected", "expected time",
                        "amortized", "worst case", "best case",
                    }:
                        return "O(" + value[start:index] + ")"
                    break
    raise media.MediaError(
        "The cover needs one O(...) expression. Supply display_notation for a compound "
        "analysis; keep qualifications and full complexity evidence in the metadata/credits."
    )


@dataclass
class _Inputs:
    spec: SolutionArtworkSpec
    provenance: dict
    font: ImageFont.FreeTypeFont
    image: Image.Image


def _load_inputs(spec: SolutionArtworkSpec) -> _Inputs:
    if not isinstance(spec, SolutionArtworkSpec):
        raise media.MediaError("Solution artwork requires a SolutionArtworkSpec.")
    try:
        spec = SolutionArtworkSpec.model_validate(spec.model_dump(mode="json"))
    except ValueError as exc:
        raise media.MediaError(f"Invalid solution artwork specification: {exc}") from exc
    image_path, data = _read_local(spec.meme.image, "Meme image")
    image_hash = hashlib.sha256(data).hexdigest()
    if image_hash != spec.meme.sha256:
        raise media.MediaError("Meme image SHA256 does not match its pinned provenance.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                image_format = source.format
                native_size = list(source.size)
                if image_format not in _IMAGE_FORMATS:
                    raise ValueError("Use a supported PNG, JPEG, WebP, GIF, BMP or TIFF image.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Choose an explicit still image, not an animated/multipage meme.")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise media.MediaError(f"Could not decode the local meme image: {exc}") from exc
    try:
        font, font_info = _load_font(spec.font_path)
        display_notation = _cover_notation(spec.complexity)
        _require_glyphs(
            font, f"{spec.problem_number}. {spec.problem_title}"
            + (spec.technique or "") + display_notation[1:],
        )
    except Exception:
        image.close()
        raise
    complexity = spec.complexity.model_dump(mode="json")
    complexity.update({
        "display_notation": display_notation,
        "label": "Time complexity" if spec.complexity.source_kind == "stream"
        else "Best-known time complexity",
        "source_label": "Stream stated" if spec.complexity.source_kind == "stream" else "Research",
    })
    provenance = {
        "renderer_version": RENDERER_VERSION, "pillow_version": pillow_version,
        "spec": spec.model_dump(mode="json"),
        "title": f"{spec.problem_number}. {spec.problem_title}",
        "complexity": complexity,
        "font": font_info,
        "meme": {
            **spec.meme.model_dump(mode="json"), "image": str(image_path),
            "sha256": image_hash, "format": image_format,
            "native_size": native_size, "display_size": list(image.size), "fit": "contain",
        },
    }
    return _Inputs(spec, provenance, font, image)


def artwork_inputs(spec: SolutionArtworkSpec) -> dict:
    """Validate/hash local bytes and return JSON-safe cache inputs; never access a URL.

    Rights and complexity evidence are declarations supplied by the editor, not
    independently verified legal clearance or inferred algorithmic claims.
    """
    inputs = _load_inputs(spec)
    inputs.image.close()
    return inputs.provenance


@dataclass(frozen=True)
class _TextBlock:
    font: ImageFont.FreeTypeFont
    lines: list[str]
    line_height: int
    height: int


def _exact_lines(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    # Reuse the portrait balancer, but restore every original space at line breaks.
    # Joining these substrings recovers the literal title/notation, even for long words.
    balanced = _wrap_title(text, font, width)
    lines = []
    cursor = 0
    for line in balanced:
        remaining = sum(not char.isspace() for char in line)
        end = cursor
        while remaining:
            remaining -= not text[end].isspace()
            end += 1
        while end < len(text) and text[end].isspace():
            end += 1
        lines.append(text[cursor:end])
        cursor = end
    return lines


def _measure_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> _TextBlock:
    lines = _exact_lines(text, font, width)
    line_height = math.ceil(font.size * 1.18)
    text_height = (len(lines) - 1) * line_height + max(
        font.getbbox(line, anchor="lt")[3] for line in lines
    )
    return _TextBlock(font, lines, line_height, text_height)


def _text_fits(block: _TextBlock, width: int, height: int) -> bool:
    return block.height <= height and all(_width(line, block.font) <= width for line in block.lines)


def _fit_text(
    text: str, base_font: ImageFont.FreeTypeFont, width: int, height: int,
    maximum: int, minimum: int,
) -> _TextBlock:
    for size in range(maximum, minimum - 1, -1):
        block = _measure_text(text, base_font.font_variant(size=size), width)
        if _text_fits(block, width, height):
            return block
    raise media.MediaError("The full artwork text cannot fit; no title or notation was omitted.")


def _fit_heading(
    title: str, technique: str | None, base_font: ImageFont.FreeTypeFont,
    width: int, height: int, maximum: int, minimum: int, gap: int,
) -> tuple[_TextBlock, _TextBlock | None]:
    if technique is None:
        return _fit_text(title, base_font, width, height, maximum, minimum), None
    # Fit both together so wrapping never changes the exact three-pixel font difference.
    for size in range(maximum, minimum + 2, -1):
        heading = _measure_text(title, base_font.font_variant(size=size), width)
        label = _measure_text(technique, base_font.font_variant(size=size - 3), width)
        if (_text_fits(heading, width, height)
                and _text_fits(label, width, height - heading.height - gap)):
            return heading, label
    raise media.MediaError(
        "The full title and data structure / algorithm cannot fit at the required "
        "three-pixel font difference; no text was omitted."
    )


def _draw_text(
    draw: ImageDraw.ImageDraw, block: _TextBlock, x: int, y: int, color: str,
) -> list[list[int]]:
    bounds = []
    for index, line in enumerate(block.lines):
        left, top, right, bottom = block.font.getbbox(line, anchor="lt")
        line_y = y + index * block.line_height
        draw.text(
            (x - left, line_y - top), line, font=block.font, fill=color, anchor="lt",
        )
        bounds.append([x, line_y, x + right - left, line_y + bottom - top])
    return bounds


def _bounds(lines: list[list[int]]) -> list[int]:
    return [
        min(line[0] for line in lines), min(line[1] for line in lines),
        max(line[2] for line in lines), max(line[3] for line in lines),
    ]


@dataclass(frozen=True)
class _NotationBlock:
    font: ImageFont.FreeTypeFont
    text: str
    diameter: int
    gap: int
    baseline: int
    circle_top: int
    text_left: int
    text_bounds: tuple[int, int, int, int]
    height: int


def _fit_notation(
    notation: str, base_font: ImageFont.FreeTypeFont, width: int, height: int,
    maximum: int, minimum: int, diameter: int,
) -> _NotationBlock:
    text = notation[1:]
    gap = max(1, round(diameter * 0.07))
    for size in range(maximum, minimum - 1, -1):
        font = base_font.font_variant(size=size)
        left, top, right, bottom = font.getbbox(text, anchor="ls")
        text_height = bottom - top
        block_height = max(diameter, text_height)
        baseline = (block_height - text_height) // 2 - top
        circle_top = (block_height - diameter) // 2
        if diameter + gap + right - left <= width and block_height <= height:
            return _NotationBlock(
                font, text, diameter, gap, baseline, circle_top, left,
                (0, top + baseline, right - left, bottom + baseline), block_height,
            )
    raise media.MediaError("The full complexity expression cannot fit; no notation was omitted.")


def _draw_notation(canvas: Image.Image, block: _NotationBlock, x: int, y: int) -> dict:
    # A square, supersampled ring is circular regardless of the font's O glyph.
    diameter = block.diameter
    stroke = max(1, round(diameter * 5 / 216))
    ring = Image.new("RGBA", (diameter * 4, diameter * 4), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        (0, 0, diameter * 4 - 1, diameter * 4 - 1), outline=_GREEN,
        width=stroke * 4,
    )
    resized = ring.resize((diameter, diameter), Image.Resampling.LANCZOS)
    circle_y = y + block.circle_top
    canvas.paste(resized, (x, circle_y), resized)
    ring.close()
    resized.close()
    text_x = x + diameter + block.gap
    ImageDraw.Draw(canvas).text(
        (text_x - block.text_left, y + block.baseline), block.text,
        font=block.font, fill=_GREEN, anchor="ls",
    )
    circle_bounds = [x, circle_y, x + diameter, circle_y + diameter]
    left, top, right, bottom = block.text_bounds
    text_bounds = [text_x + left, y + top, text_x + right, y + bottom]
    return {
        "notation_bounds": _bounds([circle_bounds, text_bounds]),
        "notation_circle_bounds": circle_bounds,
        "notation_text_bounds": text_bounds,
        "notation_line_bounds": [_bounds([circle_bounds, text_bounds])],
        "notation_o_style": "drawn_circle",
        "notation_circle_stroke": stroke,
        "notation_font_size": block.font.size,
    }


def _compose(inputs: _Inputs, width: int, height: int) -> tuple[Image.Image, dict]:
    scale = min(width / 1280, height / 720)
    margin = max(10, round(48 * scale))
    gap = max(4, round(20 * scale))
    minimum = max(4, round(18 * scale))
    title_area = [margin, margin, width - margin, round(height * 0.36)]
    title, technique = _fit_heading(
        inputs.provenance["title"], inputs.spec.technique, inputs.font,
        title_area[2] - margin, title_area[3] - margin,
        max(minimum, round(64 * scale)), minimum, gap,
    )
    lower_top = title_area[3] + gap
    lower_bottom = height - margin
    left_width = round(width * 0.47) - margin
    complexity = inputs.provenance["complexity"]
    notation = _fit_notation(
        complexity["display_notation"], inputs.font, left_width, lower_bottom - lower_top,
        max(minimum, round(192 * scale)), minimum, round(216 * scale),
    )
    notation_y = min(
        lower_bottom - notation.height,
        max(lower_top, round(height * 0.70) - notation.height // 2),
    )
    meme_area = [round(width * 0.52), lower_top, width - margin, lower_bottom]
    if meme_area[2] <= meme_area[0] or meme_area[3] <= meme_area[1]:
        raise media.MediaError("There is not enough space to contain the full meme image.")
    photo = ImageOps.contain(
        inputs.image, (meme_area[2] - meme_area[0], meme_area[3] - meme_area[1]),
        method=Image.Resampling.LANCZOS,
    )
    photo_x, photo_y = meme_area[2] - photo.width, meme_area[3] - photo.height
    canvas = Image.new("RGB", (width, height), "#000000")
    canvas.paste(photo, (photo_x, photo_y), photo)
    draw = ImageDraw.Draw(canvas)
    title_bounds = _draw_text(draw, title, margin, margin, "#ffffff")
    technique_bounds = (
        _draw_text(draw, technique, margin, margin + title.height + gap, _LIME_YELLOW)
        if technique is not None else []
    )
    notation_layout = _draw_notation(canvas, notation, margin, notation_y)
    layout = {
        "title_area": title_area, "title_lines": title.lines,
        "title_line_bounds": title_bounds, "title_bounds": _bounds(title_bounds),
        "title_font_size": title.font.size,
        "technique_lines": technique.lines if technique is not None else [],
        "technique_line_bounds": technique_bounds,
        "technique_bounds": _bounds(technique_bounds) if technique_bounds else None,
        "technique_font_size": technique.font.size if technique is not None else None,
        "technique_color": _LIME_YELLOW if technique is not None else None,
        "complexity_label_lines": [], "complexity_label_bounds": None,
        "complexity_label_line_bounds": [],
        "notation_lines": [complexity["display_notation"]], **notation_layout,
        "source_label_lines": [], "source_label_bounds": None,
        "meme_area": meme_area,
        "meme_bounds": [photo_x, photo_y, photo_x + photo.width, photo_y + photo.height],
        "meme_native_size": list(inputs.image.size), "meme_fit": "contain",
        "attribution_lines": [], "attribution_line_bounds": [], "attribution_bounds": None,
    }
    photo.close()
    return canvas, layout


def _output_path(output: Path, inputs: _Inputs) -> Path:
    try:
        path = _local_path(str(output), "Thumbnail output", absolute=False).resolve()
        _local_path(str(path), "Thumbnail output")
        for source in (inputs.provenance["meme"]["image"], inputs.provenance["font"]["path"]):
            if path == Path(source) or (path.exists() and path.samefile(source)):
                raise ValueError("A solution thumbnail cannot overwrite its source image or font.")
        if path.suffix.lower() not in {".jpg", ".jpeg"}:
            raise ValueError("Solution thumbnail output must be a .jpg or .jpeg file.")
        return path
    except (OSError, ValueError) as exc:
        raise media.MediaError(str(exc)) from exc


def render_solution_thumbnail(
    spec: SolutionArtworkSpec, output: Path, *, width: int = 1280, height: int = 720,
) -> dict:
    """Atomically write a black landscape JPEG; bounds are [left, top, right, bottom]."""
    if (
        type(width) is not int or type(height) is not int
        or width < 320 or height < 180 or width <= height
    ):
        raise media.MediaError("Solution thumbnails require landscape dimensions of at least 320x180.")
    inputs = _load_inputs(spec)
    try:
        output = _output_path(output, inputs)
        image, layout = _compose(inputs, width, height)
    finally:
        inputs.image.close()
    partial = output.parent / f".{output.stem}.{uuid4().hex}.tmp.jpg"
    created = False
    try:
        media._make_parent(output)
        with partial.open("xb") as handle:
            created = True
            image.save(
                handle, format="JPEG", quality=95, subsampling=0, optimize=True, progressive=True,
            )
        os.replace(partial, output)
    except (OSError, ValueError) as exc:
        raise media.MediaError(f"Could not write the solution thumbnail JPEG: {exc}") from exc
    finally:
        image.close()
        if created:
            partial.unlink(missing_ok=True)
    return {
        **inputs.provenance, "width": width, "height": height, "format": "JPEG", "mode": "RGB",
        "text": {
            "title": inputs.provenance["title"],
            "technique": inputs.spec.technique or "",
            "notation": inputs.provenance["complexity"]["display_notation"],
            "complexity_label": "", "source_label": "", "attribution": "",
        },
        "layout": layout,
    }
