# Existing source-video CLI: a reproducible procedure

This guide covers the actual `clipfarm.workflow` implementation, not the
request-local animation/audio/music-film producers. Read `PRODUCTION.md` and the
chosen format runbook first. The Python stages are deterministic; the editor
performs semantic selection and real output review.

## 1. Prepare exactly once

```powershell
$python = (Resolve-Path '.venv\Scripts\python.exe').Path
$request = '2026-11-10T02:01:12.239+05:30' # EXAMPLE; use the NEW creation prompt.
$video = 'D:\Footage\[LeetCode] coding-stream.mp4'
& $python -m clipfarm workflow prepare --video $video --workflow leetcode --format vertical --session-timestamp $request
```

LeetCode still requires `[LeetCode]` or `[ LeetCode ]` in the filename, even with
explicit `--workflow leetcode`. If an original is untagged, preserve it and make
a byte-identical tagged copy in the new private run area, verifying both hashes
and recording the original/copy relationship; do not rename the original or
mislabel unrelated content as LeetCode. Tagged filenames also auto-route.
For System Design use `--workflow system-design` with its original filename;
that explicit route is vertical only and does not require the LeetCode tag.
For native complete solves use `--workflow leetcode --format horizontal`.
An optional supplied transcript uses `--transcript`; otherwise local granular
TXT/JSON are generated with the small model. `--language en` is appropriate only
when the source language is actually English.

Save the printed absolute `plan.json` path. Preparation starts with no selected
cuts, `reviewed_entire_transcript: false` and no approval. If transcription was
interrupted, resume its printed `--run-id` with the original options. Once a plan
exists, edit/resume that plan instead of preparing again.

## 2. Read and inspect the entire source

Read `source-transcript.txt`, `source-cues.json` and any supplied transcript.
Record all problems/topics, omissions, errors and meaningful silence.

```powershell
$plan = 'D:\Work\ClipFarm\.clipfarm\workflow-runs\NEW-RUN\plan.json'
& $python -m clipfarm workflow inspect --plan $plan --start 0 --end 600 --step 60
```

Repeat bounded ranges through the actual duration. Refine selected scenes and
BRB/crop changes; 60s reconnaissance is not frame-exhaustive privacy review.
Choose explicit normalized source regions after display rotation. Inspect pixels,
not just OCR. Update the prepared profile/cuts without replacing source hashes,
delivery binding or unrelated cuts.

## 3. Author the chosen format

Use the folder's `profile.example.json` and `cut.example.json` as **illustrative
schema examples**, not reviewed selections. They are partial documents to merge
into the prepared plan; never feed them directly to `--plan`.

Replace every time, crop, problem title, rationale, evidence path and statement
with actual source-grounded content. Keep vertical `show_question_title: true`.
Camera absence is explicit, not inferred from face-detector failure.

Set `reviewed_entire_transcript: true` and substantive `editorial_notes` only
after the full reading. Give each cut a concrete takeaway and real
`coherence_review`. `source_cues`, if needed, use absolute source seconds and
replace only that cut's captions; preserve uncertain phrases explicitly.

Example geometry is not portable to another recording. Different source scenes
need per-segment overrides. Useful silent coding/results must survive trimming.

## 4. Validate, render, independently transcribe

```powershell
$cut = 'NEW-CUT-ID'
& $python -m clipfarm workflow validate --plan $plan
& $python -m clipfarm workflow draft --plan $plan --cut $cut
& $python -m clipfarm workflow review-transcribe --plan $plan --cut $cut --model small --language en
```

Use the real language or omit the hint. A failure is not a reason to clear
validation or stamp review flags. Drafts are immutable under
`drafts\<cut-id>\<signature-prefix>`. `latest.json` identifies the current one.
`review-transcribe` produces `review-asr.txt`, `review-asr.json` and an initially
pending `review.json`; an existing review is not silently replaced.

Read every output-ASR line and mapped caption. Inspect actual encoded headings,
content, camera, joins, runtime evidence, correction notes, cover and ending.
Compare source and output, not merely the planned timing.

Vertical default delivery is 1080x1920/30fps H.264/yuv420p with AAC48k when
audio exists; maximum 180s. Horizontal uses normalized native landscape size,
30fps, and no short-duration cap. This CLI is not a same-FPS lossless archival
transcoder or a grading workflow.

## 5. Approve only the exact reviewed candidate

Complete the generated `review.json`, retaining its video/transcript/thumbnail/
music hashes. Identify the actual reviewer (for example Copilot), give substantive
notes and limitations, and set only checks actually completed. Use
`clipfarm.workflow.review_checks(plan, cut)` when inspecting required checks;
do not make up review keys or bulk-set flags from encoder success.

Shared base checks cover coherence, useful content, captions, visuals and BRB.
Persistent headings add `question_title_reviewed`; submission adds actual
submission/runtime/result-zoom checks; corrections add correction review.
Horizontal and stylized finishing have their own extra gates.

If anything changes, render and review the new signature. A stale ASR or review
cannot approve changed media.

## 6. Deliver locally and finish the card

```powershell
& $python -m clipfarm workflow publish --plan $plan --cut $cut
```

`publish` verifies exact artifacts, independent ASR and substantive approval;
copies to private `final`, then to the original-request session under `results`.
The single accumulating gallery retains earlier source clips.

Follow `PRODUCTION.md` for current separate posting fields/credits, cover review,
music recommendation policy, exact-folder navigation and genuine browser copying.
Legacy `PostingRecord`/gallery helpers do not automatically satisfy every later
separate-field authoring requirement. Do not falsely claim they do.

Repeated publish reuses identical approved media; it never re-encodes it or
grants user/platform approval. Conflicting finals need a preserved new edition.
