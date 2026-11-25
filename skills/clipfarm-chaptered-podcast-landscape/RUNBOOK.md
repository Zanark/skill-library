# Full narration with one chapter/heading clock

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Inputs and full-source authoring

Require complete local narration, actual audio metadata/hash, supplied permitted
Cozy full-room artwork, transcript/cue provenance, technical references and
speaker estimates if used. Do not automatically adopt new rights/disclosure
or account decisions from old completed collections.

Read every cue. Create a complete source-to-scene coverage ledger; nothing
substantive disappears because it is hard to animate. Author any correction to
wrong source teaching visibly and separately while retaining spoken captions.
Preserve narrow uncertain names/numbers rather than inventing a clean transcript.

## One canonical timeline

Author scene/action/caption/chapter data in original source time.
Chapters are ordered, start from the final video clock and have meaningful titles.
Each chapter supplies:

```json
{
  "start_frame": 0,
  "end_frame": 900,
  "title": "Actual topic",
  "scenes": ["scene-0"],
  "caption_ids": ["caption-0"]
}
```

This is an authoring example, not a shared schema. The new producer must validate
contiguous intended coverage, bounds, caption ownership and stable scene IDs.
Generate both the persistent top heading and YouTube description timestamps from
these exact boundaries. Do not separately type approximate chapter times.

## Landscape composition

At 1920x1080:

1. Reserve an external top padded band for the current chapter topic.
2. Aspect-contain the **complete Cozy studio** with padding on every side.
3. Fit the causal teaching panel inside the artwork's intended internal board.
   The original used white with a warm/yellow outline; the invariants film used
   a dark teaching theme without recoloring the canonical room.
4. Reserve extra external space below the image for clear lower spoken captions.
5. Use green-active/white-inactive estimated speaker contours, derived from this
   exact artwork hash, only where source analysis supports them.

Colored guide zones from the planning image were location guides, not mandatory
purple/maroon fills. Do not crop the room, cover the illustration with captions,
or borrow masks from Boldly Outlined portrait art.

Teaching must visibly perform narrated operations: construct/populate maps,
advance loops/pointers, carry stable values through moves and show intermediate
updates before outcomes. The room is context, not a replacement for the lesson.

## Original audio and sequential chapters

The full source audio stays uncut/unsped, without added music or an intro hold.
If the source contains compatible original AAC, encode video-only chapter chunks
and mux the full original packet stream once. Keep actual packet payload/PTS/DTS
and decoded samples, not merely nominal duration.

Use integer output frame boundaries and continuous source time. Check actual
last-frame/audio-end coverage; do not truncate a tail with `-shortest` or hide a
gap at a chapter concat. Preserve source silence if part of the full recording.

The observed qualified software settings were 1080p30, libx264 fast/CRF18,
two encoder threads and yuv420p, plus original AAC. They are not a lossless-video
promise; do not lower them for performance.

## Optimize identical work, not quality

Cache static room/grid/text layers and exact complete-frame RGB where state is
unchanged. An unchanged chunk can be reused only when the exact renderer/code,
assets, captions, actions and timing hashes agree. A caption edit requires new
affected chunks and review; unrelated chunks can remain byte-identical.

The invariants production verified pixel/bit-identical redundant-work elimination
before using it. Sample throughput gains were not whole-film time guarantees.
Do not claim PyAV/hardware is faster without actual representative measurement.

Seal designs and hashes first, then render sequentially with bounded memory.
Do not launch many full native encoders or reopen finished private producers.

## Review and final packaging

Fully decode the joined movie, verify frame count/duration and original audio
identity. Inspect all chapter/scene boundaries, causal intermediate states,
dense labels, captions and final completion. Read fresh independent output-ASR
in full. Reuse earlier ASR only with exact unchanged full audio and explicit
inheritance provenance, never calling it fresh after a visual-only revision.

Confirm encoded topic headings and generated chapter description timestamps
match exactly. Review the landscape cover as landscape; portrait 3:4 cropping
does not apply. Keep metadata private/unapproved unless actual authorization says
otherwise; platform "publish date", rights, disclosure and account are not
automatically decided by a full successful encode.

Deliver a clean new bundle/session gallery with source/code/evidence retained
privately. Do not call it a Short, restore deleted old collections, or close the
separately planned shared animation/productization workstreams.
