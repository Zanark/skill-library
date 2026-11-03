from __future__ import annotations

import hashlib
import json
import shutil
import threading
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from pydantic import ValidationError

from clipfarm import media, music
from clipfarm.music_models import BeatBoundary, MusicRights, MusicSpec, StylizedEdit, TrendEvidence


@pytest.fixture
def workspace():
    root = Path(__file__).resolve().parents[1] / ".clipfarm" / "music-tests" / uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc) - timedelta(minutes=1)


def native_data():
    return {
        "route": "instagram", "title": "Synthetic study", "artist": "Test author",
        "track_url": "https://www.instagram.com/reels/audio/123/",
        "bpm": 120, "beat_review": "Editor measured twelve evenly spaced beats in the selected excerpt.",
        "native_checked_at": timestamp(), "region": "IN",
        "account_context": "Creator account; organic personal post checked manually.",
    }


def rights_data(workspace):
    proof = workspace / "permission.txt"
    proof.write_text("Original synthetic test tones; not a license for any third-party track.", encoding="utf-8")
    return {
        "scope": "Original synthetic tones only", "usage": "Automated local rendering tests",
        "territory": "Worldwide", "checked_by": "Test author", "checked_at": timestamp(),
        "permission_note": "I created these synthetic test tones for local regression tests.",
        "platforms": ["instagram", "youtube"], "attribution_required": True,
        "attribution": "  Synthetic study - Test author\nOriginal test-only tones.  ",
        "proof_file": str(proof), "proof_sha256": digest(proof),
    }


def write_wav(path, samples, rate=48000):
    values = np.asarray(samples)
    if values.ndim == 1:
        values = np.column_stack((values, values))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(values.shape[1])
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(np.round(values * 32767).astype("<i2").tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as source:
        assert source.getframerate() == 48000
        assert source.getsampwidth() == 2
        channels = source.getnchannels()
        return np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").reshape(-1, channels) / 32768


def embedded_data(workspace, *, seconds=5, rate=48000):
    track = workspace / "original tone with spaces.wav"
    time = np.arange(round(seconds * rate)) / rate
    write_wav(track, 0.25 * np.sin(2 * np.pi * 1000 * time), rate)
    return {
        "route": "embedded", "title": "Synthetic study", "artist": "Test author",
        "bpm": 120, "beat_review": "Editor measured twelve evenly spaced beats in the selected excerpt.",
        "file": str(track), "sha256": digest(track), "rights": rights_data(workspace),
    }


def style_for(data, **settings):
    return StylizedEdit(music=MusicSpec.model_validate(data), **settings)


def ffmpeg(workspace, duration, *arguments):
    media._run(
        media._base() + ["-loglevel", "error", "-threads", "1", "-filter_complex_threads", "1"]
        + list(map(str, arguments)) + ["-progress", "pipe:1", "-nostats"],
        workspace, duration, lambda *_: None, threading.Event(),
    )


def render_mix(workspace, style, track, duration, source=None):
    output = workspace / f"mix-{uuid4().hex}.wav"
    # A silent lavfi input occupies index 0 when the source has no audio stream.
    arguments = (media._PROTOCOLS + ["-i", source]) if source is not None else [
        "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={duration:.12f}",
    ]
    ffmpeg(
        workspace, duration, *arguments, *media._PROTOCOLS, "-i", track,
        "-filter_complex", music.audio_graph(style, duration, source is not None),
        "-map", "[music_mix]", "-c:a", "pcm_s16le", "-n", output,
    )
    return read_wav(output)


def test_model_defaults_and_stable_inputs_without_local_assets():
    style = style_for(native_data())
    assert style.preset == "speech-first" and style.boundaries == []
    assert style.transition_frames == 4 and style.music_gain_db == -20
    assert style.duck_threshold == 0.025 and style.duck_ratio == 8
    assert style.attack_ms == 15 and style.release_ms == 350 and style.fade_seconds == 0.5
    assert style.music.start_seconds == 0 and style.music.beat_offset_seconds == 0
    assert style.music.trend_max_age_days == 7
    assert music.inputs(style) == music.inputs(style)
    assert music.inputs(style)["assets"] == {}
    assert music.inputs(style)["renderer"] == music.RENDERER_VERSION
    assert StylizedEdit.model_validate_json(style.model_dump_json()) == style
    assert StylizedEdit.model_validate_json(style.model_dump_json()).model_dump_json() == style.model_dump_json()


@pytest.mark.parametrize("field,value", [
    ("title", " "), ("artist", "\t"), ("track_url", ""), ("region", "\n"),
    ("account_context", " "), ("beat_review", "                x                 "),
    ("beat_review", "xxxxxxxxxxxxxxxxxxxxxxxx"), ("bpm", 39.9), ("bpm", 241),
    ("bpm", float("nan")), ("start_seconds", -0.1), ("start_seconds", float("inf")),
    ("beat_offset_seconds", -0.1), ("beat_offset_seconds", 0.5),
    ("native_checked_at", datetime(2026, 1, 1)), ("native_checked_at", None),
    ("trend_max_age_days", 0), ("trend_max_age_days", 31), ("trend_max_age_days", True),
    ("unexpected", "extra"),
])
def test_invalid_music_fields(field, value):
    data = native_data()
    data[field] = value
    with pytest.raises(ValidationError):
        MusicSpec.model_validate(data)


@pytest.mark.parametrize("url", [
    "file:///C:/music.wav", "https://", "ftp://example.org/track", "https://user:pass@example.org",
    " https://example.org", "https://example.org/path name", "https://example.org:99999/",
    "https:\\\\example.org", "https://example.org/\n", "https://example.org:0/",
])
def test_invalid_urls(url):
    data = native_data()
    data["track_url"] = url
    with pytest.raises(ValidationError):
        MusicSpec.model_validate(data)


@pytest.mark.parametrize("missing", ["track_url", "native_checked_at", "region", "account_context"])
def test_native_route_requires_availability_details(missing):
    data = native_data()
    del data[missing]
    with pytest.raises(ValidationError):
        MusicSpec.model_validate(data)


@pytest.mark.parametrize("field", ["file", "sha256", "rights"])
def test_native_route_forbids_embedded_fields(workspace, field):
    embedded = embedded_data(workspace)
    data = native_data()
    data[field] = embedded[field]
    with pytest.raises(ValidationError, match="forbids"):
        MusicSpec.model_validate(data)


@pytest.mark.parametrize("missing", ["file", "sha256", "rights"])
def test_embedded_route_requires_local_rights(workspace, missing):
    data = embedded_data(workspace)
    del data[missing]
    with pytest.raises(ValidationError):
        MusicSpec.model_validate(data)


def test_embedded_route_rejects_native_attestation(workspace):
    data = embedded_data(workspace)
    data["region"] = "IN"
    with pytest.raises(ValidationError, match="Native availability"):
        MusicSpec.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("scope", " "), ("usage", ""), ("territory", "\t"), ("checked_by", " "),
    ("checked_at", datetime(2026, 1, 1)), ("license_url", ""), ("permission_note", " "),
    ("platforms", ["instagram"]), ("platforms", ["instagram", " "]),
    ("platforms", ["instagram", "youtube", "YouTube"]),
    ("attribution", None), ("attribution", ""), ("attribution", " \t "),
    ("attribution_required", "yes"), ("proof_sha256", "x" * 64),
    ("proof_sha256", "a" * 63), ("extra", True),
])
def test_rights_reject_incomplete_attestations(workspace, field, value):
    data = rights_data(workspace)
    data[field] = value
    with pytest.raises(ValidationError):
        MusicRights.model_validate(data)


def test_rights_license_or_permission_and_optional_credit(workspace):
    data = rights_data(workspace)
    del data["permission_note"]
    with pytest.raises(ValidationError, match="license_url"):
        MusicRights.model_validate(data)
    data["license_url"] = "https://example.org/license"
    data["attribution_required"] = False
    del data["attribution"]
    data["platforms"] = ["Instagram", "YouTube"]
    rights = MusicRights.model_validate(data)
    assert rights.platforms == ["instagram", "youtube"]
    assert rights.attribution is None
    data["attribution"] = " "
    with pytest.raises(ValidationError):
        MusicRights.model_validate(data)


@pytest.mark.parametrize("provider_note", [
    "Available through Meta Sound Collection.",
    "Available through the Instagram music library.",
    "Available through the YouTube Audio Library.",
])
def test_provider_access_never_supplies_cross_platform_permission(workspace, provider_note):
    data = rights_data(workspace)
    data["permission_note"] = provider_note
    del data["platforms"]
    with pytest.raises(ValidationError, match="platforms"):
        MusicRights.model_validate(data)
    data["platforms"] = ["instagram"]
    with pytest.raises(ValidationError):
        MusicRights.model_validate(data)


@pytest.mark.parametrize("path", [
    "relative.wav", "\\\\server\\share\\track.wav", "//server/share/track.wav",
    "https://example.org/track.wav", "file:///C:/track.wav", "\\\\?\\C:\\track.wav",
    "C:\\track.wav:hidden", " ", "C:\\track\x00.wav",
])
def test_local_track_and_proof_path_policy(workspace, path):
    data = embedded_data(workspace)
    data["file"] = path
    with pytest.raises(ValidationError):
        MusicSpec.model_validate(data)
    rights = rights_data(workspace)
    rights["proof_file"] = path
    with pytest.raises(ValidationError):
        MusicRights.model_validate(rights)


def trend_data(when=None):
    return {
        "observed_at": when if when is not None else timestamp(), "region": "IN",
        "url": "https://example.org/regional-observation",
        "note": "Editor observed this track in a specific regional music chart.",
    }


@pytest.mark.parametrize("field,value", [
    ("observed_at", datetime(2026, 1, 1)), ("region", " "), ("url", ""),
    ("note", "short"), ("note", "                    "),
])
def test_trend_evidence_requires_meaningful_details(field, value):
    data = trend_data()
    data[field] = value
    with pytest.raises(ValidationError):
        TrendEvidence.model_validate(data)


def test_freshness_checked_at_use_not_during_serialization():
    now = datetime.now(timezone.utc)
    data = native_data()
    data["native_checked_at"] = now - timedelta(days=6)
    data["trend"] = trend_data(now - timedelta(days=2))
    spec = MusicSpec.model_validate(data)
    original = spec.model_dump_json()
    spec.validate_freshness(now)
    with pytest.raises(ValueError, match="stale"):
        spec.validate_freshness(now + timedelta(days=2))
    assert spec.model_dump_json() == original
    with pytest.raises(ValueError, match="timezone-aware"):
        spec.validate_freshness(datetime(2026, 1, 1))


@pytest.mark.parametrize("which", ["native_future", "native_stale", "trend_future", "trend_stale", "rights_future"])
def test_inputs_reject_stale_or_future_evidence(workspace, which):
    now = datetime.now(timezone.utc)
    data = embedded_data(workspace) if which == "rights_future" else native_data()
    if which.startswith("native"):
        data["native_checked_at"] = now + (
            timedelta(days=1) if which.endswith("future") else -timedelta(days=8)
        )
    elif which.startswith("trend"):
        data["trend_max_age_days"] = 2
        data["trend"] = trend_data(now + (
            timedelta(days=1) if which.endswith("future") else -timedelta(days=3)
        ))
    else:
        data["rights"]["checked_at"] = now + timedelta(days=1)
    style = style_for(data)
    with pytest.raises(ValueError, match="future|stale"):
        music.inputs(style)


def test_exact_freshness_boundaries():
    now = datetime.now(timezone.utc)
    data = native_data()
    data["native_checked_at"] = now - timedelta(days=7)
    data["trend"] = trend_data(now - timedelta(days=30))
    data["trend_max_age_days"] = 30
    spec = MusicSpec.model_validate(data)
    spec.validate_freshness(now)
    with pytest.raises(ValueError, match="stale"):
        spec.validate_freshness(now + timedelta(microseconds=1))


@pytest.mark.parametrize("field,value", [
    ("segment_index", -1), ("segment_index", True), ("segment_index", 1.5),
    ("safe_tail_seconds", -0.1), ("safe_tail_seconds", 0.501),
    ("transition", "flash"), ("safety_note", "too short"),
    ("safety_note", "                           "), ("extra", 1),
])
def test_boundary_validation(field, value):
    data = {"segment_index": 0, "safety_note": "The preceding thought finishes before this silent tail."}
    data[field] = value
    with pytest.raises(ValidationError):
        BeatBoundary.model_validate(data)


def test_unique_boundaries_and_defaults():
    boundary = BeatBoundary(segment_index=0, safety_note="The thought finishes before this silent tail.")
    assert boundary.transition == "cut" and boundary.safe_tail_seconds == 0
    with pytest.raises(ValidationError, match="unique"):
        style_for(native_data(), boundaries=[boundary, boundary])


@pytest.mark.parametrize("field,value", [
    ("preset", "energetic"), ("transition_frames", 1), ("transition_frames", 7),
    ("transition_frames", True), ("music_gain_db", -41), ("music_gain_db", -5.9),
    ("music_gain_db", float("nan")), ("duck_threshold", 0), ("duck_threshold", 0.26),
    ("duck_ratio", 1), ("duck_ratio", 21), ("attack_ms", 4), ("attack_ms", 101),
    ("release_ms", 99), ("release_ms", 1001), ("fade_seconds", 0.049),
    ("fade_seconds", 2.01), ("extra", True),
])
def test_style_bounds(field, value):
    with pytest.raises(ValidationError):
        style_for(native_data(), **{field: value})


def test_embedded_inputs_bind_verified_track_and_proof(workspace):
    data = embedded_data(workspace)
    data["sha256"] = data["sha256"].upper()
    style = style_for(data)
    result = music.inputs(style)
    assert result == music.inputs(style)
    assert result["assets"]["track"] == {
        "sha256": data["sha256"].lower(), "size": Path(data["file"]).stat().st_size,
    }
    assert result["assets"]["proof"]["sha256"] == data["rights"]["proof_sha256"]
    assert result["style"]["music"]["rights"]["attribution"] == data["rights"]["attribution"]


@pytest.mark.parametrize("route", ["embedded", "instagram"])
def test_inputs_and_style_json_mode_round_trip_with_all_dates(workspace, route):
    data = embedded_data(workspace) if route == "embedded" else native_data()
    data["trend"] = trend_data()
    if route == "embedded":
        data["rights"]["expires_at"] = timestamp() + timedelta(days=2)
    style = style_for(data)
    bound = music.inputs(style)
    assert json.loads(json.dumps(bound, allow_nan=False)) == bound
    reloaded = StylizedEdit.model_validate(json.loads(json.dumps(style.model_dump(mode="json"))))
    assert music.inputs(reloaded) == bound
    assert isinstance(bound["style"]["music"]["trend"]["observed_at"], str)
    if route == "embedded":
        assert isinstance(bound["style"]["music"]["rights"]["checked_at"], str)
        assert isinstance(bound["style"]["music"]["rights"]["expires_at"], str)
    else:
        assert isinstance(bound["style"]["music"]["native_checked_at"], str)


def test_rights_expiry_requires_aware_time_after_check(workspace):
    data = rights_data(workspace)
    data["expires_at"] = datetime(2026, 1, 1)
    with pytest.raises(ValidationError, match="timezone-aware"):
        MusicRights.model_validate(data)
    data["expires_at"] = data["checked_at"]
    with pytest.raises(ValidationError, match="after checked_at"):
        MusicRights.model_validate(data)


def test_rights_expiration_checked_at_use_without_changing_signature(workspace):
    now = datetime.now(timezone.utc)
    data = embedded_data(workspace)
    data["rights"]["checked_at"] = now - timedelta(days=2)
    data["rights"]["expires_at"] = now + timedelta(days=1)
    style = style_for(data)
    original = style.model_dump_json()
    style.music.validate_freshness(now)
    with pytest.raises(ValueError, match="expired"):
        style.music.validate_freshness(data["rights"]["expires_at"])
    assert style.model_dump_json() == original
    assert data["rights"]["expires_at"].isoformat() in music.instructions(style, 1)


def test_every_public_use_rejects_expired_rights(workspace):
    now = datetime.now(timezone.utc)
    data = embedded_data(workspace)
    data["rights"]["checked_at"] = now - timedelta(days=2)
    data["rights"]["expires_at"] = now - timedelta(days=1)
    style = style_for(data)
    for operation in (
        lambda: music.inputs(style),
        lambda: music.stage_track(style, workspace / "unused", 1, threading.Event()),
        lambda: music.audio_graph(style, 1, True),
        lambda: music.instructions(style, 1),
    ):
        with pytest.raises(ValueError, match="expired"):
            operation()
    assert not (workspace / "unused").exists()


@pytest.mark.parametrize("target", ["track", "proof"])
@pytest.mark.parametrize("operation", ["mutate", "remove", "directory"])
def test_inputs_reject_changed_missing_or_nonfile_assets(workspace, target, operation):
    data = embedded_data(workspace)
    style = style_for(data)
    path = Path(data["file"] if target == "track" else data["rights"]["proof_file"])
    if operation == "mutate":
        path.write_bytes(path.read_bytes() + b"changed")
    else:
        path.unlink()
        if operation == "directory":
            path.mkdir()
    with pytest.raises(ValueError, match="SHA-256|exist|ordinary"):
        music.inputs(style)


def test_inputs_revalidate_mutated_models():
    style = style_for(native_data())
    style.music.bpm = float("inf")
    with pytest.raises(ValueError):
        music.inputs(style)


def test_native_staging_is_noop_and_has_no_local_preview(workspace, monkeypatch):
    style = style_for(native_data())
    monkeypatch.setattr(media, "_run", lambda *a, **kw: pytest.fail("Native route must not start FFmpeg"))
    assert music.stage_track(style, workspace / "unused", 3, threading.Event()) is None
    assert not (workspace / "unused").exists()
    with pytest.raises(ValueError, match="cannot"):
        music.audio_graph(style, 3, True)


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf"), 0.000001])
def test_invalid_duration_rejected(workspace, duration):
    style = style_for(native_data())
    for operation in (
        lambda: music.stage_track(style, workspace, duration, threading.Event()),
        lambda: music.audio_graph(style, duration, False),
        lambda: music.instructions(style, duration),
    ):
        with pytest.raises(ValueError, match="duration"):
            operation()


@pytest.mark.parametrize("rate,duration", [(48000, 1.25), (44100, 1.0), (48000, 0.123456), (44100, 0.0333333333)])
def test_stage_selected_samples_stereo_resampling_and_original_preserved(workspace, rate, duration):
    data = embedded_data(workspace, rate=rate)
    data["start_seconds"] = 0.5
    style = style_for(data)
    staged = music.stage_track(style, workspace / "stage", duration, threading.Event())
    samples = read_wav(staged)
    assert samples.shape == (round(duration * 48000), 2)
    assert digest(Path(data["file"])) == data["sha256"]
    assert digest(Path(data["rights"]["proof_file"])) == data["rights"]["proof_sha256"]
    assert sorted(path.name for path in staged.parent.iterdir()) == ["music.wav"]
    assert np.sqrt(np.mean(samples[100:-100] ** 2)) == pytest.approx(0.25 / np.sqrt(2), rel=0.02)


def test_stage_selects_nonzero_track_offset(workspace):
    data = embedded_data(workspace, seconds=2)
    count = 48000
    first = np.zeros(count)
    second = 0.3 * np.sin(2 * np.pi * 1000 * np.arange(count) / count)
    write_wav(Path(data["file"]), np.concatenate((first, second)))
    data["sha256"] = digest(Path(data["file"]))
    data["start_seconds"] = 1
    staged = music.stage_track(style_for(data), workspace / "stage", 0.5, threading.Event())
    assert np.sqrt(np.mean(read_wav(staged) ** 2)) > 0.20


def test_staging_rejects_missing_audio_without_reading_a_playlist(workspace):
    data = embedded_data(workspace)
    path = Path(data["file"])
    path.write_text("#EXTM3U\nhttps://example.invalid/private-track.wav\n", encoding="ascii")
    data["sha256"] = digest(path)
    with pytest.raises(media.MediaError):
        music.stage_track(style_for(data), workspace / "stage", 1, threading.Event())
    assert not (workspace / "stage" / "music-stage").exists()


@pytest.mark.parametrize("offset,duration", [(0, 2), (0.75, 0.5), (3, 1)])
def test_staging_rejects_unavailable_length_and_cleans_snapshot(workspace, offset, duration):
    data = embedded_data(workspace, seconds=1)
    data["start_seconds"] = offset
    with pytest.raises(media.MediaError, match="too short|render"):
        music.stage_track(style_for(data), workspace / "stage", duration, threading.Event())
    assert not (workspace / "stage" / "music-stage").exists()
    assert digest(Path(data["file"])) == data["sha256"]


def test_stage_never_overwrites_existing_work_or_source(workspace):
    data = embedded_data(workspace)
    stage = workspace / "music-stage"
    stage.mkdir()
    protected = stage / "music.wav"
    protected.write_bytes(b"existing caller content")
    with pytest.raises(media.MediaError, match="unused"):
        music.stage_track(style_for(data), workspace, 1, threading.Event())
    assert protected.read_bytes() == b"existing caller content"
    assert digest(Path(data["file"])) == data["sha256"]


def test_precancelled_staging_does_not_create_work(workspace):
    data = embedded_data(workspace)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(media.CancelledError):
        music.stage_track(style_for(data), workspace / "stage", 1, cancel)
    assert not (workspace / "stage").exists()


def test_staging_detects_midcopy_source_mutation(workspace, monkeypatch):
    data = embedded_data(workspace, seconds=8)
    original_open = Path.open
    source = Path(data["file"]).resolve()
    reads = 0

    class MutatingReader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, count):
            nonlocal reads
            block = self.stream.read(count)
            reads += 1
            if reads == 1:
                with original_open(source, "r+b") as changed:
                    changed.seek(-1, 2)
                    changed.write(b"X")
            return block

    def mutating_open(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        # Only mutate the source during the copy, not its initial input verification.
        if path == source and mode == "rb" and (workspace / "stage" / "music-stage").exists():
            return MutatingReader(stream)
        return stream

    monkeypatch.setattr(Path, "open", mutating_open)
    with pytest.raises(ValueError, match="changed|SHA-256"):
        music.stage_track(style_for(data), workspace / "stage", 1, threading.Event())
    assert not (workspace / "stage" / "music-stage").exists()


def test_staging_honors_cancellation_during_copy(workspace, monkeypatch):
    data = embedded_data(workspace)
    cancel = threading.Event()
    original = music._verified_file

    def cancelled_copy(*args, **kwargs):
        if kwargs.get("copy_to") is not None:
            cancel.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(music, "_verified_file", cancelled_copy)
    with pytest.raises(media.CancelledError):
        music.stage_track(style_for(data), workspace / "stage", 1, cancel)
    assert not (workspace / "stage" / "music-stage").exists()


@pytest.mark.parametrize("target", ["track", "proof", "snapshot"])
def test_staging_rechecks_inputs_after_decoder(workspace, monkeypatch, target):
    data = embedded_data(workspace)
    run = media._run

    def mutate_after_decode(*args, **kwargs):
        run(*args, **kwargs)
        path = (
            Path(data["file"]) if target == "track" else
            Path(data["rights"]["proof_file"]) if target == "proof" else
            workspace / "stage" / "music-stage" / "track-source.bin"
        )
        with path.open("ab") as changed:
            changed.write(b"changed")

    monkeypatch.setattr(media, "_run", mutate_after_decode)
    with pytest.raises(ValueError, match="SHA-256"):
        music.stage_track(style_for(data), workspace / "stage", 1, threading.Event())
    assert not (workspace / "stage" / "music-stage").exists()


def test_decoder_uses_verified_snapshot_and_propagates_cancellation(workspace, monkeypatch):
    data = embedded_data(workspace)
    cancel = threading.Event()

    def cancel_decoder(command, cwd, duration, progress, received_cancel):
        snapshot = Path(command[command.index("-i") + 1])
        assert snapshot.name == "track-source.bin" and snapshot.parent == cwd
        assert digest(snapshot) == data["sha256"]
        assert snapshot != Path(data["file"])
        assert command[command.index("-map") + 1] == "0:a:0"
        assert command[command.index("-protocol_whitelist") + 1] == "file,pipe"
        assert "concat" not in command[command.index("-format_whitelist") + 1]
        assert received_cancel is cancel
        progress(0.5, "synthetic cancellation")
        cancel.set()
        raise media.CancelledError("Synthetic cancellation")

    monkeypatch.setattr(media, "_run", cancel_decoder)
    with pytest.raises(media.CancelledError):
        music.stage_track(style_for(data), workspace / "stage", 1, cancel)
    assert not (workspace / "stage" / "music-stage").exists()
    assert digest(Path(data["file"])) == data["sha256"]


def test_audio_graph_ducks_only_music_with_unboosted_limiter(workspace):
    style = style_for(embedded_data(workspace))
    graph = music.audio_graph(style, 3.5, True)
    assert "[0:a:0]" in graph and "[1:a:0]" in graph and "[music_mix]" in graph
    assert "asplit=2" in graph and "sidechaincompress=" in graph
    assert "amix=inputs=2:duration=first:dropout_transition=0:normalize=0" in graph
    assert "level=false:latency=true" in graph
    assert "volume=-20.0dB" in graph and "makeup=1" in graph
    assert "end_sample=168000" in graph and "afade=t=out:ss=144000:ns=24000" in graph
    assert "afade" not in graph.split("[0:a:0]")[1].split(";")[0]
    music_only = music.audio_graph(style, 3.5, False)
    assert "[0:a:0]" not in music_only and "amix" not in music_only
    assert "sidechaincompress" not in music_only


def amplitude(samples, frequency, start, end):
    values = samples[round(start * 48000):round(end * 48000), 0]
    phase = 2 * np.pi * frequency * np.arange(len(values)) / 48000
    return 2 * abs(np.mean(values * np.exp(-1j * phase)))


def test_real_ffmpeg_music_only_fades_gain_and_exact_duration(workspace):
    data = embedded_data(workspace)
    # Generate an original tone through the actual bundled FFmpeg, not a real track.
    track = workspace / "ffmpeg-tone.wav"
    ffmpeg(workspace, 4, "-f", "lavfi", "-i",
           "aevalsrc=0.25*sin(2*PI*1000*t)|0.25*sin(2*PI*1000*t):s=48000:d=4",
           "-c:a", "pcm_s16le", "-n", track)
    data.update(file=str(track), sha256=digest(track))
    style = style_for(data, music_gain_db=-20, fade_seconds=0.5)
    staged = music.stage_track(style, workspace / "stage", 3, threading.Event())
    values = render_mix(workspace, style, staged, 3)
    assert values.shape == (144000, 2)
    assert amplitude(values, 1000, 1, 2) == pytest.approx(0.025, abs=0.00008)
    assert amplitude(values, 1000, 0, 0.1) < 0.004
    assert amplitude(values, 1000, 2.9, 3) < 0.004
    assert np.max(np.abs(values)) < 0.026
    assert np.max(np.abs(values[-1])) < 0.0001


def test_real_ffmpeg_speech_proxy_preserved_while_music_ducks(workspace):
    data = embedded_data(workspace, seconds=6)
    style = style_for(data, music_gain_db=-20, fade_seconds=0.1, release_ms=150)
    time = np.arange(6 * 48000) / 48000
    original = 0.30 * np.sin(2 * np.pi * 200 * time) * ((time >= 2) & (time < 4))
    source = workspace / "narration-proxy.wav"
    write_wav(source, original)
    staged = music.stage_track(style, workspace / "stage", 6, threading.Event())
    mixed = render_mix(workspace, style, staged, 6, source)
    assert mixed.shape == (288000, 2)
    assert amplitude(mixed, 200, 2.5, 3.5) == pytest.approx(0.30, abs=0.001)
    before = amplitude(mixed, 1000, 1, 1.5)
    during = amplitude(mixed, 1000, 2.5, 3.5)
    after = amplitude(mixed, 1000, 5.5, 5.8)
    assert before == pytest.approx(0.025, abs=0.00008)
    assert during < before * 0.25
    assert after == pytest.approx(before, rel=0.05)


def test_real_ffmpeg_narration_edges_are_not_faded_or_delayed(workspace):
    data = embedded_data(workspace, seconds=1)
    write_wav(Path(data["file"]), np.zeros(48000))
    data["sha256"] = digest(Path(data["file"]))
    style = style_for(data)
    original = np.zeros(48000)
    original[[0, 1, 10, 239, 240, 47000, 47998, 47999]] = 0.4
    source = workspace / "edge-impulses.wav"
    write_wav(source, original)
    staged = music.stage_track(style, workspace / "stage", 1, threading.Event())
    mixed = render_mix(workspace, style, staged, 1, source)
    assert mixed.shape == (48000, 2)
    np.testing.assert_allclose(mixed, read_wav(source), atol=1 / 32768)


def test_real_ffmpeg_limiter_prevents_clipping_without_gain_boost(workspace):
    data = embedded_data(workspace, seconds=1)
    time = np.arange(48000) / 48000
    loud = 0.9 * np.sin(2 * np.pi * 1000 * time)
    write_wav(Path(data["file"]), loud)
    data["sha256"] = digest(Path(data["file"]))
    style = style_for(data, music_gain_db=-6, duck_threshold=0.25, duck_ratio=2, fade_seconds=0.05)
    source = workspace / "loud-source.wav"
    write_wav(source, loud)
    staged = music.stage_track(style, workspace / "stage", 1, threading.Event())
    mixed = render_mix(workspace, style, staged, 1, source)
    assert mixed.shape == (48000, 2)
    assert np.max(np.abs(mixed)) <= 0.9501
    assert np.max(np.abs(mixed[12000:36000])) >= 0.94


@pytest.mark.parametrize("duration", [1 / 48000, 0.001, 1 / 30, 0.1])
def test_real_ffmpeg_short_outputs_keep_exact_sample_count(workspace, duration):
    style = style_for(embedded_data(workspace, seconds=1))
    staged = music.stage_track(style, workspace / "stage", duration, threading.Event())
    mixed = render_mix(workspace, style, staged, duration)
    assert mixed.shape == (round(duration * 48000), 2)


def test_real_ffmpeg_shorter_narration_does_not_truncate_music(workspace):
    style = style_for(embedded_data(workspace, seconds=2), fade_seconds=0.1)
    time = np.arange(48000) / 48000
    source = workspace / "short-source-audio.wav"
    write_wav(source, 0.3 * np.sin(2 * np.pi * 200 * time))
    staged = music.stage_track(style, workspace / "stage", 2, threading.Event())
    mixed = render_mix(workspace, style, staged, 2, source)
    assert mixed.shape == (96000, 2)
    assert amplitude(mixed, 200, 0, 0.5) == pytest.approx(0.3, abs=0.001)
    assert amplitude(mixed, 200, 1.5, 1.8) < 0.001
    assert amplitude(mixed, 1000, 1.5, 1.8) > 0.02


def test_instructions_native_caveats_and_exact_grid():
    data = native_data()
    data.update(start_seconds=12.375, beat_offset_seconds=0.125, bpm=123.456)
    text = music.instructions(style_for(data), 12.5)
    for expected in [
        data["title"], data["artist"], data["track_url"], "12.375 seconds", "123.456",
        "0.125 + n * (60 / 123.456)", "original audio only", "no added track",
        "local preview cannot audition", "inside Instagram", "manually balance",
        "Recheck region", "commercial eligibility", "Do not transfer",
        "Retain this original, no-added-music export for YouTube",
        "Do not upload the Instagram-soundtrack version to YouTube without separate rights",
        "No trend evidence supplied", "Source audio may already include music",
    ]:
        assert expected in text
    assert "trending" not in text.lower()


def test_instructions_embedded_preserve_exact_attribution_and_regional_evidence(workspace):
    data = embedded_data(workspace)
    data["trend"] = trend_data()
    style = style_for(data)
    text = music.instructions(style, 3)
    assert data["rights"]["attribution"] in text
    assert "BOTH Instagram and YouTube descriptions" in text
    assert "attestation, not legal validation" in text
    assert "platform clearance guarantee" in text
    assert "Provider or library access alone does not establish rights for both platforms" in text
    assert "not a universal" in text and "region: IN" in text
    assert data["trend"]["observed_at"].isoformat() in text
    assert data["trend"]["url"] in text and data["trend"]["note"] in text


def test_every_public_use_rejects_stale_native_evidence(workspace):
    data = native_data()
    data["native_checked_at"] = datetime.now(timezone.utc) - timedelta(days=8)
    style = style_for(data)
    for operation in (
        lambda: music.inputs(style),
        lambda: music.stage_track(style, workspace, 1, threading.Event()),
        lambda: music.audio_graph(style, 1, False),
        lambda: music.instructions(style, 1),
    ):
        with pytest.raises(ValueError, match="stale"):
            operation()
