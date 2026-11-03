"""Native-landscape edits with an explicitly synthetic cover and exact source spans."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFont

from . import media, montage, thumbnails
from .horizontal_models import HorizontalRenderSegment, SubtitleRegion
from .models import Cue, MediaInfo

INTRO_FADE_SECONDS = 4.0
_FPS = 30
_PART_FRAMES = 60 * _FPS


def _frame_plan(
    info: MediaInfo, segments: list[HorizontalRenderSegment], intro_hold: float,
) -> tuple[list[int], int]:
    if info.width <= info.height or info.width % 2 or info.height % 2:
        raise media.MediaError("Horizontal video needs even, normalized native landscape dimensions.")
    if not segments:
        raise media.MediaError("A horizontal solve needs at least one segment.")
    if (not math.isfinite(intro_hold) or not 0 <= intro_hold <= 10
            or abs(intro_hold * _FPS - round(intro_hold * _FPS)) > 1e-7):
        raise media.MediaError("Intro hold must be 0–10 seconds on the 30 fps frame grid.")
    frames = []
    previous_end = 0.0
    for segment in segments:
        if segment.start < previous_end - 1e-9:
            raise media.MediaError("Horizontal segments must be chronological and nonoverlapping.")
        if segment.start >= info.duration or segment.end > info.duration + 1e-7:
            raise media.MediaError("The horizontal segment extends beyond the source video.")
        count = math.floor((min(segment.end, info.duration) - segment.start) * _FPS + 1e-7)
        if count < 1:
            raise media.MediaError("Every horizontal segment must contain at least one 30 fps frame.")
        frames.append(count)
        previous_end = segment.end
    if sum(frames) < round(INTRO_FADE_SECONDS * _FPS):
        raise media.MediaError("The retained body must contain at least 4 seconds for the cover fade.")
    return frames, round(intro_hold * _FPS)


def _same_path(a: Path, b: Path) -> bool:
    return a == b or (a.exists() and b.exists() and a.samefile(b))


def _cover(path: Path, info: MediaInfo) -> None:
    try:
        with Image.open(path) as image:
            if (image.format != "JPEG" or image.size != (info.width, info.height)
                    or image.getexif().get(274, 1) != 1):
                raise media.MediaError(
                    "The cover must be a nonrotated JPEG matching the normalized native video dimensions."
                )
            image.load()
    except (OSError, ValueError) as exc:
        raise media.MediaError(f"Could not read the cover JPEG: {exc}") from exc


@dataclass(frozen=True)
class _CaptionLayout:
    font: ImageFont.FreeTypeFont
    lines: tuple[str, ...]
    x: int
    y: int
    line_height: int
    padding: int
    rectangle: tuple[int, int, int, int]


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> tuple[str, ...]:
    """Wrap complete literal text, including oversized identifiers, without clipping."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if thumbnails._width(candidate, font) <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ""
        for character in word:
            if thumbnails._width(line + character, font) > width:
                if not line:
                    raise media.MediaError("A subtitle character cannot fit the selected empty rectangle.")
                lines.append(line)
                line = ""
            line += character
    if line:
        lines.append(line)
    return tuple(lines)


def _caption_layout(info: MediaInfo, region: SubtitleRegion, text: str) -> _CaptionLayout:
    left, top = math.ceil(region.x * info.width), math.ceil(region.y * info.height)
    right = min(info.width, math.floor((region.x + region.w) * info.width))
    bottom = min(info.height, math.floor((region.y + region.h) * info.height))
    base = thumbnails._font()
    preferred = max(10, round(info.height * 0.04))
    minimum = max(9, math.ceil(info.height / 36))
    for size in range(preferred, minimum - 1, -1):
        font = base.font_variant(size=size)
        padding = max(2, math.ceil(size * 0.22))
        # Leave explicit bearing/shaping headroom rather than clipping ASS to fit.
        width = math.floor((right - left - 2 * padding) / 1.1)
        if width < 1:
            continue
        lines = _wrap(text, font, width)
        line_height = math.ceil(size * 1.5)
        if lines and len(lines) * line_height + 2 * padding <= bottom - top:
            y = top + padding + (bottom - top - 2 * padding - len(lines) * line_height) // 2
            return _CaptionLayout(
                font, lines, (left + right) // 2, y, line_height, padding, (left, top, right, bottom),
            )
    raise media.MediaError(
        "Subtitle text cannot fit the selected empty rectangle at a readable size; "
        "choose more verified empty space. No text was clipped or omitted."
    )


def _source_bursts(cues: list[Cue]) -> list[Cue]:
    result = []
    for cue in sorted(cues, key=lambda value: (value.start, value.end)):
        canonical = " ".join(cue.text.split())
        positions = [index for index, char in enumerate(canonical) if not char.isspace()]
        cursor, previous_end = 0, None
        for index, (start, end, display) in enumerate(media._caption_bursts(cue, width=24)):
            characters = "".join(display.split())
            if not characters:
                continue
            begin = positions[cursor]
            cursor += len(characters)
            finish = positions[cursor - 1] + 1
            text = canonical[begin:finish]
            # The shared burst helper inserts both word and mid-identifier line
            # breaks. Recover actual source boundaries, not its display newlines.
            if previous_end == begin:
                result[-1].text += text
                result[-1].end = end
            else:
                result.append(Cue(id=f"{cue.id}:{index}", start=start, end=end, text=text))
            previous_end = finish
    return result


def _local_cues(
    bursts: list[Cue], start: float, duration: float, info: MediaInfo,
    segment: HorizontalRenderSegment,
) -> list[Cue]:
    local = []
    for burst in bursts:
        begin, end = max(0, burst.start - start), min(duration, burst.end - start)
        if end <= begin:
            continue
        if segment.captions:
            _caption_layout(info, segment.subtitle_region, burst.text)
            if local and begin < local[-1].end - 1e-7:
                raise media.MediaError("Overlapping source captions need editorial correction before rendering.")
        local.append(Cue(id=burst.id, start=begin, end=end, text=burst.text))
    return local


def _ass(cues: list[Cue], info: MediaInfo, region: SubtitleRegion) -> str:
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {info.width}\nPlayResY: {info.height}\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n"
        "; Source-time proportional bursts, not word-accurate alignment.\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    styles, events = [], []
    for index, cue in enumerate(cues):
        layout = _caption_layout(info, region, cue.text)
        family = layout.font.getname()[0]
        styles.append(
            f"Style: C{index},{family},{layout.font.size},&H00FFFFFF,&H00FFFFFF,"
            f"&H20181818,&H20181818,-1,0,0,0,100,100,0,0,3,{layout.padding},0,8,0,0,0,1"
        )
        start, end = media._ass_time(cue.start), media._ass_time(cue.end)
        if start == end:
            end = media._ass_time(cue.start + 0.01)
        for line_index, line in enumerate(layout.lines):
            y = layout.y + line_index * layout.line_height
            events.append(
                f"Dialogue: 0,{start},{end},C{index},,0,0,0,,"
                + rf"{{\an8\q2\pos({layout.x},{y})}}" + media._ass_escape(line)
            )
    return (
        header + "\n".join(styles)
        + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events) + "\n"
    )


def _video_options() -> list[str]:
    # JPEG cover frames and source footage must agree on range at every concat join.
    return [
        "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-threads", "2", "-bf", "0",
        "-pix_fmt", "yuv420p", "-color_range", "tv", "-r", str(_FPS), "-video_track_timescale", "15360",
        "-metadata:s:v:0", "rotate=0", "-progress", "pipe:1", "-nostats",
    ]


def _render_part(
    source: Path, info: MediaInfo, segment: HorizontalRenderSegment | None, cues: list[Cue],
    path: Path, frames: int, cover: Path, body_frame: int,
    progress: media.Progress, cancel: threading.Event,
) -> montage._Timing:
    duration = frames / _FPS
    command = media._base() + ["-loglevel", "error", "-xerror", "-y", "-threads", "2"]
    if segment is None:
        command += ["-loop", "1", "-framerate", str(_FPS)] + media._PROTOCOLS + ["-i", cover.name]
        graph = (
            f"[0:v:0]scale=in_range=auto:out_range=tv,setsar=1,"
            f"trim=end_frame={frames},setpts=N/({_FPS}*TB)[picture]"
        )
    else:
        command += ["-ss", f"{segment.start:.9f}", "-t", f"{duration:.12f}"]
        command += media._PROTOCOLS + ["-i", str(source)]
        graph = (
            f"[0:v:0]{media._NORMALIZE},scale=in_range=auto:out_range=tv,fps={_FPS},"
            f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={frames},setpts=N/({_FPS}*TB)[native]"
        )
        if body_frame < round(INTRO_FADE_SECONDS * _FPS):
            command += ["-loop", "1", "-framerate", str(_FPS)] + media._PROTOCOLS + ["-i", cover.name]
            # Fade on the continuous body timeline, then trim to this part. A cut
            # inside the first four seconds must not restart the cover's opacity.
            graph += (
                f";[1:v:0]scale=in_range=auto:out_range=tv,format=yuva420p,setsar=1,"
                f"fade=t=out:st=0:d={INTRO_FADE_SECONDS}:alpha=1,"
                f"trim=start_frame={body_frame}:end_frame={body_frame + frames},"
                f"setpts=N/({_FPS}*TB)[cover];[native][cover]overlay=shortest=1:format=yuv420[picture]"
            )
        else:
            graph += ";[native]null[picture]"
    if segment is not None and segment.captions and cues:
        ass_path = path.with_suffix(".ass")
        ass_path.write_text(_ass(cues, info, segment.subtitle_region), encoding="utf-8")
        graph += f";[picture]ass=filename={ass_path.name}[video]"
    else:
        graph += ";[picture]null[video]"
    if info.has_audio:
        audio = (
            "anullsrc=r=48000:cl=stereo," if segment is None else
            "[0:a:0]aresample=48000:first_pts=0,aformat=sample_fmts=s16:channel_layouts=stereo,"
        )
        graph += (
            f";{audio}apad=whole_len={frames * 1600},atrim=end_sample={frames * 1600},"
            "asetpts=N/SR/TB[audio]"
        )
    graph_path = path.with_suffix(".graph")
    graph_path.write_text(graph, encoding="utf-8")
    command += ["-filter_complex_threads", "2", "-filter_complex_script", graph_path.name, "-map", "[video]"]
    if info.has_audio:
        command += ["-map", "[audio]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
    command += _video_options() + [path.name]
    media._run(command, path.parent, duration, progress, cancel, span=0.95)
    timing = montage._measure(path, duration, cancel)
    montage._verify_timing(timing, frames, info.has_audio, pcm=True)
    progress(1, "Native horizontal part timing verified")
    for extension in (".ass", ".graph"):
        path.with_suffix(extension).unlink(missing_ok=True)
    return timing


def render_horizontal(
    source: Path, info: MediaInfo, segments: list[HorizontalRenderSegment], cues: list[Cue],
    output: Path, thumbnail: Path, progress: media.Progress, cancel: threading.Event,
    *, intro_hold: float = 1.0,
) -> list[montage.MontageSpan]:
    """Preserve full normalized framing; the four-second fade overlaps real footage."""
    media._check_cancel(cancel)
    frames, hold_frames = _frame_plan(info, segments, intro_hold)
    source = media._source(source)
    output = Path(output).expanduser().resolve()
    if str(thumbnail).startswith(("\\\\", "//")):
        raise media.MediaError("Choose a local cover JPEG, not a network share.")
    thumbnail = Path(thumbnail).expanduser().resolve()
    destinations = [
        output.with_suffix(".srt"), output.with_suffix(".source-map.json"),
        output.with_suffix(".transcript.txt"), output,
    ]
    if (output.suffix.lower() != ".mp4" or _same_path(source, thumbnail)
            or any(_same_path(path, original) for path in destinations for original in (source, thumbnail))
            or any(path.is_dir() for path in destinations)):
        raise media.MediaError("Choose separate .mp4/sidecar paths; source media and cover cannot be overwritten.")
    _cover(thumbnail, info)
    x264, ass = media._capabilities(media.ffmpeg_exe())
    if not x264 or (cues and any(segment.captions for segment in segments) and not ass):
        raise media.MediaError("Horizontal renders need libx264; burnt captions also need libass.")
    bursts = _source_bursts(cues)
    # Fail before encoding if a retained subtitle cannot fit its verified space.
    prepared = []
    for segment, count in zip(segments, frames):
        media._check_cancel(cancel)
        prepared.append(_local_cues(bursts, segment.start, count / _FPS, info, segment))
    media._make_parent(output)
    work = output.parent / f".horizontal_{uuid4().hex}"
    spans: list[montage.MontageSpan] = []
    remapped: list[Cue] = []
    total_frames = hold_frames + sum(frames)
    done_frames = 0
    previous_caption_source_end = None
    try:
        work.mkdir()
        cover = work / "cover.jpg"
        shutil.copyfile(thumbnail, cover)
        _cover(cover, info)
        with cover.open("rb") as stream:
            cover_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        concat = ["ffconcat version 1.0"]
        part_index = 0

        def render_part(segment, local, count, body_frame):
            nonlocal done_frames, part_index
            media._check_cancel(cancel)
            path = work / f"part_{part_index:06}.mov"
            timing = _render_part(
                source, info, segment, local, path, count, cover, body_frame,
                lambda fraction, _: progress(
                    0.90 * (done_frames + count * fraction) / total_frames,
                    f"Encoding horizontal part {part_index + 1}",
                ), cancel,
            )
            concat.extend([f"file {path.name}", f"duration {float(timing.video_end):.12f}"])
            done_frames += timing.frames
            part_index += 1

        if hold_frames:
            render_part(None, [], hold_frames, 0)
        for index, (segment, count, local) in enumerate(zip(segments, frames, prepared)):
            start_frame = done_frames
            span = montage.MontageSpan(
                index=index, source_start=segment.start, source_end=segment.start + count / _FPS,
                output_start=start_frame / _FPS, output_end=(start_frame + count) / _FPS,
            )
            for offset in range(0, count, _PART_FRAMES):
                chunk_frames = min(_PART_FRAMES, count - offset)
                begin, end = offset / _FPS, (offset + chunk_frames) / _FPS
                chunk_cues = [
                    Cue(id=cue.id, start=max(0, cue.start - begin),
                        end=min(end, cue.end) - begin, text=cue.text)
                    for cue in local if cue.end > begin and cue.start < end
                ]
                chunk = segment.model_copy(update={
                    "start": segment.start + begin, "end": segment.start + end,
                })
                render_part(chunk, chunk_cues, chunk_frames, done_frames - hold_frames)
            spans.append(span)
            previous_caption_source_end = montage._append_mapped_cues(
                remapped, local, span, previous_caption_source_end,
            )
        concat_path = work / "parts.ffconcat"
        concat_path.write_text("\n".join(concat) + "\n", encoding="ascii")
        final = work / "result.mp4"
        command = (
            media._base() + ["-loglevel", "error", "-xerror", "-y"] + media._PROTOCOLS
            + ["-f", "concat", "-safe", "1", "-i", concat_path.name,
               "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy"]
        )
        if info.has_audio:
            command += [
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-af", f"atrim=end_sample={total_frames * 1600},asetpts=N/SR/TB",
            ]
        command += [
            "-map_metadata", "-1", "-map_chapters", "-1", "-video_track_timescale", "15360",
            "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", final.name,
        ]
        duration = total_frames / _FPS
        media._run(
            command, work, duration, lambda fraction, _: progress(fraction, "Joining horizontal video and audio"),
            cancel, start=0.90, span=0.08,
        )
        montage._verify_timing(montage._measure(final, duration, cancel), total_frames, info.has_audio, pcm=False)
        verified = media.probe(final)
        if (verified.width, verified.height, verified.fps, verified.video_codec, verified.has_audio) != (
            info.width, info.height, _FPS, "h264", info.has_audio,
        ):
            raise media.MediaError("The horizontal output failed its native video format verification.")
        media._check_cancel(cancel)
        srt, source_map, transcript = (
            work / "result.srt", work / "result.source-map.json", work / "result.transcript.txt",
        )
        srt.write_text(media._srt(remapped), encoding="utf-8")
        source_map.write_text(json.dumps({
            "version": 2, "mode": "horizontal", "fps": _FPS, "duration": duration,
            "width": info.width, "height": info.height,
            "segments": [span.model_dump() for span in spans],
            "synthetic_intro": {
                "kind": "thumbnail_hold_and_overlay", "timebase": "output_seconds",
                "thumbnail_sha256": cover_hash, "output_start": 0.0, "output_end": hold_frames / _FPS,
                "hold_seconds": hold_frames / _FPS, "hold_frames": hold_frames,
                "fade_seconds": INTRO_FADE_SECONDS, "fade_start": hold_frames / _FPS,
                "fade_end": hold_frames / _FPS + INTRO_FADE_SECONDS,
                "source_video_start": hold_frames / _FPS,
                "source_audio_start": hold_frames / _FPS if info.has_audio else None,
                "audio_during_hold": "silence" if info.has_audio else "none",
                "first_source_time": segments[0].start,
                "explanation": (
                    "The hold is a synthetic cover image, not source footage. Its cover overlay fades "
                    "linearly for exactly four seconds over moving retained footage. Source video and "
                    "unfaded source audio begin after the hold; captions are above the overlay. "
                    "No audio stream is generated when the source has none."
                ),
            },
            "subtitle_regions": [
                {"segment_index": index, "output_start": span.output_start, "output_end": span.output_end,
                 "enabled": segment.captions, "region": segment.subtitle_region.model_dump()}
                for index, (segment, span) in enumerate(zip(segments, spans))
            ],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        transcript.write_text(
            "\n\n".join(
                f"[{media._srt_time(cue.start)} --> {media._srt_time(cue.end)}]\n{cue.text}"
                for cue in remapped
            ) + ("\n" if remapped else "No transcript cues intersect the selected segments.\n"),
            encoding="utf-8",
        )
        montage._publish(list(zip([srt, source_map, transcript, final], destinations)), cancel)
        progress(1, "Horizontal video, captions and source map ready")
        return spans
    except OSError as exc:
        raise media.MediaError(f"Could not write the horizontal video: {exc}") from exc
    finally:
        if work.exists():
            shutil.rmtree(work)
