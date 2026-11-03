# ClipFarm

A local-first cutting room for turning long recordings into captioned Instagram
Reels, YouTube Shorts and opt-in horizontal LeetCode solution videos.

Import a video, find passages in its transcript, review the composition, and export
vertical MP4s. Files are processed on your computer, not sent to a video-editing
service. There is no account, API key, subscription, or automatic publishing.

## Downloads

[GitHub releases](https://github.com/Zanark/ClipFarm/releases) provide a source ZIP,
Python wheel, source distribution and SHA-256 checksums. Use the source ZIP for
the Windows launcher and Copilot skill installer; the wheel provides the Python
studio and workflow CLI. See [the changelog](CHANGELOG.md) for release highlights.
Recordings, transcripts, model weights and proprietary fonts are not bundled.

## Editorial references and private history

The [public workflow reference](docs/LEETCODE-WORKFLOW.md) contains reusable
editorial requirements. Recording-based PDF/HTML case studies, their review
records, production histories and original manuals are retained only in the
private migration archive. Proposed analysis tools and request-specific
animation experiments are not silently promoted to shared engine features.

## Start on Windows

Requires **Python 3.11 or newer**. From this directory:

```powershell
.\Start-ClipFarm.ps1
```

The first start creates `.venv` and installs the declared dependencies, including
a bundled FFmpeg. The studio opens at **http://127.0.0.1:8741**. Leave the terminal
running; press Ctrl+C there to stop it.

For optional local speech transcription:

```powershell
.\Start-ClipFarm.ps1 -Transcription
```

If the studio is already running, stop it before restarting with this switch.

The transcription package is optional. Selecting a speech model in the studio
downloads that model's weights on first use. Processing then runs locally on CPU.
Internet access is needed for installation and the first model download, not for
editing or rendering with an imported transcript. Cancelling during model loading
may take until loading finishes.

Alternatively:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m clipfarm --open
```

`--port 8742` changes the port; `--data-dir D:\ClipFarmData` moves the project/output
store. The launcher always binds to loopback. This is a single-user desktop tool,
not a server intended for public or LAN exposure.

## Automated LeetCode editorial workflow

For tagged LeetCode recordings, use the dedicated **full-transcript review,
multi-section montage, submission/runtime zoom, humor and BRB-exclusion workflow**:
[LeetCode workflow and cross-directory command](docs/LEETCODE-WORKFLOW.md).

```powershell
.\Start-ClipFarm.ps1 -Workflow -SetupOnly
.\Install-ClipFarmSkill.ps1
```

Then run `/skills reload` in an existing Copilot CLI session and prompt:
`Use the /clipfarm-leetcode skill for "VIDEO_PATH".`
**Only the video is required.** The workflow generates a granular local speech
transcript automatically, saving timestamped `transcript_granular.txt` lines and
a JSON companion with ASR-estimated start/end times. Supplying a transcript remains
optional: add `with transcript "TRANSCRIPT_PATH"` to reuse one without source ASR.
The personal skill works from any directory. Copilot makes semantic editorial
decisions; local Python stages render, transcribe and enforce review/provenance
gates. A standalone `prepare` call does not automatically understand a video.

New vertical plans enable **persistent question headings in genuine Consolas**:
the actual LeetCode problem title appears above the feeds for the whole clip,
including silent footage. Author the exact title in `cut.problem`, or override
with `cut.question_title`; never substitute a catchy clip headline. Preserve
`profile.show_question_title: true` when editing the prepared profile. The layout
reserves title space without moving the lower spoken captions. Existing plans
remain unchanged until explicitly opted in, rerendered and freshly reviewed.
Horizontal videos and their cover/introduction workflow are unaffected.

**One creation prompt produces `results\session_<timestamp>\`.** Open its single
`index.html` to browse every source's clips, or `<clip-folder>\clip.mp4` for a video.
Pass the same `--session-timestamp "TIMEZONE_AWARE_PROMPT_TIMESTAMP"` when preparing
each source. Folder timestamps use `YYYYMMDD_HHMMSS_ffffff` in Asia/Kolkata;
they refer to the original prompt, not rendering. Direct CLI calls without a chat
timestamp honestly record CLI request time. Legacy collections remain unchanged.
`publish` copies the approved MP4/SRT/transcript bundles there automatically.
The entire `results` folder is Git-ignored; `.clipfarm` retains private working
files and the original publication records.

Session galleries show **Open session folder** immediately below the heading.
It opens the containing directory in a **new tab in the same browser**, using a
normal relative folder link. Open the local `index.html` directly to browse its
files; no Windows File Explorer, protocol registration, running studio or network
service is needed. Moving a gallery changes the destination to its new containing
folder. The original gallery tab stays open.

If served over HTTP/S instead of opened as a local file, directory listings depend
on that server's configuration. The old `explorer install/open` CLI remains only
for compatibility with archived `clipfarm:` links; new gallery buttons do not use it.

Future authored gallery cards must separate **Caption**, **Hashtags**, **Thumbnail
alt text** and required **Credits**, each with a genuine one-click copy button.
Caption contains no hashtags or music credits. Select **at most five relevant,
unique lowercase hashtags per post**, with **at most1,000 characters including
# signs and spaces** in the separate Hashtags field. Choose the strongest
clip-specific tags; fewer than five is fine, and no length padding is needed.
All hashtags form **one space-separated block, without hard line breaks between
tags**. The block never appears in Caption; on-screen wrapping adds no copied
newlines. The1,000-character budget is for hashtags only, not prose or a claimed
platform allowance. This September30 authoring rule leaves existing galleries and
legacy shared helpers unchanged; verify the new section when authoring a gallery.
Reload an open gallery before copying revised text; changing local
files does not update already-published Instagram captions.
Preserve the reviewed takeaway and
qualifications rather than cutting them for tags. Ordinary prose and identifiers
retain their case. If clipboard access
is blocked, the selected text can be copied manually with Ctrl+C/Cmd+C.
These are posting descriptions, not replacements for spoken subtitles.
An optional reviewed `posting.json` supplies clip-specific copy bound to the
video/thumbnail hashes. Without it, the gallery clearly labels its conservative
title/cover-based suggestions for review. See the
[posting-copy contract](docs/LEETCODE-WORKFLOW.md#copy-ready-posting-text).

The current editorial workflow also authors a **song recommendation for each clip**:
exact song/artist/version, why it fits, a listening link, quiet mix guidance and a
copyable search for Instagram/YouTube. The user adds the music; the MP4 retains
original audio. The preference is **Snowfall-like, but warmer and less somber**.
An optional video-hash-bound `music-recommendation.json` supplies this card without
re-rendering. Legacy galleries without one remain unchanged. Suggestions do not
claim current trend status, account availability, rights or full-duration fit.
See [music recommendations](docs/MUSIC-EDITS.md#current-delivery-recommendations-only).

Each new vertical clip also includes a **1080x1920 `thumbnail.jpg`** with the
**problem name, separator, specific clip topic, separator, then a camera/avatar
image if present**. Both text blocks use genuine plain Consolas. The shot is
framed around the middle-to-lower-middle (center57.5% down), below compact text:
maximum64px problem /68px topic. A softly frosted version of the same camera crop
fills the backdrop, with subtle reproducible Gaussian grain; the camera card has a
drop shadow and the original light blue-grey border (#45616a), not a red border.
IndianRed separators, cream text and the full camera image/aspect ratio are preserved.
The camera shot is
randomly selected from retained camera footage. The gallery uses it as the video poster and
offers a Thumbnail download. Selection stays within the clip's retained footage
and is reused on subsequent publication; the video itself is not changed.
For visually verified sources with no camera/avatar, explicitly set
`profile.camera_mode: "absent"` in the editorial plan and omit all face crops.
This uses a larger relevant-code/diagram pane with the same lower captions and
animated results, plus a text-only problem/topic thumbnail with honest no-camera
provenance. Camera absence is never inferred; default camera-present behavior and
approved exports are unchanged until explicitly archived and replaced. No code or
diagram image substitutes for an absent camera on new covers; omit that image
section and its separator. See [the vertical contract](docs/LEETCODE-WORKFLOW.md#explicitly-camera-free-sources).

Direct preparation: `python -m clipfarm workflow prepare --video "VIDEO_PATH"`.
Source ASR defaults to the local `small` model with language detection; optional
`--language en` or `--model base` controls recognition. Completed audio chunks are
checkpointed; resume an interrupted preparation with the printed `--run-id` and
the same options. Recognition can mishear code terms; editorial review is still required.

The original numbered TODO catalogue and production ledger are preserved in
the private migration archive's `clipfarm\TODO` directory, not public Git.
The public `TODO` directory contains clearly marked fresh-work templates.

### Reviewed System Design vertical clips

System Design requires explicit opt-in; keep original filenames rather than tagging
them as LeetCode:

```powershell
.\.venv\Scripts\python.exe -m clipfarm workflow prepare --workflow system-design --video "test-inputs\22 Sept\Design a Rate Limiter _ System Design Interview.mp4"
```

Only vertical output is supported. Preparation generates the same local transcript
and an **unreviewed, empty plan**, not automatic selections or approvals. After reading
the complete transcript and reviewing source frames, manually author `explanation`
or genuinely `funny` cuts. Coverage-first plans allow at most five core clips per
ten source minutes (`max(1, floor(seconds /120))`) and two optional genuine humor
bonuses per recording. Combine related topics rather than expanding A/B/A+B
duplicates; these are ceilings, not targets. Reconcile every substantive point
against delivered coverage. Explicitly authorized editor corrections can preserve
inaccurate source explanations with referenced, clearly labelled on-screen notes;
original speech/subtitles remain intact and notes require separate output review.

Use explicit reviewed segment `content_region` (diagram/code) and `face_region`
crops, or shared `profile.code_region` / `profile.face_region` crops. The compatible
segment `view: "code"` also displays diagrams. For genuinely camera-free sources,
explicitly declare `profile.camera_mode: "absent"`; never invent a camera crop.
There are no submission/runtime-results categories or views in this mode.

Set each cut's `question_title` to the actual design question, for example
`"Design a Rate Limiter"`. With the prepared `show_question_title` flag enabled,
**only that question** appears above the video feed. The Consolas thumbnail shows
that problem name, a separator, the descriptive clip topic from `title`, then a
separator and the camera/avatar if present, exactly as for vertical LeetCode.
Camera-free covers are text-only, not diagram substitutes. Keep full scope
qualifications in editorial notes. Review the entire
heading and its separation from all feeds before checking `question_title_reviewed`.

Continue with the existing `validate`, `draft`, `review-transcribe` and `publish`
commands using `--plan`. The same 180-second limit, BRB scanning, independent
rendered-output ASR, caption/visual/coherence/usefulness review and explicit approval
gates apply. Workflow identity follows the draft, ASR, review, manifest and gallery;
these exports are labeled **System Design**, not LeetCode. Existing automatic tagged
LeetCode routing and horizontal behavior are unchanged.

### Horizontal complete-solve videos

Ask **"create horizontal format solution videos from my stream"** and supply the
local recording. The same skill creates one chronological video per completed
question, preserving the original horizontal layout, removing unnecessary silence
and tangents, retaining important silent work, and placing captions in reviewed
empty space near the bottom. This is the editorial CLI workflow, not a new mode
in the manual studio.

Each video gets a black cover with its **exact LeetCode number/title in Consolas**,
followed immediately by the **data structure / algorithm used**, left-aligned in
lime-yellow Consolas (#dfff00), exactly **3px smaller** than the title font.
It also has bare green complexity such as **O(n)** and a topic-related image at bottom-right
(cats preferred). The O is a **large circular graphic** in the lower-left
(216px across with a5px outline at1280x720), not a letter-sized glyph. No complexity headings, "average",
invented meme captions, badges or on-image credits; prefer transparent cat stickers
unless the background contributes to the joke.
Stream-stated complexity takes precedence; otherwise the editor researches and
cites **best-known** complexity, without claiming the demonstrated code achieves it.
Complexity qualifications, research basis and required image attribution remain in
metadata and `credits.txt`; the renderer does not scrape arbitrary images.

The cover holds for **one second**, then dissolves into moving footage over
**four seconds**. Narration and captions start with the footage, without fading
away the first words. The exact cover JPEG is included in the final bundle.
Horizontal videos keep native landscape dimensions and have **no three-minute
limit**; disk, CPU and processing time still apply. Vertical output remains default.

```powershell
.\.venv\Scripts\python.exe -m clipfarm workflow prepare --video "VIDEO_PATH" --format horizontal
```

See [horizontal plan, artwork and review contract](docs/HORIZONTAL-SOLVES.md).
Approved videos, thumbnails and attribution/source notes go to
`results\session_<timestamp>\<problem-title-id>\`, sharing the session's one
landscape-aware gallery.

## Manual studio workflow

The studio uses a YouTube Studio-inspired header, content sidebar and editing
panels, with Solarized Dark surfaces and IndianRed (`#CD5C5C`) accents. The local
clip gallery shares the palette. This changes application chrome, not exported
video colors or burned-in captions.

1. **Import a recording.** For multi-hour videos, use an absolute local path:
   it references the original without duplicating it. Browser uploads also work
   but need temporary and destination disk space. Keep referenced originals in place.
2. **Add a transcript.** Import SRT, WebVTT, timed JSON, or timestamped TXT; edit caption text and
   timing in the studio. Optional transcription can generate captions from speech.
3. **Find clips.** Suggest passages with a target duration and optional keywords,
   or create a clip manually at the playhead. Suggestions look for hooks, sentence
   endings, pauses, and keyword matches; they are not semantic or virality scores.
4. **Review framing.** Analyze a clip, choose a layout, adjust source regions or
   the crop's focal point, and render a low-resolution preview. The preview is
   the actual encoder output, not a simulated CSS crop.
5. **Export.** Render selected clips, then download the MP4 and clip-local SRT.
   Subtitles may be burned in or kept as a separate file. Review the result in
   the destination app before posting.

### Transcript formats

All transcript timestamps refer to the **original video's** timeline, not each clip's.
Timed JSON accepts an array or an object containing `segments` or `cues`:

```json
[
  {"start": 12.4, "end": 15.8, "text": "Here is the idea."},
  {"start": 15.8, "end": 20.1, "text": "This is why it works."}
]
```

Timestamped TXT accepts Tactiq-style inline timestamps (leading `#` export headers
are ignored), or standalone timestamps followed by a paragraph:

```text
00:00:17.199 Here is the idea.
00:00:20.400 This is why it works.
```

TXT start times are preserved. Because these exports do not supply end times,
ClipFarm infers each end from the next timestamp and caps it at eight seconds or
half a second per word, whichever is longer. The final caption is also bounded
by the video duration. This avoids leaving captions onscreen across long breaks.
Granular line timestamps are preferable to paragraph blocks. End times and
proportional caption bursts are **estimates, not audio/word-level alignment**;
review and edit them before publishing. Caption bursts are timed on the original
timeline before trimming, so cuts do not replay an entire long paragraph.

Untimestamped text alone cannot provide reliable subtitle timing. ClipFarm does **not**
pretend it can align an untimed transcript: import timed subtitles, or transcribe
the audio locally and correct the generated words. Local transcription is speech
recognition, not forced alignment of supplied text.

Names, mixed-language speech, music, overlapping speakers, and words at the
10-minute transcription chunk boundaries may require correction. Captions retain
the transcript's language; ClipFarm does not translate them.

## Vertical composition

| Layout | Behavior |
| --- | --- |
| Auto | Uses sampled face evidence to choose a composition; uncertain footage stays fully visible. |
| Follow | Follows a detected main face with smoothed crop motion and scene-cut resets. |
| Fit | Preserves the whole frame against a soft, blurred version of the source. |
| Stacked feeds | Separately composes camera and content regions; both can be adjusted. |
| Manual crop | Uses your chosen focal point instead of automatic tracking. |
| LeetCode | Explicit avatar and code-only regions, lower boxed captions, and animated results zoom with dimmed surroundings; camera and captions stay bright. |

Automatic analysis is a local **OpenCV frontal-face heuristic**, not a model that
understands every action, slide, game HUD, camera border, or active speaker. It can
miss profiles, tiny faces, occluded faces, and unusual layouts. Multiple speakers
or uncertain detection should be reviewed using Fit or manual regions. Smooth
camera motion is not a guarantee of editorially perfect composition.

Avatars and masked faces (including cardboard-head streams) may not be detected
at all. Use the region-drawing controls for these feeds rather than assuming face
tracking understands them. The local `test-inputs\` folder is Git-ignored for
private test videos, transcripts, and inspection images.

The supplied visual references inform the preview's conservative guides: keep
critical material clear of the top 14%, bottom 35%, left 6%, and right 14%
(extra room for interaction icons). Captions default near 60% of frame height.
These are **ClipFarm design margins**, not an asserted universal platform rule.
Guides are not burned into the export. UI overlays vary by platform, device,
caption length, and organic/ad placement.

No framing system can both enlarge every subject and preserve every pixel of a
wide screen inside a narrow vertical frame. Fit and stacked layouts prioritize
preservation; crop layouts prioritize the subject. Review small screen text at
phone size.

## Vertical export preset

| Setting | Export | Preview |
| --- | --- | --- |
| Canvas | 1080 x 1920, 9:16 | 360 x 640, 9:16 |
| Video | H.264, yuv420p, 30 fps | Same composition, lower resolution |
| Audio | AAC, 48 kHz when source has audio | AAC when present |
| Container | MP4 with fast-start | MP4 with fast-start |
| Clip duration | Up to 180 seconds | Same clip |
| Captions | Burned-in clean/bold styling plus optional SRT | Same placement |

The shared preset is intended for Reels and Shorts, not a promise of upload
approval or reach. Upscaling does not restore missing source detail. Caption
bursts use cue-level timing and proportional splits, **not word-accurate karaoke**.

YouTube's [three-minute Shorts documentation](https://support.google.com/youtube/answer/15424877)
confirms vertical/square videos up to three minutes can be categorized as Shorts.
See also [Instagram's Reel size/aspect-ratio help](https://help.instagram.com/1038071743007909).
Platform limits and rights rules can change. Use video and audio you are entitled
to publish; ClipFarm does not license downloaded content or bypass Content ID.

## Long recordings, persistence, and limits

- There is **no application-imposed source-duration limit** for finite,
  seekable, supported video files. Real limits are available disk, CPU, decoder
  support, and elapsed processing time; this does not mean infinite/live input.
- Rendering seeks to a selected clip instead of loading the whole recording into
  memory. Face analysis samples that clip with a bounded frame budget. Optional
  transcription extracts ten-minute audio chunks to bound audio memory.
- MP4, MOV, MKV, WEBM, AVI, M4V, MTS, M2TS, and TS are accepted. Decoder support
  depends on FFmpeg. A format accepted by FFmpeg may not play in your browser;
  use the encoded preview in that case.
- Projects, captions, clip edits, and job history are stored in
  `.clipfarm\studio.sqlite3`. Imported originals are never modified.
  Studio outputs live in `.clipfarm\exports\<clip-title>\`, using filesystem-safe
  versions of saved clip titles rather than GUID folder names. Previews add
  ` - preview`; repeated exports add ` (2)`, ` (3)`, etc. without overwriting files.
  Downloaded MP4/SRT files use the same readable names. Existing GUID folders are
  renamed on studio startup, preserving job IDs and updating download references.
- A single background worker processes one job at a time, preventing a batch
  from launching many encoders at once. You can cancel queued or running work.
- Exports use immutable saved snapshots. Later edits do not alter an in-flight
  export. Preview/export history may therefore contain older versions.
- After an unclean shutdown, unfinished jobs are marked **interrupted**, not
  falsely completed or silently restarted. Submit those jobs again.
- Generated transcription is also saved as downloadable JSON. If edits happen
  during transcription, the result does not overwrite them; import that JSON
  when ready.
- Moving source files breaks their references. Import their new location as a
  new project. There is currently no source-relink, platform publishing, speaker
  diarization, or automatic music-selection feature. Explicit vertical
  [speech-first music edits](docs/MUSIC-EDITS.md) support documented local music
  or an Instagram in-app handoff, safe beat handles, previews and review gates.
  Authored per-clip gallery recommendations are implemented; they do not change
  audio or require a verified native handoff. Automatic selection, verified current
  Instagram trend discovery and full-duration matching remain incomplete. The
  earlier trend-first contract remains available for a future explicit request;
  no random/generated-song fallback.
  Non-contiguous montages are available
  through the editorial workflow CLI, not the studio's single-range cut editor.
- The data folder is ignored by Git and is not automatically cleaned or backed
  up. Stop the studio before moving/backing it up or removing old files.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
```

Browser integration uses Playwright with installed Microsoft Edge on Windows.
Tests can use another browser via `CLIPFARM_BROWSER_CHANNEL`; if the chosen browser
is unavailable, install it before running the browser test.

The implementation is a FastAPI API, SQLite project/job store, one media worker,
FFmpeg renderer, OpenCV face analyzer, and dependency-free browser UI. Optional
faster-whisper runs speech recognition locally. FFmpeg's bundled license and
codec terms still apply if you redistribute the application or its dependencies.
