---
name: clipfarm-native-grade-portrait
description: Grade a local SDR portrait video while retaining its native displayed geometry, full source timing and original audio through ClipFarm's shared color engine. Use for source-preserving portrait finishes such as the real 950x1144 export, not forced 9:16 reframing or an A/B review deliverable.
---

# Native-size portrait SDR finish

Checkout: `__CLIPFARM_ROOT__`; resolve this marker from the repository when needed.

Read:

- `__CLIPFARM_ROOT__\skills\clipfarm-color-grading\SKILL.md`
- `__CLIPFARM_ROOT__\skills\_shared\GRADING-WORKFLOW.md`
- `__CLIPFARM_ROOT__\skills\clipfarm-native-grade-portrait\RUNBOOK.md`
- `__CLIPFARM_ROOT__\docs\COLOR-GRADING.md`

Confirm the display-normalized source is portrait. Retain its complete picture
and source frame cadence; a portrait recording need not be 9:16. Do not apply
the editorial clip's canvas, duration cap, 30fps, captions, intro or music.
Use the existing Studio worker or one explicit standalone store, never both.

Inspect real color/track metadata before choosing an interpretation. The adjacent
typed recipe is an unreviewed editable starting point with automatic supported
SDR interpretation, not a copy of the historical source's unknown-tag assumption.
Author the look, render actual representative comparisons and inspect them.

Follow the core exact-candidate approval/export policy; do not infer user
aesthetic approval from delegated choices, tests or encoder success. Save actual
feedback and immutable revisions. Deliver the engine's verified native final and
provenance locally, preserving original media/old editions. No proprietary LUT,
Hollywood certification, upload or silent unsupported-source conversion.
