"""Authored music suggestions, separate from rendered audio and verified handoffs."""

from __future__ import annotations

import html
from typing import Literal

from pydantic import AwareDatetime, Field, HttpUrl, field_validator

from .models import Model
from .posting import copy_field

RECOMMENDATION_FILE = "music-recommendation.json"


class MusicRecommendation(Model):
    schema_version: Literal[1] = 1
    kind: Literal["suggestion"] = "suggestion"
    song: str = Field(min_length=1, max_length=200)
    artist: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=300)
    reference_url: HttpUrl
    fit_reason: str = Field(min_length=1, max_length=1000)
    mix_guidance: str = Field(min_length=1, max_length=1000)
    video_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    recommended_by: str = Field(min_length=1, max_length=200)
    recommended_at: AwareDatetime

    @field_validator("song", "artist", "version", "fit_reason", "mix_guidance", "recommended_by")
    @classmethod
    def plain_text(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Music suggestions require nonblank plain text without control characters.")
        return value

    @field_validator("reference_url")
    @classmethod
    def public_reference(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("Music reference URLs must not contain credentials.")
        return value

    @property
    def search_text(self) -> str:
        return f"{self.artist} - {self.song}"


def recommendation_fields(record: MusicRecommendation, key: str, bundle_name: str, duration: float) -> str:
    name = html.escape(bundle_name, quote=True)
    return (
        '<section class="posting-text music-recommendation" aria-label="Suggested music to add yourself">'
        '<h3>Suggested music - add it yourself</h3>'
        f'<p><strong>{html.escape(record.song)} - {html.escape(record.artist)}</strong><br>'
        f'<span class="posting-note">Version: {html.escape(record.version)}</span></p>'
        f'<p><strong>Why this clip:</strong> {html.escape(record.fit_reason)}</p>'
        f'<p><strong>Mix:</strong> {html.escape(record.mix_guidance)}</p>'
        f'<p><a href="{html.escape(str(record.reference_url), quote=True)}" target="_blank" '
        'rel="noopener noreferrer">Listen / identify the recording</a> &middot; '
        f'<a href="{name}/{RECOMMENDATION_FILE}">Recommendation details</a></p>'
        + copy_field(record.search_text, f"{key}:music", "Search in Instagram / YouTube",
                     "Copy song search", rows=2)
        + '<p class="posting-note">Suggestion only; this export has no added music. '
        'Add the track separately in each app. Availability and current trend status are unverified. '
        f'Check that the permitted excerpt covers this {duration:.1f}s clip; '
        'do not cut teaching or loop music just to fit. Final volume balance is yours to audition.</p>'
        '</section>'
    )
