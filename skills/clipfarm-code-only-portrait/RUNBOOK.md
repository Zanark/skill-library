# Large code pane without a camera: 9:16

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Prepare and inspect

Use the same existing CLI stages in `SOURCE-WORKFLOW.md`:

```powershell
& $python -m clipfarm workflow prepare --video $video --workflow leetcode --format vertical --session-timestamp $request
```

The video is sufficient; source transcripts are generated locally when needed.
Understand the complete source and inspect meaningful silent coding and results.

After actual camera-absence inspection, set:

```json
{
  "show_question_title": true,
  "camera_mode": "absent",
  "face_region": null,
  "code_region": {"x": 0.36, "y": 0.10, "w": 0.63, "h": 0.59},
  "subtitle_y": 0.82,
  "caption_style": "clean"
}
```

These crop values are illustrative. No segment may introduce a `face_region`.
Use an explicit `results_region` only after visually verifying the actual panel.

## Output layout

The question remains above the feed in genuine plain Consolas.
With question headings, the contained code region uses approximately
x=0.025/y=0.16/w=0.95/h=0.58. This is reserved space, not a crop that stretches
the source. Lower captions stay around y=0.82 over a blurred source background.
An authorized correction shortens the content pane to reserve a separate note
band; it must not cover code or spoken subtitles.

Choose tightly relevant code/diagram crops per scene. Remove unrelated browser
panels, not useful context required to understand an example. A wide source
example and narrow code editor can require different `content_region` values.

## Cuts and result animation

Use the same coverage-first ceilings and concrete viewer takeaways as the
camera-present format. Useful mistakes/debugging can be retained faithfully;
do not title every short excerpt a complete solution.

Actual result passages use `view: "results"` and an independently verified ROI.
The bright whole results crop slowly grows from 68% to 100%; the background
dims without hiding heading/subtitles. Preserve loading where useful and review
the entire transition to avoid a visible full-size/shrink/jump.

`category: "submission"` needs source evidence for actual submission and runtime.
Do not invent it for an explanation cut merely because its endpoint is Accepted.
Trim silence conservatively; the action and final meaning determine what stays.

## Covers, finishing and review

Future covers contain the problem, one separator and the clip topic, with
complete plain-Consolas text. **No camera image and no second separator.**
Do not substitute a code screenshot. Old content-shot camera-free covers were
legacy editions; the current text-only rule governs new authoring.

Keep essentials within `(0,240,1080,1680)` and inspect full 9:16 plus exact 3:4.
No grid background is inherited from the separate animated-explainer treatment.

Render and independently transcribe the actual MP4. Read every output-ASR line
and mapped caption, inspect source/code readability, correction accuracy,
question persistence, each crop switch/result zoom/join and ending.
`camera_mode: "absent"` is provenance, not permission to skip privacy review.

For separately requested quiet embedding, follow `..\_shared\MUSIC-FINISHING.md`.
Ordinary outputs keep source audio and optional separately authored suggestions.
Keep credits, caption, hashtags and alt text separate.

## Implementation and failure map

- `WorkflowProfile.camera_declaration` rejects a declared absent camera plus ROI.
- `WorkflowPlan.source_bounds` rejects absent-camera face overrides/horizontal use.
- `media._filter_graph` chooses the large content branch instead of a face layer.
- `workflow.thumbnail_frame`/`ensure_thumbnail` use explicit absence provenance.
- Shared draft/review/publish remains hash-bound and immutable.

Missing code context needs a new crop/selection, not a fabricated face or caption.
If there is no useful complete point, record that disposition rather than padding
the collection. Preserve old drafts and any narrow `[unclear]` fragments.
