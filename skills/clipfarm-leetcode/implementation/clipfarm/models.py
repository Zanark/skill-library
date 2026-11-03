from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer, model_validator


def new_id() -> str:
    return uuid4().hex


def validate_question_title(value: str) -> str:
    if not value.strip() or len(value) > 120 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Question titles require 1-120 nonblank plain-text characters without control characters.")
    return value.strip()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EditorialCorrection(Model):
    text: str = Field(min_length=1, max_length=180)
    sources: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def reviewed_plain_text(self) -> EditorialCorrection:
        self.text = self.text.strip()
        if not self.text or any(ord(c) < 32 or ord(c) == 127 for c in self.text):
            raise ValueError("Editorial corrections require nonblank plain text without control characters.")
        if any(urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).hostname
               for url in self.sources):
            raise ValueError("Editorial corrections require public HTTP(S) reference URLs.")
        return self


class MediaInfo(Model):
    duration: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)
    has_audio: bool = True
    video_codec: str = ""


class Cue(Model):
    id: str = Field(default_factory=new_id)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_cue(self) -> Cue:
        self.text = self.text.strip()
        if not self.text or self.end <= self.start:
            raise ValueError("Caption text must be nonempty and end must be after start.")
        return self


class Region(Model):
    """Normalized source coordinates, after display rotation."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def fits(self) -> Region:
        if self.x + self.w > 1.000001 or self.y + self.h > 1.000001:
            raise ValueError("The source region must fit inside the video.")
        return self


class TrackPoint(Model):
    time: float = Field(ge=0)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    cut: bool = False


class Analysis(Model):
    layout: Literal["follow", "fit", "split"]
    confidence: float = Field(ge=0, le=1)
    message: str
    track: list[TrackPoint] = Field(default_factory=list)
    face_region: Region | None = None
    warnings: list[str] = Field(default_factory=list)


class Clip(Model):
    id: str = Field(default_factory=new_id, pattern=r"^[a-f0-9]{32}$")
    title: str = Field(default="Untitled clip", min_length=1, max_length=120)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    layout: Literal["auto", "follow", "fit", "split", "manual", "leetcode"] = "auto"
    focus_x: float = Field(default=0.5, ge=0, le=1)
    focus_y: float = Field(default=0.5, ge=0, le=1)
    camera_mode: Literal["required", "absent"] = "required"
    face_region: Region | None = None
    content_region: Region | None = None
    captions: bool = True
    caption_style: Literal["clean", "punchy"] = "clean"
    subtitle_y: float = Field(default=0.60, ge=0.2, le=0.88)
    results_zoom: bool = False
    question_title: str | None = Field(default=None, min_length=1, max_length=120)
    correction: EditorialCorrection | None = None
    analysis: Analysis | None = None
    reason: str = ""

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        if self.camera_mode == "required":
            result.pop("camera_mode", None)
        if self.question_title is None:
            result.pop("question_title", None)
        if self.correction is None:
            result.pop("correction", None)
        return result

    @model_validator(mode="after")
    def duration(self) -> Clip:
        if self.question_title is not None:
            self.question_title = validate_question_title(self.question_title)
            if self.layout != "leetcode":
                raise ValueError("Question titles require the explicit editorial feed layout.")
        if self.end <= self.start:
            raise ValueError("Clip end must be after its start.")
        if self.end - self.start > 180.001:
            raise ValueError("Clips are limited to 180 seconds for the shared vertical preset.")
        if self.camera_mode == "absent" and (self.layout != "leetcode" or self.face_region is not None):
            raise ValueError("An absent camera requires the LeetCode layout and no face_region.")
        if self.layout == "leetcode":
            if self.content_region is None or (self.camera_mode == "required" and self.face_region is None):
                raise ValueError("LeetCode requires explicit avatar and code/results regions.")
            if self.subtitle_y == 0.60:
                self.subtitle_y = 0.82
            if not 0.77 <= self.subtitle_y <= 0.88:
                raise ValueError("LeetCode subtitle_y must be between 0.77 and 0.88.")
        elif self.subtitle_y > 0.63:
            raise ValueError("Non-LeetCode subtitle_y must not exceed 0.63.")
        if self.correction is not None and (self.layout != "leetcode" or self.subtitle_y < 0.82):
            raise ValueError("Editorial corrections require the editorial layout and subtitle_y >= 0.82.")
        return self


class Project(Model):
    id: str = Field(default_factory=new_id, pattern=r"^[a-f0-9]{32}$")
    name: str
    source: str
    media: MediaInfo
    created_at: str
    cues: list[Cue] = Field(default_factory=list)
    clips: list[Clip] = Field(default_factory=list)
    transcript_note: str = ""
    revision: int = 0

    @model_validator(mode="after")
    def within_source(self) -> Project:
        if any(c.end > self.media.duration + 0.1 for c in self.clips):
            raise ValueError("A clip extends past the end of the source.")
        if len({c.id for c in self.clips}) != len(self.clips):
            raise ValueError("Clip IDs must be unique.")
        return self


class Job(Model):
    id: str = Field(default_factory=new_id, pattern=r"^[a-f0-9]{32}$")
    project_id: str
    clip_id: str | None = None
    kind: Literal["analyze", "preview", "export", "transcribe"]
    status: Literal["queued", "running", "completed", "failed", "cancelled", "interrupted"] = "queued"
    progress: float = 0
    message: str = "Queued"
    created_at: str
    output: str | None = None
    subtitles: str | None = None
    export_folder: str | None = Field(default=None, max_length=160)
    error: str | None = None
    revision: int = 0
