from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, Field, SerializerFunctionWrapHandler, field_validator, model_serializer, model_validator

from .horizontal_models import SubtitleRegion
from .models import Cue, EditorialCorrection, MediaInfo, Model, Region, validate_question_title
from .music_models import StylizedEdit
from .solution_artwork import SolutionArtworkSpec

SAFE_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,79}$"


class TimeRange(Model):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    reason: str = ""

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("Range end must be after its start.")
        return self


class WorkflowSegment(TimeRange):
    view: Literal["code", "results"] = "code"
    face_region: Region | None = None
    content_region: Region | None = None
    subtitle_region: SubtitleRegion | None = None
    trim_silence: bool | None = None
    correction: EditorialCorrection | None = None

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        # Old vertical cut signatures must survive the addition of opt-in fields.
        for key in ("subtitle_region", "trim_silence", "correction"):
            if result.get(key) is None:
                result.pop(key, None)
        return result


class VisualEvidence(Model):
    time: float = Field(ge=0)
    image: str
    description: str
    kind: Literal["layout", "brb", "submission", "results", "introduction", "implementation",
                  "completion", "subtitle_space"]
    verified_by: str = ""
    runtime_ms: float | None = Field(default=None, ge=0)


class WorkflowProfile(Model):
    show_question_title: bool = False
    camera_mode: Literal["required", "absent"] = "required"
    face_region: Region | None = None
    code_region: Region | None = None
    results_region: Region | None = None
    subtitle_y: float = Field(default=0.82, ge=0.77, le=0.88)
    caption_style: Literal["clean", "punchy"] = "clean"

    @model_validator(mode="after")
    def camera_declaration(self) -> WorkflowProfile:
        if self.camera_mode == "absent" and self.face_region is not None:
            raise ValueError("An absent camera cannot have a face_region.")
        return self

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        # Preserve every existing camera-present profile and cut signature.
        if self.camera_mode == "required":
            result.pop("camera_mode", None)
        if not self.show_question_title:
            result.pop("show_question_title", None)
        return result


class HorizontalOptions(Model):
    chapter: TimeRange
    artwork: SolutionArtworkSpec
    subtitle_region: SubtitleRegion
    preserve_ranges: list[TimeRange] = Field(default_factory=list)
    coverage_review: str = ""
    subtitle_review: str = ""
    intro_hold_seconds: float = Field(default=1.0, ge=0, le=10)

    @model_validator(mode="after")
    def frame_aligned_hold(self) -> HorizontalOptions:
        frames = self.intro_hold_seconds * 30
        if abs(frames - round(frames)) > 1e-6:
            raise ValueError("The thumbnail hold must use whole 30 fps frames.")
        return self


class WorkflowCut(Model):
    id: str = Field(pattern=SAFE_ID_PATTERN)
    title: str = Field(min_length=1, max_length=240)
    category: Literal["explanation", "submission", "funny", "solution"]
    problem: str = ""
    question_title: str | None = Field(default=None, min_length=1, max_length=120)
    rationale: str = Field(min_length=1)
    segments: list[WorkflowSegment] = Field(min_length=1, max_length=100)
    trim_silence: bool = True
    coherence_review: str = ""
    evidence: list[VisualEvidence] = Field(default_factory=list)
    source_cues: list[Cue] | None = Field(default=None, min_length=1)
    horizontal: HorizontalOptions | None = None
    stylized: StylizedEdit | None = None

    @model_validator(mode="after")
    def plain_question_title(self) -> WorkflowCut:
        if self.question_title is not None:
            self.question_title = validate_question_title(self.question_title)
        return self

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        if result.get("horizontal") is None:
            result.pop("horizontal", None)
        if self.question_title is None:
            result.pop("question_title", None)
        if self.stylized is None:
            result.pop("stylized", None)
        else:
            result["stylized"] = self.stylized.model_dump(mode="json")
        return result


class DeliverySession(Model):
    requested_at: AwareDatetime
    timestamp_source: Literal["prompt", "cli"] = "prompt"
    notice: str = ""

    @field_validator("requested_at", mode="before")
    @classmethod
    def iso_timestamp(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError("Delivery timestamps require a timezone-aware ISO datetime, not a numeric epoch.")
        return value

    @field_validator("requested_at")
    @classmethod
    def local_request_time(cls, value: datetime) -> datetime:
        return value.astimezone(timezone(timedelta(hours=5, minutes=30)))

    @property
    def directory_name(self) -> str:
        return f"session_{self.requested_at:%Y%m%d_%H%M%S_%f}"


class WorkflowPlan(Model):
    schema_version: Literal[1] = 1
    workflow: Literal["leetcode", "system-design"] = "leetcode"
    output_format: Literal["vertical", "horizontal"] = "vertical"
    clip_policy: Literal["coverage-first-v1"] | None = None
    delivery: DeliverySession | None = None
    run_id: str = Field(pattern=SAFE_ID_PATTERN)
    source: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    transcript: str
    transcript_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    cues_sha256: str = Field(default="", pattern=r"^(?:[a-f0-9]{64})?$")
    media: MediaInfo
    profile: WorkflowProfile = Field(default_factory=WorkflowProfile)
    reviewed_entire_transcript: bool = False
    editorial_notes: str = ""
    exclusions: list[TimeRange] = Field(default_factory=list)
    evidence: list[VisualEvidence] = Field(default_factory=list)
    cuts: list[WorkflowCut] = Field(default_factory=list)

    @model_serializer(mode="wrap")
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        if self.clip_policy is None:
            result.pop("clip_policy", None)
        if self.delivery is None:
            result.pop("delivery", None)
        else:
            result["delivery"] = self.delivery.model_dump(mode="json")
        return result

    @model_validator(mode="after")
    def source_bounds(self):
        if self.output_format == "horizontal" and self.profile.show_question_title:
            raise ValueError("Persistent question headers are vertical-only; horizontal artwork/layout is unchanged.")
        if self.workflow == "system-design" and self.output_format != "vertical":
            raise ValueError("System Design currently supports vertical output only.")
        if self.output_format == "horizontal" and any(c.stylized for c in self.cuts):
            raise ValueError("Speech-first music finishing is vertical-only; horizontal solves remain unchanged.")
        if len({cut.id for cut in self.cuts}) != len(self.cuts):
            raise ValueError("Workflow cut IDs must be unique.")
        ranges = (self.exclusions + [segment for cut in self.cuts for segment in cut.segments]
                  + [cue for cut in self.cuts for cue in cut.source_cues or []]
                  + [cut.horizontal.chapter for cut in self.cuts if cut.horizontal]
                  + [r for cut in self.cuts if cut.horizontal for r in cut.horizontal.preserve_ranges])
        if any(r.end > self.media.duration + 0.05 for r in ranges):
            raise ValueError("A workflow range extends beyond the source.")
        evidence = self.evidence + [item for cut in self.cuts for item in cut.evidence]
        if any(item.time >= self.media.duration for item in evidence):
            raise ValueError("Visual evidence must be within the source.")
        if self.output_format == "horizontal" and self.media.width <= self.media.height:
            raise ValueError("Horizontal complete solves require a landscape source; its original layout is preserved.")
        if self.profile.camera_mode == "absent":
            if self.output_format != "vertical":
                raise ValueError("The absent-camera composition is only for vertical plans.")
            if self.profile.face_region is not None or any(
                s.face_region is not None for cut in self.cuts for s in cut.segments
            ):
                raise ValueError("An absent camera cannot have profile or segment face_region crops.")
        if self.output_format == "horizontal" and (
            self.clip_policy is not None or any(s.correction for c in self.cuts for s in c.segments)
        ):
            raise ValueError("Coverage-first budgets and editorial corrections are vertical-only.")
        return self
