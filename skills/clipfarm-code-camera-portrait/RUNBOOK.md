# Camera above code: 9:16 source-video reel

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Inputs and preparation

Supply a local video; an optional timed transcript is supported. Use the actual
camera region, including a drawn/avatar camera rather than face detection.
Record problem titles, available teaching, source rights and privacy exclusions.
Read the shared production and source-workflow guides.

```powershell
& $python -m clipfarm workflow prepare --video $video --workflow leetcode --format vertical --session-timestamp $request
```

The LeetCode route still requires a tagged filename. For an untagged source,
keep the original and create a hash-verified byte-identical private tagged copy,
as described in the shared guide. Preparation does not select clips or infer
correct crops. Read all generated cues; inspect source frames and changes of
editor/browser layout.

## Composition

`profile.example.json` describes the fields, not another video's coordinates.
All regions are normalized to the source **after display rotation**.

| Output layer | Question-enabled target |
|---|---|
| Heading | Actual problem name, genuine plain Consolas, above y=0.134 |
| Camera | Aspect-contained, roughly x=0.10/y=0.16/w=0.80/h=0.20 |
| Code | Aspect-contained, x=0.025/y=0.39/w=0.95/h=0.35 |
| Captions | White boxed bursts near y=0.82 |
| Backdrop | Blurred source, not the animated-explainer grid |

These are renderer placements, not a crop prescription. Set `face_region` to
the complete reviewed source camera; `code_region` must exclude irrelevant
problem text, browser chrome, chat and testcase clutter. Use per-segment
`face_region`/`content_region` overrides when the source changes.

Keep `show_question_title: true`. `cut.problem` supplies the actual question;
`question_title` can explicitly override it. The clip's `title` is a specific
takeaway, not a replacement for the question.

## Editing and actual results

Choose a useful scoped explanation, faithful solve/debug story, real submission
or genuine setup/payoff. Keep all solved problems in the coverage ledger.
Current coverage-first ceilings replace automatic A/B/A+B expansion.

For result focus, inspect a distinct results crop. Split the timeline into code
and `view: "results"` passages. A `submission` cut needs source-frame evidence
for Submit and the actual Accepted/runtime panel, with actual milliseconds.
Testcase runtime is not submission runtime.

The renderer scales the entire results ROI from 68% to full size with eased
motion and dims the surrounding backdrop up to 70%, keeping camera, headings
and captions bright. Start during genuine loading where useful, so a full-size
Accepted panel does not jump smaller before its zoom. Review early/middle/end
zoom and adjoining crop transitions, not only a still.

Useful silent work is not automatically dead air. Disable cut silence trimming
where necessary. Corrections, when authorized, retain the spoken mistake and
use a separate referenced editor note; do not falsify subtitles.

## Render, review, deliver

Follow `SOURCE-WORKFLOW.md` for exact stages and pending-review handling.
Required checks include the persistent heading; submission/correction/music
checks apply only when those features are present. Read the actual independent
output transcript and every mapped caption. Inspect code legibility, privacy,
camera aspect, all joins and actual completion.

Cover: complete problem name, separator, specific topic, separator, retained
camera shot. Use plain Consolas, cream text, IndianRed separators, a single
thin blue-grey `#45616a` camera border/shadow, and frosted same-camera backdrop
with restrained deterministic grain on the backdrop only. Essential content
must survive the centered 3:4 crop. Do not use the code panel as cover camera art.

Music is recommendation-only unless the new request explicitly opts into
embedding. `..\_shared\MUSIC-FINISHING.md` documents the separately implemented
finishing path; it does not change this composition or certify trends.

## Tools and recovery

- `clipfarm.workflow_models.WorkflowProfile`, `WorkflowCut`: typed edit data.
- `clipfarm.workflow.compile_segments`, `draft_cut`, `transcribe_draft`, `publish`:
  actual stage owners; use the documented CLI for normal operation.
- `clipfarm.media._filter_graph`: current camera/code/result composition.
- `clipfarm.montage.render_montage`: frame/source maps and PCM/AAC assembly.
- `clipfarm.thumbnails`, `question_titles`: source-bound art and headings.

If a crop is wrong, preserve the draft, fix only affected edit data, make a new
signature and review it. Never replace the source transcript wholesale to make
a subtitle appear correct. Missing actual teaching/results is an editorial
blocker, not something an encoder or skill can manufacture.
