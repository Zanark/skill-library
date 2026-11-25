# System-design recording into a diagram-first portrait reel

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Inputs and actual commands

```powershell
& $python -m clipfarm workflow prepare --video $video --workflow system-design --format vertical --session-timestamp $request
```

Keep original filenames. Read every source cue and inspect the complete topic
progression before selecting passages. Build a topic coverage ledger rather
than a LeetCode problem/result ledger. Follow `SOURCE-WORKFLOW.md` for the
remaining commands and pending approval.

## Editorial selections

Each clip must teach a real design point or retain a genuine comedic setup and
payoff. Combine related discussion instead of mechanically publishing A, B and
A+B duplicates. Core/humor ceilings apply per source, not as quotas.

Titles must be honest about scope: an admission sketch is not a full distributed
implementation; a receipt example is not an entire reservation system.
Preserve assumptions and meaningful corrections.

The typed cut uses `category: "explanation"` or `"funny"`, source segments and a
substantive coherence review. Do not set `solution`, `submission`,
`view: "results"`, `runtime_ms` or submission/results evidence.
Current shared System Design rejects horizontal output.

## Framing

- `profile.show_question_title: true`.
- Explicit `cut.question_title`: only the real design question, for example
  `Design a Rate Limiter`, not the question plus promotional clip headline.
- Camera-free sources: `camera_mode: "absent"`, no face ROIs; a large relevant
  content pane beneath the heading and captions near y=0.82.
- Declare source `code_region`, or per-segment `content_region`, around the
  **relevant diagram**, not the whole browser. Preserve required arrows,
  labels and context; change crops when slides/boards change.
- A genuinely camera-present future source can use the existing optional camera
  branch after source-specific review. Do not claim that branch was present in
  the two historical diagram-only productions.

The backdrop is blurred source, not the separately authored animated grid.
Diagrams are retained moving source footage; this skill does not redraw them
or generate causal animation from narration.

## Corrections without misleading subtitles

If the user authorizes retaining source mistakes, a segment can carry a
`correction` with short plain text and verified public source URLs.
The shared note budget is 180 characters and it needs `subtitle_y >= 0.82`.
Show a labelled editor correction in its own band whenever the mistaken claim
is present. Preserve original speech and its captions.

For example, distinguish fixed windows resetting per interval from sliding
windows tracking a moving interval. Verify the source and explanation for the
actual cut; the example is not automatic fact-checking or a finding about new
footage. Require actual `corrections_reviewed` inspection on output.

## Review, cover and delivery

Read all independent rendered-output ASR and mapped captions. Inspect source
diagram legibility, correct heading, correction timing/full text, each join,
source-to-output meaning and ending. A structurally valid topic list is not
whole-source semantic coverage.

Cover hierarchy: complete design question, separator, specific topic. For the
camera-free combination stop there: no camera, no second separator, no
replacement diagram image. Use genuine plain Consolas and full/3:4 review.
Ground scope qualifications in the card, not a false complete-design claim.

Use the normal one-session accumulating gallery, separate future caption/tags/
alt/credits fields and same-browser folder links. Music recommendation versus
explicit embedding remains the shared finishing choice, not a new layout.

## Failure map and source owners

`workflow_for(..., "system-design")` establishes routing.
`workflow.validate_plan` enforces explicit content regions, category restrictions
and absence of invented runtime/result evidence.
`WorkflowPlan` rejects unsupported horizontal System Design.
`workflow.draft_cut` uses the ordinary deterministic montage implementation;
fresh ASR/review/publication remain the same gates.

If a diagram is not readable at the intended crop, revise the source range/crop
or state the blocker. Do not zoom irrelevant panels, replace the speaker with
invented narration, or relax privacy/review to fill a clip quota.
