# Large single-character arm demonstration

## Scope and dependencies

Read the adjacent README and normative SKILL.md for the selected composition, inputs and limits. A compatible current ClipFarm checkout and newly permitted assets are required. The source's introductory production-history section is not part of this public operating guide.

## Reference composition

At 1080x1920:

```text
Header text reference origins: (90,335), (90,449)
Outer character card: (78,523)..(1002,1424)
Contained character image: 900x877 at (90,535)
Separate caption panel: (78,1490)..(1002,1670)
Teaching board: none
```

Refit newly permitted art without cutting hands/body or stretching perspective.
Keep environment context and outside breathing room. This is a prototype card
composition; recheck current app safe zones and cover 3:4 essentials separately.

## Correct limb isolation

1. Freeze native art hash and coordinates. Draw a tight alpha silhouette around
   the near cuff/hand only, including antialiased edge pixels.
2. Explicitly exclude laptop, desk, cup/saucer and microphone from that matte.
   A rectangular crop is not a limb mask.
3. Reconstruct the fixed base where the original limb was removed, with local
   skin/sleeve/desk continuation appropriate to the exact image.
4. Choose an anatomically plausible native pivot near the cuff/shoulder path,
   not the center of the whole crop.
5. Apply small rotation/translation to the isolated limb, retaining local art
   perspective, then composite into the clean plate.
6. Restore exact fixed prop pixels in their correct occlusion order. Verify no
   old palm fragment remains under an over-broad cup mask.

The later eye/arm test refined this with precise cup/saucer contours and exact
stationary laptop/coffee/microphone restoration. Prefer that protected-prop
methodology for new work; derive masks afresh, do not import private masks.

## Stepped motion and source clocks

The historical gesture used six held pose samples per second on a 30fps output.
That is stop-motion-like **2D animation**, not filmed physical stop motion.
Use restrained anticipation, explanatory raise/turn and return poses; hold them
long enough to read. A new performance needs its own timed keyframes.

Only the male near forearm/hand gestures in this demonstrated scope.
The far/microphone-side arm stays fixed because occlusion makes simple warping
unsafe. Do not imply both arms or the female host were animated.

The original excerpt retained source 633.1..640.5s, with no speed change or music.
For a new test choose authorized speech and map its captions/mouth/limb actions
to the same clock. Do not reuse those source times on another file.
Keep idle/silent behavior explicit.

## Review at the actual defect boundary

Inspect native mask/clean plate, all distinct poses and before/after samples for
**every** pose transition. Then inspect decoded full frames and actual motion.
Compare fixed prop pixels through the entire native sequence, excluding only
explicitly permitted speaker-outline changes from equality masks.

Pixel equality is useful for stationary props; it does not establish a natural
gesture or repair bad reconstruction. Visually inspect wrists, sleeve joins,
exposed desk, laptop edges and surrounding environment.

Preserve original audio packets/samples for a visual-only revision and verify
timing. Read fresh output-ASR where speech output changes; exact-audio inherited
evidence must be labeled as such. Inspect full and center-3:4 cover.

Use `CUSTOM-PRODUCERS.md` for bounded encoding and immutable local publication.
Keep approximate 2D repair limits, lack of direct listening/user approval and
rights/disclosure caveats in the review. No automatic rig adoption or upload.
