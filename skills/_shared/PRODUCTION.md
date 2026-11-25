# Shared production contract for format skills

These are instructions for a tool-capable editor, not automatic clip selection
or an AI server. A human can use the same commands and checklists. Start with
`skills\README.md`, choose one composition/orientation, and read its `SKILL.md`
and `RUNBOOK.md`. Do not run every format on an input.

For the separately requested cinematic music full-review/draft skills, the
[cinematic mode contract](CINEMATIC-MUSIC.md) defines the applicable media-review
and explicit draft-proxy exceptions below. It does not change the16format
catalogue, other workflows or existing media. In particular, current cinema
galleries are generated directly without desktop/phone/browser UI QA unless
asked; actual video lyric/progress and cover inspection remain mode-specific.

## Checkout, tools and private workspace

Use the checkout containing this document, not a hardcoded original machine path.
An installed entry has `__CLIPFARM_ROOT__` replaced by the guarded installer.
When reading a repository entry directly, resolve that marker to the parent of
this `skills` directory. Run commands with that repository as working directory.

```powershell
Set-Location 'D:\Work\ClipFarm' # Replace with the actual checkout.
$python = (Resolve-Path '.venv\Scripts\python.exe').Path
& $python -m clipfarm workflow --help
& $python -c "from clipfarm.media import ffmpeg_exe; print(ffmpeg_exe())"
```

Python 3.11+ is declared; the original Windows production environment used 3.13.
Core dependencies include Pillow, NumPy, OpenCV, Pydantic and imageio-ffmpeg.
`.[workflow]` adds faster-whisper, modern RapidOCR and ONNX Runtime. Some
request-local decoders also used PyAV; that is an optional dependency, not proof
that every private producer works on a clean installation.

Do not install packages merely to inspect a runbook. After a genuine missing
dependency failure, use the declared setup:

```powershell
.\Start-ClipFarm.ps1 -Workflow -SetupOnly
```

First-use model downloads require internet; transcription/inference stays local.
Use only `opencv-python`, not a mixture with `opencv-python-headless`. Custom
OpenCV producers must retain `cv2.ocl.setUseOpenCL(False)` on this Windows machine.
Prefer bounded CPU threads and one native full-resolution encoder at a time.
Do not promise a GPU speedup or a whole-film completion time from a small sample.

Check whether a Studio or worker is already using the data directory. Never
restart, terminate, focus, reinstall or migrate the user's running application.
CLI editorial runs and Studio jobs are separate. A different port alone does
not isolate mutable data. Do not remove another process's lock.

Create a **new** private run under `.clipfarm\batch-runs` or use the shared
workflow's new run ID. Keep inputs read-only. Never execute an old `produce.py`,
`review.py`, `delivery.py`, repair helper or publisher just because it still
exists: many bind exact old hashes, absolute paths and one-shot side effects.

The original request timestamp owns a delivery session, not the render date.
Preserve one timestamp across every source in one request. New shared CLI runs
accept `--session-timestamp`; custom producers must record the same meaning in
their own manifest. Recover missing historical times; never invent them.

## Understand before cutting or animating

1. Inventory source identity, actual duration, dimensions, display rotation,
   sample/frame rate, audio streams and relevant rights.
2. Generate local granular speech transcripts if none are supplied. Read every
   cue in bounded blocks; record coverage rather than sampling a few keywords.
   Music-only videos do not need speech ASR.
3. Inventory scenes, useful silent work, BRB, actual submissions, changes of crop,
   private screen details, uncertainty and real comedic setup/payoff.
4. Write a source-to-output coverage ledger. Every substantive point/problem
   needs a delivery or an explicit disposition. Concept excerpts are not complete
   solutions. Never invent narration to repair absent teaching.
5. For future vertical source clips, use coverage-first ceilings:
   `max(1, floor(source_seconds / 120))` core clips plus at most two genuine funny
   bonuses per recording. These are ceilings, not quotas. Do not automatically
   expand A, B and A+B duplicates.
6. Preserve spoken mistakes and uncertain speech honestly. With authorization,
   put referenced editor corrections in a distinct visual region; do not make
   subtitles say something different from the source. Keep `[unclear]` where needed.

Audio-only teaching films still require whole-source understanding. Their speaker
labels and pitch contours are acoustic estimates, not verified human identity.
ASR, RMS, pitch plots and successful playback do not establish direct listening.

## Clocks and quality

Keep source seconds, output seconds, integer frame index and audio sample/packet
positions distinct. For each retained span record its source and output bounds.
Use source PTS for moving camera footage; a source frame number is not necessarily
`seconds * 30`, especially for VFR or 25fps recordings.

Shared source-video montage uses source-timeline caption burst splitting, PCM
intermediates and one final AAC encode to avoid per-cut encoder delay.
Audio-led films that preserve the full original AAC use packet-preserving mux
and compare packet timing/decoded content. Music handles are sample-counted.
These are different policies: do not promise bit-identical AAC after a new mix.

30fps motion changes in approximately 33.3ms steps. A request for slightly slower
mouth motion is not a literal microsecond contract or permission to slow speech.
Synthetic silent reading holds must be declared in maps, not hidden extra footage.

Preserve agreed resolution, frame rate, encoding quality, diagram detail, audio
and review. Optimize redundant work instead: cache identical static layers or
exact full RGB frames; decode camera incrementally; reuse a chapter only if all
its input/renderer hashes and timing match. Compare actual pixels/output before
claiming parity. Never lower quality, skip ASR/review or silently use a 360p
preview as a final to meet a deadline.

## Video safe areas and thumbnail crops are different

Protect teaching, headings and spoken subtitles from the actual Instagram and
YouTube Shorts UI references for the requested production. Generic guides are
heuristics, not a platform guarantee. Inspect full output and phone-scale
composition; arbitrary "safe" coordinates cannot replace that check.

Future portrait thumbnails are 1080x1920, but **all essential text/art/subjects**
must fit in the centered 1080x1440 rectangle `(0,240,1080,1680)`. Review both the
full 9:16 image and that exact 3:4 crop. Top/bottom 240px are expendable background.
This does not convert the video to 3:4 or change landscape artwork.

Never stretch source pictures/camera crops. Use genuine plain Consolas where
required; a missing font must fail visibly. The repository does not distribute
the proprietary font. Do not substitute screenshots of code for an absent face.

## New output review

- Decode actual output; verify dimensions, frame count, duration and audio clocks.
- Read fresh independent output ASR for speech and compare every caption/source
  cue. Inherit old ASR only with explicitly recorded exact unchanged audio and
  provenance; never call inherited evidence fresh.
- Inspect each join, crop change, correction, actual result zoom and synthetic
  hold. Animated films need intermediate causal states, not only endpoints.
- Open the actual generated images. A screenshot saved to disk, a hash, a motion
  metric or a tool response containing no pixels is not visual review.
- Inspect full and center-cropped cover, actual title, safe areas and privacy.
- Keep listening, editorial review, user approval, rights and upload clearance
  separate. Do not auto-fill true approval flags or attribute an agent's review
  to the user.

Use a new immutable candidate after edits. Preserve rejected candidates and
original receipts. Do not backdate an inspection to make a past gate look passed.
Shared CLI `publish` is **local delivery**, not social-platform posting.

## Gallery and copy-ready delivery

One creation prompt gets one accumulating session `index.html`, with direct clip
folders, explicit scope notices, poster/download links and truthful dimensions.
Do not create a new public gallery per source/cut. Do not recreate deleted
historical results as a side effect of documenting their format.

Future cards need separate **Caption**, **Hashtags**, **Thumbnail alt text** and
required **Credits**, each genuinely copied in one click. Caption has no tags or
music credits. Use natural, specific first-person copy for **future** posts,
grounded in what the user actually did/said, not invented experiences or a
generic "I explain" template. Do not retroactively restore the withdrawn
October 2 existing-caption rewrite; that reconciliation remains separately tracked.

At most five relevant unique lowercase hashtags, at most 1000 characters
including `#`/spaces, one space-separated block. These are authoring limits,
not universal platform limits. Keep qualifications intact. Legacy helpers still
have older budgets and do not automatically supply a separate hashtag field.

Required credits have their own field and actual posting-placement instructions.
Local credit files do not discharge license-required platform attribution.
Alt text describes the actual cover, not invented imagery. Optional music
suggestions must identify the exact recording and remain unverified where
availability/trend/excerpt evidence is absent.

Reuse `clipfarm.explorer.add_explorer_button` for the session heading and
`export_folder_sort_key`, `export_folder_field`, `EXPORT_FOLDER_CSS` for cards.
Show the exact actual export directory including suffixes, sorted
case-insensitively. Links open a directory in a new tab of the **same browser**.
`append_gallery_css` preserves stylesheet CSP hashes; never relax CSP to fix copy.

Verify actual clipboard contents, playback/seek/end, folder links and a narrow
viewport in an isolated browser. An honest manual-copy fallback is useful but
does not pass the direct-copy requirement. The legacy vinyl galleries' recorded
native-clipboard limitations remain historical, not magically fixed by this guide.

## Failure, resume and rights

On failure, retain the input snapshot, log, last successful stage and partial
candidate; report the exact failed gate. Resume a finished shared plan, not
`prepare` over it. Inspect interrupted staging/locks before retrying. Never
overwrite a different approved final or run a broad directory cleanup.

Artwork/music/fonts/reference images are not automatically redistributable.
Use newly supplied or rights-documented assets. Do not upload source recordings,
transcripts, frames or private run data to a cloud editor or third-party search.
Do not turn this package into a downloader, uploader, paid provider, scheduler
or automatic consent mechanism. No commit/push is authorized by production.
