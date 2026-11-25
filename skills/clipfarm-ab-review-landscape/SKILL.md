---
name: clipfarm-ab-review-landscape
description: Produce a real matched-time landscape A/B grading review MP4, original on the left and graded on the right, with ClipFarm's shared engine, scopes and decoded samples. This is review evidence, not an approved final, a fake CSS comparison, a new soundtrack or a forced landscape crop of the source.
---

# Landscape moving A/B grading review

Checkout: `__CLIPFARM_ROOT__`; resolve repository markers from the actual clone.

Read:

- `__CLIPFARM_ROOT__\skills\clipfarm-color-grading\SKILL.md`
- `__CLIPFARM_ROOT__\skills\_shared\GRADING-WORKFLOW.md`
- `__CLIPFARM_ROOT__\skills\clipfarm-ab-review-landscape\RUNBOOK.md`
- `__CLIPFARM_ROOT__\docs\COLOR-GRADING.md`

Use `grading preview` through the existing worker. Save one exact candidate,
choose source windows of at most30seconds, and inspect its real encoded
`comparison.mp4`, graded proxy, samples, scopes and metadata.

Each half contains the complete aspect-correct source at the same instant.
The source proxy's longest edge is at most720px. Confirm the doubled proxy
width exceeds its height before calling this landscape; do not stretch/crop a
very tall source or add a new custom renderer to force the label.

The adjacent typed preview request contains an all-zero placeholder revision ID
and version0. Replace both from real current state; never submit it unchanged.
No approval is included or required to create review evidence. Do not run
`approve`/`export` merely to make a comparison, inherit old consent, claim a full
native-resolution review, or deliver a proxy as the finished source grade.
