"""Portrait artwork with separate problem/topic text and an optional explicit camera."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import media
from .models import Region

_SIZE = (1080, 1920)
_BASE = "#002b36"
_PANEL = "#073642"
_CREAM = "#eee8d5"
_ACCENT = "#cd5c5c"
_CAMERA_BORDER = "#45616a"
_TITLE_WIDTH = 900
_TITLE_HEIGHT = 560
_CAMERA_SIZE = (948, 790)


def _font() -> ImageFont.FreeTypeFont:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidates = [windows / "segoeuib.ttf", windows / "arialbd.ttf"]
    if os.name != "nt":
        root = Path(os.sep)
        candidates.extend([
            root / "usr" / "share" / "fonts" / "truetype" / "dejavu" / "DejaVuSans-Bold.ttf",
            root / "usr" / "share" / "fonts" / "dejavu" / "DejaVuSans-Bold.ttf",
            root / "System" / "Library" / "Fonts" / "Supplemental" / "Arial Bold.ttf",
        ])
    candidates.append(Path("DejaVuSans-Bold.ttf"))
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size=120)
        except OSError:
            continue
    raise media.MediaError(
        "Thumbnail titles require an installed bold TrueType font: "
        "Segoe UI Bold, Arial Bold, or DejaVu Sans Bold."
    )


def _width(text: str, font: ImageFont.FreeTypeFont) -> int:
    left, _, right, _ = font.getbbox(text)
    return math.ceil(max(right - left, font.getlength(text)))


def _wrap_title(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    # Oversized words are split without adding hyphens or dropping any characters.
    pieces: list[tuple[str, bool]] = []
    for word in text.split():
        first = True
        while word:
            low, high = 1, len(word)
            while low < high:
                middle = (low + high + 1) // 2
                if _width(word[:middle], font) <= width:
                    low = middle
                else:
                    high = middle - 1
            if _width(word[:low], font) > width:
                raise media.MediaError("A title character cannot fit the thumbnail text area.")
            pieces.append((word[:low], first))
            word = word[low:]
            first = False

    # Prefer fewer lines, then balanced lengths rather than a tiny orphan last line.
    best: dict[int, tuple[int, int, list[str]]] = {len(pieces): (0, 0, [])}
    for start in range(len(pieces) - 1, -1, -1):
        line = ""
        options = []
        for end in range(start, len(pieces)):
            piece, space = pieces[end]
            line += (" " if end > start and space else "") + piece
            line_width = _width(line, font)
            if line_width > width:
                break
            count, cost, following = best[end + 1]
            options.append((count + 1, cost + (width - line_width) ** 2, [line, *following]))
        best[start] = min(options, key=lambda option: option[:2])
    return best[0][2]


@dataclass(frozen=True)
class _Title:
    font: ImageFont.FreeTypeFont
    lines: list[str]
    line_height: int
    height: int


def _fit_title(
    text: str, *, base_font: ImageFont.FreeTypeFont | None = None,
    max_size: int = 120, height_limit: int = _TITLE_HEIGHT, line_limit: int | None = None,
) -> _Title:
    base_font = base_font if base_font is not None else _font()
    max_lines = line_limit or (3 if len(text) <= 56 else 4 if len(text) <= 84 else 6)
    for limit in dict.fromkeys((max_lines, 6)):
        for size in range(max_size, 39, -2):
            font = base_font.font_variant(size=size)
            lines = _wrap_title(text, font, _TITLE_WIDTH)
            line_height = math.ceil(size * 1.12)
            height = (len(lines) - 1) * line_height + max(
                font.getbbox(line, anchor="lt")[3] for line in lines
            )
            if len(lines) <= limit and height <= height_limit:
                return _Title(font, lines, line_height, height)
    raise media.MediaError("The full title cannot fit the thumbnail; no text was omitted.")


def _extract_region(source: Path, at: float, region: Region) -> Image.Image:
    # Normalize display rotation/SAR before interpreting the explicit display-space
    # region. RGB plus exact=1 keeps odd-pixel crops free of chroma-grid rounding.
    crop = (
        f"crop=w='max(1,round(iw*{region.w:.12f}))':"
        f"h='max(1,round(ih*{region.h:.12f}))':"
        f"x='round(iw*{region.x:.12f})':y='round(ih*{region.y:.12f})':exact=1"
    )
    result = media._bounded(
        media._base() + ["-loglevel", "error", "-threads", "2", "-ss", f"{at:.6f}"]
        + media._PROTOCOLS + [
            "-i", str(source), "-map", "0:v:0", "-an", "-sn", "-dn",
            "-vf", f"{media._NORMALIZE},format=rgb24,{crop}",
            "-frames:v", "1", "-threads", "1", "-c:v", "png",
            "-f", "image2pipe", "pipe:1",
        ],
    )
    if not result.stdout:
        raise media.MediaError("No thumbnail source frame exists at that time.")
    try:
        with Image.open(BytesIO(result.stdout)) as frame:
            return frame.convert("RGB")
    except (OSError, ValueError) as exc:
        raise media.MediaError(f"Could not decode the thumbnail source frame: {exc}") from exc


def problem_topic_renderer(camera_mode: Literal["required", "absent"]) -> str:
    return {"required": "problem-topic-camera-3", "absent": "problem-topic-camera-1"}[camera_mode]


def _backdrop(shot: Image.Image | None = None, *, grain: bool = False) -> Image.Image:
    gradient = ImageOps.colorize(
        Image.linear_gradient("L").resize(_SIZE), black=_PANEL, white=_BASE,
    )
    if shot is None:
        return gradient
    backdrop = ImageOps.fit(shot, (270, 480), method=Image.Resampling.LANCZOS)
    backdrop = backdrop.filter(ImageFilter.GaussianBlur(22)).resize(
        _SIZE, Image.Resampling.LANCZOS,
    )
    result = Image.blend(gradient, backdrop, 0.18)
    if grain:
        noise = np.random.default_rng(23).normal(0, 1.2, (_SIZE[1], _SIZE[0], 1))
        pixels = np.asarray(result, dtype=np.float32) + np.clip(noise, -4, 4)
        result = Image.fromarray(np.rint(pixels).clip(0, 255).astype(np.uint8))
    return result


def _camera_card(
    canvas: Image.Image, photo: Image.Image, x: int, y: int, *, border: str,
) -> list[int]:
    card = [x - 16, y - 16, x + photo.width + 16, y + photo.height + 16]
    shadow = Image.new("L", _SIZE)
    ImageDraw.Draw(shadow).rounded_rectangle(
        [card[0] - 4, card[1] + 10, card[2] + 4, card[3] + 20], radius=30, fill=170,
    )
    canvas.paste("#001b22", (0, 0), shadow.filter(ImageFilter.GaussianBlur(24)))
    ImageDraw.Draw(canvas).rounded_rectangle(card, radius=26, fill=_PANEL, outline=border, width=2)
    # Keep every camera pixel, including the rectangular image's corners.
    canvas.paste(photo, (x, y))
    return card


def _compose(shot: Image.Image, title: _Title, *, camera_mode: str = "required") -> tuple[Image.Image, dict]:
    canvas = _backdrop(shot)
    subject = "content" if camera_mode == "absent" else "camera"
    photo = ImageOps.contain(shot, (948, 1050) if camera_mode == "absent" else _CAMERA_SIZE,
                            method=Image.Resampling.LANCZOS)
    gap = 90
    top = (_SIZE[1] - title.height - gap - photo.height) // 2
    photo_x = (_SIZE[0] - photo.width) // 2
    photo_y = top + title.height + gap
    shot_bounds = [photo_x, photo_y, photo_x + photo.width, photo_y + photo.height]
    _camera_card(canvas, photo, photo_x, photo_y, border=_CAMERA_BORDER)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [480, top + title.height + 34, 600, top + title.height + 40],
        radius=3, fill=_ACCENT,
    )

    line_bounds = []
    for index, line in enumerate(title.lines):
        left, upper, right, lower = title.font.getbbox(line, anchor="lt")
        x = (_SIZE[0] - (right - left)) // 2
        y = top + index * title.line_height
        draw.text((x - left, y - upper), line, font=title.font, fill=_CREAM, anchor="lt")
        line_bounds.append([x, y, x + right - left, y + lower - upper])
    layout = {
        "font": " ".join(title.font.getname()),
        "font_size": title.font.size,
        "title_lines": title.lines,
        "line_bounds": line_bounds,
        "title_bounds": [
            min(box[0] for box in line_bounds), top,
            max(box[2] for box in line_bounds), top + title.height,
        ],
        f"{subject}_bounds": shot_bounds,
        f"{subject}_native_size": list(shot.size),
        f"{subject}_fit": "contain",
    }
    return canvas, layout


def _compose_problem_topic(
    shot: Image.Image | None, problem: _Title, topic: _Title,
) -> tuple[Image.Image, dict]:
    canvas = _backdrop(shot, grain=shot is not None)
    boxes = [(90, 80, 990, 350), (90, 440, 990, 710)] if shot is not None else [
        (90, 400, 990, 760), (90, 900, 990, 1290),
    ]
    separators = [[310, 396, 770, 400]]
    if shot is None:
        separators = [[160, 818, 920, 822]]
    else:
        separators.append([310, 738, 770, 742])
    layout = {"font": " ".join(problem.font.getname()), "separators": separators}
    if shot is not None:
        photo = ImageOps.contain(shot, (948, 640), method=Image.Resampling.LANCZOS)
        x = (_SIZE[0] - photo.width) // 2
        y = 1104 - photo.height // 2
        card = _camera_card(canvas, photo, x, y, border=_CAMERA_BORDER)
        layout.update(camera_bounds=[x, y, x + photo.width, y + photo.height],
                      camera_native_size=list(shot.size), camera_fit="contain",
                      camera_card={"bounds": card, "border_color": _CAMERA_BORDER,
                                   "border_width": 2, "shadow_blur": 24},
                      background={"kind": "frosted-camera", "blend": 0.18, "blur_radius": 22,
                                  "grain": {"distribution": "gaussian", "sigma": 1.2,
                                            "max_delta": 4, "seed": 23}})
    draw = ImageDraw.Draw(canvas)
    for key, text, box in zip(("problem", "topic"), (problem, topic), boxes):
        top = box[1] + (box[3] - box[1] - text.height) // 2
        bounds = []
        for index, line in enumerate(text.lines):
            left, upper, right, lower = text.font.getbbox(line, anchor="lt")
            x = (_SIZE[0] - (right - left)) // 2
            y = top + index * text.line_height
            draw.text((x - left, y - upper), line, font=text.font, fill=_CREAM, anchor="lt")
            bounds.append([x, y, x + right - left, y + lower - upper])
        layout[key] = {
            "font": " ".join(text.font.getname()), "font_size": text.font.size,
            "lines": text.lines, "line_bounds": bounds, "area": list(box),
        }
    for separator in separators:
        draw.rectangle(separator, fill=_ACCENT)
    return canvas, layout


def render_thumbnail(
    source: Path, at: float | None, region: Region | None, title: str, output: Path,
    *, camera_mode: Literal["required", "absent"] = "required",
    font_family: Literal["default", "Consolas"] = "default",
    topic: str | None = None,
) -> dict:
    """Atomically write a 1080x1920 JPEG containing the selected crop and full title.

    With ``topic``, the two distinct text blocks use genuine Consolas. An absent
    camera then requires ``at=None, region=None`` and produces a text-only cover.
    Without ``topic``, the original single-title/content-shot format is preserved.
    ``at`` is a source-timeline time; ``region`` is an explicit normalized crop in
    autorotated, square-pixel display coordinates. A camera crop is required unless
    ``camera_mode="absent"`` explicitly selects a relevant content crop instead.
    No face detection or time selection is performed. Returned layout bounds use
    [left, top, right, bottom].
    """
    source = media._source(source)
    text_only = topic is not None and camera_mode == "absent"
    timestamp = None
    if text_only:
        if at is not None or region is not None:
            raise media.MediaError("A text-only thumbnail must not claim a source time or image crop.")
    else:
        try:
            timestamp = float(at)
        except (TypeError, ValueError, OverflowError) as exc:
            raise media.MediaError("Thumbnail time must be a finite, nonnegative number.") from exc
        if isinstance(at, bool) or not math.isfinite(timestamp) or timestamp < 0:
            raise media.MediaError("Thumbnail time must be a finite, nonnegative number.")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise media.MediaError("Thumbnail title must contain 1 to 120 characters of nonempty text.")
    if camera_mode not in ("required", "absent"):
        raise media.MediaError("Thumbnail camera_mode must be 'required' or explicitly 'absent'.")
    if topic is not None:
        if (not isinstance(topic, str) or not topic.strip() or len(topic) > 240
                or any(ord(char) < 32 for char in topic)):
            raise media.MediaError("Thumbnail topic must contain 1 to 240 characters of plain nonempty text.")
        if " ".join(topic.split()).casefold() == " ".join(title.split()).casefold():
            raise media.MediaError("Thumbnail topic must describe the clip's focus, not repeat the problem name.")
    subject = "content" if camera_mode == "absent" else "camera"
    if not text_only:
        if not isinstance(region, Region):
            raise media.MediaError(f"A thumbnail requires an explicit {subject} Region.")
        try:
            region = Region.model_validate(region.model_dump())
        except ValueError as exc:
            raise media.MediaError(f"Invalid thumbnail {subject} region: {exc}") from exc
    if str(output).startswith(("\\\\", "//")):
        raise media.MediaError("Choose a local thumbnail output, not a network share.")
    output = Path(output).expanduser().resolve()
    if output == source or (output.exists() and output.samefile(source)):
        raise media.MediaError("A thumbnail cannot overwrite its source.")
    if output.suffix.lower() not in {".jpg", ".jpeg"}:
        raise media.MediaError("Thumbnail output must be a .jpg or .jpeg file.")

    if font_family not in ("default", "Consolas"):
        raise media.MediaError("Thumbnail font_family must be default or Consolas.")
    base_font = None
    if font_family == "Consolas" or topic is not None:
        from .solution_artwork import _load_font, _require_glyphs

        base_font, _ = _load_font(None)
        _require_glyphs(base_font, title)
        if topic is not None:
            _require_glyphs(base_font, topic)
    if topic is not None:
        fitted_title = _fit_title(" ".join(title.split()), base_font=base_font,
                                 max_size=104 if text_only else 64,
                                 height_limit=360 if text_only else 270)
        fitted_topic = _fit_title(" ".join(topic.split()), base_font=base_font,
                                 max_size=88 if text_only else 68,
                                 height_limit=390 if text_only else 270, line_limit=9)
    else:
        fitted_title = _fit_title(" ".join(title.split()), base_font=base_font)
    shot = None
    if not text_only:
        assert timestamp is not None and region is not None
        shot = _extract_region(source, timestamp, region)
    if topic is not None:
        image, layout = _compose_problem_topic(shot, fitted_title, fitted_topic)
    else:
        assert shot is not None
        image, layout = _compose(shot, fitted_title, camera_mode=camera_mode)
    media._make_parent(output)
    partial = output.parent / f".{output.stem}.{uuid4().hex}.tmp.jpg"
    created = False
    try:
        with partial.open("xb") as handle:
            created = True
            image.save(
                handle, format="JPEG", quality=95, subsampling=0, optimize=True, progressive=True,
            )
        os.replace(partial, output)
    except OSError as exc:
        raise media.MediaError(f"Could not write the thumbnail JPEG: {exc}") from exc
    finally:
        if created:
            partial.unlink(missing_ok=True)
    return {
        "width": _SIZE[0], "height": _SIZE[1], "title": title,
        "source_time": timestamp, "layout": layout,
        **({f"{subject}_region": region.model_dump()} if region is not None else {}),
        **({"topic": topic, "renderer": problem_topic_renderer(camera_mode),
            "camera_mode": camera_mode, "shot_kind": "none" if text_only else "camera"}
           if topic is not None else
           {"camera_mode": "absent", "shot_kind": "content"} if camera_mode == "absent" else {}),
    }
