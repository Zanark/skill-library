---
name: clipfarm-color-grading
description: Color grade a local SDR video through ClipFarm's shared engine. Create editable looks, inspect real A/B comparisons, preserve immutable feedback iterations and export only after explicit user approval. Supports new footage or an exact existing grading session; no embedded AI server, cloud upload or automatic consent.
---

# ClipFarm color grading

Use the real local grading engine, not a parallel FFmpeg grading implementation
or a list of hypothetical settings. The checkout is `__CLIPFARM_ROOT__`.
Read its `docs\COLOR-GRADING.md` and the command help before starting.
Use `__CLIPFARM_ROOT__\.venv\Scripts\python.exe`; set the working directory to
the checkout in **each** shell call. This is a separate workflow from clipping,
subtitling, music, animation and publishing.

## Authority and boundaries

- Keep all media and raw evidence local. No upload, paid provider, credential,
  model download, automatic schedule, account change or platform publication.
- The caller's brief and rights-cleared references guide authored numeric
  parameters. Do not copy a proprietary LUT, claim an exact film-stock/filmmaker
  emulation, or promise Hollywood quality from a preset or numeric test.
- User autonomy such as "do the needful", silence, successful encoding and the
  agent's visual preference are **not approval**. Never call `approve` on the
  user's behalf without explicit approval of the exact reviewed candidate.
- Preserve the source and older editions. Do not grade delivered collections,
  overwrite another session, invent feedback, or change clip defaults.
- SDR-first only. Known HDR/PQ/HLG, declared camera-log, transparency and
  interlaced workflows are rejected. Unknown log encoding cannot be detected
  reliably from appearance. Stop on unsupported/conflicting evidence; never
  force an SDR override to make an unsupported source pass.
- Inspect actual images using available image-reading tools. Inspect moving
  transitions through actual playback when available, or multiple decoded
  frames with their limitations stated. Do not call a contact sheet full
  playback, claim listening without audio access, or claim calibrated monitoring.

## Choose the existing worker

If Studio is running, use its supplied loopback origin with `--studio` on every
command. Do not start a second worker or silently fall back after an HTTP write
failure. The UI's **Copy exact-session skill prompt** supplies the origin,
session, source and observed version. Re-read state; that observed version can
already be stale.

Without Studio, use one explicit `--data-dir` consistently. Standalone commands
own the normal data lock and single media worker, wait for their own jobs and
cancel their owned work on Ctrl+C. A lock conflict means use the existing Studio,
not another encoder pointed at the same database.

```powershell
Set-Location -LiteralPath '__CLIPFARM_ROOT__'
& '.\.venv\Scripts\python.exe' -m clipfarm grading --help
& '.\.venv\Scripts\python.exe' -m clipfarm grading presets
& '.\.venv\Scripts\python.exe' -m clipfarm grading inspect --video 'C:\Videos\source.mp4'
```

In live Studio mode inspect `--project PROJECT_ID`, not `--video`. The engine
needs no transcript and does not impose the vertical clip's duration/layout/FPS.

## Brief and source

1. Establish source/session, intended range and output, the actual desired look,
   preservation constraints and any supplied reference's recorded rights basis.
   Record important assumptions and actual feedback in the saved brief/notes.
   If a reference is used, record its local identity/hash and actual permission
   statement; it is a visual reference, not an engine asset or uploaded input.
2. Read actual color metadata. Use automatic interpretation only with supported,
   complete declarations. An explicit Rec.709/sRGB/BT.601 interpretation requires
   a genuinely known encoding, not a resolution-based or visual guess.
3. Use a sensible SDR/browser MP4 starting target unless the request/source
   requires the supported 10bit4:4:4 MKV target. Do not silently drop unsupported
   audio to make MP4 work. Keep professional mastering/HDR qualification separate.
4. For a known source and sufficiently clear brief, start without unnecessary
   preference questions. Ask only for a material unresolved source/intent issue.
   Missing tools, unsafe interpretation or denied access is a blocker.

Prepare a new session using **exactly one** of `--video` / `--project`.
Use an existing session for feedback/resumption instead of repeated imports.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 prepare --project PROJECT_ID --mode ai-assisted --brief 'ACTUAL BRIEF' --preset cinematic
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 status --session SESSION_ID
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 recipe --session SESSION_ID
```

These are templates; replace identifiers with returned IDs. Do not execute
placeholders. Preserve returned session/version/revision IDs and file manifests.

## Author, render, inspect, iterate

1. Read the current recipe and catalogue. Start with one of 26 original looks
   when appropriate, or neutral/custom parameters. Presets are editable numeric
   starting points, not the only permitted briefs. Keep source corrections
   separate from look parameters/intensity.
2. Save typed recipe JSON in the private working area. Numeric bounds, monotone
   curves, source-time shots and normalized protected rectangles are validated
   by the shared engine. No arbitrary filter scripts, automatic segmentation,
   tracked masks or interpolated keyframes are supplied by this release.
3. Submit an immutable revision with the current optimistic version and an
   honest actual-feedback/change note. Never silently retry a conflicting write
   or lose another client's edits; reload and reconcile.
4. Render representative moving previews: faces/neutrals, dark/bright passages,
   gradients, recorded text/graphics and relevant shot transitions. One average
   frame is insufficient. Use exact source ranges, not random stills.
5. Inspect the actual comparison, source/graded sample PNGs and scopes. Inspect
   downloaded local artifacts and their recorded identity; a manifest alone is
   not a visual review. Use additional local decoded frames when useful, never
   a different grading pipeline. Check clipping, hue/skin stability, shadow
   separation, banding, protected content and temporal discontinuities.
6. Present the actual candidate paths/links and plain-language changes/limits.
   Collect **real** feedback; save the next revision and repeat. If feedback or
   approval is pending, stop safely with exact resumable IDs, not unattended
   iteration, an invented "looks good" or arbitrary autoaccept after N attempts.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 revise --session SESSION_ID --version CURRENT_VERSION --recipe 'C:\Private\candidate.json' --note 'ACTUAL FEEDBACK AND CHANGE'
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 preview --session SESSION_ID --version CURRENT_VERSION --start SOURCE_SECONDS --duration 6
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 files --session SESSION_ID --job COMPLETED_PREVIEW_ID
```

Use the returned version after every completed preview/revision/approval/export,
not the earlier value. To restore an older recipe use `revise --based-on
REVISION_ID` with a real note. The new revision is unapproved, even when its
parameters match an older approved recipe.

## Explicit approval and delivery

Only after the user actually approves a clearly identified reviewed candidate:

1. Re-read its session/current revision. Confirm the user's scope and selected
   real preview IDs. If the recipe, source, range, output, processor or evidence
   changed, obtain a fresh comparison/approval; do not reinterpret old consent.
2. Record the user's actual approval wording and exact reviewed preview IDs
   using `approve --version CURRENT_VERSION --preview PREVIEW_ID
   --confirmation approve-reviewed-look --note 'ACTUAL APPROVAL'`.
3. Export that approved current revision through `export --session SESSION_ID
   --version CURRENT_VERSION`. Do not add a competing renderer, strip audio,
   reduce quality silently or reinterpret an encoding failure as completion.
4. Inspect the delivered edition and its metadata. Technical verification,
   sampled-look approval, full-film visual review, final-file acceptance,
   calibrated/colorist qualification and publication clearance are separate.
5. Deliver actual final paths/links and concise limitations. Keep the saved
   history and provenance. No automatic upload or claim of real user approval
   from synthetic tests.

The engine binds approval to source, recipe, processor, regenerated LUTs and
reviewed artifacts. Do not weaken those checks. Relative white balance and
skin-hue protection are approximations, not RAW Kelvin calibration or semantic
skin detection. Lossy encoding and display management remain real limitations.
