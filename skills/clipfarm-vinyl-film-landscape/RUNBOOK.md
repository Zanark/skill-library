# Full-song landscape picture-disc film

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Inputs and exact audio

Require full local master WAV, complete square sleeve art, complete circle RGBA
art and permissions/attribution. Source masters in the original production were
48k stereo PCM16; inspect the new source rather than assuming it.

Keep full source sample count/levels and add exactly two seconds of silence at
each end, with no gain, normalization, EQ or fades by default.
Compute duration as `(source_samples + 4*sample_rate) / sample_rate`.
Use `ceil(duration * 30)` video frames so fractional song endings are not cut.
Do not use a rounded duration or `-shortest` to hide a one-frame shortage.

The circle input reference was 2048x2048 RGBA. Retain its complete transparent
corners, native rim, curved lettering, vignette and grooves, mapped to the whole
record diameter. The square cover remains complete on a separate sleeve.
Do not replace either with a generic record or the superseded cropped print.

## Shared background RGB for new work

From the canonical **square** cover:

1. Ignore fully transparent pixels.
2. Quantize valid RGB pixels to four colors using Pillow median-cut without
   dithering.
3. Count cluster populations and choose the largest (deterministic RGB tie-break).
4. Save method, source hash and exact RGB once.
5. Use that same RGB for video and thumbnail background.

Do not derive it from black/transparent circle padding, independently choose a
thumbnail accent, darken/tint it or add a background gradient/grain that changes
the saved color. Local object shadows/material lighting remain appropriate.
Earlier films used track accents; the later preference did not authorize their
retroactive recoloring.

## Re-author the composition

The historical 1920x1080 reference used:

```text
Platter center: (1238,473)
Native projected radius: 537
Vertical tilt: 0.58
Perspective factor: 0.12
Texture working diameter: 1536
Square sleeve: 320x320 on a 344x344 upper-left framed panel
Rotation target: 5 rpm, eased in/out over the silent handles
```

Use Pillow for background, sleeve, measured text, track/album labels and
soundprint. Keep image and text hierarchy uncluttered; no LeetCode problem/camera
template. Add fixed chassis/cast shadow/spindle separately.

For the disc, make output coordinate arrays relative to center, undo the vertical
tilt/perspective to get normalized record-plane coordinates, then rotate the
texture lookup angle by `angle(t)`. `cv2.remap` samples complete RGBA art through
its alpha. Keep spindle, chassis and lighting fixed after this rotating layer.
Never rotate a baked room reflection with the artwork.

Maintain continuous rotation phase; do not restart the disc each frame/chapter.
Ease angular velocity through handles with a smooth polynomial while the music
itself stays unchanged. Inspect lettering and outer rim under perspective.

## Grooves, ink and spectrum

The final material was a **2D physically motivated approximation**, not ray
tracing. Its reference used 132 radial groove cycles, radial/tangential roughness
0.36/0.065, dielectric F0=0.045 and fixed cool key/warm fill. Radial groove normals
perturb an anisotropic GGX-like specular field. Bright outer printed lettering
receives matte-ink treatment so it stays legible. Preserve the art, not a new
rotating painted gloss.

Compute audio features locally from mono-average samples: 4096-sample Hann
windows at 30 updates/sec, 48 roughly logarithmic bands spanning about 3..1100Hz,
98th-percentile normalization, power compression 0.55 and faster attack than
release. A separate 140-bin waveform trace can decorate the sleeve.
These numerical references describe the original aesthetic, not proof of
acoustic fidelity or a mandatory universal equalizer.

Precompute projection, static lighting/masks and audio features. Stream frames;
do not cache the whole film. Derive visual audio position after the leading
handle, holding silence at both ends.

## Encoding and verification

Use the custom-producer staging procedure. The original hardware path used AMD
AMF H.264 quality/CQP I/P/B QPs18/20/20; libx264 fast/CRF18 was an explicit
software alternative. Qualify whichever actually exists rather than assuming
GPU support. Native output is 1080p30/yuv420p; the reference tagged BT.709 and
encoded AAC320k/48k stereo, with fast-start MP4.

Preserve selected resolution/fps/detail/audio. Check full source-to-output PCM
alignment/level and exact handles, allowing codec error rather than claiming AAC
is mathematically identical to WAV. Compare actual decoded frame count/end
coverage. Four early films once lost a frame through fractional `-t` handling;
the corrected ceiling-CFR check matters.

Inspect decoded rotation, stationary reflections/spindle, material/lettering,
spectrum, first/music-start/music-end/last frames and full landscape thumbnail.
No speech ASR/subtitle generation is needed; verify there is no subtitle stream.
Listening and aesthetic/user acceptance remain unestablished unless actually done.

## Delivery and recovery

Deliver a new immutable local edition with full audio/art provenance, required
credits and honest rights limits. New requested editions of an existing
collection use explicit version folders; never overwrite old approved bytes.
Do not rerun historical migration/rename helpers or force a blocked file move.

Legacy full-vinyl galleries had native-copy limitations. New galleries must
implement genuine separate one-click fields; this document does not repair old
ones or certify platform licensing. No automatic upload, new score composition
or shared visualizer editor is implied.
