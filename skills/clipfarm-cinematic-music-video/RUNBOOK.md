# Full-length cinematic music video: full media review

## What this skill does

Turn a new permitted local song and lyrics into one continuous original story,
then review the complete lyric/story timeline and actual encoded result. This
is a deliberate editor/agent procedure, not a prebuilt arbitrary-song renderer.
Read [the common cinematic contract](../_shared/CINEMATIC-MUSIC.md) first.

The full route must not inherit the sampled-only review of a prior production.
It also does not promise perfect singing recognition, human hearing or creative
approval. Complete, evidence-based inspection and exact uncertainty reporting
are the contract. Do not start a new video when only skill installation is asked.

## 1. Bind the new request and preserve every source sample

Record the original request time, explicit mode `full-review`, source/lyrics/
art/font hashes, actual full decoded samples, rate/channels and source mtime.
Read all words/sections, including repeated choruses and instrumental passages.
Confirm whether a storyboard-first checkpoint was requested; otherwise continue
autonomously through the complete workflow without adding an approval stop.

Use the complete original recording, not its title's suggested duration.
Create a new private run with input, story/shot/action timeline, lyric-occurrence
ledger, producer, design captures, sealed inputs, candidate and review evidence.
Resolve all assets from those inputs. Never execute an old one-shot producer.

## 2. Establish actual lyric occurrences and timing

Use the existing local faster-whisper path with the real language and word
timestamps. Keep source recognition independent: do not feed it the supplied
lyrics as a prompt and then treat its repetition as independent confirmation.
Read every source segment/word, not only the first recognised chorus.

For each supplied/sung occurrence record:

| Field | Required meaning |
|---|---|
| `id` | Unique occurrence identity, even when text repeats |
| `supplied_text` / `display_text` | Preserve source wording and explain any grounded correction |
| `start` / `end` | Source-clock seconds, not proportional lyric-sheet spacing |
| `source_evidence` | Actual recognised excerpt/word bounds and supporting local timing evidence |
| `timing_basis` | For example reviewed model estimate, supplied verified timing, or unresolved |
| `disposition` | Present, recording variation, instrumental, mismatch or unresolved; never silently omitted |

Reconcile omissions, extra repeats, actual order and long instrumental gaps.
Do not silently replace supplied words with a singing hallucination. Preserve
the original song and record genuine recording/lyric differences. Technical
corrections belong in a separately labelled visual note, not invented singing.

ASR-supported phrase boundaries that are consistent with the source evidence
and inspected output may be labelled **reviewed estimates**, not phonetic
verification. A missing, contradictory or merely word-count-spaced alignment
is unresolved and blocks fully reviewed delivery. Try a bounded targeted local
recognition/timing refinement where useful; do not loop until a model echoes
the desired lyrics. If reliable evidence is unavailable, retain a review
candidate and state the exact limitation.

## 3. Write a complete narrative and action ledger

Create a coherent beginning, growing difficulty, choices/consequences and payoff.
Define original/permitted characters with consistent silhouettes, proportions,
props and expressive movement. Map every song section to purposeful shots and
visible actions; recurring choruses must advance the story, not reset it.

Use a source-time scene/action ledger with stable object IDs and initial,
intermediate and outcome states. Resolve pointing, moving, carrying, looking,
turning and contacts. If a technical concept is illustrated, validate its
actual trace and assumptions, not a vaguely related final diagram.

Plan camera endpoints, spatial continuity, material/light intent, lyric band,
separate correction space and title/cover hierarchy. Share the saved cover-
derived background base with the thumbnail; do not import unrelated layouts.
The story may express a section's meaning without literal word-by-word images.

## 4. Author and inspect native designs

Build a new deterministic compositor: state at source time, not integration
from the previous rendered frame. Use existing Python/raster or browser/WebGL
tools as appropriate; install no unrelated renderer automatically.

Inspect every scene's opening, intermediate and ending composition and the
important action states. Check complete actor/prop extents, correct facing/
ownership, feet/hand contacts, actual faces/number surfaces and occlusion.
Bounds/motion percentages do not substitute for actual returned image pixels.

Use the optional [source-clock lyric reference](../_shared/cinematic-lyric-window.js)
or an equally explicit implementation. Cache static text/layout separately;
draw lyric-window progress on every frame. Verify repeated identical text gets
a new occurrence ID/reset, gaps clear the window, and seeking gives the same
state. The helper's elapsed phrase fraction is not word-level karaoke.

Inspect full1080x1920 cover and exact centered3:4crop. Repair encountered issues,
retain earlier studies and seal exact renderer/timeline/lyric/asset/helper hashes.
Native design clearance is not approval of the not-yet-encoded movie.

## 5. Encode the entire new full-quality edition

Default to1080x1920/30fps and the qualified production quality. The observed
native path used4xMSAA and libx264medium/CRF17, not a universal GPU requirement.
Do not reduce quality because a previous draft used a proxy.

Use one owned bounded encoder and source time `i/fps`; cover the complete
audio duration with the ceiling frame count. Stream raw pixels directly if
using WebGL; do not route the bulk through Playwright/DevTools. Mux original
full audio using the explicitly recorded packet/PCM policy, with no added
intro hold, fade, silence, replacement soundtrack or hidden `-shortest` trim.

Freeze inputs throughout encoding. An edit creates a new immutable candidate
and invalidates affected review; it does not rewrite a delivered movie.

## 6. Review the actual encoded movie, not only its source program

Decode the complete output and verify every video PTS/frame, dimensions/rate,
stream geometry, audio coverage and beginning/ending. Compare decoded audio
with expected original samples/clock and representative signal windows;
handle real zero silence explicitly instead of undefined correlation. Record
codec padding rather than trimming the song to make counts look equal.

Run fresh independent recognition on the rendered audio and read all segments.
Compare source/output recognition and the entire occurrence ledger. A raw old
ASR file is not fresh output evidence; exact justified reuse must be labelled
inherited and cannot stand in for this route's required independent pass.

Build an encoded review manifest covering:

1. Every scene's beginning/middle/end and every important causal action.
2. Both sides of every camera/scene join plus useful in-motion states.
3. Every lyric occurrence's first visible, middle and last visible frames,
   plus the nearest before/after boundary, repetition reset and instrumental
   gaps. Deduplicate frame files without dropping any occurrence's coverage.
4. The complete lyric text/line wrapping/contrast and separation from action,
   title and any correction, including dense/long lines.
5. Native/encoded colour and motion comparisons at representative states,
   actual full/center cover and opening/completion.

For a cue starting between frames, use the actual first frame at/after start;
do not expect its progress to be exactly0. The final visible frame may be below
100% and the next cue resets. Inspect the decoded progress area at multiple
times within the SAME occurrence: a midpoint screenshot alone cannot detect
a frozen bar. Do not approve a simulated native bar instead of the encoded one.

Also inspect whichever lyric-window behaviours the new design actually uses:
active/current-next lines, scrolling, phrase fill, supported word highlighting
and overall song progress. Distinguish the full-song clock from the current
cue's clock; a changing global bar does not prove that the active lyric or
its local progress is correct. Do not add word karaoke without grounded times.

Actually open/read every review sheet/crop and record image/time/occurrence
coverage. A capture tool that returns no pixels is not an inspection. Record
disagreements, fix them in a new candidate and recheck affected states/joins.
Full decode/PTS is mechanical coverage, not a claim that every pixel was viewed
or that the agent listened to the track.

## 7. Gate local delivery and preserve separate approvals

The review record binds the exact movie/input hashes and records:

- All scene/action/join and lyric-occurrence reviews with actual image evidence.
- Source/output recognition reconciliation and timing basis for every occurrence.
- Text/progress/reset/gap checks, unresolved items and full audio/PTS results.
- Full/center cover inspection and separate user/listening/rights status.
- `gallery_ui_qa: not-run-per-current-preference` unless specifically requested.

No unresolved essential lyric/timing/progress/visual/audio conflict may be hidden
behind `review_complete:true`. If blocked, deliver an accurately labelled review
candidate with the failed gate, not a draft silently promoted to full clearance.
Inherent model-estimate precision must remain visible even after full review.

After substantive review, atomically deliver a new full-quality versioned bundle
and the one request's index. Include movie, cover, storyboard, lyric SRT/timing
basis, source map, evidence summary and separate posting fields using the common
helpers. Generate the index directly; do not restore gallery desktop/phone/
browser playback/copy/layout tests unless asked.

State actual duration, local paths and material remaining limits. Keep human
creative acceptance and upload clearance false/unrecorded until explicit evidence.
Creating this skill does not approve old films or start/finish the shared engine.

## Recovery and draft promotion

On any failure retain exact inputs, stage/log, partial candidate and evidence.
Resume only that new run's verified stage. Do not replay a historical publisher,
overwrite an approved edition or kill a shared process.

To develop an early draft, reuse its source-bound story/assets and valid
observations only. Create a NEW full-quality edition, convert any draft
frame-index actions through source seconds to the new fps, establish/review
all lyric timing and run this entire full procedure. A proxy cannot become a
fully reviewed final through renaming, upscaling or copying its review flags.
