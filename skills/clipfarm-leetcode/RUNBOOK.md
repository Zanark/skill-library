# Core editorial workflow

Read [SKILL.md](SKILL.md), the checkout's contributor contract and the
[shared source-video procedure](../_shared/SOURCE-WORKFLOW.md). The skill entry
is normative; this runbook is an operator map, not an automatic semantic editor.

## Route and inputs

Use the complete permitted source recording and original request timestamp.
The transcript is optional: preparation generates local granular TXT/JSON.
LeetCode routing requires the actual filename tag; explicit System Design uses
its own route and preserves the source filename. Horizontal means an explicitly
requested complete solve, not a crop of a vertical topic clip.

- Default vertical LeetCode: useful source-grounded topic, debug, submission or
  genuine-humor clips, with explicit camera declaration and verified regions.
- Explicit vertical System Design: design-topic coverage, relevant diagrams/
  slides/code and a question-only heading, without invented submissions.
- Explicit horizontal LeetCode: one chronological complete solve per problem,
  native layout, bottom quiet caption areas and matching numbered cover/intro.

Preserve the complete transcript meaning and solved-problem coverage. Ceilings
are not quotas. A scoped explanation is not a complete solution; a testcase
runtime is not a submission runtime.

## Prepare, inspect and author

From the current ClipFarm checkout and declared environment:

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm workflow --help
& '.\.venv\Scripts\python.exe' -m clipfarm workflow prepare --video 'D:\Footage\[LeetCode] stream.mp4' --session-timestamp 'ORIGINAL_TIMEZONE_AWARE_REQUEST'
```

Replace placeholders with actual values. Save the returned absolute plan path.
Read every cue and inspect actual frames through the complete source. Record
topics, BRB, meaningful silent work, private content, camera/content changes,
actual results and uncertainties before selecting clips.

Populate the prepared plan using actual times/crops and the applicable
format-specific examples. Preserve source hashes, session binding, title
visibility, immutable snapshot rules and unrelated cuts. Do not execute an
example as an approved plan or prepare over a completed preparation.

## Render and review

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm workflow validate --plan 'ACTUAL_PLAN'
& '.\.venv\Scripts\python.exe' -m clipfarm workflow draft --plan 'ACTUAL_PLAN' --cut ACTUAL_CUT
& '.\.venv\Scripts\python.exe' -m clipfarm workflow review-transcribe --plan 'ACTUAL_PLAN' --cut ACTUAL_CUT
```

Read all fresh output recognition and mapped captions. Inspect actual encoded
text, camera, useful code/diagrams, every join, results motion, corrections,
full/center-safe cover and completion. A saved screenshot, metric or encoder
exit does not supply semantic review or the user's approval.

Record only completed applicable checks in the generated review, bound to the
exact candidate. Changed media requires a new signature/review. See
[shared production rules](../_shared/PRODUCTION.md) for posting fields, source
clocks, rights and current gallery handling; follow the source contract's
workflow-specific gates rather than importing a different mode's shortcut.

## Deliver and recover

Use `workflow publish --plan ACTUAL_PLAN --cut ACTUAL_CUT` only after real
review. It delivers approved local files into the original request's one
accumulating timestamped gallery, not to a social platform.

Retain source, plan, immutable drafts, evidence and exact folder names. On
failure preserve the actual log and resumable IDs; never remove a shared lock,
invent a missing source fact, replay a frozen producer or overwrite a different
final. Keep technical, editorial, user, listening and public-rights approvals
separate.
