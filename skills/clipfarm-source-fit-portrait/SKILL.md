---
name: clipfarm-source-fit-portrait
description: Make a full-frame, aspect-contained portrait clip from a local recording using the existing Studio Fit renderer, faithful captions and a blurred-source background. Covers the original real-footage framing demonstration; not cropped code panels, face tracking, native-size grading or a complete-solve workflow.
---

# Full source frame inside a portrait canvas

Checkout: `__CLIPFARM_ROOT__`. Resolve this marker to the actual checkout when
reading the repository copy; the guarded installer binds it automatically.

Read:

- `__CLIPFARM_ROOT__\skills\_shared\PRODUCTION.md`
- `__CLIPFARM_ROOT__\skills\clipfarm-source-fit-portrait\RUNBOOK.md`
- `__CLIPFARM_ROOT__\docs\STUDIO-WORKBENCH.md`

Use the running Studio's loopback API/UI and its single worker. Do not start a
second worker, drive the user's browser, or change another project's clips.
Choose explicit `layout: "fit"`; do not rely on Auto detecting a cardboard
avatar. The complete sharp picture is aspect-contained over a blurred duplicate.
There is no separately extracted camera panel.

The existing renderer produces 360x640 previews and 1080x1920 final MP4s at
30fps, with at most 180 seconds per clip. It re-encodes selected audio to AAC;
this is not native-PTS or audio-packet-preserving grading.

Understand the source, retain useful context, generate local speech cues if
needed, and review actual captions/privacy/readability. The adjacent typed
`clip.example.json` is illustrative, not a saved project, reviewed cut or consent.
An earlier Fit preview proves this composition was made, not that it was an
approved editorial reel. Use the coding-specific skill when code needs its own
larger pane. Deliver new immutable files only; no upload or old-media rewrite.
