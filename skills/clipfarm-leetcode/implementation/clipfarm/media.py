"""Local, streaming FFmpeg composition and deliberately conservative face heuristics."""

from __future__ import annotations

import math
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterator
from uuid import uuid4

import cv2
import numpy as np

from .models import Analysis, Clip, Cue, MediaInfo, Region, TrackPoint

# Analysis uses CPU-backed arrays. Lazy OpenCL initialization in a Windows worker
# can stall interpreter shutdown, so initialize the CPU-only backend before workers.
cv2.ocl.setUseOpenCL(False)

Progress = Callable[[float, str], None]
_PROTOCOLS = ["-protocol_whitelist", "file,pipe"]
_MAX_SAMPLES = 360
_NORMALIZE = "scale=w='trunc(iw*max(sar,1)/2)*2':h='trunc(ih/min(sar,1)/2)*2',setsar=1"
_VIDEO_SUFFIXES = {
    ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".flv",
    ".mpeg", ".mpg", ".ts", ".mts", ".m2ts", ".ogv", ".3gp", ".mxf",
}


class MediaError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


def ffmpeg_exe() -> str:
    override = os.environ.get("FFMPEG_BINARY")
    if override:
        candidate = shutil.which(override) or override
        if not Path(candidate).is_file():
            raise MediaError("FFMPEG_BINARY does not point to an executable FFmpeg file.")
        return str(Path(candidate).resolve())
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError) as exc:
        raise MediaError("FFmpeg is unavailable. Install ClipFarm's imageio-ffmpeg dependency.") from exc


def _source(source: Path) -> Path:
    supplied = str(source)
    if supplied.startswith(("\\\\", "//")):
        raise MediaError("Choose a local disk video, not a network share.")
    try:
        path = Path(source).expanduser().resolve()
    except OSError as exc:
        raise MediaError(f"Could not access the source video: {exc}") from exc
    if not path.is_file():
        raise MediaError(f"Source video does not exist: {path.name}")
    if path.suffix.lower() not in _VIDEO_SUFFIXES:
        raise MediaError("Choose an ordinary local video file, not a playlist or image.")
    return path


def _make_parent(output: Path) -> None:
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise MediaError(f"Could not create the output directory: {exc}") from exc


def _base() -> list[str]:
    return [ffmpeg_exe(), "-hide_banner", "-nostdin"]


def _check_cancel(cancel: threading.Event) -> None:
    if cancel.is_set():
        raise CancelledError("Media processing cancelled.")


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def _detail(stderr: str | bytes) -> str:
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    return "\n".join(stderr.strip().splitlines()[-12:])[-3500:]


def _bounded(command: list[str], *, cwd: Path | None = None, timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout, creationflags=_creationflags(),
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"FFmpeg did not respond within {timeout:g} seconds.") from exc
    except OSError as exc:
        raise MediaError(f"Could not launch FFmpeg: {exc}") from exc
    if result.returncode:
        raise MediaError(f"FFmpeg failed: {_detail(result.stderr)}")
    return result


def _creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _parse_probe(log: str) -> MediaInfo:
    incoming, separator, outgoing = log.partition("Output #0")
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", incoming)
    video = next(
        (line for line in incoming.splitlines() if re.search(r"Stream #\S+.*Video:", line)),
        "",
    )
    output_video = next((line for line in outgoing.splitlines() if "Video:" in line), "")
    size = re.search(r"(?<!\w)(\d{2,6})x(\d{2,6})(?!\w)", output_video)
    fps_match = re.search(r"([\d.]+)(k?)\s+fps\b", video) or re.search(
        r"([\d.]+)(k?)\s+tbr\b", video
    )
    if not (duration_match and separator and size and fps_match):
        raise MediaError("Could not read a finite video duration, display size, and frame rate.")
    hours, minutes, seconds = map(float, duration_match.groups())
    duration = hours * 3600 + minutes * 60 + seconds
    fps = float(fps_match[1]) * (1000 if fps_match[2] else 1)
    codec = re.search(r"Video:\s*([^\s,(]+)", video)
    if duration <= 0 or not math.isfinite(duration) or fps <= 0 or not math.isfinite(fps):
        raise MediaError("The source has an invalid duration or frame rate.")
    return MediaInfo(
        duration=duration, width=int(size[1]), height=int(size[2]), fps=fps,
        has_audio=bool(re.search(r"Stream #\S+.*Audio:", incoming)),
        video_codec=codec[1] if codec else "",
    )


def probe(source: Path) -> MediaInfo:
    """Decode one frame; FFmpeg reports the autorotated, square-pixel display size."""
    source = _source(source)
    result = _bounded(
        _base() + ["-loglevel", "info", "-threads", "2"] + _PROTOCOLS
        + ["-i", str(source), "-map", "0:v:0", "-an", "-sn", "-dn",
           "-vf", _NORMALIZE,
           "-frames:v", "1", "-f", "null", "-"],
        timeout=30,
    )
    return _parse_probe(result.stderr.decode("utf-8", errors="replace"))


def thumbnail(source: Path, output: Path, at: float = 0) -> None:
    source = _source(source)
    if not math.isfinite(at) or at < 0:
        raise MediaError("Thumbnail time must be a finite, nonnegative number.")
    output = Path(output).resolve()
    if output == source:
        raise MediaError("A thumbnail cannot overwrite its source.")
    if output.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise MediaError("Thumbnail output must be a .jpg or .png file.")
    _make_parent(output)
    partial = output.parent / f"thumb_{uuid4().hex}{output.suffix}"
    try:
        _bounded(
            _base() + ["-loglevel", "error", "-y", "-threads", "2", "-ss", f"{at:.6f}"]
            + _PROTOCOLS + ["-i", str(source), "-map", "0:v:0", "-an", "-sn", "-dn",
                           "-vf", "scale=480:trunc(480/(iw*sar/ih)/2)*2,setsar=1",
                           "-frames:v", "1", "-update", "1", partial.name],
            cwd=output.parent,
        )
        if not partial.is_file() or partial.stat().st_size == 0:
            raise MediaError("No thumbnail frame exists at that time.")
        os.replace(partial, output)
    finally:
        partial.unlink(missing_ok=True)


def _duration(info: MediaInfo, clip: Clip) -> float:
    if clip.start >= info.duration or clip.end > info.duration + 0.1:
        raise MediaError("The selected clip extends beyond the source video.")
    return min(clip.end, info.duration) - clip.start


def _stderr_reader(stream, lines: deque[str], capture: list[str] | None = None) -> None:
    try:
        for line in iter(stream.readline, b""):
            text = line.decode("utf-8", errors="replace").rstrip()
            lines.append(text)
            if capture is not None:
                capture.append(text)
    finally:
        stream.close()


def _run(
    command: list[str], cwd: Path, duration: float, progress: Progress, cancel: threading.Event,
    *, start: float = 0, span: float = 1, stderr_capture: list[str] | None = None,
) -> None:
    """Drain both pipes concurrently; only the subprocess we started can be terminated."""
    _check_cancel(cancel)
    try:
        process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=_creationflags(),
        )
    except OSError as exc:
        raise MediaError(f"Could not launch FFmpeg: {exc}") from exc
    errors: deque[str] = deque(maxlen=60)
    updates: queue.SimpleQueue[str] = queue.SimpleQueue()

    def read_progress() -> None:
        try:
            for line in iter(process.stdout.readline, b""):
                updates.put(line.decode("ascii", errors="replace").strip())
        finally:
            process.stdout.close()

    readers = [
        threading.Thread(target=_stderr_reader, args=(process.stderr, errors, stderr_capture), daemon=True),
        threading.Thread(target=read_progress, daemon=True),
    ]
    for reader in readers:
        reader.start()
    started = last_update = time.monotonic()
    try:
        while True:
            _check_cancel(cancel)
            while not updates.empty():
                line = updates.get()
                last_update = time.monotonic()
                if line.startswith("out_time_us="):
                    try:
                        fraction = int(line.split("=", 1)[1]) / 1_000_000 / duration
                    except ValueError:
                        continue
                    progress(start + span * min(0.995, max(0, fraction)), "Encoding vertical video")
            if process.poll() is not None:
                break
            if time.monotonic() - last_update > 120:
                raise MediaError("FFmpeg stopped reporting progress for two minutes.")
            if time.monotonic() - started > max(180, duration * 90):
                raise MediaError("The render exceeded its bounded processing time.")
            cancel.wait(0.08)
        for reader in readers:
            reader.join(timeout=3)
        _check_cancel(cancel)
        if process.returncode:
            raise MediaError(f"FFmpeg could not render this clip: {_detail(chr(10).join(errors))}")
    finally:
        _stop(process)
        for reader in readers:
            reader.join(timeout=3)


def _sample_frames(
    source: Path, info: MediaInfo, clip: Clip, cancel: threading.Event,
) -> Iterator[tuple[float, np.ndarray]]:
    duration = _duration(info, clip)
    rate = min(2.0, _MAX_SAMPLES / duration)
    factor = min(1.0, 480 / max(info.width, info.height))
    width = max(2, int(info.width * factor) // 2 * 2)
    height = max(2, int(info.height * factor) // 2 * 2)
    count = min(_MAX_SAMPLES, max(1, math.ceil(duration * rate)))
    command = (
        _base() + ["-loglevel", "error", "-threads", "2", "-ss", f"{clip.start:.6f}"]
        + _PROTOCOLS + ["-i", str(source), "-t", f"{duration:.6f}", "-map", "0:v:0",
                       "-an", "-sn", "-dn", "-vf",
                       f"fps={rate:.9f}:start_time=0:round=up,scale={width}:{height},setsar=1",
                       "-frames:v", str(count), "-threads", "1", "-pix_fmt", "rgb24",
                       "-f", "rawvideo", "pipe:1"]
    )
    _check_cancel(cancel)
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_creationflags(),
        )
    except OSError as exc:
        raise MediaError(f"Could not start face-analysis decoding: {exc}") from exc
    errors: deque[str] = deque(maxlen=30)
    frames: queue.Queue[bytes | None] = queue.Queue(maxsize=2)
    finished = threading.Event()

    def put(value: bytes | None) -> bool:
        while not finished.is_set():
            try:
                frames.put(value, timeout=0.1)
                return True
            except queue.Full:
                continue
        return False

    def read_frames() -> None:
        try:
            size = width * height * 3
            while not finished.is_set():
                frame = process.stdout.read(size)
                if not frame:
                    break
                if len(frame) != size:
                    errors.append("The decoder returned an incomplete video frame.")
                    break
                if not put(frame):
                    break
        finally:
            put(None)
            process.stdout.close()

    readers = [
        threading.Thread(target=_stderr_reader, args=(process.stderr, errors), daemon=True),
        threading.Thread(target=read_frames, daemon=True),
    ]
    for reader in readers:
        reader.start()
    index = 0
    deadline = time.monotonic() + max(90, duration * 5)
    try:
        while True:
            _check_cancel(cancel)
            if time.monotonic() > deadline:
                raise MediaError("Face-analysis decoding exceeded its time limit.")
            try:
                frame = frames.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                break
            yield index / rate, np.frombuffer(frame, dtype=np.uint8).reshape(height, width, 3)
            index += 1
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise MediaError("The frame decoder did not finish.") from exc
        for reader in readers:
            reader.join(timeout=2)
        if process.returncode or errors:
            raise MediaError(f"Could not analyze source frames: {_detail(chr(10).join(errors))}")
        if not index:
            raise MediaError("The selected clip contains no decodable video frames.")
    finally:
        finished.set()
        _stop(process)
        for reader in readers:
            reader.join(timeout=3)


@dataclass
class _Observation:
    time: float
    face: Region | None
    ambiguous: bool = False
    cut: bool = False
    detail: float = 0


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _padded_face(face: Region) -> Region:
    width, height = min(1, face.w * 2.0), min(1, face.h * 2.2)
    return Region(
        x=_clamp(face.x + face.w / 2 - width / 2, 0, 1 - width),
        y=_clamp(face.y + face.h * 0.45 - height * 0.42, 0, 1 - height),
        w=width, h=height,
    )


def _smooth_track(observations: list[_Observation]) -> list[TrackPoint]:
    points: list[TrackPoint] = []
    previous: Region | None = None
    pending_cut = False
    for observation in observations:
        pending_cut |= observation.cut
        if observation.face is None or observation.ambiguous:
            continue
        face = observation.face
        reset = pending_cut or previous is None
        if not reset:
            values = {}
            for key in ("x", "y", "w", "h"):
                old, new = getattr(previous, key), getattr(face, key)
                values[key] = old if abs(new - old) <= 0.012 else old + (new - old) * 0.45
            values["x"] = min(values["x"], 1 - values["w"])
            values["y"] = min(values["y"], 1 - values["h"])
            face = Region(**values)
        points.append(TrackPoint(time=observation.time, cut=pending_cut, **face.model_dump()))
        previous, pending_cut = face, False
    return points


def _choose_analysis(observations: list[_Observation], info: MediaInfo, duration: float) -> Analysis:
    warnings = ["Face framing is a sampled Haar-detector heuristic, not action or active-speaker recognition."]
    track = _smooth_track(observations)
    good = [o for o in observations if o.face is not None and not o.ambiguous]
    confidence = len(good) / max(1, len(observations))
    fallback = Analysis(
        layout="fit", confidence=confidence,
        message="Preserving the complete picture: no sustained, unambiguous main face.",
        track=track, warnings=warnings,
    )
    if good:
        faces = np.array([[o.face.x, o.face.y, o.face.w, o.face.h] for o in good])
        median = np.median(faces, axis=0)
        face = Region(x=float(median[0]), y=float(median[1]), w=float(median[2]), h=float(median[3]))
        fallback.face_region = _padded_face(face)
    if info.width <= info.height:
        fallback.message = "Preserving the original portrait composition."
        return fallback
    if len(good) < 3 or confidence < 0.78 or any(o.ambiguous for o in observations):
        return fallback
    times = [0, *(o.time for o in good), duration]
    if max(b - a for a, b in zip(times, times[1:])) > 1.5:
        return fallback
    if any(o.cut and o.face is None for o in observations):
        return fallback
    corners = [
        (o.face.x + o.face.w / 2 < 0.25 or o.face.x + o.face.w / 2 > 0.75)
        and (o.face.y + o.face.h / 2 < 0.3 or o.face.y + o.face.h / 2 > 0.7)
        for o in good
    ]
    stable = float(np.max(np.std(faces[:, :2], axis=0))) < 0.035
    split = (
        info.width / info.height >= 1.35 and confidence >= 0.88 and duration >= 2
        and face.w <= 0.22 and face.h <= 0.32 and face.w * face.h <= 0.04
        and sum(corners) / len(corners) >= 0.9 and stable
        and float(np.median([o.detail for o in good])) > 0.055
    )
    if split:
        return Analysis(
            layout="split", confidence=confidence, track=track, face_region=fallback.face_region,
            message="A persistent small corner face suggests screen plus webcam; review both regions.",
            warnings=warnings + ["Split is heuristic. Confirm the face and screen rectangles before exporting."],
        )
    if face.w < 0.08 or face.h < 0.12:
        return fallback
    return Analysis(
        layout="follow", confidence=confidence, track=track, face_region=fallback.face_region,
        message="Following a sustained dominant face with smoothing and sampled scene-cut resets.",
        warnings=warnings,
    )


def analyze(
    source: Path, info: MediaInfo, clip: Clip, progress: Progress, cancel: threading.Event,
) -> Analysis:
    if clip.layout == "leetcode":
        raise MediaError("LeetCode uses supplied avatar/editor regions, not automatic face detection.")
    source = _source(source)
    duration = _duration(info, clip)
    _check_cancel(cancel)
    progress(0, "Sampling only the selected clip for face framing")
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        progress(1, "Face detector unavailable; preserving the full source")
        return Analysis(
            layout="fit", confidence=0, message="Face detector unavailable; preserving the full source.",
            warnings=["OpenCV's bundled Haar detector is missing. Reinstall opencv-python to enable face framing."],
        )
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise MediaError("OpenCV could not load its bundled face detector.")
    observations: list[_Observation] = []
    previous_small = previous_hist = None
    try:
        for timestamp, frame in _sample_frames(source, info, clip, cancel):
            _check_cancel(cancel)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            small = cv2.resize(gray, (32, 32))
            hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
            cv2.normalize(hist, hist, alpha=1, norm_type=cv2.NORM_L1)
            cut = False
            if previous_small is not None:
                distance = cv2.compareHist(previous_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                change = float(np.mean(np.abs(small.astype(float) - previous_small.astype(float))))
                cut = distance > 0.60 or (change > 48 and distance > 0.25)
            previous_small, previous_hist = small, hist
            boxes = detector.detectMultiScale(
                cv2.equalizeHist(gray), scaleFactor=1.1, minNeighbors=5, minSize=(18, 18),
            )
            boxes = sorted(boxes, key=lambda box: int(box[2]) * int(box[3]), reverse=True)
            ambiguous = len(boxes) > 1 and boxes[1][2] * boxes[1][3] >= boxes[0][2] * boxes[0][3] * 0.3
            face = None
            edges = cv2.Canny(gray, 70, 140)
            if boxes:
                x, y, width, height = map(int, boxes[0])
                face = Region(x=x / frame.shape[1], y=y / frame.shape[0],
                              w=width / frame.shape[1], h=height / frame.shape[0])
                edges[y:y + height, x:x + width] = 0
            observations.append(_Observation(timestamp, face, ambiguous, cut, float(np.mean(edges > 0))))
            progress(min(0.99, timestamp / duration), "Checking face stability and scene changes")
    except cv2.error as exc:
        raise MediaError(f"OpenCV face analysis failed: {exc}") from exc
    analysis = _choose_analysis(observations, info, duration)
    progress(1, analysis.message)
    return analysis


def _clip_cues(cues: list[Cue], clip: Clip, duration: float) -> list[Cue]:
    result = []
    for cue in sorted(cues, key=lambda cue: (cue.start, cue.end)):
        if cue.end <= clip.start or cue.start >= clip.start + duration:
            continue
        # Split on the source timeline before trimming. Otherwise a short cut
        # inside a long paragraph replays every word at a compressed speed.
        for index, (begin, finish, text) in enumerate(_caption_bursts(
                cue, width=20 if clip.caption_style == "punchy" else 24)):
            start, end = max(0, begin - clip.start), min(duration, finish - clip.start)
            if end > start:
                result.append(Cue(id=f"{cue.id}:{index}", start=start, end=end, text=text))
    return result


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def _srt(cues: list[Cue]) -> str:
    return "\n\n".join(
        f"{i}\n{_srt_time(cue.start)} --> {_srt_time(cue.end)}\n{cue.text}"
        for i, cue in enumerate(cues, 1)
    ) + ("\n" if cues else "")


def _ass_escape(text: str) -> str:
    # WORD JOINER leaves a literal backslash visible but prevents \N, \h or overrides.
    return (
        text.replace("\\", "\\\u2060").replace("{", r"\{").replace("}", r"\}")
        .replace("\r\n", "\n").replace("\r", "\n").replace("\n", r"\N")
    )


def _caption_bursts(cue: Cue, width: int = 28) -> list[tuple[float, float, str]]:
    lines: list[str] = []
    for paragraph in cue.text.splitlines():
        lines.extend(_caption_lines(paragraph, width))
    chunks = ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    weights = [max(1, len(chunk)) for chunk in chunks]
    total, elapsed = sum(weights), 0
    result = []
    for chunk, weight in zip(chunks, weights):
        start = cue.start + (cue.end - cue.start) * elapsed / total
        elapsed += weight
        end = cue.start + (cue.end - cue.start) * elapsed / total
        result.append((start, end, chunk))
    return result


def _caption_lines(paragraph: str, width: int) -> list[str]:
    def units(char: str) -> float:
        if unicodedata.combining(char) or char == "\u200d":
            return 0
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            return 2
        if char in "MW@%":
            return 1.8
        return 1.2 if char.isupper() else 1

    lines: list[str] = []
    line, length = "", 0.0
    for word in paragraph.split():
        word_length = sum(map(units, word))
        if line and length + 1 + word_length > width:
            lines.append(line)
            line, length = "", 0
        if line:
            line += " "
            length += 1
        for char in word:
            cost = units(char)
            if line and length + cost > width:
                lines.append(line)
                line, length = "", 0
            line += char
            length += cost
    if line or not lines:
        lines.append(line)
    return lines


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    seconds, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def _ass(cues: list[Cue], clip: Clip) -> str:
    heading = None
    correction = None
    if clip.correction is not None:
        from .editorial_corrections import correction_layout

        correction = correction_layout(clip.correction.text)
    if clip.question_title is not None:
        from .question_titles import title_layout

        heading = title_layout(clip.question_title)
    font = "Arial" if (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf").is_file() else "sans-serif"
    punchy = clip.caption_style == "punchy"
    size, outline = (64, 5) if punchy else (56, 3)
    y = round(_clamp(clip.subtitle_y * 1920, 1920 * 0.14 + size * 1.5, 1920 * 0.65 - size * 1.5))
    border, shadow, center, left, right = 1, 2, 497, 65, 151
    outline_color, back_color = "&H00101010", "&H80000000"
    if clip.layout == "leetcode":
        border, outline, shadow, center, left, right = 3, 8, 0, 540, 54, 54
        outline_color = back_color = "&H20181818"
        y = round(_clamp(clip.subtitle_y * 1920, 1920 * 0.74 + size * 1.5 + outline,
                         1920 * 0.96 - size * 1.5))
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n"
        "; Bursts use proportional cue timing, NOT word-accurate alignment or karaoke.\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,{outline_color},{back_color},"
        f"-1,0,0,0,100,100,0,0,{border},{outline},{shadow},5,{left},{right},0,1\n"
        + (f"Style: Question,Consolas,{heading['font_size']},&H00FFFFFF,&H00FFFFFF,"
           "&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,5,54,54,0,1\n" if heading else "")
        + (f"Style: Correction,Consolas,{correction['font_size']},&H00D5E8EE,&H00D5E8EE,"
           "&H00362B00,&H00362B00,0,0,0,0,100,100,0,0,3,8,0,5,54,54,0,1\n" if correction else "")
        + "\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    if correction:
        events.append(
            f"Dialogue: 2,0:00:00.00,{_ass_time(clip.end - clip.start)},Correction,,0,0,0,,"
            + r"{\an5\q2\pos(540,1384)}" + _ass_escape("\n".join(correction["lines"]))
        )
    if heading:
        events.append(
            f"Dialogue: 1,0:00:00.00,{_ass_time(clip.end - clip.start)},Question,,0,0,0,,"
            + r"{\an5\q2\pos(540,152)}" + _ass_escape("\n".join(heading["lines"]))
        )
    for cue in cues:
        for start, end, text in _caption_bursts(cue, width=20 if punchy else 24):
            start_time, end_time = _ass_time(start), _ass_time(end)
            if start_time == end_time:
                end_time = _ass_time(start + 0.01)
            events.append(
                f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,"
                + r"{\an5\q2\pos(" + str(center) + "," + str(y) + ")}" + _ass_escape(text)
            )
    return header + "\n".join(events) + "\n"


def _crop_size(info: MediaInfo, track: list[TrackPoint] | None = None) -> tuple[int, int]:
    height = min(info.height, info.width * 16 / 9)
    if track:
        needed = max(max(p.h * info.height * 4.2, p.w * info.width * 1.8 * 16 / 9) for p in track)
        height = min(height, max(height * 0.82, needed))
    return max(2, int(height * 9 / 16) // 2 * 2), max(2, int(height) // 2 * 2)


def _crop_xy(point: TrackPoint, info: MediaInfo, width: int, height: int) -> tuple[float, float]:
    return (
        _clamp((point.x + point.w / 2) * info.width - width / 2, 0, info.width - width),
        _clamp((point.y + point.h * 0.38) * info.height - height * 0.32, 0, info.height - height),
    )


def _track_commands(track: list[TrackPoint], info: MediaInfo, width: int, height: int) -> str:
    if not track:
        raise MediaError("Follow framing needs a usable face track. Analyze again or choose Fit / Manual.")
    points = sorted(track, key=lambda point: point.time)
    if points[0].time > 0:
        points.insert(0, points[0].model_copy(update={"time": 0}))
    lines = []
    for index, point in enumerate(points):
        x, y = _crop_xy(point, info, width, height)
        ex, ey = f"{x:.6f}", f"{y:.6f}"
        if index + 1 < len(points):
            next_point = points[index + 1]
            dt = next_point.time - point.time
            if dt > 0 and not next_point.cut:
                nx, ny = _crop_xy(next_point, info, width, height)
                ex += f"+({nx - x:.6f})*(t-{point.time:.6f})/{dt:.6f}"
                ey += f"+({ny - y:.6f})*(t-{point.time:.6f})/{dt:.6f}"
        lines.append(f"{point.time:.6f} crop@subject x '{ex}', crop@subject y '{ey}';")
    return "\n".join(lines) + "\n"


def _region_crop(region: Region, info: MediaInfo) -> str:
    width = max(2, min(info.width, int(region.w * info.width)) // 2 * 2)
    height = max(2, min(info.height, int(region.h * info.height)) // 2 * 2)
    x = min(info.width - width, max(0, int(region.x * info.width) // 2 * 2))
    y = min(info.height - height, max(0, int(region.y * info.height) // 2 * 2))
    return f"crop={width}:{height}:{x}:{y}"


def _results_ease(elapsed: float, duration: float, clock: str = "t") -> str:
    if not math.isfinite(elapsed) or elapsed < 0 or not math.isfinite(duration) or duration <= 0:
        raise MediaError("Results animation timing must be finite, with positive duration and nonnegative elapsed time.")
    # Reserve a hold for short events, and reach the final size on their last frame.
    ramp = min(1.9, duration * 0.8, max(0, duration - 1 / 30))
    if ramp < 1e-9:
        return "1"
    return f"(1-cos(PI*clip(({clock}+{elapsed:.12f})/{ramp:.12f},0,1)))/2"


def _filter_graph(
    info: MediaInfo, clip: Clip, layout: str, width: int, height: int,
    face: Region | None, track: list[TrackPoint], ass_name: str | None, commands_name: str | None,
    *, results_elapsed: float = 0, results_duration: float | None = None,
    results_dim_elapsed: float | None = None, results_dim_duration: float | None = None,
    fade_in_frames: int = 0, fade_out_frames: int = 0, retained_frames: int | None = None,
) -> str:
    """Results elapsed/duration are retained output seconds within a same-ROI event.

    Elapsed offsets this segment's local clock; duration is the entire event,
    defaulting to the bounded clip duration for a standalone render.
    Separate dim timing spans adjacent results crops; omitted values inherit zoom timing.
    """
    no_camera = layout == "leetcode" and clip.camera_mode == "absent"
    results = layout == "leetcode" and clip.results_zoom
    if results:
        event_duration = _duration(info, clip) if results_duration is None else results_duration
        ease = _results_ease(results_elapsed, event_duration)
        dim_ease = _results_ease(
            results_elapsed if results_dim_elapsed is None else results_dim_elapsed,
            event_duration if results_dim_duration is None else results_dim_duration, "T",
        )
    filters = [f"[0:v:0]setpts=PTS-STARTPTS,{_NORMALIZE},fps=30[base]"]
    if layout in {"manual", "follow"}:
        crop_width, crop_height = _crop_size(info, track if layout == "follow" else None)
        if layout == "follow":
            x, y = _crop_xy(track[0], info, crop_width, crop_height)
            filters.append(
                f"[base]sendcmd=f={commands_name},crop@subject={crop_width}:{crop_height}:{x:.6f}:{y:.6f},"
                f"scale={width}:{height}:flags=lanczos[composed]"
            )
        else:
            x = _clamp(clip.focus_x * info.width - crop_width / 2, 0, info.width - crop_width)
            y = _clamp(clip.focus_y * info.height - crop_height / 2, 0, info.height - crop_height)
            filters.append(f"[base]crop={crop_width}:{crop_height}:{x:.6f}:{y:.6f},scale={width}:{height}:flags=lanczos[composed]")
    else:
        branches = "[back][front]" if layout == "fit" else "[back][screen]" if no_camera else "[back][face][screen]"
        filters.append(f"[base]split={2 if layout == 'fit' or no_camera else 3}{branches}")
        # Blur at quarter resolution; this background does not pretend to restore source detail.
        bw, bh = width // 4 // 2 * 2, height // 4 // 2 * 2
        background = (
            f"[back]scale={bw}:{bh}:force_original_aspect_ratio=increase,"
            f"crop={bw}:{bh},gblur=sigma=16"
        )
        if results:
            # Dim only the blurred backdrop, before placing the bright camera/results.
            filters += [
                background + ",split=2[undimmed][shade]",
                "[shade]drawbox=color=black:t=fill[black]",
                f"[undimmed][black]blend=all_expr='A+(B-A)*0.70*({dim_ease})',"
                f"scale={width}:{height}[background]",
            ]
        else:
            filters.append(background + f",scale={width}:{height}[background]")
        if layout == "fit":
            pane_height = height if info.height >= info.width else int(height * 0.62) // 2 * 2
            filters.append(
                f"[front]scale={width}:{pane_height}:force_original_aspect_ratio=decrease:"
                "force_divisible_by=2:flags=lanczos[sharp]"
            )
            y = "(H-h)/2" if info.height >= info.width else f"({height * 0.62:.4f}-h)/2"
            filters.append(f"[background][sharp]overlay=(W-w)/2:{y}:shortest=1[composed]")
        elif layout == "leetcode":
            if clip.content_region is None or (not no_camera and face is None):
                raise MediaError("LeetCode requires explicit avatar and code/results regions.")
            if no_camera and (face is not None or clip.face_region is not None):
                raise MediaError("An absent camera cannot have a face_region.")
            fw = int(width * 0.80) // 2 * 2
            fh = int(height * 0.25) // 2 * 2
            sw = int(width * 0.95) // 2 * 2
            sh = int(height * (0.69 if no_camera else 0.41)) // 2 * 2
            fy = height * 0.05
            sy = height * (0.05 if no_camera else 0.33)
            if clip.question_title is not None:
                fy = height * 0.16
                fh = int(height * 0.20) // 2 * 2
                sy = height * (0.16 if no_camera else 0.39)
                sh = int(height * (0.58 if no_camera else 0.35)) // 2 * 2
            if clip.correction is not None:
                sh = int(height * 0.66 - sy) // 2 * 2
            editor_scale = (
                f"scale={sw}:{sh}:force_original_aspect_ratio=decrease:"
                "force_divisible_by=2:flags=lanczos"
            )
            if results:
                # Scale the whole verified ROI, never zoom by cropping away evidence.
                factor = f"(0.68+0.32*({ease}))"
                editor_scale = (
                    f"scale=w='max(2,trunc(min({sw}/iw,{sh}/ih)*iw*{factor}/2)*2)':"
                    f"h='max(2,trunc(min({sw}/iw,{sh}/ih)*ih*{factor}/2)*2)':"
                    "eval=frame:flags=lanczos,setsar=1"
                )
            if no_camera:
                filters += [
                    f"[screen]{_region_crop(clip.content_region, info)},{editor_scale}[editor]",
                    f"[background][editor]overlay=(W-w)/2:{sy:.4f}+({sh}-h)/2:shortest=1[composed]",
                ]
            else:
                filters += [
                    f"[face]{_region_crop(face, info)},scale={fw}:{fh}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos[avatar]",
                    f"[screen]{_region_crop(clip.content_region, info)},{editor_scale}[editor]",
                    f"[background][avatar]overlay=(W-w)/2:{fy:.4f}+({fh}-h)/2:shortest=1[layer]",
                    f"[layer][editor]overlay=(W-w)/2:{sy:.4f}+({sh}-h)/2:shortest=1[composed]",
                ]
        else:
            if face is None:
                raise MediaError("Split needs a face region. Draw the webcam rectangle or analyze a visible face first.")
            content = clip.content_region or Region(x=0, y=0, w=1, h=1)
            fw, fh = int(width * 0.86) // 2 * 2, int(height * 0.25) // 2 * 2
            sw, sh = int(width * 0.94) // 2 * 2, int(height * 0.27) // 2 * 2
            filters += [
                f"[face]{_region_crop(face, info)},scale={fw}:{fh}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos[webcam]",
                f"[screen]{_region_crop(content, info)},scale={sw}:{sh}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos[content]",
                f"[background][webcam]overlay=(W-w)/2:{height * 0.045:.4f}+({fh}-h)/2:shortest=1[layer]",
                f"[layer][content]overlay=(W-w)/2:{height * 0.30:.4f}+({sh}-h)/2:shortest=1[composed]",
            ]
    tail = ""
    if fade_in_frames:
        tail += f"fade=t=in:start_frame=0:nb_frames={fade_in_frames},"
    if fade_out_frames:
        if retained_frames is None or retained_frames <= fade_out_frames:
            raise MediaError("A transition needs its exact retained frame count.")
        tail += f"fade=t=out:start_frame={retained_frames - fade_out_frames}:nb_frames={fade_out_frames},"
    # Permanent headings and spoken captions are composited after safe-gap effects.
    tail += f"ass=filename={ass_name}," if ass_name else ""
    filters.append(f"[composed]{tail}setsar=1,format=yuv420p[outv]")
    return ";\n".join(filters)


@lru_cache(maxsize=8)
def _capabilities(executable: str) -> tuple[bool, bool]:
    encoders = _bounded([executable, "-hide_banner", "-encoders"], timeout=15)
    filters = _bounded([executable, "-hide_banner", "-filters"], timeout=15)
    return b"libx264" in encoders.stdout, bool(re.search(rb"\bass\s+", filters.stdout))


def _prepare_layout(
    source: Path, info: MediaInfo, clip: Clip, progress: Progress, cancel: threading.Event,
) -> tuple[str, Region | None, list[TrackPoint], Analysis | None]:
    if clip.layout == "leetcode":
        if clip.content_region is None or (clip.camera_mode == "required" and clip.face_region is None):
            raise MediaError("LeetCode requires explicit avatar and code/results regions.")
        if clip.camera_mode == "absent" and clip.face_region is not None:
            raise MediaError("An absent camera cannot have a face_region.")
        return "leetcode", clip.face_region, [], None
    need_analysis = clip.layout in {"auto", "follow"} or (clip.layout == "split" and clip.face_region is None)
    analysis = clip.analysis if need_analysis else None
    if need_analysis and analysis is None:
        analysis = analyze(source, info, clip, progress, cancel)
    layout = analysis.layout if clip.layout == "auto" and analysis else clip.layout
    face = clip.face_region or (analysis.face_region if analysis else None)
    track = analysis.track if analysis else []
    if layout == "follow" and (not track or (analysis and analysis.layout == "fit")):
        layout = "fit"
        if analysis:
            analysis = analysis.model_copy(deep=True)
            analysis.warnings.append("Requested Follow fell back to Fit because no sustained unambiguous face was available.")
            analysis.layout = "fit"
    if layout == "split" and face is None:
        raise MediaError("Split needs a face region. Draw the webcam rectangle or analyze a visible face first.")
    return layout, face, track, analysis


def render(
    source: Path, info: MediaInfo, clip: Clip, cues: list[Cue], output: Path, preview: bool,
    progress: Progress, cancel: threading.Event,
) -> Analysis | None:
    source = _source(source)
    duration = _duration(info, clip)
    _check_cancel(cancel)
    output = Path(output).resolve()
    if output == source or output.suffix.lower() != ".mp4":
        raise MediaError("Choose a separate .mp4 output file; the source cannot be overwritten.")
    local_cues = _clip_cues(cues, clip, duration)
    x264, ass = _capabilities(ffmpeg_exe())
    if not x264 or (((clip.captions and local_cues) or clip.question_title is not None
                    or clip.correction is not None) and not ass):
        raise MediaError("This FFmpeg build needs libx264 and libass. Use the bundled imageio-ffmpeg binary.")
    need_analysis = clip.layout in {"auto", "follow"} or (clip.layout == "split" and clip.face_region is None)
    layout, face, track, analysis = _prepare_layout(
        source, info, clip, lambda fraction, message: progress(fraction * 0.2, message), cancel,
    )
    _make_parent(output)
    token = uuid4().hex
    partial = output.parent / f"render_{token}.mp4"
    ass_path = output.parent / f"captions_{token}.ass"
    graph_path = output.parent / f"graph_{token}.txt"
    commands_path = output.parent / f"track_{token}.txt"
    srt_partial = output.parent / f"captions_{token}.srt"
    artifacts = [partial, ass_path, graph_path, commands_path, srt_partial]
    sidecar_published = False
    complete = False
    try:
        ass_name = None
        if (clip.captions and local_cues) or clip.question_title is not None or clip.correction is not None:
            ass_path.write_text(_ass(local_cues if clip.captions else [], clip), encoding="utf-8")
            ass_name = ass_path.name
        if local_cues:
            srt_partial.write_text(_srt(local_cues), encoding="utf-8")
        if layout == "follow":
            crop_width, crop_height = _crop_size(info, track)
            commands_path.write_text(_track_commands(track, info, crop_width, crop_height), encoding="utf-8")
        width, height = (360, 640) if preview else (1080, 1920)
        graph_path.write_text(
            _filter_graph(info, clip, layout, width, height, face, track, ass_name,
                          commands_path.name if layout == "follow" else None),
            encoding="utf-8",
        )
        command = (
            _base() + ["-loglevel", "warning", "-y", "-threads", "2", "-ss", f"{clip.start:.6f}"]
            + _PROTOCOLS + ["-i", str(source), "-t", f"{duration:.6f}",
                           "-filter_complex_threads", "2", "-filter_complex_script", graph_path.name,
                           "-map", "[outv]", "-map", "0:a:0?", "-sn", "-dn",
                           "-map_metadata", "-1", "-map_chapters", "-1",
                           "-c:v", "libx264", "-threads", "2",
                           "-preset", "veryfast" if preview else "fast", "-crf", "25" if preview else "20",
                           "-pix_fmt", "yuv420p", "-r", "30",
                           "-c:a", "aac", "-b:a", "128k" if preview else "192k", "-ar", "48000",
                           "-af", "aresample=48000:first_pts=0",
                           "-movflags", "+faststart", "-metadata:s:v:0", "rotate=0",
                           "-progress", "pipe:1", "-nostats", partial.name]
        )
        progress(0.2 if need_analysis else 0, "Rendering preview" if preview else "Rendering 1080 × 1920 export")
        _run(command, output.parent, duration, progress, cancel,
             start=0.2 if need_analysis else 0, span=0.79 if need_analysis else 0.99)
        if not partial.is_file() or partial.stat().st_size < 100:
            raise MediaError("FFmpeg finished without producing a usable MP4.")
        _check_cancel(cancel)
        verified = probe(partial)
        if (verified.width, verified.height, verified.video_codec) != (width, height, "h264"):
            raise MediaError("The rendered MP4 failed its video format verification.")
        _check_cancel(cancel)
        if local_cues:
            os.replace(srt_partial, output.with_suffix(".srt"))
            sidecar_published = True
        os.replace(partial, output)
        complete = True
        progress(1, "Preview ready" if preview else "Export ready")
        return analysis
    except OSError as exc:
        raise MediaError(f"Could not write the rendered clip: {exc}") from exc
    finally:
        for artifact in artifacts:
            artifact.unlink(missing_ok=True)
        if sidecar_published and not complete:
            output.with_suffix(".srt").unlink(missing_ok=True)
