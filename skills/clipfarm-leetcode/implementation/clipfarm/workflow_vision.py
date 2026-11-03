"""Local visual evidence, not a certification that unsampled video is clean.

Images and OCR boxes use the autorotated, square-pixel source coordinate system.
``ScreenReader.inspect`` accepts uint8 BGR images (including caller-supplied ROI
crops); its boxes are pixel coordinates relative to that image, not normalized.
No video, image, or recognized text is sent to a service.
"""

from __future__ import annotations

import json
import math
import queue
import re
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Callable, Iterator
from uuid import uuid4

import cv2
import numpy as np

from . import media
from .models import MediaInfo


class VisionError(media.MediaError):
    """Evidence could not be obtained; callers must not interpret this as clean."""


_BRB = re.compile(r"(?<!\w)(?:b[\s.\-]*r[\s.\-]*b|be\s+right\s+back)(?!\w)", re.I)
_ACCEPTED = re.compile(
    r"^\s*accepted(?:\s*[!✓✔]|\s*\d+\s*/\s*\d+\s+test\s*cases?\s+passed"
    r"|\s+runtime\s*:\s*\d+(?:\.\d+)?\s*ms)?\s*$", re.I,
)
_RUNTIME = re.compile(r"^\s*[©ⓘ@]?\s*(?:run\s*time|execution\s*time)\s*[:：]?\s*", re.I)
_MILLISECONDS = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?)\s*(?:[|·]?\s*beats(?=\s|\d|$).*)?$", re.I,
)
_LIMIT = 20000
_DISCLAIMER = (
    "OCR can miss text or confuse it with code/history. No detection is not proof "
    "of absence; unsampled frames are unreviewed. Manually verify results and crops."
)


def _rect(word: dict) -> tuple[float, float, float, float]:
    points = word["box"]
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def _near(label: dict, value: dict) -> bool:
    x0, y0, x1, y1 = _rect(label)
    vx0, vy0, vx1, vy1 = _rect(value)
    height = max(y1 - y0, vy1 - vy0, 8)
    same_line = abs((y0 + y1 - vy0 - vy1) / 2) <= height
    below = 0 <= vy0 - y1 <= max(height * 4, 75)
    return ((same_line and -height <= vx0 - x1 <= max(height * 12, 180))
            or (below and vx0 < x1 + height * 3 and vx1 > x0 - height * 3))


def _classify_words(words: list[dict]) -> dict:
    text = "\n".join(word["text"] for word in words)
    brb = bool(_BRB.search(text))
    reliable = [word for word in words if word["score"] >= 0.55]
    accepted_words = [word for word in reliable if _ACCEPTED.fullmatch(word["text"])]
    reliable_text = "\n".join(word["text"] for word in reliable)
    result_context = bool(
        accepted_words
        or re.search(r"\btest\s*results?\b", reliable_text, re.I)
        or (re.search(r"\bbeats\b", reliable_text, re.I)
            and re.search(r"\bmemory\b", reliable_text, re.I))
    )
    candidates = []
    if result_context:
        for label in reliable:
            label_text = label["text"]
            if _ACCEPTED.fullmatch(label_text) and re.search(r"\bruntime\b", label_text, re.I):
                label_text = re.sub(r"^\s*accepted\s+", "", label_text, flags=re.I)
            match = _RUNTIME.match(label_text)
            if not match:
                continue
            tail = label_text[match.end():].strip()
            direct = _MILLISECONDS.fullmatch(tail)
            if direct:
                candidates.append({"value": float(direct[1]), "words": [label]})
            elif not tail:
                for value in reliable:
                    if value is label or not _near(label, value):
                        continue
                    number = _MILLISECONDS.fullmatch(value["text"])
                    if number:
                        candidates.append({"value": float(number[1]), "words": [label, value]})
                    elif re.fullmatch(r"\d+(?:\.\d+)?", value["text"].strip()):
                        units = [w for w in reliable if re.fullmatch(r"ms", w["text"], re.I)
                                 and _near(value, w) and _near(label, w)]
                        if units:
                            candidates.append({"value": float(value["text"]),
                                               "words": [label, value, units[0]]})
    values = {item["value"] for item in candidates}
    warnings = []
    if not words:
        warnings.append("No text recognized; this is not evidence that the frame is safe.")
    if any(word["score"] < 0.55 for word in words):
        warnings.append("Low-confidence OCR text exists; inspect the frame manually.")
    if len(values) > 1:
        warnings.append("Conflicting runtime values; runtime_ms is deliberately unset.")
    return {
        "text": text, "brb": brb, "accepted": bool(accepted_words),
        "runtime_ms": next(iter(values)) if len(values) == 1 else None,
        "words": words, "runtime_candidates": candidates,
        "status": "text_detected" if words else "no_text",
        "warnings": warnings,
        "confidence": {
            "brb": "text_match" if brb else "not_detected",
            "accepted": "ocr_candidate_not_verified" if accepted_words else "not_detected",
            "runtime_ms": "ocr_candidate_not_verified" if len(values) == 1 else "unresolved",
        },
    }


class ScreenReader:
    """Reuse one local RapidOCR engine. Import/model load occurs only on construction."""

    def __init__(self) -> None:
        try:
            from rapidocr import RapidOCR
        except (ImportError, OSError) as exc:
            raise VisionError(
                'Local OCR is unavailable. In ClipFarm\'s environment run '
                'python -m pip install -e ".[workflow]" and retry; no scan was approved.'
            ) from exc
        try:
            self._engine = RapidOCR(params={
                "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
                "EngineConfig.onnxruntime.use_cuda": False,
                "EngineConfig.onnxruntime.use_dml": False,
                "Global.log_level": "error",
            })
        except Exception as exc:
            raise VisionError(f"Could not initialize local RapidOCR: {exc}") from exc
        self._lock = threading.Lock()

    def inspect(self, image: np.ndarray) -> dict:
        """Inspect a BGR uint8 frame or crop; OCR geometry stays relative to it."""
        if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
                or image.ndim != 3 or image.shape[2] != 3 or not image.size):
            raise VisionError("OCR requires a nonempty uint8 BGR image with three channels.")
        try:
            with self._lock:
                output = self._engine(np.ascontiguousarray(image))
            fields = (output.boxes, output.txts, output.scores)
            if all(value is None for value in fields):
                result = []
            elif any(value is None for value in fields) or len({len(value) for value in fields}) != 1:
                raise ValueError("Malformed OCR output")
            else:
                result = list(zip(*fields))
            words = []
            for box, text, score in result or []:
                points = np.asarray(box, dtype=float)
                score = float(score)
                if (points.shape != (4, 2) or not np.isfinite(points).all()
                        or not math.isfinite(score) or not 0 <= score <= 1
                        or not isinstance(text, str)):
                    raise ValueError("Malformed OCR geometry, score or text")
                if text.strip():
                    words.append({"text": text.strip(), "score": score, "box": points.tolist()})
            return _classify_words(words)
        except Exception as exc:
            raise VisionError(f"Local OCR failed; frame is unreviewed: {exc}") from exc


def _check_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise VisionError("Visual scan cancelled; coverage is incomplete.")


def _source_info(source: Path) -> tuple[Path, MediaInfo]:
    try:
        source = media._source(source)
        return source, media.probe(source)
    except (media.MediaError, OSError) as exc:
        raise VisionError(str(exc)) from exc


def _output_dir(path: Path) -> Path:
    if str(path).startswith(("\\\\", "//")):
        raise VisionError("Evidence must be written to a local directory.")
    try:
        path = Path(path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        raise VisionError(f"Could not create the evidence directory: {exc}") from exc


def _time(at: float, info: MediaInfo) -> float:
    if not isinstance(at, (float, int)) or not math.isfinite(at) or not 0 <= at < info.duration:
        raise VisionError(f"Frame time must be finite and in [0, {info.duration:g}).")
    return float(at)


def _command(source: Path, at: float) -> list[str]:
    return [
        media.ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error",
        "-threads", "2", "-ss", f"{at:.9f}", "-protocol_whitelist", "file,pipe",
        "-i", str(source), "-map", "0:v:0", "-an", "-sn", "-dn",
    ]


def _frame(source: Path, at: float, info: MediaInfo) -> np.ndarray:
    try:
        output = media._bounded(
            _command(source, at) + ["-vf", media._NORMALIZE, "-frames:v", "1",
                                   "-c:v", "png", "-threads", "1",
                                   "-f", "image2pipe", "pipe:1"], timeout=45,
        )
        if not output.stdout:
            raise VisionError(f"No video frame exists at {at:g}s (container duration may include audio padding).")
        image = cv2.imdecode(np.frombuffer(output.stdout, np.uint8), cv2.IMREAD_COLOR)
    except (media.MediaError, cv2.error) as exc:
        raise VisionError(f"Could not extract the frame at {at:g}s: {exc}") from exc
    if image is None or image.shape != (info.height, info.width, 3):
        raise VisionError(f"No full-resolution frame could be decoded at {at:g}s.")
    return image


def _save_image(path: Path, image: np.ndarray) -> str:
    try:
        ok, encoded = cv2.imencode(path.suffix, image)
        if not ok:
            raise VisionError(f"Could not encode evidence: {path.name}")
        path.write_bytes(encoded.tobytes())
    except (OSError, cv2.error) as exc:
        raise VisionError(f"Could not save evidence: {exc}") from exc
    return str(path.resolve())


def _image_name(at: float) -> str:
    return f"frame-{at:013.6f}.png"


def inspect_frame(source: Path, at: float, output_dir: Path,
                  reader: ScreenReader | None = None) -> dict:
    """Save and OCR one full-resolution frame. ``time`` is the requested seek time.

    FFmpeg seeks to the first decodable frame at/after it; source-frame quantization
    is reported, not falsely presented as a measured presentation timestamp.
    """
    source, info = _source_info(source)
    at = _time(at, info)
    directory = _output_dir(output_dir)
    image = _frame(source, at, info)
    path = _save_image(directory / _image_name(at), image)
    reader = reader if reader is not None else ScreenReader()
    try:
        result = reader.inspect(image)
    except Exception as exc:
        raise VisionError(f"OCR failed at {at:g}s; evidence remains at {path}: {exc}") from exc
    return {
        **result, "time": at, "image": path, "width": info.width, "height": info.height,
        "timestamp_kind": "requested_seek_seconds", "frame_period": 1 / info.fps,
    }


def _intervals(intervals: list[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    if not intervals:
        raise VisionError("At least one nonempty scan interval is required.")
    checked = []
    for interval in intervals:
        if (not isinstance(interval, (tuple, list)) or len(interval) != 2
                or not all(isinstance(t, (int, float)) and math.isfinite(t) for t in interval)):
            raise VisionError("Scan intervals must contain two finite timestamps.")
        start, end = map(float, interval)
        if not 0 <= start < end <= duration:
            raise VisionError(f"Scan intervals must lie within [0, {duration:g}].")
        checked.append((start, end))
    merged: list[tuple[float, float]] = []
    for start, end in sorted(checked):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _sample_times(intervals: list[tuple[float, float]], step: float,
                  info: MediaInfo) -> list[float]:
    if not isinstance(step, (int, float)) or not math.isfinite(step) or step <= 0:
        raise VisionError("Sampling step must be finite and positive.")
    times = set()
    for start, end in intervals:
        # The container duration may include a partial extra audio frame. Snap the
        # whole-source endpoint down to a nominal video-frame boundary before seeking.
        last_frame = math.floor(max(0, info.duration * info.fps - 1) + 1e-8) / info.fps
        last = min(end, last_frame)
        last = max(start, last)
        count = math.floor((last - start) / step) + 1
        if count > _LIMIT:
            raise VisionError(f"Scan would exceed {_LIMIT} samples; split it into bounded intervals.")
        times.update(round(start + index * step, 9) for index in range(count))
        times.add(round(last, 9))
        if len(times) > _LIMIT:
            raise VisionError(f"Scan would exceed {_LIMIT} samples; split it into bounded intervals.")
    return sorted(times)


def _brb_ranges(samples: list[dict], step: float, duration: float) -> list[dict]:
    ranges = []
    for sample in sorted(samples, key=lambda item: item["time"]):
        if not sample["brb"]:
            continue
        at = sample["time"]
        start, end = max(0, at - step), min(duration, at + step)
        if ranges and start <= ranges[-1]["end"] + 1e-8:
            ranges[-1]["end"] = max(end, ranges[-1]["end"])
            ranges[-1]["evidence_times"].append(at)
        else:
            ranges.append({
                "start": start, "end": end, "evidence_times": [at],
                "reason": "OCR BRB/be right back candidate; padded by one sample step, not exact boundaries.",
            })
    return ranges


def _stream_frames(source: Path, times: list[float], info: MediaInfo,
                   cancel: threading.Event | None) -> Iterator[tuple[float, np.ndarray]]:
    """Decode a bounded regular run in one process; queue at most two full frames."""
    step = times[1] - times[0]
    command = _command(source, times[0]) + [
        "-t", f"{times[-1] - times[0] + max(1, 2 / info.fps):.9f}",
        "-vf", f"{media._NORMALIZE},select='gte(t,selected_n*{step:.9f}-0.000001)'",
        "-frames:v", str(len(times)), "-fps_mode", "passthrough",
        "-pix_fmt", "bgr24", "-threads", "1", "-f", "rawvideo", "pipe:1",
    ]
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, creationflags=media._creationflags())
    except OSError as exc:
        raise VisionError(f"Could not start local frame decoder: {exc}") from exc
    frames: queue.Queue = queue.Queue(maxsize=2)
    errors: deque[str] = deque(maxlen=20)
    stopping = threading.Event()
    size = info.width * info.height * 3

    def put(item) -> None:
        while not stopping.is_set():
            try:
                frames.put(item, timeout=0.1)
                return
            except queue.Full:
                pass

    def read() -> None:
        try:
            for _ in times:
                data = bytearray()
                while len(data) < size and not stopping.is_set():
                    block = process.stdout.read(size - len(data))
                    if not block:
                        break
                    data.extend(block)
                if len(data) != size:
                    put(VisionError("Local decoder returned a truncated frame."))
                    return
                put(np.frombuffer(data, np.uint8).reshape(info.height, info.width, 3))
        except Exception as exc:
            put(VisionError(f"Local decoder failed: {exc}"))
        finally:
            process.stdout.close()

    readers = [
        threading.Thread(target=read, daemon=True),
        threading.Thread(target=media._stderr_reader, args=(process.stderr, errors), daemon=True),
    ]
    for worker in readers:
        worker.start()
    try:
        for at in times:
            _check_cancel(cancel)
            waited = 0.0
            while True:
                _check_cancel(cancel)
                try:
                    frame = frames.get(timeout=0.25)
                    break
                except queue.Empty:
                    waited += 0.25
                    if waited >= 45:
                        raise VisionError("Local decoder stalled; sampled coverage is incomplete.")
            if isinstance(frame, Exception):
                raise VisionError(f"{frame} {' '.join(errors)}")
            yield at, frame
        try:
            code = process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise VisionError("Local decoder did not exit after producing the requested frames.") from exc
        if code:
            raise VisionError(f"Local decoder failed: {' '.join(errors)}")
    finally:
        stopping.set()
        media._stop(process)
        for worker in readers:
            worker.join(timeout=3)


def _frames(source: Path, times: list[float], info: MediaInfo,
            cancel: threading.Event | None) -> Iterator[tuple[float, np.ndarray]]:
    index = 0
    while index < len(times):
        _check_cancel(cancel)
        stop = index + 1
        if stop < len(times):
            step = times[stop] - times[index]
            if 1 / info.fps <= step <= 5:
                while (stop < len(times) and stop - index < 64
                       and times[stop] - times[index] <= 120
                       and abs(times[stop] - times[stop - 1] - step) < 1e-7):
                    stop += 1
        if stop - index >= 3:
            yield from _stream_frames(source, times[index:stop], info, cancel)
        else:
            stop = index + 1
            yield times[index], _frame(source, times[index], info)
        index = stop


def _write_report(directory: Path, report: dict) -> None:
    partial = directory / f"report-{uuid4().hex}.part"
    try:
        partial.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")),
                           encoding="utf-8")
        partial.replace(directory / "report.json")
    except OSError as exc:
        raise VisionError(f"Could not persist visual coverage report: {exc}") from exc
    finally:
        partial.unlink(missing_ok=True)


class _ContactSheets:
    def __init__(self, directory: Path):
        self.directory = directory
        self.tiles: list[np.ndarray] = []
        self.paths: list[str] = []
        self.page = 0

    def add(self, image: np.ndarray, sample: dict) -> None:
        tile = np.zeros((204, 320, 3), np.uint8)
        h, w = image.shape[:2]
        scale = min(320 / w, 180 / h)
        thumb = cv2.resize(image, (max(1, round(w * scale)), max(1, round(h * scale))))
        tile[:thumb.shape[0], :thumb.shape[1]] = thumb
        label = f"{sample['time']:.3f}s"
        if sample["brb"]:
            label += " BRB"
        if sample["accepted"]:
            label += " Accepted?"
        if sample["runtime_ms"] is not None:
            label += f" {sample['runtime_ms']:g}ms?"
        cv2.putText(tile, label, (5, 197), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        sample["contact_sheet"] = str((self.directory / f"contact-{self.page:03}.jpg").resolve())
        sample["contact_cell"] = len(self.tiles)
        self.tiles.append(tile)
        if len(self.tiles) == 24:
            self.flush()

    def flush(self) -> None:
        if not self.tiles:
            return
        count = len(self.tiles)
        self.tiles.extend(np.zeros_like(self.tiles[0]) for _ in range((-count) % 4))
        sheet = np.vstack([np.hstack(self.tiles[i:i + 4]) for i in range(0, len(self.tiles), 4)])
        self.paths.append(_save_image(self.directory / f"contact-{self.page:03}.jpg", sheet))
        self.tiles.clear()
        self.page += 1


def scan_intervals(
    source: Path, intervals: list[tuple[float, float]], output_dir: Path, step: float = 1.0,
    progress: Callable[[float, str], None] | None = None,
    cancel: threading.Event | None = None,
) -> dict:
    """Sample endpoints and regular steps, saving contact sheets and hit frames.

    Short regular runs stream through FFmpeg; sparse scans seek rather than decode
    hours between samples. RAM is bounded to a few frames plus one contact page.
    A failure/cancellation persists an incomplete report and raises ``VisionError``.
    ``coverage.requested_samples_complete`` only describes the sampling plan, never
    all frames. Even a successful scan has ``certified_clean=False``.
    """
    _check_cancel(cancel)
    source, info = _source_info(source)
    requested_intervals = intervals
    intervals = _intervals(intervals, info.duration)
    times = _sample_times(requested_intervals, step, info)
    anchors = {round(start, 9) for start, _ in requested_intervals}
    directory = _output_dir(output_dir)
    report = {
        "source": str(source), "duration": info.duration, "step": step,
        "samples": [], "brb_ranges": [], "contact_sheets": [],
        "coverage": {
            "status": "running", "intervals": intervals, "requested_intervals": requested_intervals,
            "requested_samples": len(times),
            "completed_samples": 0, "requested_samples_complete": False,
            "continuous_coverage": False, "certified_clean": False,
            "timestamp_kind": "requested_seek_seconds", "frame_period": 1 / info.fps,
            "max_planned_sample_gap_seconds": min(step, max(end - start for start, end in intervals)),
        },
        "warnings": [_DISCLAIMER, "Only interval starts, OCR hits and large visual changes retain full-resolution frames."],
    }
    _write_report(directory, report)
    sheets = _ContactSheets(directory)
    previous = None
    previous_time = None
    iterator = None
    try:
        reader = ScreenReader()
        iterator = _frames(source, times, info, cancel)
        for index, (at, image) in enumerate(iterator):
            _check_cancel(cancel)
            result = reader.inspect(image)
            if at in anchors or (previous_time is not None and at - previous_time > step + 1e-7):
                previous = None
            small = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (96, 54))
            change = (float(np.abs(small.astype(np.float32) - previous).mean() / 255)
                      if previous is not None else None)
            previous = small.astype(np.float32)
            previous_time = at
            keep = result["brb"] or result["accepted"] or result["runtime_ms"] is not None
            keep = keep or change is None or change >= 0.25
            path = _save_image(directory / _image_name(at), image) if keep else None
            sample = {**result, "time": at, "image": path, "scene_change_score": change}
            report["samples"].append(sample)
            report["coverage"]["completed_samples"] = index + 1
            sheets.add(image, sample)
            if progress:
                progress((index + 1) / len(times), f"OCR sampled {at:.3f}s ({index + 1}/{len(times)})")
            if (index + 1) % 24 == 0:
                report["brb_ranges"] = _brb_ranges(report["samples"], step, info.duration)
                report["contact_sheets"] = sheets.paths
                _write_report(directory, report)
        if len(report["samples"]) != len(times):
            raise VisionError("Decoder stopped before all planned samples were inspected.")
        _check_cancel(cancel)
        sheets.flush()
        report["coverage"].update(status="completed", requested_samples_complete=True)
    except Exception as exc:
        report["coverage"]["status"] = "cancelled" if cancel is not None and cancel.is_set() else "failed"
        report["warnings"].append(f"Incomplete visual evidence: {exc}")
        try:
            sheets.flush()
        except VisionError as save_exc:
            report["warnings"].append(str(save_exc))
        raise VisionError(f"Visual scan incomplete: {exc}") from exc
    finally:
        if iterator is not None and hasattr(iterator, "close"):
            iterator.close()
        report["brb_ranges"] = _brb_ranges(report["samples"], step, info.duration)
        report["contact_sheets"] = sheets.paths
        _write_report(directory, report)
    return report
