# Optional music is finishing, not another orientation

Portrait coding/System Design clips were delivered both with original audio and
with explicitly requested quiet licensed instrumentals. The panel geometry stayed
the same; do not create a duplicate layout skill for every track or mix revision.

Shared implementation: `clipfarm.music_models`, `music`, `stylized` and
`workflow style/preview`. Full details: `docs\MUSIC-EDITS.md`.
Original-song picture-disc films are a different family, not this mixer.

## Default versus explicit request

Ordinary source clips retain source audio, with a separately authored warm,
less-somber instrumental suggestion where required. `MusicRecommendation` binds
exact song/artist/version/link, reason, quiet mix advice, reviewer/date and video
hash. Unknown trend/account/excerpt status remains unverified. A suggestion does
not download, mix or clear the recording.

The September 27/28 quiet-CC collection explicitly requested **embedded** audio;
recommendations alone did not satisfy it. Ten later mixes used distinct
recordings and separate required credits. The current surviving collection root
was renamed `session_soundtracked_2026-09-27__17-45-16`; old paths in receipts are
historical, not instructions to republish them.

## Existing command sequence

Read the real schema; do not invent a `trend` CLI mode:

```powershell
& $python -m clipfarm workflow music-schema
& $python -m clipfarm workflow style --plan $plan --cut $cut --settings $settings
& $python -m clipfarm workflow preview --plan $plan --cut $cut
& $python -m clipfarm workflow draft --plan $plan --cut $cut
& $python -m clipfarm workflow review-transcribe --plan $plan --cut $cut --model small --language en
```

`style` changes only the named cut and backs up the old plan. A preview is the
whole edit at 360x640, not a final. Final review needs the 1080x1920 candidate.

`embedded` needs a local track/hash and exact local permission proof/hash,
reviewer/date, intended use/territory, permission for both platforms and complete
required attribution. Record exact recording/version/passage start/end. Distinct
gain or a tiny offset shift does not make a passage different. Short tracks fail
rather than silently looping. Source music rights remain independent.

`instagram` embeds no platform track: actual recent account/region availability,
exact identity/offset and manually reviewed beat grid are required. A catalogue
link is not that evidence. The schema has no implemented YouTube-native route.
Never transfer an Instagram soundtrack/license to a YouTube export.

## Speech-first constraints

Do not shorten narration to land on a beat. Optional internal join handles need
actual expendable silence, no captions/evidence/corrections/meaningful work,
`trim_silence: false`, and at most 0.5s of safe tail. A short dip is at most six
frames per side, not a flash or speed ramp. Headings/captions remain undimmed.

Embedded music uses 48k stereo PCM staging, quiet gain, music-only edge fades,
sidechain ducking keyed by source audio, limiter and one final AAC encode.
Source audio is not a clean separated vocal stem; background noise can trigger
ducking. Metrics/ASR cannot replace actual final listening/balancing.

Complete real rights, beat, transition and mix review; native/trend gates apply
only when actually selected. Do not certify a current India trend from old use
counts, a monthly list, full-song length or a passing infrastructure test.
Discovery/matching/full-native-duration/three-mode integration remains separate
open work. No random/royalty-free substitute for an explicitly trend-first brief.

Keep credits out of creator prose, separately copyable with license-required
posting placement. No upload or account conversion is part of these skills.
