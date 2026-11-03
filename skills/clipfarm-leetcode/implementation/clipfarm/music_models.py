"""Explicit music-route attestations and conservative, speech-first edit settings."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, HttpUrl, field_validator, model_validator

from .models import Model


def _text(value: str, label: str, *, meaningful: bool = False, multiline: bool = False) -> str:
    if not value.strip():
        raise ValueError(f"{label} must not be blank.")
    allowed = "\r\n\t" if multiline else ""
    if any((ord(char) < 32 and char not in allowed) or ord(char) == 127 for char in value):
        raise ValueError(f"{label} must be plain text without control characters.")
    if meaningful and (len(value.strip()) < 20 or len(value.split()) < 3):
        raise ValueError(f"{label} needs a meaningful explanation of at least 20 characters.")
    return value


def _url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
        HttpUrl(value)
    except ValueError as exc:
        raise ValueError("Music evidence URLs must be valid HTTP(S) URLs.") from exc
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or (port is not None and port < 1) or "\\" in value
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Music evidence URLs must be valid HTTP(S) URLs without credentials.")
    return value


def _local_path(value: str) -> Path:
    _text(value, "Local file path")
    if (
        value.startswith(("\\\\", "//"))
        or PureWindowsPath(value).drive.startswith("\\\\")
        or re.match(r"^[a-zA-Z][\w+.-]*://", value)
        or not Path(value).is_absolute()
    ):
        raise ValueError("Music and proof files require absolute local disk paths, not URLs or shares.")
    if ":" in value[len(PureWindowsPath(value).drive):]:
        raise ValueError("Music and proof files must not use alternate data streams.")
    return Path(value)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Music evidence timestamps must be timezone-aware.")
    return value


def _age(value: datetime, now: datetime, label: str, max_days: int | None = None) -> None:
    elapsed = now - value
    if elapsed < timedelta(0):
        raise ValueError(f"{label} must not be in the future.")
    if max_days is not None and elapsed > timedelta(days=max_days):
        raise ValueError(f"{label} is stale; recheck within {max_days} days before use.")


class TrendEvidence(Model):
    observed_at: datetime
    region: str
    url: str
    note: str

    _timestamp = field_validator("observed_at")(_aware)
    _reference = field_validator("url")(_url)

    @field_validator("region")
    @classmethod
    def region_text(cls, value: str) -> str:
        return _text(value, "Trend region")

    @field_validator("note")
    @classmethod
    def meaningful_note(cls, value: str) -> str:
        return _text(value, "Trend evidence note", meaningful=True)


class MusicRights(Model):
    """An editor's documented attestation, not legal or platform-clearance validation."""

    scope: str
    usage: str
    territory: str
    checked_by: str
    checked_at: datetime
    expires_at: datetime | None = None
    license_url: str | None = None
    permission_note: str | None = None
    platforms: list[str] = Field(min_length=2)
    attribution_required: bool = Field(strict=True)
    attribution: str | None = None
    proof_file: str
    proof_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    _timestamp = field_validator("checked_at")(_aware)

    @field_validator("expires_at")
    @classmethod
    def expiry_time(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value is not None else None

    @field_validator("scope", "usage", "territory", "checked_by", "permission_note")
    @classmethod
    def declaration(cls, value: str | None) -> str | None:
        return _text(value, "Rights declaration") if value is not None else None

    @field_validator("license_url")
    @classmethod
    def reference(cls, value: str | None) -> str | None:
        return _url(value) if value is not None else None

    @field_validator("attribution")
    @classmethod
    def exact_credit(cls, value: str | None) -> str | None:
        return _text(value, "Attribution", multiline=True) if value is not None else None

    @field_validator("proof_file")
    @classmethod
    def local_proof(cls, value: str) -> str:
        _local_path(value)
        return value

    @field_validator("proof_sha256")
    @classmethod
    def canonical_hash(cls, value: str) -> str:
        return value.lower()

    @field_validator("platforms")
    @classmethod
    def platform_names(cls, values: list[str]) -> list[str]:
        names = [_text(value, "Platform").strip().lower() for value in values]
        if len(set(names)) != len(names):
            raise ValueError("Rights platforms must be unique.")
        if not {"instagram", "youtube"}.issubset(names):
            raise ValueError("Embedded music rights must cover BOTH instagram and youtube.")
        return names

    @model_validator(mode="after")
    def documented_permission(self) -> MusicRights:
        if self.license_url is None and self.permission_note is None:
            raise ValueError("Music rights need a license_url or a documented permission_note.")
        if self.attribution_required and self.attribution is None:
            raise ValueError("Required attribution must be supplied exactly as authorized.")
        if self.expires_at is not None and self.expires_at <= self.checked_at:
            raise ValueError("Music rights expires_at must be after checked_at.")
        return self


class MusicSpec(Model):
    route: Literal["embedded", "instagram"]
    title: str
    artist: str
    track_url: str | None = None
    start_seconds: float = Field(default=0.0, ge=0)
    bpm: float = Field(ge=40, le=240)
    beat_offset_seconds: float = Field(default=0.0, ge=0)
    beat_review: str
    file: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    rights: MusicRights | None = None
    native_checked_at: datetime | None = None
    region: str | None = None
    account_context: str | None = None
    trend: TrendEvidence | None = None
    trend_max_age_days: int = Field(default=7, ge=1, le=30, strict=True)

    @field_validator("title", "artist", "region", "account_context")
    @classmethod
    def named_text(cls, value: str | None) -> str | None:
        return _text(value, "Track and availability details") if value is not None else None

    @field_validator("beat_review")
    @classmethod
    def measured_grid(cls, value: str) -> str:
        return _text(value, "Human-measured beat review", meaningful=True)

    @field_validator("track_url")
    @classmethod
    def track_reference(cls, value: str | None) -> str | None:
        return _url(value) if value is not None else None

    @field_validator("file")
    @classmethod
    def local_track(cls, value: str | None) -> str | None:
        if value is not None:
            _local_path(value)
        return value

    @field_validator("sha256")
    @classmethod
    def canonical_hash(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("native_checked_at")
    @classmethod
    def availability_time(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value is not None else None

    @model_validator(mode="after")
    def route_contract(self) -> MusicSpec:
        if self.beat_offset_seconds >= 60 / self.bpm:
            raise ValueError("beat_offset_seconds must precede one beat period (60 / bpm).")
        if self.route == "embedded":
            if self.file is None or self.sha256 is None or self.rights is None:
                raise ValueError("Embedded music requires file, sha256, and documented rights.")
            if any(value is not None for value in (self.native_checked_at, self.region, self.account_context)):
                raise ValueError("Native availability fields belong only to the instagram route.")
        else:
            if any(value is not None for value in (self.file, self.sha256, self.rights)):
                raise ValueError("Instagram-native music forbids local file, sha256, and rights.")
            if any(value is None for value in (
                self.track_url, self.native_checked_at, self.region, self.account_context,
            )):
                raise ValueError("Instagram music requires track_url, native_checked_at, region, and account_context.")
        return self

    def validate_freshness(self, now: datetime | None = None) -> None:
        """Check at use, without inserting a moving timestamp into serialized signatures."""
        now = _aware(now if now is not None else datetime.now(timezone.utc))
        if self.trend is not None:
            _age(self.trend.observed_at, now, "Trend evidence", self.trend_max_age_days)
        if self.native_checked_at is not None:
            _age(self.native_checked_at, now, "Instagram availability check", 7)
        if self.rights is not None:
            _age(self.rights.checked_at, now, "Music rights check")
            if self.rights.expires_at is not None and now >= self.rights.expires_at:
                raise ValueError("Music rights have expired; obtain and document current permission before use.")


class BeatBoundary(Model):
    segment_index: int = Field(ge=0, strict=True)
    safe_tail_seconds: float = Field(default=0.0, ge=0, le=0.5)
    transition: Literal["cut", "dip"] = "cut"
    safety_note: str

    @field_validator("safety_note")
    @classmethod
    def editorial_safety(cls, value: str) -> str:
        return _text(value, "Boundary safety note", meaningful=True)


class StylizedEdit(Model):
    preset: Literal["speech-first"] = "speech-first"
    music: MusicSpec
    boundaries: list[BeatBoundary] = Field(default_factory=list)
    transition_frames: int = Field(default=4, ge=2, le=6, strict=True)
    music_gain_db: float = Field(default=-20.0, ge=-40, le=-6)
    duck_threshold: float = Field(default=0.025, ge=0.001, le=0.25)
    duck_ratio: float = Field(default=8.0, ge=2, le=20)
    attack_ms: float = Field(default=15.0, ge=5, le=100)
    release_ms: float = Field(default=350.0, ge=100, le=1000)
    fade_seconds: float = Field(default=0.5, ge=0.05, le=2)

    @model_validator(mode="after")
    def unique_boundaries(self) -> StylizedEdit:
        indexes = [boundary.segment_index for boundary in self.boundaries]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Beat boundaries must have unique segment_index values.")
        return self
