# Landscape A/B review: two synchronized complete pictures

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Tools and preflight

Follow [the shared grading procedure](../_shared/GRADING-WORKFLOW.md) and
[the core skill](../clipfarm-color-grading/SKILL.md). Use the same typed recipe,
float RGB/65-cube LUT engine and current Studio worker as the eventual final,
not a second FFmpeg filter chain or JavaScript/CSS look.

No transcript, title art, subtitles or source segmentation is required.
New inputs must have permitted local use and supported SDR/color/track evidence.
Use an existing exact session when reviewing an iteration; do not import the
same recording again or silently change its range/target.

Each source is normalized for display rotation/sample aspect, then reduced
aspect-correctly to a source proxy edge of at most 720px. Original and graded
halves use matched source instants and are horizontally stacked. It is a
landscape output only when `2 * proxy_width > proxy_height`. Read actual
encoded dimensions after rendering; rounding affects the near-square boundary.
An extremely tall source can instead produce portrait A/B. Do not call that
this evidenced landscape format or crop/retime it to manufacture compliance.

## Prepare one saved candidate

For a new source create a real grading session with a clear brief and supported
color interpretation. [The native portrait recipe](../clipfarm-native-grade-portrait/recipe.example.json)
is a typed illustrative starting point. For an existing candidate:

```powershell
Set-Location -LiteralPath 'D:\Work\ClipFarm' # Replace with the actual checkout.
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 status --session SESSION_ID
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 recipe --session SESSION_ID
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 preview --session SESSION_ID --version CURRENT_VERSION --start SOURCE_SECONDS --duration 6
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 files --session SESSION_ID --job COMPLETED_PREVIEW_ID
```

Replace placeholders. Every completed preview advances saved session state;
re-read its version before another write. The
[preview example](preview.example.json) is a real `GradeJobRequest` shape for
`POST /api/grading/sessions/SESSION_ID/jobs`, but its all-zero revision ID and
version 0 are **unusable placeholders**, not an existing approved candidate.
Use the CLI to resolve these from the current real session when possible.

Select useful dark/bright/skin/neutral/gradient windows and hard-shot/protected
content boundaries. Maximum 30 seconds is a per-preview limit, not a cap on input
length or a reason to alter narration. Several previews may be needed. The
historical two windows are not appropriate for arbitrary footage.

## Inspect, record and stop at the right boundary

Open the completed job's actual `comparison.mp4`: **left ungraded, right graded**.
Both views must show the same action at the same source instant, with preserved
aspect, no stretching/cropped evidence, and no fabricated moving content.
Check the metadata's source window and relative frame-clock verification.
Preview audio handling is separate from the final engine's original-packet
preservation check; merely playing a proxy does not establish that final check.

Inspect actual motion or multiple decoded transition frames with their limits
stated. Check clipping, skin/neutrals, shadow/highlight detail, hue stability,
banding, recorded UI/text and shot/mask discontinuities. Open matched PNGs and
scopes too; their reduced samples and sRGB display conversion do not constitute
calibrated native-resolution review. A file hash establishes identity, not
whether the color looks good.

Retain `comparison.mp4`, `graded.mp4`, `source-frame.png`, `graded-frame.png`,
`scopes.png` and `metadata.json` with source/session/revision/recipe/processor/LUT
identity. Use manifest paths/loopback URLs, not guessed export-folder suffixes.
If downloading, retain/verify the expected file hash.

This skill finishes with **unapproved review evidence**. There is no reason to
call `approve` or `export`, create a posting gallery, relabel the proxy a master,
or upload it. If actual feedback requests another look, make an immutable new
revision and new comparison. If a final is subsequently authorized, use the core
grading skill's exact-candidate gate and source-preserving export, not hstack
as the final movie.

On stale state reload/reconcile; on missing/tampered evidence regenerate only
the affected owned review after fixing the cause. Preserve older candidates.
On a format/color/runtime error report it explicitly. Do not create another
worker, bypass source interpretation, delete old files or invent user approval.
