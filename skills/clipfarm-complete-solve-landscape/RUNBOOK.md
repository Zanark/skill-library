# Complete solve in the original landscape arrangement

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Input and selection

```powershell
& $python -m clipfarm workflow prepare --video $video --workflow leetcode --format horizontal --session-timestamp $request
```

The source must be landscape. Output keeps its normalized native dimensions and
complete camera/code/screen arrangement. No avatar/code crop or vertical dimming.
The shared body is encoded at 30fps; native layout does not mean bit-identical
video or original frame cadence.

Read every source cue. Inventory every attempted/completed problem. Keep problem
introduction, actual reasoning, implementation/corrections and genuine completion
in order. Remove BRB/tangents and unnecessary pauses, not useful silent coding,
diagrams or result waiting. Missing completion is an explicit blocker.

Author `category: "solution"` and `horizontal.chapter`. Source segments must be
chronological/nonoverlapping and within that chapter. `horizontal.preserve_ranges`
protects important silent work; per-segment `trim_silence: false` is supported.
BRB exclusions conflicting with required protected work need reconciliation.
There is no 180-second cap.

## Caption rectangle

Inspect each scene and choose a normalized bottom empty rectangle.
`SubtitleRegion` requires y>=0.65, width>=0.30 and height>=0.055, fully inside
the frame. It is not safe merely because it meets those inequalities.
Use per-segment overrides where the source layout changes. Do not hide code,
camera or meaningful subtitles already in the source.

Record source-frame `subtitle_space` evidence for each distinct rectangle.
Also record `introduction` in the first selected span, `implementation`, and
`completion` in the last. Add actual submission/results evidence where present;
do not invent it when source completion is code-only.

## Cover and opening

Use genuine plain Consolas and a black landscape canvas. At 1280x720:

- Full exact numbered problem title at top, white.
- Demonstrated technique immediately beneath, left aligned, lime `#dfff00`,
  exactly 3px smaller than the jointly fitted title.
- Green `#36e16a` complexity at lower-left. Draw O as a **216px geometric ring**
  with 5px outline, centered around 70% canvas height; not a font glyph.
- A relevant rights-cleared local image at bottom-right, cats preferred.
  Preserve objects/backgrounds that supply the joke. No invented meme text,
  "average"/complexity headings, badges or on-image credits.

Scale the entire design proportionally for other native sizes. Use the complexity
actually stated with timestamp/quote; otherwise supply cited best-known research
and disclose the distinction in metadata. Never label a different demonstrated
algorithm with the researched optimum.

Record image hash, provenance, relevance, search query if used, rights and any
required attribution. Search ranking is not a license. The renderer does no
hidden download/research. Missing permitted artwork is a real gate.

Use one-second static cover hold, then four-second dissolve over moving footage.
Source narration and captions start after the hold; do not repeat or insert four
extra body seconds. Keep first words unattenuated. The source map marks the
synthetic hold; the dissolve overlaps the first four body seconds.

`intro_hold_seconds` can be 0..10 in whole 30fps frames if explicitly selected.
The exact generated cover is fingerprinted before rendering and copied unchanged
as `thumbnail.jpg`. A new cover/technique changes the candidate signature.

## Review and deliver

Follow the exact common CLI stages. Long visual scans and independent output-ASR
are bounded/chunked, not silently truncated to a short maximum. Inspect every
join, protected work, full completion, empty caption region, actual cover,
early/middle/end dissolve and first words.

Additional horizontal checks are `complete_solve_reviewed`,
`original_layout_preserved`, `silent_work_preserved`, `subtitle_space_reviewed`,
`thumbnail_reviewed`, `complexity_verified`, `meme_rights_verified` and
`intro_fade_reviewed`. Submission/runtime checks apply only to actual claims.
Never promote agent review to user approval.

Deliver one landscape-aware accumulating gallery for the creation prompt, with
the matching JPEG and complete `credits.txt`. Preserve required posting credits.
Do not infer that a historical thumbnail-only update altered existing MP4 intros.

## Actual source owners and failure recovery

`workflow.validate_horizontal_cut` checks chronological evidence/contracts;
`horizontal.render_horizontal` assembles the native body and cover dissolve;
`solution_artwork.SolutionArtworkSpec` binds technique/complexity/image evidence;
`workflow.prepare_horizontal_cover` and `verify_horizontal_cover_binding`
protect exact intro/cover identity.

The adjacent cut example deliberately contains no completed review/evidence.
Replace it with real source fields and image hash; structural examples do not
pass publication. If no caption space or full solve exists, report that constraint
instead of changing framing, inventing narration or falsely claiming completion.
