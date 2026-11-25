# Re-authoring request-local productions safely

The animated, audio-led, character and picture-disc films were made with real
local Python producers. Those producers are frozen, input-bound private programs,
not an installed `clipfarm animation` or `clipfarm vinyl` command.

The format runbooks below explain their actual algorithms and tools sufficiently
for an editor/agent to author a **new request-local producer**. That deliberate
authoring step is part of these skills. They are not one-click arbitrary-input
renderers, automatic semantic animation or the planned shared no-code product.
Do not pass these templates to `workflow prepare` or the Studio job queue.

## Files for a new job

Create a new private directory with these roles (names are an authoring convention,
not a schema the application already understands):

```text
new-production\
  input.json          source/art/audio/font identity and permission notes
  timeline.json       selected source spans, scenes, actions, captions, chapters
  produce.py          new pure compositor plus bounded encoder orchestration
  design\             full-resolution candidate frames, explicitly inspected
  sealed-inputs.json  reviewed plan/code/asset hashes
  candidate\          video, cover, source map and fresh output-ASR
  review.json         real evidence, limits and pending/actual decisions
  completion.json     final paths/hashes, only after completed local delivery
```

Never copy an old approval or use `reviewed: true` in a starter template.
Keep private recordings/art/fonts/transcripts out of the committed skill folder.
Resolve all assets from explicit new job inputs, not Downloads or a sibling
workspace. New assets require their own rights review and art-specific masks.

## Exact reusable tool roles

| Tool | Use | Important limit |
|---|---|---|
| Pillow `Image`, `ImageDraw`, `ImageFont`, `ImageOps` | Editable raster layers, measured text, containment, compositing | Font availability and text fit need checks |
| NumPy | Coordinates, masks, audio windows, static caches, numeric equality | An aggregate metric is not perceptual approval |
| OpenCV | Contours, local image warps/remap, bounded frame decode | Disable OpenCL on this Windows machine |
| FFmpeg from `clipfarm.media.ffmpeg_exe()` | Decode, exact-rate raw frames, H.264, audio staging/mux, full-decode checks | Use the actual installed binary; no codec/fps assumption |
| faster-whisper | Local speech cues and independent output-ASR | ASR-estimated timing, no direct listening/identity proof |
| PyAV, when explicitly available | Packet/PTS inspection, bounded source-frame decode and exact AAC comparison | Optional; private import paths are not a package API |
| ClipFarm `Cue`, transcript parsers, posting/explorer helpers | Existing typed cues and gallery/copy/navigation behavior | Helpers do not implement a general scene engine |

Use the declared environment. Only restore/install a missing optional dependency
after an actual failure; do not install Blender, a GPU stack, model provider or
an unrelated renderer merely because a visual looks three-dimensional.

## 1. Author source/output time maps before pictures

For each retained passage record source start/end, output start/end and the
rounding rule. Use integer output frame intervals `[start_frame,end_frame)`.
Render frame `i` at `i / fps`; audio uses real samples/packets, not frame-rounded
decimal strings. Declare every synthetic silent hold. Full-source chaptered
films have no automatic intro or audio shortening.

For moving source camera, resolve the source timestamp through this same map and
select the appropriate decoded PTS. Keep a bounded lookahead buffer, never the
whole movie. Choose held/hidden camera behavior explicitly during synthetic holds.

For source audio, FFmpeg can decode a private bounded WAV without uploading:

```powershell
$ffmpeg = (& $python -c "from clipfarm.media import ffmpeg_exe; print(ffmpeg_exe())").Trim()
& $ffmpeg -nostdin -hide_banner -loglevel error -n -i $audio -vn -ac 2 -ar 48000 -c:a pcm_s16le $wav
```

This example decodes a whole local audio file. For long speech recognition,
extract bounded 600-second windows with short overlaps and reconcile overlap
ownership, rather than passing hours of decoded audio to the model.
For raw narration without a shared workflow plan, an author can invoke local
`faster_whisper.WhisperModel("small", device="cpu", compute_type="int8",
cpu_threads=2)` with `word_timestamps=True`, `beam_size=3` and the real language.
Use bounded input windows, offset their times and deduplicate overlap; read all
resulting words/cues. This is not a new `workflow prepare --audio` switch.

## 2. Make narrated operations real

Represent stable objects separately from timed actions. An authoring template:

```json
{
  "objects": [
    {"id": "item-0", "kind": "tile", "label": "7", "initial": {"x": 180, "y": 600, "visible": true}}
  ],
  "actions": [
    {"start_frame": 30, "end_frame": 45, "object": "item-0", "property": "position",
     "from": [180,600], "to": [400,600], "easing": "smoothstep",
     "meaning": "Move the same value into its inspected destination"}
  ]
}
```

This is a documented **authoring interchange example**, not a public application
schema. A new producer must validate/interpret it or use an equally explicit
typed representation. Reject unknown objects, reversed intervals, accidental
overlapping writes, out-of-frame bounds and nonsensical state.

Start from the scene's initial state, apply completed actions, interpolate the
active action, then draw. For normalized phase `u` in `[0,1]`, smoothstep is
`u*u*(3-2*u)`; discrete assignments change only at their declared boundary.
Do not repeatedly integrate motion from the previous rendered frame: direct
time evaluation makes seeking/review deterministic.

Give each caption/narrated claim a scene/action ledger entry. Construct/populate
maps, advance pointers/loops, move stable tiles, compare and update intermediate
state **before** the outcome. Resolve every "this"/"here". A finished diagram with
changing captions, pulses or camera movement is not causal teaching.

Measure actual text with the selected font. Wrap and fit without truncating,
reserving headings/captions/character/inset rectangles. Route arrows and shadows
around labels across their entire trajectory, not only endpoints.

## 3. Compose design frames

Build static background/text/art layers once. For every candidate state:

1. Copy the immutable background.
2. Draw heading and teaching board according to the selected format.
3. Draw stable actors in explicit z-order at their evaluated state.
4. Composite real source-camera or artwork/rig layers in their reserved regions.
5. Draw spoken captions and separate referenced corrections.
6. Check actual bounds/contrast and inspect full-size/phone-scale output.

The profile runbook specifies which layers belong above/below each other.
Dark/light boards, text repairs and mouth cadence do not authorize a new global
background or a migration of older media.

## 4. Stream frames; do not cache a movie

The historical software path commonly used 30fps RGB frames, `libx264`,
`-preset fast -crf 18 -threads 2 -pix_fmt yuv420p`. Those are observed high-quality
delivery settings, not mathematically lossless compression. Preserve the selected
production's resolution/fps/settings; any hardware alternative needs parity and
qualification rather than an assumed speedup.

This is the actual pattern a new `produce.py` can use after defining its own
`render_frame(i)` compositor and reviewed `width`, `height`, `fps`, `frame_count`:

```python
from pathlib import Path
import subprocess
from clipfarm.media import ffmpeg_exe

# These are inputs from the newly reviewed plan, not hidden globals.
def encode_frames(render_frame, output, width, height, fps, frame_count):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    with output.with_suffix(".encode.log").open("xb") as log:
        process = subprocess.Popen([
            ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{width}x{height}", "-framerate", str(fps),
            "-i", "pipe:0", "-an", "-frames:v", str(frame_count),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-threads", "2", "-pix_fmt", "yuv420p", str(output),
        ], stdin=subprocess.PIPE, stderr=log)
        try:
            for index in range(frame_count):
                frame = render_frame(index).convert("RGB")
                if frame.size != (width, height):
                    raise ValueError(f"Wrong frame size at {index}")
                process.stdin.write(frame.tobytes())
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f"Encoding failed; inspect {log.name}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
```

This **documented building block is not a shipped renderer API**. Supply the
format-specific compositor, validation, cancellation and staging around it.
Encode to a new explicit partial candidate; do not expose it as a final.
Disk logs avoid unread stderr deadlocks. Stop only that owned encoder.

## 5. Choose the correct audio policy

For unchanged full original AAC, encode video-only first, then mux source audio
with explicit `-map` and `-c:v copy -c:a copy`. Avoid `-shortest` hiding missing
frames, an unexamined `-t` truncating the tail, or resampling/re-encoding "for
convenience". Verify packet payloads/timestamps and decoded audio afterward.
Not every codec/container permits copying; fail or obtain a documented new policy.

For edited speech, audio-only clip holds or music fades, stage explicitly timed
PCM and encode once. Retain the source map and compare against expected samples,
allowing only the declared fade/hold/mix. Never call this packet-identical audio.
Music full films preserve full masters with exact silent handles; excerpts have
a separate selected-range/fade contract.

Choose video end coverage using rational duration: a full-song film with fractional
duration may need `ceil(duration * fps)` frames. The last video frame can cover
the end; it must not truncate audio. Do not repair a one-frame deficit by changing
the original song duration. Validate actual muxed clocks before delivery.

## 6. Verify, then publish an immutable edition

Use the actual FFmpeg to fully decode video and audio, check errors/end coverage,
and collect frame/packet timing as required. Retained AAC comparisons can use
PyAV's demuxed packet bytes/PTS/DTS/time base; sample comparisons need decoded
PCM and expected source maps. Scope claims to checks actually performed.

Read fresh independent output speech-ASR. Inspect encoded action transitions,
camera joins, characters/props, captions and the cover. Save actual image-view
coverage and unresolved words/rights/identity/listening limits. Full-song music
does not require invented ASR or subtitles.

Only after substantive real review should the new delivery script atomically
copy the candidate into its new session bundle and write the gallery/completion
receipt. A safe custom publisher must verify exact inputs and stage outputs,
refuse collisions, preserve older editions and retain current posting controls.
It is **not** authorized to set user approval or `readyForUpload=true`.

The old private sources listed in the format catalogue remain read-only
mechanism/evidence references. Their absolute paths, imports, approval records
and output directories are deliberately not packaged or replayed.
