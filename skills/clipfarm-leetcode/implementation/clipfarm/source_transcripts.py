from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
from numbers import Real
from pathlib import Path
from threading import Event
from typing import Callable
from uuid import uuid4

from .media import CancelledError, MediaError, ffmpeg_exe
from .models import Cue, MediaInfo
from .transcribe import available


ENGINE = "faster-whisper"
ALGORITHM_VERSION = 2
CHUNK_SECONDS = 600
OVERLAP_SECONDS = 2
GROUPING = {"max_words": 8, "max_characters": 56, "max_seconds": 4, "pause_seconds": 0.65}
_SENTENCE_END = re.compile(r"""[.!?。！？][\s"'”’)\]]*$""")


def _check_cancel(cancel: Event) -> None:
    if cancel.is_set():
        raise CancelledError("Source transcription cancelled.")


def _engine_version() -> str | None:
    try:
        return version(ENGINE)
    except PackageNotFoundError:
        return None


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _write_checkpoint(path: Path, payload: dict) -> None:
    pending = path.with_name(f".{path.name}.{uuid4().hex}.pending")
    try:
        with pending.open("xb") as stream:
            stream.write(_json_bytes({"sha256": _digest(payload), "payload": payload}))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def _read_checkpoint(path: Path) -> dict:
    def unique_fields(pairs: list[tuple]) -> dict:
        fields = {}
        for key, value in pairs:
            if key in fields:
                raise ValueError(f"duplicate field: {key}")
            fields[key] = value
        return fields

    try:
        record = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
        if (not isinstance(record, dict) or set(record) != {"sha256", "payload"}
                or not isinstance(record["payload"], dict)
                or record["sha256"] != _digest(record["payload"])):
            raise ValueError("invalid envelope or checksum")
        return record["payload"]
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise MediaError(f"Corrupt source-ASR checkpoint {path.name}: {exc}") from exc


def _window(index: int, duration: float) -> dict:
    start = index * CHUNK_SECONDS
    end = min(duration, start + CHUNK_SECONDS)
    return {"start": start, "end": end, "decode_start": max(0, start - OVERLAP_SECONDS),
            "decode_end": min(duration, end + OVERLAP_SECONDS)}


def _owns(word: dict, window: dict, duration: float) -> bool:
    midpoint = (word["start"] + word["end"]) / 2
    return (window["start"] <= midpoint < window["end"]
            or midpoint == window["end"] == duration)


def _validate_words(words: object, start: float, end: float) -> None:
    if not isinstance(words, list):
        raise MediaError("Invalid native word timestamps: words must be a list.")
    previous = -1.0
    for word in words:
        if (not isinstance(word, dict) or set(word) != {"start", "end", "text"}
                or not isinstance(word["text"], str) or not word["text"].strip()):
            raise MediaError("Invalid native word timestamps: missing word text or timing.")
        a, b = word["start"], word["end"]
        if (not isinstance(a, Real) or not isinstance(b, Real)
                or isinstance(a, bool) or isinstance(b, bool)
                or not math.isfinite(a) or not math.isfinite(b)
                or not start <= a <= b <= end or a < previous):
            raise MediaError("Invalid native word timestamps: nonfinite, reversed, out-of-order "
                             "or outside the decoded source interval.")
        previous = a


def _text(words: list[dict]) -> str:
    # Native Whisper tokens include their own spaces, punctuation and contractions.
    return " ".join("".join(word["text"] for word in words).split())


def _group_words(words: list[dict], duration: float) -> list[Cue]:
    _validate_words(words, 0, duration)
    cues: list[Cue] = []
    group: list[dict] = []
    end = 0.0

    def emit() -> None:
        if not group:
            return
        if end <= group[0]["start"]:
            raise MediaError("Native ASR returned isolated zero-duration words; cannot create "
                             "a positive-duration cue without inventing timing.")
        text = _text(group)
        if len(text) > 4000:
            raise MediaError("Native ASR word group exceeds the supported cue text length.")
        cues.append(Cue(start=group[0]["start"], end=end, text=text))

    for word in words:
        if group:
            pause = word["start"] - end >= GROUPING["pause_seconds"]
            target = (_SENTENCE_END.search(group[-1]["text"]) is not None
                      or len(group) >= GROUPING["max_words"]
                      or len(_text([*group, word])) > GROUPING["max_characters"]
                      or max(end, word["end"]) - group[0]["start"] > GROUPING["max_seconds"])
            # Keep millisecond-colliding starts and zero-length words without inventing time.
            if (round(word["start"] * 1000) > round(group[0]["start"] * 1000)
                    and (pause or (target and end > group[0]["start"]
                                   and word["end"] > word["start"]))):
                emit()
                group = []
        if not group:
            end = word["end"]
        else:
            end = max(end, word["end"])
        group.append(word)
    emit()
    return cues


def _extract_audio(source: Path, offset: float, length: float, wav: Path, cancel: Event) -> None:
    _check_cancel(cancel)
    log_path = wav.with_suffix(".log")
    try:
        with log_path.open("wb") as log:
            process = subprocess.Popen([
                ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-protocol_whitelist", "file,pipe", "-ss", str(offset), "-i", str(source),
                "-t", str(length), "-vn", "-ac", "1", "-ar", "16000", str(wav),
            ], stdout=subprocess.DEVNULL, stderr=log)
            try:
                while process.poll() is None:
                    if cancel.wait(0.2):
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        raise CancelledError("Source transcription cancelled.")
                _check_cancel(cancel)
                if process.returncode:
                    with log_path.open("rb") as error:
                        error.seek(max(0, log_path.stat().st_size - 2000))
                        detail = error.read().decode("utf-8", errors="replace")
                    raise MediaError(f"Audio extraction failed: {detail}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    finally:
        log_path.unlink(missing_ok=True)


def _native_words(segments, window: dict, duration: float, cancel: Event) -> list[dict]:
    words: list[dict] = []
    length = window["decode_end"] - window["decode_start"]
    for segment in segments:
        _check_cancel(cancel)
        text = getattr(segment, "text", "")
        native = getattr(segment, "words", None)
        if not isinstance(text, str):
            raise MediaError("Invalid native ASR segment text.")
        if not native:
            if text.strip():
                raise MediaError("ASR recognized speech without native word timestamps.")
            continue
        local = [{"start": getattr(word, "start", None), "end": getattr(word, "end", None),
                  "text": getattr(word, "word", None)} for word in native]
        _validate_words(local, 0, length)
        if " ".join(text.split()) != _text(local):
            raise MediaError("ASR segment text does not match its timestamped words; "
                             "refusing to silently omit recognized text.")
        words.extend({"start": window["decode_start"] + float(word["start"]),
                      "end": window["decode_start"] + float(word["end"]), "text": word["text"]}
                     for word in local)
    _check_cancel(cancel)
    _validate_words(words, window["decode_start"], window["decode_end"])
    # Context is owned by exactly one core interval, never deduplicated by word spelling.
    return [word for word in words if _owns(word, window, duration)]


def _load_model(model_name: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise MediaError("Local transcription is not installed. "
                         "Run .\\Start-ClipFarm.ps1 -Transcription.") from exc
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def generate(
    source: Path, info: MediaInfo, *, source_sha256: str, directory: Path,
    model_name: str = "small", language: str | None = None,
    progress: Callable[[float, str], None], cancel: Event,
) -> tuple[list[Cue], dict]:
    """Generate source cues from native ASR words, with a private per-run chunk cache."""
    _check_cancel(cancel)
    if language is not None and (not isinstance(language, str)
                                 or not re.fullmatch(r"[a-z]{2,3}", language)):
        raise ValueError("Use a lowercase language code such as en, or omit it for detection.")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("A local ASR model name is required.")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", source_sha256):
        raise ValueError("source_sha256 must be the source video's SHA-256 digest.")
    if not info.has_audio:
        raise MediaError("This video has no audio stream to transcribe.")
    if source.resolve().is_relative_to(directory.resolve()):
        raise MediaError("Source media must be outside the source-ASR working directory.")

    count = math.ceil(info.duration / CHUNK_SECONDS)
    engine_version = _engine_version()
    config = {
        "schema_version": 1, "engine": ENGINE, "engine_version": engine_version,
        "algorithm_version": ALGORITHM_VERSION, "source_sha256": source_sha256.lower(),
        "duration": info.duration, "model": model_name, "language_hint": language,
        "device": "cpu", "compute_type": "int8", "word_timestamps": True,
        "vad_filter": True, "beam_size": 3, "chunk_seconds": CHUNK_SECONDS,
        "overlap_seconds": OVERLAP_SECONDS, "grouping": dict(GROUPING),
    }
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.json"
    expected = {"config": config, "chunk_count": count}
    files = {directory / f"chunk-{index:06d}.json" for index in range(count)}
    existing = set(directory.glob("chunk-*.json"))
    if existing - files:
        raise MediaError("Incompatible source-ASR checkpoint: unexpected chunk files.")
    if manifest.exists():
        saved = _read_checkpoint(manifest)
        saved_config = saved.get("config")
        if engine_version is None and isinstance(saved_config, dict):
            saved_version = saved_config.get("engine_version")
            if isinstance(saved_version, str) and saved_version:
                # Complete checkpoints can be read without the optional ASR installation.
                config["engine_version"] = saved_version
        if _json_bytes(saved) != _json_bytes(expected):
            raise MediaError("Incompatible source-ASR checkpoint configuration. "
                             "Use a new run directory for a different source or ASR settings.")
    elif existing:
        raise MediaError("Corrupt source-ASR checkpoint: chunks exist without a manifest.")

    config_sha256 = _digest(config)
    chunks: dict[int, dict] = {}
    for index in range(count):
        _check_cancel(cancel)
        path = directory / f"chunk-{index:06d}.json"
        if path not in existing:
            continue
        chunk = _read_checkpoint(path)
        window = _window(index, info.duration)
        try:
            if (set(chunk) != {"config_sha256", "index", "window", "words", "detected_language"}
                    or chunk["config_sha256"] != config_sha256
                    or type(chunk["index"]) is not int or chunk["index"] != index
                    or _json_bytes(chunk["window"]) != _json_bytes(window)
                    or (chunk["detected_language"] is not None
                        and (not isinstance(chunk["detected_language"], str)
                             or not re.fullmatch(r"[a-z]{2,3}", chunk["detected_language"])))):
                raise MediaError("invalid chunk configuration or language")
            _validate_words(chunk["words"], window["decode_start"], window["decode_end"])
            if not all(_owns(word, window, info.duration) for word in chunk["words"]):
                raise MediaError("words outside this chunk's ownership interval")
        except (MediaError, TypeError, ValueError) as exc:
            raise MediaError(f"Corrupt source-ASR checkpoint {path.name}: {exc}") from exc
        chunks[index] = chunk

    reused = len(chunks)
    if reused < count:
        if not available():
            raise MediaError("Local transcription is not installed. "
                             "Run .\\Start-ClipFarm.ps1 -Transcription.")
        if config["engine_version"] != engine_version:
            raise MediaError("Cannot verify the installed ASR version for this partial checkpoint.")
        _check_cancel(cancel)
        progress(reused / count, f"Loading {model_name}. First use downloads model weights; "
                 "video stays local.")
        _check_cancel(cancel)
        model = _load_model(model_name)
        _check_cancel(cancel)
        if not manifest.exists():
            _write_checkpoint(manifest, expected)
        for index in range(count):
            _check_cancel(cancel)
            if index in chunks:
                continue
            window = _window(index, info.duration)
            wav = directory / f".audio-{uuid4().hex}.wav"
            try:
                progress(len(chunks) / count, f"Transcribing source chunk {index + 1} / {count}")
                _check_cancel(cancel)
                _extract_audio(source, window["decode_start"],
                               window["decode_end"] - window["decode_start"], wav, cancel)
                _check_cancel(cancel)
                options = {"language": language} if language is not None else {}
                segments, detected = model.transcribe(
                    str(wav), word_timestamps=True, vad_filter=True, beam_size=3, **options)
                words = _native_words(segments, window, info.duration, cancel)
                detected_language = getattr(detected, "language", None)
                if (detected_language is not None
                        and (not isinstance(detected_language, str)
                             or not re.fullmatch(r"[a-z]{2,3}", detected_language))):
                    raise MediaError("Invalid ASR detected language.")
                chunk = {"config_sha256": config_sha256, "index": index, "window": window,
                         "detected_language": detected_language, "words": words}
                _check_cancel(cancel)
                _write_checkpoint(directory / f"chunk-{index:06d}.json", chunk)
                chunks[index] = chunk
            finally:
                wav.unlink(missing_ok=True)

    _check_cancel(cancel)
    words = [word for index in range(count) for word in chunks[index]["words"]]
    cues = _group_words(words, info.duration)
    if not cues:
        raise MediaError("No speech detected. Import a timed transcript or try another model "
                         "in a new run directory.")
    metadata = {
        "origin": "generated", "engine": ENGINE, "engine_version": config["engine_version"],
        "algorithm_version": ALGORITHM_VERSION, "model": model_name, "language_hint": language,
        "word_timestamps": True, "timestamp_source": "native_asr_words", "local_only": True,
        "device": "cpu", "compute_type": "int8", "source_sha256": source_sha256.lower(),
        "duration": info.duration, "chunk_seconds": CHUNK_SECONDS,
        "overlap_seconds": OVERLAP_SECONDS, "grouping": dict(GROUPING),
        "chunk_count": count, "completed_chunk_count": len(chunks), "reused_chunk_count": reused,
        "transcribed_chunk_count": count - reused,
        "silent_chunk_count": sum(not chunk["words"] for chunk in chunks.values()),
        "word_count": len(words), "cue_count": len(cues),
        "detected_languages": sorted({chunk["detected_language"] for chunk in chunks.values()
                                      if chunk["detected_language"] is not None}),
        "chunks": [{"index": index, **chunks[index]["window"],
                    "word_count": len(chunks[index]["words"]),
                    "detected_language": chunks[index]["detected_language"]}
                   for index in range(count)],
        "timing_note": (
            "Generated locally from native ASR word-time estimates, not forced alignment or "
            "human-verified transcription. Cue boundaries retain native word-time envelopes; "
            "TXT rounds starts to milliseconds, while JSON preserves actual starts and ends."
        ),
        "timing_limitations": [
            "Automatically recognized text and native word times are ASR estimates, not "
            "forced alignment or human-verified transcription.",
            "Cues use native word-time envelopes; no proportional timing is invented. "
            "Zero-duration words are merged with neighbors or rejected explicitly.",
            "Words whose cue starts would round to the same millisecond are grouped together "
            "without dropping text or synthesizing timestamps.",
            "Overlapping decode windows use word-midpoint ownership at chunk boundaries, "
            "not text-based deduplication. ASR may still misrecognize speech at seams.",
        ],
    }
    _check_cancel(cancel)
    progress(1.0, f"Source transcription complete: {len(cues)} timestamped cues.")
    _check_cancel(cancel)
    return cues, metadata
