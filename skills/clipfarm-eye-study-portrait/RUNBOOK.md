# Both-host eye movement with corrected near-arm motion

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Composition

The two source crops were 620x604, reframed to 680x662:

```text
Top character image:    (160,382), 680x662
Bottom character image: (160,1084), 680x662
Native left crop:      (70,190)..(690,794)
Native right crop:     (1046,178)..(1666,782)
```

These are references for the original art, not masks/coordinates that transfer
to a new image. The layout has header/captions and no open teaching board.
Retain full-body/hands/environment context within each crop and actual phone
safe-zone review. Do not call a centered-3:4 thumbnail another video orientation.

## Build face-specific eyes

1. Freeze exact artwork/reference hashes and local face geometry.
2. Fit each host's near/far eye independently: perspective, scale, rotation and
   occlusion differ. Preserve glasses rims and do not infer a 3D face model.
3. Remove original printed eyes only within local repair regions.
4. Fit local skin-color planes from valid nearby samples, excluding dark hair/
   glasses and white prints; blend carefully. The old flat-color patch looked
   pasted on, while dark inpainting smeared hair/glasses into the lids.
5. Draw transformed open-eye/gaze/pupil/lid sprites, clipped to appropriate
   face/glasses apertures. Eyelids do not float above frames.
6. Use explicit gaze target keyframes and blink events; evaluate them at output
   frame time, not an unrelated random loop.

The historical blink frames were left `[27,117,189]` and right `[50,147,207]`,
with lid states `[0,.50,1,1,.55,.12]`. These establish staggered held closures,
not a reusable blink schedule for arbitrary speech. New timing needs review.

## Arm and stationary props

Use the tight near-cuff/hand silhouette method from the gesture-study runbook,
not a rectangular laptop-containing crop. Reference native pivot was `(210,427)`,
six held poses per second. Rebuild occluded skin/sleeve locally.

Restore exact laptop, cup/saucer and microphone pixels in fixed space, with
precise contours. A broad cup mask previously preserved old palm pixels; inspect
the whole pose path and remove orange remnants rather than hiding them.
Keep masks at native resolution before scaling into cards.

## Mouth, speech and sample identity

The old study retained source 633.1..640.5s and copied all 320 existing AAC
packets/timestamps; decoded samples also matched. It used the V7 mouth map at a
specific offset. Those source times/map do not apply to a new recording.

A new test must use its own exact source/speaker/silence clock and art-specific
mouth events if mouth motion is included. Eye/arm activity never justifies
changing narration speed or calling approximate visemes forced alignment.

## Review plan

Before encoding, inspect original/repair/sprite/occlusion assets for each host.
After encoding, inspect all distinct arm transitions and actual blink/gaze
before/during/after samples, plus full frames. Check both faces, eyewear, eye
angle, skin repair, wrists and room context.

For stationary-prop equality, compare the protected pixels through the native
frame sequence. Exclude only deliberate speaker-outline changes from those
masks, not arbitrary failure pixels. Metrics do not replace visual inspection.

Verify full audio/PTS/sample identity for a visual-only copy policy; read output
ASR and actual captions, inspect full and center-3:4 room cover, and check real
gallery playback/seek/end/copy/folder links/mobile layout.
Record exact samples viewed and remaining 2D approximation/rights/listening/
user-approval limits. Do not award human acceptance from successful tests.

## Tools and recovery

Use Pillow/NumPy/OpenCV for local planes, masks and sprite warps, bounded
PyAV/FFmpeg for packet/time checks and high-quality native frame encoding.
The shared custom-producer guide supplies safe staging/encoding order.
The old producer was renamed from `prototype.py` to `motion.py` after an import
name collision: new modules should avoid shadowing imported helper names.

Preserve every old test and accepted layout. A new rig, both-arm motion, whole
body animation or workflow default is separate scope, not implied by this skill.
