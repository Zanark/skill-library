# Early cinematic music-video draft / animatic

## Outcome and authority

Show what an original cinematic story could look like, quickly and honestly.
This is a new local concept movie, not final visual/lyric approval. Read the
[common contract](../_shared/CINEMATIC-MUSIC.md); its source preservation, full-
song default, identity, rights and delivery rules apply here.

Use this only for an explicit draft/concept/animatic request. If the user asks
only for a storyboard, do not produce a movie. If only skills are requested,
do not start any video. An unqualified existing fast production is not
automatically an early draft merely because it uses sampled review.

## 1. Intake without a full singing audit

Capture original request time, source/lyrics/art identity, hash/mtime and actual
full decoded audio duration/samples. Read all supplied words and understand the
whole structure, repeats and concept. A source header's approximate duration
is not enough to decide an ending; a lyric2:30label is not a trim command.

Preserve the complete original recording, including start/end, levels and speed.
Do not run source/output singing ASR solely to audit these lyrics. Do not ask
the user to supply a transcript as a prerequisite or download another track.

Create a new private source-bound run with `mode: early-draft`. Record the
deliberately skipped recognition/lyric/progress/full-scene/join review, not
passing booleans. Never copy an old film's review or hard-coded producer.

## 2. Block the full story before polishing

Write a concise logline, consistent original/permitted cast, stakes and ending.
Map a beginning, development and payoff across the entire song, including
instrumental passages. Save section/shot/action beats and a visible storyboard.
Unless a storyboard-first stop was requested, continue to the concept movie.

Spend effort on readable staging, a few meaningful actor/prop movements and
motivated shot changes. Repeated choruses develop the story. Use simplified
geometry/materials, blocked motion, fewer background details, cached static
layers and restrained effects instead of polishing every asset.

Keep stable character/object IDs and the same source-time clock as the song.
Rough is allowed; contextless stills, missing later sections or a misleading
technical trace are not. Repair obvious encountered clipping/wrong identity/
prop contact even though exhaustive review is deliberately skipped.

## 3. Declare the preview instead of silently lowering a final

The proposed lightweight default is720x1280/24fps, explicitly a portrait proxy.
An existing already-qualified higher-quality authoring path may be retained
when changing it would cost more than it saves. Record actual dimensions/fps/
codec/quality in metadata and gallery; do not promise a measured speedup.

This proxy choice applies ONLY to the explicitly requested early draft.
It does not change ordinary fast-production or full-review quality. Keep
logical/source seconds separate from frame indices; use the full-song ceiling
frame count at the selected draft fps. Scale measured typography/clearances
from the design canvas rather than clipping a1080p overlay onto a smaller film.

Put a restrained but visible **DRAFT** mark inside the actual movie's safe
composition. Preserve enough space to understand the planned story/lyrics.
Use DRAFT in the filename/card/poster/metadata; a sidecar alone is insufficient.

## 4. Treat optional lyrics as estimated

A draft may omit the lyric window to concentrate on story/look. If included,
use supplied words and unique occurrence IDs with estimated section holds.
Keep `timing_basis: estimated-unreviewed` and show a clear estimate notice.
Do not pretend proportional word-count spacing is real vocal alignment.

Omit unsupported word-specific highlighting/karaoke. A phrase elapsed bar
may be included only as visibly estimated choreography; it is not sync proof.
The common [lyric-clock reference](../_shared/cinematic-lyric-window.js) can
prevent stale/reset errors without certifying that the cue times match singing.
No source/output singing recognition or every-line progress audit is required.

## 5. Render once, inspect a small real sample

Inspect a few native designs that show the beginning, important turning point,
most crowded/longest-text scene and payoff. View the actual returned pixels.
Seal the new inputs and run one bounded owned encoder at the declared proxy
settings, with complete original audio and no extra title hold/music/retiming.

After encoding:

- Check actual dimensions/fps/streams, full audio sample/duration coverage,
  video end coverage, source hash/mtime and basic decodability.
- Inspect roughly5..8 source-specific encoded states spanning beginning,
  development, hardest composition/action and ending; fix actual defects.
- Check representative original/output audio windows and original zero silence
  separately; signal checks are not direct listening.
- View the actual full1080x1920 cover and exact centered3:4crop.

Do not expand this into singing ASR, every lyric/progress state, every camera
join or all-framePTS inspection unless specifically requested. If more work
is needed because a real defect appears, do the bounded repair and record it.
Do not claim skipped checks were completed.

## 6. Deliver the idea with a clear next-stage boundary

Stage one new versioned draft bundle under the original request's session:
`draft.mp4`,1080x1920draft-marked thumbnail, storyboard/timeline and a receipt
that binds exact source/renderer/output hashes. Generate the single index
directly with the common posting/folder/CSP helpers. No gallery desktop/phone/
browser verification unless asked.

The movie, gallery and metadata must make these clear:

- EARLY DRAFT / concept demonstration, with actual proxy size and full duration.
- What the draft demonstrates: story/cast/staging/palette, not final polish.
- Lyrics absent or estimated; full ASR/lyric/progress/scene-join checks not run.
- Full-review complete, actual user approval and ready-for-upload are false.
- Source music/lyric permissions still need their own evidence before posting.

Include natural first-person draft copy if posting fields are provided, but
never imply this rough edition is a final public release. Keep a separate
rights/credits field. Leave owned processes/listeners closed after completion.

## Continuing later

Do not automatically start the full render after a draft or ask for approval
when the user is AFK. Deliver the idea and stop. A later explicit full request
routes to [the full-review procedure](../clipfarm-cinematic-music-video/RUNBOOK.md).

That is a NEW immutable full-quality edition: reuse valid story/assets/input
facts, rebuild source-time/full-fps mapping, establish actual lyric alignment
and perform all full-mode review. Never rename/upscale the proxy or copy
`review_complete` flags to manufacture a finished full film.
