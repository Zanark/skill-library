# Horizontal complete-solve videos

**Separate custom audio-led format:** its preservation boundary is recorded in
[HASHMAP-AUDIO-VIDEO-PLAN.md](HASHMAP-AUDIO-VIDEO-PLAN.md).
It uses a padded studio illustration, a persistent current-topic heading above
it with matching YouTube chapter timestamps, an internal animated teaching board
and external lower subtitles for the complete source audio. It is not this native-source
complete-solve workflow. Do not apply this workflow's
cover hold, cuts or artwork automatically to that proposal.

Invoke the installed `clipfarm-leetcode` skill with:

> Create horizontal format solution videos from my stream "D:\Videos\[LeetCode] stream.mp4".

This explicitly selects horizontal output. Ordinary clip requests still produce
vertical reels. The manual studio and its shared 180-second preset are unchanged.
Read the general [LeetCode workflow](LEETCODE-WORKFLOW.md) for local transcription,
whole-source review, BRB inspection, immutable drafts and publication.

## What gets edited

Create one chronological video per problem, from its introduction through the
completed implementation and genuine outcome. Preserve meaningful explanation,
diagrams, coding, necessary corrections, Submit and Accepted/results when present.
Do not replace the demonstrated algorithm with a cleaner one or manufacture
missing narration. If completion is absent, report the blocker instead of calling
an excerpt a complete solve.

Remove tangents, BRB and unnecessary pauses. Silence detection is not semantic:
the editor must identify important silent typing, whiteboard work, reading and
submission waiting. Put those ranges in `horizontal.preserve_ranges`, or set a
segment's `trim_silence` to `false`. Evidence frames get automatic silence guards
of 0.5 seconds before and 1 second after; these guards are not a substitute for
protecting an entire meaningful action. BRB exclusions always win, and conflicts
with declared protected work fail for editorial reconciliation.

The body preserves **native normalized landscape dimensions, aspect ratio and
the full camera/code/screen arrangement**. No crops, stacked feeds, pan/zoom,
results dimming, speed-up or extra music are applied. Display rotation and
square-pixel normalization still apply. Portrait/square sources are rejected,
not silently converted.

Select an explicit normalized bottom `subtitle_region` that is empty in the
actual source. Override it per segment when scenes change. It must fit inside
the frame, start at or below y=0.65, and have at least 0.3 width and 0.055 height.
The renderer fits readable two-line caption bursts into that rectangle; inspect
the encoded result for important content underneath. If no suitable space
exists, flag the scene rather than covering code or altering the source layout.
These are source-specific placements, not universal platform-safe margins.

## Thumbnail and opening

The reference is the user's supplied thumbnail and video
`https://www.youtube.com/watch?v=mQv23roNvnE`
("300. Longest Increasing Subsequence | Daily LeetCode [ Jan 5 ]").

The landscape cover has:

- A black background and full white `{number}. {exact problem title}` at the top.
- Genuine **Consolas** monospace; no silent font substitution or shortened title.
- The actual **data structure / algorithm used**, immediately below the full title,
  left-aligned with it, in **lime-yellow (#dfff00) Consolas**. Its font size is exactly
  **3px smaller than the fitted title font** at every output resolution (for example,
  64px title / 61px technique). Wrap and fit both together without truncating either;
  keep the complexity ring and meme geometry unchanged.
- Only the green complexity expression below-left, such as **O(n)**. The O is a
  **huge geometrically circular ring**, not a letter-sized circle:216px
  diameter with a5px outline on1280x720 (30% of its height), centered at about70% canvas height in
  the lower-left. Scale the design proportionally for other resolutions and center
  the parenthesized Consolas expression vertically beside it. Keep the circle large
  even when a longer expression needs smaller text.
- A topic-related image contained at bottom-right; cats are preferred. No invented
  meme captions, number badges or other added text. Prefer clean transparent
  sticker-like cutouts, but retain a box/background/object when it supplies the joke.
- No complexity heading, "average", research/source label or on-image credits.
  Evidence, qualifications, licensing and attribution remain in metadata/credits.

The editor searches for a relevant cat meme and chooses the first suitable result
whose usage rights can be established. A search ranking is not a license. Keep a
local image, its SHA-256, source URL where applicable, relevance, rights declaration
and attribution. User-provided/permitted, public-domain, appropriately licensed or
original artwork is supported. If no suitable permitted image is available, obtain
a supplied asset or agree on original artwork; do not silently use an unrelated
random image or imply that scraped imagery is licensed. Never upload private
stream content to perform these searches.

For complexity, use the value **actually stated for this problem in the stream**,
including its timestamp and quote. Preserve that statement even when best-known
complexity differs; disclose a suspected error rather than silently correcting the
speaker. If none is stated, research the exact problem using reputable references,
record a URL and explanation, and identify it as **best-known** in metadata/credits,
not as extra text on the cover.
Do not present a researched optimum as the demonstrated algorithm's complexity.
The Python renderer does not guess complexity, search the web, or invoke an LLM:
the calling editor supplies and reviews this evidence.

Set `horizontal.artwork.technique` to a concise source-grounded name such as
`Hash Set`, `Hash Map`, `Geometry`, or `Dynamic Programming`. Identify the technique
actually implemented, not an unrelated problem tag or the researched optimal
solution; preserve supporting code/frame evidence in the editorial review.
Newly authored covers include this field. It is optional only for compatibility
with older plans; absent values add no label, and blank/control text is rejected.
The label is fingerprinted into artwork, recorded in metadata/credits and bound
to the intro/review. A thumbnail-only revision can be delivered separately; never
swap the JPEG inside an approved video bundle or imply its encoded intro changed.

`complexity.notation` preserves the original analysis. A single expression with a
recognized qualifier, such as `O(n) average`, displays as `O(n)` without losing that
qualification from the credits. For a compound analysis, provide an explicit
`complexity.display_notation` containing one `O(...)` expression; the renderer must
not silently choose between different bounds. Parenthesized/nested expressions are
preserved. The renderer preserves a supplied image's alpha channel; choosing and
reviewing a context-preserving background removal is the editor's responsibility.

Consolas is normally read from `%WINDIR%\Fonts\consola.ttf`. A permitted local
Consolas file can be supplied with `font_path`. Missing/wrong fonts fail clearly;
the repository does not distribute the font.

The exact generated `thumbnail.jpg` is rendered **before** the draft video and
is part of its fingerprinted artifacts. Publication copies it, not a new random
cover. Changing artwork, evidence, fonts or settings invalidates the old draft.
`credits.txt` accompanies the output with complexity sources and meme attribution;
retain any required attribution in the eventual platform description.

The default opening is:

| Output time | Picture | Source/audio timeline |
| --- | --- | --- |
| 0-1s | Static thumbnail | Synthetic hold, silence |
| 1-5s | Thumbnail dissolves into moving source footage | First four seconds of the retained body, original narration |
| 5s onward | Original full-frame body with subtitles | Body continues without repeating its opening |

The dissolve always lasts **four seconds**. The separate hold defaults to **one
second** and is adjustable with `intro_hold_seconds` from 0 to 10 in whole 30fps
frames. The body must contain at least four seconds. Captions remain visible above
the fading image after the hold. Narration starts unattenuated with the footage;
there is no audio fade that could hide the first words.

## Preparing and authoring a plan

```powershell
$python = 'C:\devdesk\homedesk\ClipFarm\.venv\Scripts\python.exe'
& $python -m clipfarm workflow prepare --video 'D:\Videos\[LeetCode] stream.mp4' --format horizontal
# Optional supplied transcript: --transcript 'D:\Videos\captions.json'
# Otherwise generate it locally; --language en can help recognition.
```

Preparation records `"output_format": "horizontal"` and an initially empty cut
list. It is not automatic editorial approval. Read every cue, inventory every
problem/scene and inspect source images before authoring cuts. Existing vertical
plans/drafts keep their signatures and cannot silently become horizontal.

Each cut has `category: "solution"` and `title` matching the exact numbered
artwork title. Retained segments must be ordered, nonoverlapping and within the
reviewed chapter. Avatar/code crops are forbidden; `view: "results"` may identify
a results passage but never adds the vertical zoom.

Abbreviated cut (all times, paths, claims and SHA values are illustrative):

```json
{
  "id": "300-longest-increasing-subsequence",
  "title": "300. Longest Increasing Subsequence",
  "category": "solution",
  "problem": "Longest Increasing Subsequence",
  "rationale": "Keep the complete solve; omit the unrelated browser tangent.",
  "segments": [
    {"start": 20, "end": 400, "reason": "Question and implementation"},
    {"start": 440, "end": 920, "reason": "Finish and submit", "trim_silence": false}
  ],
  "trim_silence": true,
  "coherence_review": "Replace with a substantive review of all selected speech and joins.",
  "horizontal": {
    "chapter": {"start": 20, "end": 920},
    "subtitle_region": {"x": 0.1, "y": 0.86, "w": 0.8, "h": 0.12},
    "preserve_ranges": [
      {"start": 180, "end": 205, "reason": "Important silent recurrence implementation"}
    ],
    "coverage_review": "Replace with a full introduction-to-completion review, including meaningful silent work.",
    "subtitle_review": "Replace with a source-frame review showing this bottom rectangle is empty throughout these scenes.",
    "intro_hold_seconds": 1,
    "artwork": {
      "problem_number": 300,
      "problem_title": "Longest Increasing Subsequence",
      "technique": "Dynamic Programming",
      "complexity": {
        "notation": "O(n^2)",
        "source_kind": "stream",
        "source_time": 100,
        "evidence": "Replace with the actual complexity statement and context."
      },
      "meme": {
        "image": "D:\\Videos\\permitted-increasing-cat.png",
        "sha256": "REPLACE_WITH_ACTUAL_SHA256",
        "rights": "user_provided",
        "rights_note": "Replace with the supplied asset's permission/rights declaration.",
        "topic": "Explain its connection to an increasing subsequence.",
        "search_query": "increasing sequence cat meme"
      }
    }
  },
  "evidence": []
}
```

Complete `evidence` with actual image paths, `time`, substantive `description`,
`kind` and `verified_by`. Required kinds are `introduction` in the first selected
segment, `implementation`, `completion` in the last selected segment, and
`subtitle_space` for each distinct caption rectangle. Add `submission` and
`results` where present; only record `runtime_ms` after checking the actual
submission-results panel. Code completion evidence need not invent a submission
that the stream does not contain. All non-BRB cut evidence must survive trimming
and frame rounding. Evidence images are fingerprinted into horizontal drafts.

For a research-based complexity value, use:

```json
{
  "notation": "O(n log n)",
  "source_kind": "research",
  "source_url": "https://cp-algorithms.com/sequences/longest_increasing_subsequence.html",
  "evidence": "Document the verified best-known approach and its parameter definitions; do not attribute it to different demonstrated code."
}
```

This is a schema example, not a finding about the user's recording. A licensed
meme additionally requires `attribution`; provenance URLs are citations, not
automatic remote downloads.

## Draft, review and deliver

```powershell
$plan = 'C:\devdesk\homedesk\ClipFarm\.clipfarm\workflow-runs\RUN_ID\plan.json'
& $python -m clipfarm workflow validate --plan $plan
& $python -m clipfarm workflow draft --plan $plan --cut 300-longest-increasing-subsequence
& $python -m clipfarm workflow review-transcribe --plan $plan --cut 300-longest-increasing-subsequence --language en
# Read output ASR + source transcript, inspect actual output, then fill review.json.
& $python -m clipfarm workflow publish --plan $plan --cut 300-longest-increasing-subsequence
```

There is **no horizontal 180-second limit** on segments or the assembled body.
Each retained span is rounded down by less than one 30fps frame. Rendering streams
native H.264/yuv420p frames and uses PCM intermediates, with a single final AAC48k
encode when source audio exists. Required disk and render time scale with retained
footage. Long-form BRB scans are split into bounded, independently cached sample
batches; no sample cap silently truncates a long solve. Output ASR extracts bounded
ten-minute audio chunks. A failed/cancelled stage never counts as approval.

The source-map records the synthetic thumbnail hold separately; real source spans
and SRT timestamps start after the hold. Its dissolve overlaps the first four
seconds of body rather than inserting or replaying four seconds of source.

Review the whole output transcript, all joins, retained corrections/silent work,
caption regions, actual completion and native-layout readability. Inspect the
cover, early/middle/end dissolve and audio/caption onset. Do not equate an encoder
success or sampled OCR scan with complete editorial review or direct listening.

Alongside the normal checks, horizontal review requires:
`complete_solve_reviewed`, `original_layout_preserved`, `silent_work_preserved`,
`subtitle_space_reviewed`, `thumbnail_reviewed`, `complexity_verified`,
`meme_rights_verified`, and `intro_fade_reviewed`. Submission/runtime checks are
added when those claims are present, not a vertical zoom check.

Approval binds the thumbnail hash as well as video/output-transcript hashes.
Final MP4, SRT, transcripts, source-map, review, manifest, identical thumbnail and
credits are copied to:

`results\session_<timestamp>\<problem-title-id>\`

Use the same original creation-prompt `--session-timestamp` for every source.
The session's single `index.html` displays landscape videos at the correct aspect
ratio, with direct clip folders and no per-source/clip indexes. The shared
[delivery and posting contract](LEETCODE-WORKFLOW.md#copy-ready-posting-text)
requires future cards to separate Caption, Hashtags, alt text and required Credits,
with a genuine one-click copy button for each. Caption has no hashtags. Choose
at most five relevant unique lowercase tags per post; the separate hashtag block
must be at most1000 characters including # signs and spaces. Keep it space-separated
without hard newlines. This is a user authoring limit, not a platform guarantee,
and does not change historical galleries or impose a1000-character caption limit.
Reconcile every problem against delivery or a specific blocker before declaring
the stream processed. No automatic upload, trending music, Docker behavior or
user approval is introduced by this mode.
