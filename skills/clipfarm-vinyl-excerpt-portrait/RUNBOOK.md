# Portrait platter excerpt with separate sleeve

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Inputs and two legitimate production paths

Require a newly permitted master, square/circle cover art, exact selected song
range and a musical/visual rationale. Inspect completed full material before
selection; signal metrics alone are not direct listening or a hook guarantee.
Keep source music and credits, not arbitrary recommendations.

The historical path consumes a matching landscape picture-disc film plus its
master and explicit scene mask. For new assets either:

1. Build a new landscape film using the landscape skill, then select/mask its
   platter window with exact source correspondence; or
2. Re-author the same platter/material projection directly at portrait size,
   driven by the master and the same visual clock.

Path 2 requires deliberate compositor authoring; do not imply the old crop/mask
script works without its input film or private mask.

## Select exact frame and sample ranges

The historical selection contract allowed 5..60s and required whole 30fps
frame bounds `[start_frame,end_frame)`. At 48k audio, one video frame is 1600
samples. Bind both film and WAV hashes, range, sample bounds and rationale.

For other source sample rates/cadences, use rational mapping and explicitly
verify decoded boundaries rather than pretending 1600 is universal.
Do not reorder music, speed it up, normalize it or quietly change the chosen
phrase because a platform excerpt is shorter.

The original excerpt applied a 40ms fade-in and 350ms fade-out, no gain/speed
change, plus a short visual ending fade. This is an explicit excerpt treatment,
**not** the full-film policy (which kept source master/handles without fades).
Record the new request's fade choice; do not call faded audio bit-identical.

## Reference composition at 1080x1920

```text
Platter/chassis scene window: 1000x592 at (40,470)
Historical landscape crop: x600/y130/width1300/height770
Separate complete square sleeve: 560x560 at (260,1150)
Caption layer: none
```

Use actual source dimensions and mask coordinates; the listed crop is not
portable to a different film. Mask the platter/chassis union with a restrained
outward feather. Exclude decorative outer halo and spectrum; source-y clearance
must prevent spectrum lines leaking outside the intended scene.
Inspect masked edges during **motion**, not only a still.

Keep complete canonical circular art on the turning record and complete square
art on the separate sleeve. Retain physical-looking grooves and stationary
record-plane reflections if authoring the scene directly. They are 2D shading,
not path-traced realism.

## Color and cover

Use the landscape runbook's deterministic four-color median-cut largest-cluster
method on the canonical square cover, ignoring fully transparent pixels.
Save source hash/method/RGB once; share the exact background RGB in the new
video and thumbnail. Do not derive it from circle padding, tint/darken it or
independently choose accents. Object-local shadows/material highlights remain.

Future covers stay 1080x1920 with all essential text/art/subjects inside
`(0,240,1080,1680)`. Inspect full and exact centered3:4 views.
This changes thumbnail authoring, not the video's aspect ratio or an old
approved song. Do not apply a LeetCode camera/problem title template.

## Render and verify

For film-derived composition, use FFmpeg's explicit exclusive video-frame trim,
matching audio sample trim, square-pixel scaling and mask composite. For direct
composition, stream original frames with the reviewed projection/material and
same audio time origin. Use qualified high-quality H.264/yuv420p/30fps with
explicit AAC settings; preserve whole source originals.

Fully decode both streams; verify one video/one audio and **no subtitle stream**,
1080x1920, exact expected frame count/end coverage and audio timing.
Compare decoded audio correlation/SNR/gain/peaks against the selected source
with declared fades, not against an imaginary unfaded bit-identical master.
Inspect source boundaries, actual motion/mask leakage, artwork text, last frame,
and matching cover. No speech ASR is required for instrumental-only material.

Keep waveform/visual sampling limits, listening, aesthetic/user approval and
rights/distribution decisions separate. Do not infer platform availability,
trends or permission from an original-song filename.

## New local delivery

Use one new session gallery for the request, separate caption/hashtags/alt/
required credits and genuine one-click copying. A musical passage is not an
unqualified promise of virality. Preserve the full films and earlier excerpts.

Do not execute the frozen `portrait_reels.py`, historical rename transactions
or thumbnail migration merely because they exist. Their exact private assets,
absolute imports and review state are not packaged with this skill.
