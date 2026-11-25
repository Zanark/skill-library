# Core SDR grading workflow

Read [SKILL.md](SKILL.md) and the [shared real-engine grading procedure](../_shared/GRADING-WORKFLOW.md).
Use a current grading-capable ClipFarm checkout and its actual command help.
These are real engine operations, not a second filter renderer or a preset
that certifies professional artistic quality.

## Preflight and ownership

Confirm the supported SDR source, intended range/output, actual look brief and
any reference's permission basis. Inspect declared color, geometry, timing and
audio rather than guessing Rec.709 from appearance/resolution.

Known unsupported HDR/log/alpha/interlace or conflicting metadata is a blocker,
not permission to force SDR. Unknown log encoding cannot be reliably detected
by appearance alone.

If Studio supplies an origin/session, keep `--studio ORIGIN` on every command.
Otherwise use one explicit `--data-dir` and the normal owned worker. A lock
conflict is not permission to start a second worker or delete a lock. Existing
sessions resume by their real identifiers; do not repeatedly reimport them.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --help
& '.\.venv\Scripts\python.exe' -m clipfarm grading presets
& '.\.venv\Scripts\python.exe' -m clipfarm grading inspect --video 'C:\Videos\source.mp4'
```

## Author and inspect

Prepare exactly one new source/project or resume the selected session. Read the
saved recipe/catalogue, author bounded numeric corrections/look parameters and
keep source interpretation separate from creative intensity.

Revise with the current optimistic version and an actual change/feedback note.
Render representative moving previews covering people/neutrals, gradients,
dark/bright material, protected graphics and scene boundaries.

Inspect the real source/graded pictures, moving A/B, scopes and recorded source
ranges. Returned file metadata is not image review. Preserve source/recipe/
processor/LUT/preview identity and disclose sampled/uncalibrated limits.

Do not fabricate feedback or iterate unattended until a preset is declared
accepted. Use returned versions after jobs, not an earlier cached value.
Restoring an old recipe creates an unapproved revision.

## Exact approval and export

Only the user's explicit approval of the identified reviewed candidate supplies
the aesthetic gate. Re-read state and bind the actual wording and selected
preview IDs with the engine's approval command. Changed source, recipe,
processor, range or target requires fresh evidence/approval.

Export the approved current revision through the same shared engine. Inspect
actual output identity, geometry/timing/audio and limits; retain earlier
editions. A review-only A/B file is not a second approved final.

Neither silence, broad autonomy, numeric tests nor encoder success authorizes
`approve`. There is no automatic upload, reference download, extra narration,
crop/caption insertion or calibrated-mastering claim.

## Failure and continuation

Reload/reconcile version conflicts rather than blindly retrying writes.
Unsupported sources/codecs and missing/tampered evidence remain explicit
failures, not silent audio removal or alternate-pipeline success.

Preserve session/revision/job IDs and exact logs. Cancel only owned work.
Do not change a running user's application, overwrite old grades or restore
another database to continue the session.
