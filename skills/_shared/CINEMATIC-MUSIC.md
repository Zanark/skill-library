# Cinematic song stories: common contract and review-mode boundary

These are two **agent-authored production skills**, not additional video
orientations or an automatic `clipfarm cinematic` command. Read the selected
entry and runbook as well as PRODUCTION/CUSTOM-PRODUCERS. Author a new local
compositor, timeline and source-bound evidence with the existing tools.
Private historical producers/assets are optional read-only evidence, never
runtime dependencies or programs to replay.

Read the selected ClipFarm checkout's contributor, workflow and applicable workstream contracts before authoring. They are external runtime inputs, not private files shipped by this library. [Current-checkout setup](../../docs/CLIPFARM-SKILLS.md#current-checkout-requirement) explains the dependency. Context ownership remains with the actual current registered base; never write a sibling store.

## Choose the requested mode, not the most convenient review

| Route | Meaning | Media review |
|---|---|---|
| `clipfarm-cinematic-music-video` | Explicit fully reviewed production | All lyric occurrences/timing/window progress, scenes/actions/joins, complete decode/PTS/audio and actual cover |
| `clipfarm-cinematic-music-draft` | Explicit early concept/animatic | Few representative movie states/basic media integrity; lyrics estimated or omitted |

Invoking full mode overrides a previous fast-review preference for that run.
Draft mode permits its declared proxy/rough finish; it never waives complete
song coverage. Installing either does not silently reset the user's standing
fast preference for unqualified ad-hoc productions or start another video.

The current user waived **gallery** desktop/phone/browser QA. Generate the
index directly in either mode unless gallery tests are separately requested.
Video lyric-window/progress inspection, video composition and full/center
thumbnail viewing are media work, not the waived gallery UI tests. Preserve
real copy/folder/CSP controls and mark UI QA not run. Earlier browser tests are
historical, not inherited evidence for a new index.

This snapshot records production procedures, not creative acceptance of a historical movie or permission to publish private source material. New productions need their own source-bound evidence and rights.

## Intake, source clock and local ownership

- Recover the ORIGINAL timezone-aware request timestamp. Use one
  `results\session_YYYYMMDD_HHMMSS_ffffff` for that request, in Asia/Kolkata;
  do not bind it to a preparation time or create per-shot galleries.
- Fingerprint the new song/lyrics/art/fonts and record source bytes/mtime,
  actual audio streams and full decoded sample count/rate. Preserve originals.
  Lyric-sheet `2:30`, an ordinary Reel ceiling and an early draft are not trim
  permission. An alternate recording is a different input, even with the same
  title/lyrics. Reinspect its real duration.
- Keep original start/end, levels and speed. No automatic intro hold, music,
  extra silence, beat-driven speech cuts or audio replacement. Use packet copy
  when genuinely qualified, otherwise full original PCM and one documented AAC
  delivery encode. Do not claim packet identity after encoding.
- Set output frames to `ceil(source_samples / sample_rate * fps)`, render
  frame `i` at `i/fps`, and cover the fractional final audio interval. Do not
  use `-shortest` or alter audio to hide a one-frame video deficit.
- Use the declared `.venv`, local FFmpeg and existing optional tools. Missing
  dependencies/models are explicit blockers; restore only after an actual
  failure, with the existing setup procedure. No cloud transcription/video.
- Keep one bounded owned encoder. Use an isolated headless browser/profile
  for WebGL creation, never the user's browser. A raw-frame data plane should
  go directly to the owned loopback encoder, not through an instrumented
  Playwright/DevTools network bridge for thousands of multi-megabyte frames.
  Bound readiness/progress, retain exact logs and close only owned processes.

## Story before a render, without an unrequested approval stop

Read all supplied lyrics and understand the whole song's structure. Genre/BPM/
instrumentation in the prompt is supplied direction, not independent hearing
or measurement. Create an original logline, consistent cast, goal/stakes,
song-section/shot/action ledger and ending. Develop repeated choruses rather
than replaying a finished pose or resetting the plot.

Give characters specific goals and visible consequences. Use dimensional or
otherwise deliberately art-directed spaces, motivated cameras/light, actual
character/prop action and readable resting moments. Camera panning over a
finished diagram does not substitute for the requested story. Technical
metaphors must preserve valid scope; qualify incorrect source claims separately
without silently rewriting original singing.

Show the storyboard in chat first only when the request asks for that
checkpoint. For an autonomous full-film/draft request, save and include the
storyboard but continue production. Do not convert an AFK instruction into a
question or a storyboard-only stop.

Keep stable character/object IDs, values and original identities separate
from transient positions. Validate complete poses and meaningful transfers;
do not duplicate live data-bearing actors during a shift/merge. Check geometry
extents, face/label surfaces, contact and real occlusion, not just camera boxes.

## Lyrics and the window's progress

Maintain unique IDs per **occurrence**, including repeated identical choruses.
Each cue has literal text and source-clock `[start,end)` bounds. Gaps belong
to the actual instrumental/silence; do not hold a stale lyric/progress forever.
Do not infer the order/timing solely by spreading words across song duration.
Validate `0 <= start < end <= actual_song_duration` and account for every
occurrence; the clock helper cannot infer the source song's duration.

The [lyric-window reference](cinematic-lyric-window.js) is a small optional helper:
`createLyricTrack(cues).at(t)` gives a cue and elapsed phrase fraction;
`drawLyricProgress(ctx,state,rect,colors)` redraws the bar. Copy it into the
new private producer and freeze that copy with the other inputs if used.
It is not a lyric aligner, scene renderer or app API.

```javascript
const track = ClipFarmLyricWindow.createLyricTrack(reviewedCues);
// Evaluate the source clock and redraw the progress area on EVERY frame.
const state = track.at(frameIndex / fps);
restoreCachedLyricPanel();
drawCurrentLyricText(state);
ClipFarmLyricWindow.drawLyricProgress(ctx, state, lyricBar, lyricColors);
```

The two drawing/cache functions above belong to the newly authored compositor.
Cache text/layout by occurrence ID, not text alone. Restore the panel and draw
progress after that cache on every frame; otherwise an overlay cache can freeze
the bar while the words stay unchanged. A new occurrence resets even when its
text repeats. Backward seeking must recompute from time, not accumulated state.

Phrase fraction is `clamp((t-start)/(end-start),0,1)`, NOT a recognized word
position. Word-specific highlighting requires separately grounded word times.
At 30fps the last frame before a cue end need not display precisely100%;
at the next cue start it resets to0. Inspect the nearest actual encoded frames,
not an impossible sub-frame promise or synthetic native-only screenshot.

## Palette, cover, posting and immutable delivery

Inspect the complete supplied/embedded canonical cover when available. Derive
the dominant RGB once per cover hash (largest deterministic four-colour
median-cut cluster, deterministic tie break), save it and share the movie/
thumbnail background base. Keep material colours/light object-local rather
than independently tinting each background. If there is no cover, create or
select permitted original artwork and record that decision, not a fake source.

Use a 1080x1920 thumbnail with all essential subjects/text inside the exact
center3:4 rectangle `(0,240,1080,1680)`, even for a smaller draft proxy.
Inspect full and exact center crop; preserve full subject bounds/aspect.
Do not import LEGO, LeetCode-camera or vinyl styling without a current request.

Stage new direct versioned bundles atomically, refuse collisions and preserve
older editions. Full candidates with unresolved required gates stay clearly
labelled review candidates. Draft filenames, visible movie mark, gallery and
metadata must say DRAFT and describe omissions; no `readyForUpload=true`.

Use existing `clipfarm.posting` and `clipfarm.explorer` helpers for one session
index, Open session folder directly under its heading, highlighted exact export
directory, same-browser folder tabs, standard CSP and four separate copy fields:
Caption, Hashtags, Thumbnail alt text, Credits. Caption is grounded natural
first-person prose, without tags/music credits. At most5 unique lowercase tags
and1000 characters in the separate space-separated hashtag block. Keep required
rights/disclosure caveats in credits; supplied music is not licence proof.

Bind source, renderer/timeline/asset hashes, output hash and actual review
coverage in the new evidence. User creative acceptance, direct listening,
public music/lyric rights, platform classification and upload are separate.
No new film, historical rerender, dependency install, background service,
commit/push or platform upload is implied by installing these skills.
