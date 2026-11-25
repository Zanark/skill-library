---
name: clipfarm-code-camera-portrait
description: Create reviewed 9:16 coding clips with the actual camera/avatar above relevant code, lower subtitles and optional verified submission zoom. Use for camera-present LeetCode explanation, debugging, submission or humor reels, not animated redraws or complete landscape solves.
---

# Coding recording: camera + code, portrait

Repository: `__CLIPFARM_ROOT__`.
For a repository-local entry, resolve that marker to the checkout containing
this `skills` directory. Do not treat the invoking directory as the repository.

Read these files before production:

- `__CLIPFARM_ROOT__\skills\_shared\PRODUCTION.md`
- `__CLIPFARM_ROOT__\skills\_shared\SOURCE-WORKFLOW.md`
- `__CLIPFARM_ROOT__\skills\clipfarm-code-camera-portrait\RUNBOOK.md`

Use the existing `workflow prepare/inspect/validate/draft/review-transcribe/publish`
commands, with `--workflow leetcode --format vertical`. Generate local transcripts
when absent. Understand the full source before selecting cuts.

Output is 1080x1920/30fps. Keep the actual camera crop above code, the real
problem heading above both and spoken captions below. Source camera and speech
share the same time map. Only actual submissions get runtime claims and the
slow results zoom; do not infer them from testcase runs.

Use the adjacent example JSON only as source-specific profile/cut scaffolding.
Never reuse illustrative crops, times or approvals. For a camera-free source,
route to `clipfarm-code-only-portrait` instead of fabricating a face.

Inspect actual output, fresh output-ASR, every join, zoom and full/3:4 cover.
Deliver one accumulating gallery for the creation prompt. No default music,
uploads, historical-gallery restoration or blanket approval.
