# Native portrait grading: keep the recording, change the look

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Required inputs and tools

Read [the complete shared grading procedure](../_shared/GRADING-WORKFLOW.md):
it supplies the real commands, setup, metadata gates, immutable state, review,
approval and recovery. No historical transcript, frame, font, reference art or
private helper is needed. The actual checkout/environment, optional grading
dependency, local FFmpeg and permitted source are required.

Record a clear actual look brief and preservation constraints. User-supplied
reference images require their own rights/provenance; do not download a film
still/proprietary LUT or upload the recording to a third party.

## Geometry and source contract

1. Inspect actual display-normalized width/height, rotation and sample aspect.
   The normalized display must be portrait. A landscape or square source can
   use the general color-grading skill, but is not evidence that this portrait
   format was delivered in another orientation.
2. Keep the entire sharp source picture. No 9:16 template, crop, letterbox,
   stacked feeds, new overlays, synthetic hold or intro is added.
3. Keep source PTS/cadence. The historical30fps is not a forced output rate;
   the engine verifies native decoded-frame counts and relative timestamps.
4. Default to the full video with `start: 0`, `end: null`. A requested source
   range is explicit and recorded; never label it the full recording.
5. Keep original compatible audio. The final verification compares copied
   packets and relative A/V clocks. This is different from the generic clip
   renderer's new AAC encode.

Do not infer compatible encoding from dimensions. Browser MP4 requires supported
even geometry and compatible original audio. Use the supported MKV target only
when warranted and permitted; explain browser/precision/lossy limits. Known
unsupported color/alpha/interlace/track layouts are explicit blockers.

## Practical authoring sequence

Copy [recipe.example.json](recipe.example.json) to a private run. It is a real
`clipfarm.grading_models.GradingRecipe`, not an approved session. Its 0.65 look
intensity is illustrative; source corrections start neutral. Read current
metadata/catalogue and choose appropriate values instead of copying numbers
from an unrelated person's shot.

Prepare through the chosen Studio origin or standalone store. Save the returned
source/session/revision/version and resolved recipe. Render representative
moving comparisons; the proxy is deliberately smaller than the final. Review
people/neutrals, highlights/shadows, gradients, recorded text and shot changes.
Use the exact source seconds for a UI/desktop interlude rather than guessing
boundaries or deleting it. Explicit hard neutral shots/protected rectangles can
preserve recorded content but are not semantic tracking.

After actual feedback, save a new immutable candidate and render fresh evidence.
Do not replace an older export. The source, recipe, range/target, processor/LUT
and actual reviewed previews must agree with the approval used for final export.
Follow the core skill; never convert an old delegated instruction into new
user aesthetic consent or suppress a color-management blocker.

## Verify and hand off

Check the **final**, not just the proxy: native displayed geometry, full/ranged
duration, decoded clock verification, original audio verification, declared
output color, recipe/processor/source hashes and actual visual transitions.
Engine checks do not prove calibrated native-resolution banding, full perceptual
watching, direct listening, exact filmmaker emulation or human acceptance.

Deliver the actual `graded.mp4`/`graded.mkv` and metadata path from the completed
job. Preserve input and previous editions, and record any remaining review
limits. Do not add a thumbnail/gallery, new music, platform conversion or upload
merely because a portrait file could be posted.

Resume feedback from its saved exact session. Re-read the current version after
every completed job/approval; stale writes, changed source/processor, missing
preview evidence and incompatible output need explicit reconciliation, not
changed hashes, a second encoder or an invented successful export.
