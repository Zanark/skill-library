"""Measured plain Consolas headings above editorial video feeds."""

from __future__ import annotations

from . import media
from .models import validate_question_title
from .solution_artwork import _load_font, _measure_text, _require_glyphs, _text_fits


def title_layout(text: str) -> dict:
    text = validate_question_title(text)
    font, provenance = _load_font(None)
    _require_glyphs(font, text)
    for size in range(72, 39, -2):
        block = _measure_text(text, font.font_variant(size=size), 972)
        if len(block.lines) <= 3 and _text_fits(block, 972, 196):
            return {
                "renderer": "question-title-1", "text": text, "font": provenance,
                "font_size": size, "lines": [line.strip() for line in block.lines],
                "bounds": [54, 48, 1026, 256], "center": [540, 152],
            }
    raise media.MediaError("The complete question title cannot fit above the feed; no text was omitted.")
