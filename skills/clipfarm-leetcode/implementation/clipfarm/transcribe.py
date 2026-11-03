from __future__ import annotations

import importlib.util
import math
import re
import subprocess
import tempfile
from pathlib import Path
from threading import Event
from typing import Callable

from .media import CancelledError, MediaError, ffmpeg_exe
from .models import Cue, MediaInfo


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def transcribe(
    source: Path, info: MediaInfo, model_name: str,
    progress: Callable[[float, str], None], cancel: Event,
    *, language: str | None = None,
) -> list[Cue]:
    if language is not None and not re.fullmatch(r"[a-z]{2,3}", language):
        raise ValueError("Use a lowercase language code such as en, or omit it for detection.")
    if not available():
        raise MediaError("Local transcription is not installed. Run .\\Start-ClipFarm.ps1 -Transcription.")
    if not info.has_audio:
        raise MediaError("This video has no audio stream to transcribe.")
    if cancel.is_set():
        raise CancelledError("Transcription cancelled.")
    from faster_whisper import WhisperModel

    progress(0, f"Loading {model_name}. First use downloads model weights; video stays local.")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    result: list[Cue] = []
    # faster-whisper decodes each input into RAM, so never pass an hours-long video directly.
    chunk_seconds = 600
    with tempfile.TemporaryDirectory(prefix="clipfarm-speech-") as temp:
        root = Path(temp)
        for index in range(math.ceil(info.duration / chunk_seconds)):
            if cancel.is_set():
                raise CancelledError("Transcription cancelled.")
            offset = index * chunk_seconds
            length = min(chunk_seconds, info.duration - offset)
            wav = root / "chunk.wav"
            with (root / "decode.log").open("wb") as log:
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
                            raise CancelledError("Transcription cancelled.")
                    if process.returncode:
                        raise MediaError(f"Audio extraction failed: {(root / 'decode.log').read_text(errors='replace')[-2000:]}")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            options = {"language": language} if language else {}
            segments, _ = model.transcribe(str(wav), vad_filter=True, beam_size=3, **options)
            for segment in segments:
                if cancel.is_set():
                    raise CancelledError("Transcription cancelled.")
                text = segment.text.strip()
                start = min(info.duration, offset + segment.start)
                end = min(info.duration, offset + segment.end)
                if text and end > start:
                    result.append(Cue(start=start, end=end, text=text))
                progress(min(0.99, end / info.duration), f"Transcribing {end / 60:.1f} / {info.duration / 60:.1f} min")
    if not result:
        raise MediaError("No speech detected. Import a timed transcript or try another model.")
    return result
