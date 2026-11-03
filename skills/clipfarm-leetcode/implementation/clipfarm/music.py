"""Local-only music snapshots and sample-bounded, narration-preserving FFmpeg graphs."""

from __future__ import annotations

import hashlib
import math
import os
import stat
import threading
import wave
from pathlib import Path

from . import media
from .music_models import StylizedEdit, _local_path

RENDERER_VERSION = "speech-first-audio-1"
SAMPLE_RATE = 48000
_CHUNK = 1024 * 1024
_DEMUXERS = "wav,mp3,flac,ogg,mov,matroska,webm,aac,aiff"


def _validated(style: StylizedEdit) -> StylizedEdit:
    # Revalidate nested values: model_copy/update and in-place edits bypass Pydantic.
    result = StylizedEdit.model_validate(style.model_dump(mode="python"))
    result.music.validate_freshness()
    return result


def _samples(duration: float) -> int:
    if not math.isfinite(duration) or duration <= 0 or not math.isfinite(duration * SAMPLE_RATE):
        raise ValueError("Music duration must be positive and finite.")
    count = round(duration * SAMPLE_RATE)
    if count < 1:
        raise ValueError("Music duration must contain at least one 48000 Hz sample.")
    return count


def _cancel(cancel: threading.Event | None) -> None:
    if cancel is not None:
        media._check_cancel(cancel)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    # Windows stat/fstat disagree on ctime; birthtime is consistent across both.
    created = getattr(info, "st_birthtime_ns", info.st_ctime_ns)
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, created


def _disk_file(value: str, label: str) -> Path:
    path = _local_path(value)
    try:
        path = path.resolve(strict=True)
        _local_path(str(path))
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError(f"{label} must be an ordinary local file.")
    except OSError as exc:
        raise ValueError(f"{label} does not exist or cannot be read: {value}") from exc
    return path


def _verified_file(
    value: str, expected: str, label: str, cancel: threading.Event | None = None,
    *, copy_to: Path | None = None,
) -> dict:
    path = _disk_file(value, label)
    digest = hashlib.sha256()
    size = 0
    _cancel(cancel)
    try:
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"{label} must be an ordinary local file.")
            destination = copy_to.open("xb") if copy_to is not None else None
            try:
                while block := source.read(_CHUNK):
                    _cancel(cancel)
                    digest.update(block)
                    size += len(block)
                    if destination is not None:
                        destination.write(block)
            finally:
                if destination is not None:
                    destination.close()
            after = os.fstat(source.fileno())
        current = path.stat()
    except OSError as exc:
        raise ValueError(f"{label} could not be read or snapshotted: {exc}") from exc
    _cancel(cancel)
    if (
        _identity(before) != _identity(after) or _identity(after) != _identity(current)
        or before.st_ctime_ns != after.st_ctime_ns
        or _disk_file(value, label) != path
    ):
        raise ValueError(f"{label} changed while being read; refresh its reviewed SHA-256.")
    actual = digest.hexdigest()
    if size != before.st_size or actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch; its bytes differ from the reviewed evidence.")
    return {"sha256": actual, "size": size}


def _bound_inputs(style: StylizedEdit, cancel: threading.Event | None = None) -> dict:
    assets = {}
    spec = style.music
    if spec.route == "embedded":
        assets["track"] = _verified_file(spec.file, spec.sha256, "Music track", cancel)
        assets["proof"] = _verified_file(
            spec.rights.proof_file, spec.rights.proof_sha256, "Music permission proof", cancel,
        )
    return {"renderer": RENDERER_VERSION, "style": style.model_dump(mode="json"), "assets": assets}


def inputs(style: StylizedEdit) -> dict:
    """Bind authored evidence and local bytes; never fetch URLs or assert legal clearance."""
    return _bound_inputs(_validated(style))


def _check_pcm(path: Path, expected_samples: int, cancel: threading.Event) -> None:
    try:
        with wave.open(str(path), "rb") as decoded:
            if (
                decoded.getframerate() != SAMPLE_RATE or decoded.getnchannels() != 2
                or decoded.getsampwidth() != 2 or decoded.getcomptype() != "NONE"
            ):
                raise media.MediaError("Staged music is not 48000 Hz stereo 16-bit PCM.")
            if decoded.getnframes() != expected_samples:
                raise media.MediaError(
                    "Music track is too short for the requested offset/duration "
                    f"({decoded.getnframes()} samples available; {expected_samples} required). "
                    "No looping or silence padding is permitted."
                )
            byte_count = 0
            while block := decoded.readframes(_CHUNK // 4):
                _cancel(cancel)
                byte_count += len(block)
            if byte_count != expected_samples * 4:
                raise media.MediaError("Staged music PCM is truncated; missing samples are not padded.")
    except (OSError, EOFError, wave.Error) as exc:
        raise media.MediaError(f"Could not verify staged music PCM: {exc}") from exc


def stage_track(
    style: StylizedEdit, work: Path, duration: float, cancel: threading.Event,
) -> Path | None:
    """Snapshot and decode only the selected track range in a new caller-owned directory."""
    count = _samples(duration)
    _cancel(cancel)
    style = _validated(style)
    if style.music.route == "instagram":
        return None
    _bound_inputs(style, cancel)
    spec = style.music
    work = _local_path(str(work.absolute()))
    work = _local_path(str(work.resolve()))
    stage = work / "music-stage"
    try:
        work.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
    except OSError as exc:
        raise media.MediaError("Music staging needs a new, unused local music-stage directory.") from exc
    snapshot = stage / "track-source.bin"
    output = stage / "music.wav"
    succeeded = False
    try:
        _verified_file(spec.file, spec.sha256, "Music track", cancel, copy_to=snapshot)
        _verified_file(str(snapshot), spec.sha256, "Music snapshot", cancel)
        command = (
            media._base() + ["-loglevel", "error", "-xerror", "-threads", "2", "-filter_threads", "1"]
            + media._PROTOCOLS
            + ["-format_whitelist", _DEMUXERS, "-ss", str(spec.start_seconds), "-i", str(snapshot),
               "-t", f"{count / SAMPLE_RATE:.12f}", "-map", "0:a:0", "-vn", "-sn", "-dn",
               "-af", f"aresample={SAMPLE_RATE}:async=0,"
               f"aformat=sample_rates={SAMPLE_RATE}:channel_layouts=stereo,"
               f"atrim=end_sample={count},asetpts=N/SR/TB",
               "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-ac", "2",
               "-progress", "pipe:1", "-nostats", "-n", str(output)]
        )
        media._run(command, stage, count / SAMPLE_RATE, lambda *_: None, cancel)
        _check_pcm(output, count, cancel)
        _verified_file(str(snapshot), spec.sha256, "Music snapshot", cancel)
        _bound_inputs(style, cancel)
        style.music.validate_freshness()
        _cancel(cancel)
        succeeded = True
        return output
    finally:
        snapshot.unlink(missing_ok=True)
        if not succeeded:
            output.unlink(missing_ok=True)
            stage.rmdir()


def audio_graph(style: StylizedEdit, duration: float, has_source_audio: bool) -> str:
    """Input 0 is assembled source audio; input 1 is the already-offset staged PCM."""
    count = _samples(duration)
    style = _validated(style)
    if style.music.route != "embedded":
        raise ValueError("Instagram-native tracks cannot be auditioned or mixed locally.")
    fade = max(1, min(round(style.fade_seconds * SAMPLE_RATE), count // 2))
    normalize = (
        f"aresample={SAMPLE_RATE}:async=0,"
        f"aformat=sample_fmts=fltp:sample_rates={SAMPLE_RATE}:channel_layouts=stereo,"
        f"atrim=end_sample={count},asetpts=N/SR/TB"
    )
    parts = [
        f"[1:a:0]{normalize},volume={style.music_gain_db}dB:precision=double:eval=once,"
        f"afade=t=in:ss=0:ns={fade},afade=t=out:ss={count - fade}:ns={fade},"
        "asetnsamples=n=1024:p=0[music_bed]"
    ]
    if has_source_audio:
        # Match packet sizes and keep the detector alive until bounded music EOF;
        # sidechaincompress can otherwise nondeterministically lose the final packets.
        parts += [
            f"[0:a:0]{normalize},apad=whole_len={count},"
            "asetnsamples=n=1024:p=0,asplit=2[source_voice][duck_key]",
            "[duck_key]apad[duck_key_padded]",
            "[music_bed][duck_key_padded]sidechaincompress="
            f"threshold={style.duck_threshold}:ratio={style.duck_ratio}:"
            f"attack={style.attack_ms}:release={style.release_ms}:"
            "makeup=1:level_in=1:level_sc=1:mix=1:link=maximum:detection=peak[ducked_music]",
            "[source_voice][ducked_music]amix=inputs=2:duration=first:"
            "dropout_transition=0:normalize=0[mixed_audio]",
        ]
        mixed = "mixed_audio"
    else:
        mixed = "music_bed"
    # Disable alimiter's default auto-level boost and compensate its lookahead latency.
    parts.append(
        f"[{mixed}]alimiter=limit=0.95:attack=5:release=50:level=false:latency=true,"
        f"atrim=end_sample={count},asetpts=N/SR/TB[music_mix]"
    )
    return ";".join(parts)


def instructions(style: StylizedEdit, duration: float) -> str:
    """Copyable delivery guidance; native availability is not a transferable license."""
    _samples(duration)
    style = _validated(style)
    spec = style.music
    lines = [
        "Speech-first music delivery",
        f"Track: {spec.title}",
        f"Artist: {spec.artist}",
        f"Track URL: {spec.track_url if spec.track_url is not None else 'Not supplied (local track).'}",
        f"Track start offset: {spec.start_seconds} seconds",
        f"Clip duration: {duration} seconds",
        f"BPM: {spec.bpm}",
        f"First beat: {spec.beat_offset_seconds} seconds relative to the rendered clip start.",
        f"Beat grid: {spec.beat_offset_seconds} + n * (60 / {spec.bpm}) seconds, n = 0, 1, 2, ...",
        f"Human-measured grid review: {spec.beat_review}",
        "",
    ]
    if spec.route == "instagram":
        lines += [
            "This clip contains original audio only (or silence if the source has no audio): no added track.",
            "The local preview cannot audition the Instagram platform track.",
            "Add this exact track inside Instagram and select the track start offset above.",
            "Preserve narration and manually balance platform music below speech; local ducking is not applied.",
            f"Availability checked: {spec.native_checked_at.isoformat()}",
            f"Checked region: {spec.region}",
            f"Checked account context: {spec.account_context}",
            "Recheck region, account, track excerpt length, and commercial eligibility at posting.",
            "Availability is not a transferable license. Do not transfer Instagram library audio rights to YouTube.",
            "Retain this original, no-added-music export for YouTube.",
            "Do not upload the Instagram-soundtrack version to YouTube without separate rights covering that use.",
            "Adding separately cleared music to the YouTube export requires its own documented permission.",
        ]
    else:
        rights = spec.rights
        lines += [
            "The selected local music is embedded with speech-first gain, ducking, and music-only fades.",
            "Documented permission is an attestation, not legal validation or a platform clearance guarantee.",
            "Provider or library access alone does not establish rights for both platforms or commercial use.",
            f"Documented scope: {rights.scope}",
            f"Documented usage: {rights.usage}",
            f"Documented territory: {rights.territory}",
            f"Rights checked by: {rights.checked_by} at {rights.checked_at.isoformat()}",
            f"Documented platforms: {', '.join(rights.platforms)}",
        ]
        if rights.license_url is not None:
            lines.append(f"License reference: {rights.license_url}")
        if rights.expires_at is not None:
            lines.append(f"Documented rights expiration: {rights.expires_at.isoformat()}; recheck before posting.")
        if rights.permission_note is not None:
            lines.append(f"Permission note: {rights.permission_note}")
        if rights.attribution is not None:
            lines += [
                "Copy the following attribution unchanged into BOTH Instagram and YouTube descriptions:"
                if rights.attribution_required else
                "Optional supplied attribution; copy unchanged into BOTH Instagram and YouTube descriptions:",
                rights.attribution,
            ]
        else:
            lines.append("The rights attestation records that attribution is not required.")
    lines += [
        "",
        "Source audio may already include music; these declarations do not clear that pre-existing audio.",
        "Review the final mix and posting eligibility before publication. No platform upload is performed.",
    ]
    if spec.trend is None:
        lines.append("No trend evidence supplied; no popularity claim is made.")
    else:
        trend = spec.trend
        lines += [
            f"Trend evidence as of {trend.observed_at.isoformat()}, region: {trend.region}",
            f"Trend evidence URL: {trend.url}",
            f"Trend evidence note: {trend.note}",
            "This is a dated regional observation, not a universal or current popularity guarantee.",
        ]
    return "\n".join(lines) + "\n"
