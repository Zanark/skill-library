# Full-frame Fit portrait: reproducible Studio procedure

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Tools, inputs and ownership

- Use the actual checkout's `.venv\Scripts\python.exe`, installed core packages,
  bundled FFmpeg and existing FastAPI/SQLite Studio.
- Input is a permitted local video and a meaningful 1..180-second range within
  it. The source recording itself can be longer. Keep its original bytes intact.
- A transcript is optional. Import SRT/VTT/timed TXT/JSON when supplied; otherwise
  request local transcription for speech. Do not ask the user to manufacture one.
  Silence/music does not justify invented subtitles.
- Read [the shared production contract](../_shared/PRODUCTION.md) for whole-source
  understanding, rights, privacy and optional posting. The commands below use the
  **generic Studio API**, not the tagged LeetCode montage CLI.
- Reuse a responsive Studio origin. Check `GET /api/health`. Do not restart it,
  install into its active environment, delete its lock or automate its normal
  browser. If none exists and startup is authorized, use the normal launcher.

Missing FFmpeg/libass/transcription support is an explicit blocker. Restore only
the declared missing dependency, with any necessary active-runtime coordination.
There is no cloud transcription fallback.

## Composition and clocks

| Property | Existing implementation |
|---|---|
| Explicit mode | `Clip.layout = "fit"` |
| Landscape source | Sharp whole frame aspect-contained in the upper 62%-height pane |
| Portrait source | Sharp whole frame aspect-contained in the whole canvas |
| Background | Enlarged/cropped source duplicate, blurred at reduced resolution |
| Subtitles | Existing clean/punchy ASS style; generic normalized anchor 0.20..0.63 |
| Example subtitle anchor | 0.60, not the editorial LeetCode 0.82 |
| Preview | 360x640, H.264 CRF25/veryfast, 30fps |
| Final | 1080x1920, H.264 CRF20/fast, 30fps |
| Audio | Original selected passage re-encoded to 48kHz AAC; not packet-identical |
| Caption timing | Source-time bursts intersected with the selected range |

Do not pass `camera_mode: "absent"` to a generic Fit clip; that explicit field
combination belongs to the LeetCode layout. Do not add a question heading or
editor correction with a schema that only permits those in the editorial layout.
Do not claim Fit preserves source FPS, native output dimensions or VFR timestamps.

Full-frame preservation can make desktop code too small. Blur is decoration,
**not redaction**: names, chats and private desktop content remain in the sharp
picture. Inspect every scene. Use
[camera + code](../clipfarm-code-camera-portrait/SKILL.md) or
[code only](../clipfarm-code-only-portrait/SKILL.md) when relevant code needs
deliberate cropping and lower captions.

## Create one owned project and obtain speech cues

Replace paths and origin before executing. Each shell starts independently;
re-establish variables or run a coherent block in one shell.

```powershell
Set-Location -LiteralPath 'D:\Work\ClipFarm' # Replace with the actual checkout.
$ErrorActionPreference = 'Stop'
$studio = 'http://127.0.0.1:8741'
Invoke-RestMethod -Uri "$studio/api/health"
$body = @{path = 'C:\Videos\source.mp4'; name = 'New full-frame portrait'} |
    ConvertTo-Json
$project = Invoke-RestMethod -Method Post -Uri "$studio/api/projects/import" `
    -ContentType 'application/json' -Body $body
$projectId = $project.id
```

Import once. For resumption use `GET /api/projects/PROJECT_ID`, not another import.
If speech cues are supplied:

```powershell
$body = @{
    filename = 'source.srt'
    content = Get-Content -LiteralPath 'C:\Videos\source.srt' -Raw
} | ConvertTo-Json
$project = Invoke-RestMethod -Method Post `
    -Uri "$studio/api/projects/$projectId/transcript" `
    -ContentType 'application/json' -Body $body
```

Without cues, submit `{"kind":"transcribe","model":"small"}` to
`POST /api/projects/PROJECT_ID/jobs`. Wait for that owned job, then re-read the
project and inspect its cues. Model weights may require the separately authorized
first-use download; inference stays local. Check ASR errors and inferred timings.
Setting `captions: true` with an empty cue list does **not** create subtitles.

## Save the cut and render

Edit a private copy of [clip.example.json](clip.example.json). Set a truthful
title/start/end, keep the full range in bounds and confirm the point makes sense.
It is a real `clipfarm.models.Clip` payload, not a complete `ProjectUpdate`.

The following save is for the **new empty owned project above**. For an existing
project, preserve every other clip in the list. `PATCH` replaces the supplied
clip list; never send only your new cut over another person's existing list.

```powershell
$project = Invoke-RestMethod -Uri "$studio/api/projects/$projectId"
if (@($project.clips).Count -ne 0) {
    throw 'This example saves only to a new empty project; preserve existing clips.'
}
$cut = Get-Content -LiteralPath 'C:\Private\fit-cut.json' -Raw | ConvertFrom-Json
$body = @{revision = $project.revision; clips = @($cut)} |
    ConvertTo-Json -Depth 12
$project = Invoke-RestMethod -Method Patch `
    -Uri "$studio/api/projects/$projectId" `
    -ContentType 'application/json' -Body $body
$clipId = $project.clips[0].id
$body = @{kind = 'preview'; clip_id = $clipId} | ConvertTo-Json
$job = Invoke-RestMethod -Method Post -Uri "$studio/api/projects/$projectId/jobs" `
    -ContentType 'application/json' -Body $body
```

Poll `GET /api/jobs/JOB_ID` with a finite deadline, not another POST. Completed,
failed, cancelled and interrupted are different outcomes. A polling deadline does
not cancel an encoder. If cancellation is needed, post only the owned job ID to
`/api/jobs/JOB_ID/cancel`, then read its terminal state.

For a completed preview, open the real `output` and `subtitles` paths returned by
the job, or `/api/jobs/JOB_ID/video` and `/api/jobs/JOB_ID/subtitles`. Inspect
motion, endpoints, speech/caption meaning, every scene and sharp-frame privacy.
Generate/read independent output speech recognition when the editorial contract
requires it; this generic route does not automatically do that review.

After actual review, submit the same job body with `kind: "export"`. This creates
a new snapshot and readable export folder, not an overwrite of the preview.
Jobs use immutable project/clip snapshots: later browser edits do not repair an
already queued export. Check the returned revision and actual saved clip.

## Delivery, failure and recovery

Verify the final **1080x1920** MP4, duration, audio and actual caption timing.
Do not hand off the 360p proxy as a 1080p final. Keep its SRT and input/range/job/
review provenance. Do not claim user approval or social-platform safe areas from
an encoder success. General Studio jobs do not automatically create the reviewed
workflow's thumbnail/posting gallery; author those only when requested, following
the shared contract and one-gallery-per-request rule.

On HTTP409 re-read the project and reconcile the changed list/revision; never
blindly retry the old replacement. On HTTP422 read the actual validation error:
source bounds, duration, subtitle anchor and unsupported field combinations are
not permission to bypass validation. For failed/cancelled/interrupted jobs keep
the evidence and create a deliberate new job only after addressing the cause.
Never serve partial files or overwrite a prior final to hide a failure.
