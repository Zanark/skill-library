"""Ordered, frame-aligned reels with one final AAC encode and traceable source spans."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import threading
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from uuid import uuid4

from pydantic import Field, model_validator

from . import media
from .models import Clip, Cue, MediaInfo, Model
from .music_models import StylizedEdit


class MontageSpan(Model):
    index: int = Field(ge=0)
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    output_start: float = Field(ge=0)
    output_end: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> MontageSpan:
        if self.source_end <= self.source_start or self.output_end <= self.output_start:
            raise ValueError("Montage spans must have positive source and output durations.")
        return self


@dataclass
class _Timing:
    frames: int = 0
    video_start: Fraction | None = None
    video_end: Fraction = Fraction(0)
    audio_start: Fraction | None = None
    audio_end: Fraction = Fraction(0)
    audio_duration: Fraction = Fraction(0)
    video_deviation: Fraction = Fraction(0)


def _frame_plan(info: MediaInfo, segments: list[Clip]) -> list[int]:
    if not segments:
        raise media.MediaError("A montage needs at least one segment.")
    durations = [media._duration(info, clip) for clip in segments]
    if math.fsum(durations) > 180 + 1e-7:
        raise media.MediaError("The complete montage must not exceed 180 seconds.")
    frames = [math.floor(duration * 30 + 1e-7) for duration in durations]
    if any(count < 1 for count in frames):
        raise media.MediaError("Every montage segment must contain at least one 30 fps output frame.")
    return frames


def _results_events(
    segments: list[Clip], frames: list[int], *, split_on_roi: bool = True,
) -> dict[int, int]:
    """Map results event starts to retained frames; dim events ignore ROI changes."""
    events: dict[int, int] = {}
    previous: Clip | None = None
    start = 0
    for index, (clip, count) in enumerate(zip(segments, frames)):
        if clip.layout != "leetcode" or not clip.results_zoom:
            previous = None
            continue
        if (previous is None or (split_on_roi and (
                clip.face_region != previous.face_region or clip.content_region != previous.content_region))):
            start = index
            events[start] = 0
        events[start] += count
        previous = clip
    return events


def _read_packet_timing(path: Path) -> _Timing:
    result = _Timing()
    bases: dict[int, Fraction] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            timebase = re.match(r"#tb\s+(\d+):\s*(\d+)/(\d+)", line)
            if timebase:
                bases[int(timebase[1])] = Fraction(int(timebase[2]), int(timebase[3]))
            elif line.strip() and not line.startswith("#"):
                columns = [column.strip() for column in line.split(",")]
                try:
                    index, pts, duration = int(columns[0]), int(columns[2]), int(columns[3])
                    begin = pts * bases[index]
                    finish = begin + duration * bases[index]
                except (ValueError, IndexError, KeyError) as exc:
                    raise media.MediaError("FFmpeg returned invalid stream timing data.") from exc
                if index == 0:
                    if result.video_start is None:
                        result.video_start = begin
                    expected = result.video_start + Fraction(result.frames, 30)
                    result.video_deviation = max(result.video_deviation, abs(begin - expected))
                    result.frames += 1
                    result.video_end = max(result.video_end, finish)
                elif index == 1:
                    if result.audio_start is None:
                        result.audio_start = begin
                    result.audio_end = max(result.audio_end, finish)
                    result.audio_duration += duration * bases[index]
    if result.frames == 0:
        raise media.MediaError("The montage segment contains no encoded video frames.")
    return result


def _measure(path: Path, duration: float, cancel: threading.Event) -> _Timing:
    metadata = path.with_suffix(".framecrc")
    try:
        command = (
            media._base() + ["-loglevel", "error", "-xerror", "-y"] + media._PROTOCOLS
            + ["-i", path.name, "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy",
               "-progress", "pipe:1", "-nostats", "-f", "framecrc", metadata.name]
        )
        media._run(command, path.parent, duration, lambda *_: None, cancel)
        return _read_packet_timing(metadata)
    finally:
        metadata.unlink(missing_ok=True)


def _verify_timing(timing: _Timing, frames: int, has_audio: bool, *, pcm: bool) -> None:
    duration = Fraction(frames, 30)
    if (
        timing.frames != frames or timing.video_start != 0
        or abs(timing.video_end - duration) > Fraction(1, 15360)
        or timing.video_deviation > Fraction(1, 15360)
    ):
        raise media.MediaError("Montage video timing verification failed; no output was published.")
    if has_audio:
        if timing.audio_start is None or abs(timing.audio_end - duration) > Fraction(1, 30):
            raise media.MediaError("Montage audio/video alignment verification failed.")
        if pcm and (
            timing.audio_start != 0 or timing.audio_duration != duration
            or timing.audio_end != duration
        ):
            raise media.MediaError("Intermediate PCM audio does not match its exact video duration.")
    elif timing.audio_start is not None:
        raise media.MediaError("An unexpected audio stream appeared in a silent-source montage.")


def _render_part(
    source: Path, info: MediaInfo, clip: Clip, cues: list[Cue], path: Path, frames: int,
    preview: bool, progress: media.Progress, cancel: threading.Event,
    *, results_elapsed: float = 0, results_duration: float | None = None,
    results_dim_elapsed: float | None = None, results_dim_duration: float | None = None,
    fade_in_frames: int = 0, fade_out_frames: int = 0,
) -> tuple[_Timing, list[Cue]]:
    duration = frames / 30
    layout, face, track, _ = media._prepare_layout(
        source, info, clip, lambda fraction, message: progress(fraction * 0.1, message), cancel,
    )
    local_cues = media._clip_cues(cues, clip, duration)
    caption_path = path.with_suffix(".ass")
    track_path = path.with_suffix(".commands")
    graph_path = path.with_suffix(".graph")
    ass_name = None
    if (clip.captions and local_cues) or clip.question_title is not None or clip.correction is not None:
        caption_path.write_text(media._ass(local_cues if clip.captions else [], clip), encoding="utf-8")
        ass_name = caption_path.name
    if layout == "follow":
        crop_width, crop_height = media._crop_size(info, track)
        track_path.write_text(media._track_commands(track, info, crop_width, crop_height), encoding="utf-8")
    width, height = (360, 640) if preview else (1080, 1920)
    transition = ({"fade_in_frames": fade_in_frames, "fade_out_frames": fade_out_frames,
                   "retained_frames": frames} if fade_in_frames or fade_out_frames else {})
    graph = media._filter_graph(info, clip, layout, width, height, face, track,
                                ass_name, track_path.name if layout == "follow" else None,
                                results_elapsed=results_elapsed, results_duration=results_duration,
                                results_dim_elapsed=results_dim_elapsed, results_dim_duration=results_dim_duration,
                                **transition)
    graph += (
        f";\n[outv]tpad=stop_mode=clone:stop_duration=1,trim=end_frame={frames},"
        "setpts=N/(30*TB)[video]"
    )
    if info.has_audio:
        # 48,000 / 30 = 1,600 samples per frame. PCM avoids per-part AAC priming.
        graph += (
            f";\n[0:a:0]aresample=48000:first_pts=0,aformat=sample_fmts=s16:channel_layouts=stereo,"
            f"apad=whole_len={frames * 1600},atrim=end_sample={frames * 1600},asetpts=N/SR/TB[audio]"
        )
    graph_path.write_text(graph, encoding="utf-8")
    command = (
        media._base() + ["-loglevel", "error", "-xerror", "-y", "-threads", "2",
                         "-ss", f"{clip.start:.9f}", "-t", f"{duration:.12f}"]
        + media._PROTOCOLS + ["-i", str(source), "-filter_complex_threads", "2",
                             "-filter_complex_script", graph_path.name, "-map", "[video]"]
    )
    if info.has_audio:
        command += ["-map", "[audio]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
    command += [
        "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1",
        "-c:v", "libx264", "-preset", "veryfast" if preview else "fast",
        "-crf", "25" if preview else "20", "-threads", "2", "-bf", "0",
        "-pix_fmt", "yuv420p", "-r", "30", "-video_track_timescale", "15360",
        "-metadata:s:v:0", "rotate=0", "-progress", "pipe:1", "-nostats", path.name,
    ]
    media._run(command, path.parent, duration, progress, cancel, start=0.1, span=0.85)
    timing = _measure(path, duration, cancel)
    _verify_timing(timing, frames, info.has_audio, pcm=True)
    progress(1, "Segment timing verified")
    return timing, local_cues


def _publish(staged: list[tuple[Path, Path]], cancel: threading.Event) -> None:
    """Sidecars first, atomic MP4 replacement last; roll sidecars back on failure."""
    backups: list[tuple[Path, Path | None]] = []
    complete = False
    try:
        for index, (source, destination) in enumerate(staged):
            media._check_cancel(cancel)
            backup = None
            if index < len(staged) - 1 and destination.exists():
                backup = source.parent / f"backup_{index}"
                os.replace(destination, backup)
            if index < len(staged) - 1:
                backups.append((destination, backup))
            os.replace(source, destination)
        complete = True
    finally:
        if not complete:
            for destination, backup in reversed(backups):
                destination.unlink(missing_ok=True)
                if backup is not None:
                    os.replace(backup, destination)


def _append_mapped_cues(
    output: list[Cue], local: list[Cue], span: MontageSpan, previous_source_end: float | None,
) -> float | None:
    for cue in local:
        if cue.end <= cue.start:
            continue
        mapped = Cue(id=cue.id, start=cue.start + span.output_start,
                     end=min(cue.end + span.output_start, span.output_end), text=cue.text)
        source_start = span.source_start + cue.start
        if (output and output[-1].id == mapped.id and output[-1].text == mapped.text
                and abs(output[-1].end - mapped.start) < 1e-6
                and previous_source_end is not None and source_start >= previous_source_end - 1e-6):
            # A crop change or removed pause can split one caption, not repeat speech.
            output[-1].end = mapped.end
        else:
            output.append(mapped)
        previous_source_end = span.source_start + cue.end
    return previous_source_end


def render_montage(
    source: Path, info: MediaInfo, segments: list[Clip], cues: list[Cue], output: Path,
    preview: bool, progress: media.Progress, cancel: threading.Event,
    *, stylized: StylizedEdit | None = None, transitions: dict[int, tuple[int, int]] | None = None,
) -> list[MontageSpan]:
    """Keep edit order; trim each end down by <1/30 s, then verify actual packet timing."""
    media._check_cancel(cancel)
    frames = _frame_plan(info, segments)
    if transitions and stylized is None:
        raise media.MediaError("Transitions require an explicit stylized opt-in.")
    source = media._source(source)
    output = Path(output).resolve()
    if output == source or output.suffix.lower() != ".mp4":
        raise media.MediaError("Choose a separate .mp4 montage output; the source cannot be overwritten.")
    x264, ass = media._capabilities(media.ffmpeg_exe())
    needs_ass = any(clip.question_title is not None or clip.correction is not None
                    or (cues and clip.captions) for clip in segments)
    if not x264 or (needs_ass and not ass):
        raise media.MediaError("Montages need libx264 and captioned montages need libass.")
    media._make_parent(output)
    work = output.parent / f".montage_{uuid4().hex}"
    spans: list[MontageSpan] = []
    remapped: list[Cue] = []
    previous_caption_source_end = None
    total_frames, done_frames = sum(frames), 0
    results_events = _results_events(segments, frames)
    results_dim_events = _results_events(segments, frames, split_on_roi=False)
    results_start_frame, results_duration = 0, None
    results_dim_start_frame, results_dim_duration = 0, None
    try:
        work.mkdir()
        music_path = None
        music_binding = None
        if stylized is not None:
            from .music import inputs as music_inputs, stage_track

            music_binding = music_inputs(stylized)
            music_path = stage_track(stylized, work, total_frames / 30, cancel)
        concat = ["ffconcat version 1.0"]
        for index, (clip, count) in enumerate(zip(segments, frames)):
            media._check_cancel(cancel)
            if index in results_events:
                results_start_frame = done_frames
                results_duration = results_events[index] / 30
            elif clip.layout != "leetcode" or not clip.results_zoom:
                results_duration = None
            if index in results_dim_events:
                results_dim_start_frame = done_frames
                results_dim_duration = results_dim_events[index] / 30
            elif clip.layout != "leetcode" or not clip.results_zoom:
                results_dim_duration = None
            part = work / f"part_{index:05}.mov"
            trimmed = clip.model_copy(update={"end": clip.start + count / 30})
            fade_in, fade_out = (transitions or {}).get(index, (0, 0))
            transition = ({"fade_in_frames": fade_in, "fade_out_frames": fade_out}
                          if fade_in or fade_out else {})
            timing, local_cues = _render_part(
                source, info, trimmed, cues, part, count, preview,
                lambda fraction, message: progress(
                    0.90 * (done_frames + count * fraction) / total_frames,
                    f"Segment {index + 1}/{len(segments)}: {message}",
                ),
                cancel,
                results_elapsed=(done_frames - results_start_frame) / 30 if results_duration else 0,
                results_duration=results_duration,
                results_dim_elapsed=(done_frames - results_dim_start_frame) / 30 if results_dim_duration else 0,
                results_dim_duration=results_dim_duration,
                **transition,
            )
            actual = float(timing.video_end)
            begin, end = done_frames / 30, (done_frames + timing.frames) / 30
            span = MontageSpan(index=index, source_start=clip.start, source_end=clip.start + actual,
                               output_start=begin, output_end=end)
            spans.append(span)
            previous_caption_source_end = _append_mapped_cues(
                remapped, local_cues, span, previous_caption_source_end,
            )
            concat += [f"file {part.name}", f"duration {actual:.12f}"]
            done_frames += timing.frames
            for extension in (".ass", ".commands", ".graph"):
                part.with_suffix(extension).unlink(missing_ok=True)
        concat_path = work / "parts.ffconcat"
        concat_path.write_text("\n".join(concat) + "\n", encoding="ascii")
        final = work / "result.mp4"
        command = (
            media._base() + ["-loglevel", "error", "-xerror", "-y"] + media._PROTOCOLS
            + ["-f", "concat", "-safe", "1", "-i", concat_path.name,
               "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "128k" if preview else "192k", "-ar", "48000",
               "-af", f"atrim=end_sample={total_frames * 1600},asetpts=N/SR/TB",
               "-map_metadata", "-1", "-map_chapters", "-1", "-video_track_timescale", "15360",
               "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", final.name]
        )
        duration = total_frames / 30
        if music_path is not None:
            from .music import audio_graph

            graph = work / "music.graph"
            graph.write_text(audio_graph(stylized, duration, info.has_audio), encoding="utf-8")
            command = (
                media._base() + ["-loglevel", "error", "-xerror", "-y"] + media._PROTOCOLS
                + ["-f", "concat", "-safe", "1", "-i", concat_path.name]
                + media._PROTOCOLS + ["-i", str(music_path), "-filter_complex_threads", "2",
                                     "-filter_complex_script", graph.name,
                                     "-map", "0:v:0", "-map", "[music_mix]", "-c:v", "copy",
                                     "-c:a", "aac", "-b:a", "128k" if preview else "192k",
                                     "-ar", "48000", "-map_metadata", "-1", "-map_chapters", "-1",
                                     "-video_track_timescale", "15360", "-movflags", "+faststart",
                                     "-progress", "pipe:1", "-nostats", final.name]
            )
        media._run(command, work, duration, progress, cancel, start=0.90, span=0.08)
        _verify_timing(_measure(final, duration, cancel), total_frames,
                       info.has_audio or music_path is not None, pcm=False)
        verified = media.probe(final)
        width, height = (360, 640) if preview else (1080, 1920)
        if (verified.width, verified.height, verified.fps, verified.video_codec) != (width, height, 30, "h264"):
            raise media.MediaError("The final montage failed its video format verification.")
        srt = work / "result.srt"
        source_map = work / "result.source-map.json"
        transcript = work / "result.transcript.txt"
        srt.write_text(media._srt(remapped), encoding="utf-8")
        source_map.write_text(json.dumps({
            "version": 1, "fps": 30, "duration": duration,
            "segments": [span.model_dump() for span in spans],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        transcript.write_text(
            "\n\n".join(
                f"[{media._srt_time(cue.start)} --> {media._srt_time(cue.end)}]\n{cue.text}"
                for cue in remapped
            ) + ("\n" if remapped else "No transcript cues intersect the selected segments.\n"),
            encoding="utf-8",
        )
        media._check_cancel(cancel)
        if stylized is not None and music_inputs(stylized) != music_binding:
            raise media.MediaError("Music settings or evidence changed during rendering; no montage was published.")
        _publish([
            (srt, output.with_suffix(".srt")),
            (source_map, output.with_suffix(".source-map.json")),
            (transcript, output.with_suffix(".transcript.txt")),
            (final, output),
        ], cancel)
        progress(1, "Montage and source map ready")
        return spans
    except OSError as exc:
        raise media.MediaError(f"Could not write the montage: {exc}") from exc
    finally:
        if work.exists():
            shutil.rmtree(work)


def detect_silences(
    source: Path, start: float, end: float, cancel: threading.Event,
    threshold_db: float = -35, min_duration: float = 0.4,
) -> list[tuple[float, float]]:
    """Return absolute-source silence intervals; errors are never treated as silence."""
    media._check_cancel(cancel)
    if (
        not all(math.isfinite(value) for value in (start, end, threshold_db, min_duration))
        or start < 0 or end <= start or min_duration <= 0 or not -120 <= threshold_db <= 0
    ):
        raise media.MediaError("Use a finite positive time range, positive minimum silence, and -120..0 dB threshold.")
    source = media._source(source)
    info = media.probe(source)
    media._check_cancel(cancel)
    if start >= info.duration or end > info.duration + 0.1:
        raise media.MediaError("The silence-detection range extends beyond the source.")
    if not info.has_audio:
        logging.getLogger(__name__).warning("Source has no audio; silence detection was explicitly skipped.")
        return []
    duration = min(end, info.duration) - start
    diagnostics: list[str] = []
    command = (
        media._base() + ["-loglevel", "info", "-xerror", "-threads", "2",
                         "-ss", f"{start:.9f}", "-t", f"{duration:.9f}"]
        + media._PROTOCOLS + ["-i", str(source), "-map", "0:a:0", "-vn", "-sn", "-dn",
                             "-af", f"aresample=48000:first_pts=0,silencedetect=noise={threshold_db:.6f}dB:d={min_duration:.9f}",
                             "-progress", "pipe:1", "-nostats", "-f", "null", "-"]
    )
    media._run(command, source.parent, duration, lambda *_: None, cancel, stderr_capture=diagnostics)
    intervals: list[tuple[float, float]] = []
    pending: float | None = None
    for line in diagnostics:
        for kind, value in re.findall(r"silence_(start|end):\s*([+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", line):
            timestamp = media._clamp(float(value), 0, duration)
            if kind == "start":
                pending = timestamp
            elif pending is not None:
                if timestamp > pending:
                    intervals.append((start + pending, start + timestamp))
                pending = None
    if pending is not None and duration > pending:
        intervals.append((start + pending, start + duration))
    return intervals
