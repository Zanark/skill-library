"""Full-frame editorial render contracts, separate from the vertical studio preset."""

from __future__ import annotations

from pydantic import Field, model_validator

from .models import Model, Region


class SubtitleRegion(Region):
    """An editor-verified empty rectangle in the bottom portion of the recording."""

    @model_validator(mode="after")
    def bottom_space(self) -> SubtitleRegion:
        if self.y < 0.65 or self.h < 0.055 or self.w < 0.3:
            raise ValueError("Horizontal subtitles need bottom empty space: y >= 0.65, h >= 0.055, w >= 0.3.")
        return self


class HorizontalRenderSegment(Model):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    subtitle_region: SubtitleRegion
    captions: bool = True
    reason: str = ""

    @model_validator(mode="after")
    def ordered(self) -> HorizontalRenderSegment:
        if self.end <= self.start:
            raise ValueError("Horizontal segment end must be after its start.")
        return self
