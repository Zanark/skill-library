# Animated teaching with a real synchronized camera inset

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## New production inputs

Use original recording, actual camera ROI per scene, source transcript, selected
speech spans and a complete narration/action ledger. Read all source material
and retain meaningful qualifications. Create a new private producer using
`CUSTOM-PRODUCERS.md`; the adjacent brief is not a shared application plan.

Every retained clause must drive an operation: construct/populate maps,
advance loops, move stable tiles, compare and update intermediate state before
the result. The camera is supporting context, not a substitute for teaching.

## Layout

Use a dark-teal subtly fading grid, open board, genuine plain Consolas and
readable roughly 40px spoken captions at 1080x1920. Reserve:

- Complete actual problem heading at top and a separate specific clip topic.
- Top-right aspect-contained camera box, target 364x312 at `(620,300)`.
- About 16px inner padding, at least 48px text/teaching separation and an 80px
  right-canvas margin; the reference frame is soft cornflower `#78a9ff`.
- A shortened/reflowed separator that does not run behind the inset.
- A lower caption band outside meaningful diagrams and app UI.

These are reviewed composition targets, not a universal platform overlay guarantee.
Keep full source-camera crop/aspect. Never stretch it or sacrifice meaningful
animation. Partial app UI overlap was allowed for this inset only, not teaching,
heading or captions. Check actual phone-scale output against the references.

## One clock for speech and camera

For each retained output span, map output time to its source asset and PTS.
The camera must use that asset and mapping, including all cuts and joins.
Do not use a random avatar loop, portrait still or fabricated mouth movement.

Decode incrementally with bounded buffers. Source may be 25fps or variable-rate;
do not equate its frame index to output 30fps. Select by timestamps, preserving
the current source frame until the next eligible PTS.

During an explicitly authored silent reading hold, choose a disclosed held source
frame or hidden inset. Do not advance unrelated source time or loop footage.
Record source-side motion/delay limitations rather than claiming perfect lip-sync.

The full-frame compositor evaluates teaching objects at output frame time and
then composites the source camera into its reserved card. Cache only unchanged
background/state layers; a cached full frame cannot freeze a moving camera.

## Cover

Use actual retained camera footage, not the video inset screenshot or a diagram.
Problem/separator/topic/separator/camera, genuine plain Consolas, cream/gold and
centered 3:4 essentials. The later thumbnail direction is **one thin blue-grey**
`#45616a` camera frame and diffuse shadow, no second rectangular frosted plate
or heavy black rim. The background keeps its soft frosted treatment; slightly
brighter faded gridlines were thumbnail-only, not a video recoloring instruction.

## Verification and delivery

Inspect actual encoded operations, intermediate states, arrow paths, captions
and camera at start/middle/end, every join/crop/hold boundary and speech activity.
Compare mapped source frames with output. ASR or arithmetic alone cannot prove
the inset is moving or perceptually synchronized.

The overlap revision requires internal clearance throughout motion: arrowheads,
shadows and outgoing labels must not cross incoming text. Route transfers around
labels and keep execution pointers in separate gutters.

Use the exact original audio policy and existing high-quality encoder settings;
do not reduce resolution/fps/diagram detail or skip independent output-ASR.
Preserve replaced editions and old covers. New artwork/signature needs fresh
review and hash binding. Deliver one new session gallery with separate posting
fields, required credits and no automatic upload.

## Tooling boundary

Pillow/NumPy draw the teaching; OpenCV/PyAV can decode source PTS/masks;
FFmpeg streams final frames and assembles the reviewed audio. The private
`Film`/motion helper names are examples, not public callable APIs. Shared AE
implementation remains separate even though this production recipe is reusable
as an editor's skill.
