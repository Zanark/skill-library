"""Explicit, unspoken editor corrections with reserved space above spoken captions."""

from . import media
from .solution_artwork import _load_font, _measure_text, _require_glyphs, _text_fits


def correction_layout(text: str) -> dict:
    display = "EDITOR CORRECTION: " + text
    font, provenance = _load_font(None)
    _require_glyphs(font, display)
    for size in range(44, 33, -2):
        block = _measure_text(display, font.font_variant(size=size), 948)
        if len(block.lines) <= 4 and _text_fits(block, 948, 176):
            return {
                "renderer": "editor-correction-1", "text": text, "font": provenance,
                "font_size": size, "lines": [line.strip() for line in block.lines],
                "bounds": [54, 1292, 1026, 1476], "center": [540, 1384],
                "content_bottom": 0.66,
            }
    raise media.MediaError("The full editor correction cannot fit; shorten it without losing its meaning.")
