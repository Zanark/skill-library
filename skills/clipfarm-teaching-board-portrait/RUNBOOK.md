# Portrait teaching animation without a camera or character strip

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## New inputs and plan

Record source path/hash, full duration/encoding, language, transcript provenance,
rights, chosen spans, any source errors and intended viewer takeaway.
For raw narration, decode bounded WAVs and transcribe locally; there is no
shared `workflow prepare --audio` command.

Read all words before selecting a useful excerpt. A true original-voice
animation keeps speech meaning/order, not an invented cleaner explanation.
Make a table per clause: source range, output frames, concept, visible referent,
action, intermediate state, result, correction/uncertainty.

## Scene model

Create stable IDs for tiles, keys, values, groups, pointers, edges and labels.
Declare their initial positions/state and ordered timed changes. Evaluate state
from time, not accumulated frame-by-frame simulation.

For a map example, explicitly:

1. Draw an empty map with visible key/value slots.
2. Move the narrated item from its original row into a stable comparison position.
3. Highlight the lookup key and show hit/miss before revealing a decision.
4. Insert/update the same identified value, with intermediate count/index state.
5. Advance the loop pointer only after the operation.
6. Hold the resulting state long enough to read, then clear outgoing arrows
   before unrelated incoming text.

For stacks/queues use real push/pop/front/back state and preserve operand order.
Narrated "this"/"here" must have a visible target at that instant.
Changing only captions or fading completed diagrams does not satisfy the format.

## Layout and typography

Use the reviewed dark-teal softly fading grid for this explicit animation
treatment, not ordinary source-video clips. Build it once at full resolution:
flat dark-teal field, thin low-contrast grid, smooth edge fade, readable cream/
gold plain-Consolas headings and distinct teaching accents.

Reserve a high heading region, generous central board, and rounded lower caption
panel. The historical HashMap band `(85,1290,900,1440)` is a useful reference,
not universal permission to overlap app UI. Fit every actual label/caption and
inspect full/phone layouts against current supplied safe-zone references.

Use measured text widths; preserve complete terminology. Avoid decorative
badges, debug chrome or a still source-code pane pretending to be animation.
Make editor corrections a separate labelled region, not rewritten speech.

## Audio, holds and encoding

Choose the exact source-to-output map before actions. The original short used
48k stereo PCM extraction and a declared final silent reading hold.
Do not copy that hold to every future source or add unrecorded duration.
Any synthetic silence/reading time appears in the source map and caption plan.

Stream native RGB frames to the same qualified FFmpeg path, typically
libx264 fast/CRF18/two threads, 30fps/yuv420p. Edited/held audio is staged as
PCM and encoded once; compare the final decoded timing to the intended map.
For an unchanged AAC source policy, use the separate packet-preserving path.
H.264 delivery is not lossless; exact caching never excuses quality cuts.

## Cover and review

Use a truthful topic/problem heading and the format's cream/gold/grid treatment.
With no camera there is no fabricated image/second camera separator.
Keep all essentials within the exact centered 3:4 area and inspect both views.

Before encoding, inspect representative initial, intermediate and outcome states.
After encoding, inspect decoded operations, longest holds, every join, caption
timing and corrections. Read fresh independent output-ASR in full.
Record exact samples actually viewed; a large motion percentage proves nothing
about whether the teaching action made sense.

Preserve original sources and rejected editions. Deliver only after real review,
in one new local session gallery with separate posting fields/credits. No
user/listening/rights approval or general shared-animation completion is implied.
