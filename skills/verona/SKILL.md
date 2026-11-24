---
name: verona
description: Use Verona as an explicitly opted-in local speaking face for this agent session. Covers distinct offline voices, six selectable models versus review-only studies, four hairstyles, corrected opaque-default mouths with creation-only transparency opt-in, shared controls, thirty tool-owned idle actions, performance sleep, cancellation and inventory-checked colors. Use for "use Verona", "speak through Verona", "give this chat a head", "customize my Verona head", or "make these heads visually distinct". Not permission to narrate secrets, control another session, install dependencies, or activate recording.
---

# Verona: a separate, recognizable speaking head for this session

## 1. What Verona is and is not

Verona is a Windows-local prototype: text becomes installed Windows
System.Speech or explicitly installed optional Kokoro audio and an audio-clocked animated 3D face. It uses CPU neural
motion, an Electron/WebGL2 head window and one loopback session-manager GUI.
An explicitly opted-in chat can own a separate warm head with its own model,
voice worker, colors, speech RAM, cancellation identity and audio clock.

It is **not** a built-in assistant, microphone listener, transcription service,
conversation scraper or cloud TTS service. It does not automatically narrate
other sessions. Importing recordings, a conversational assistant and accepted
human-accurate articulation are not established features. Do not claim a face,
emotion, female identity or pronunciation has passed human acceptance.

Installing or reading this skill alone does not start Verona or authorize
speaking. Act when the user requests it for this chat. Keep written answers;
speak concise useful summaries, not every log line or tool result. Never send
secrets, capabilities, private incident payloads or raw conversation to speech.
Remote agents need actual command execution on this Windows machine; a skill
cannot make their remote loopback reach the user's speakers.

## 2. Locate a prepared checkout before running anything

Use the checkout path supplied by the user or this session's trusted context.
On the author's machine it is `C:\devdesk\homedesk\Verona`; that is an example,
not a universal install location. Verify the target's `README.md`, `AGENTS.md`,
`VeronaAgent.cmd`, `verona\agent.py` and `docs\prototype-guide.md`.
Do not search whole disks or assume the current project is Verona.

Use a process-local preamble like this, replacing the root when appropriate:

```powershell
$VeronaRoot = 'C:\devdesk\homedesk\Verona'
$Agent = Join-Path $VeronaRoot 'VeronaAgent.cmd'
$Python = Join-Path $VeronaRoot '.local\cpu-env\Scripts\python.exe'
```

Shell variables and working directories may not survive between agent tool
calls. Repeat the preamble in each fresh shell; use absolute launcher paths.
Use Verona's existing CPU environment, not another project's Python.
The prepared app also needs its pinned model/native assets, installed Windows
English voice and local Electron. A skill contains none of those dependencies.
On missing setup, report the exact missing prerequisite and follow the
checkout's guide only with setup permission. Do not automatically download
models, run installers, change a global Python environment or execute a Maya
scene. No camera, microphone, admin rights or cloud speech is required.

## 3. Establish ownership and reuse one manager

1. Use a unique lower-case name for this chat. Prefer `agent-` plus this
   session's UUID without hyphens, for example
   `agent-62456741b7f547b99eece8ce9d6c7606`. Use your own identity, **never copy
   that example**. If the host exposes no session UUID, generate a fresh UUID
   once and retain the resulting name for this chat. Names allow 1-48 ASCII
   letters/digits/underscores/hyphens, beginning with a letter or digit.
2. Record your head's exact name, model, five colors and current request ID in
   this chat's permitted private context when available. Do not create a
   cross-project context store or public transcript to do this.
   On resume, reuse that recorded name, including an owner-approved social
   persona name. Do not reconstruct the old UUID-derived descriptor after a
   rename or create a duplicate merely because that obsolete name is absent.
3. Inventory the manager:

   ```powershell
   & $Agent list
   ```

   This returns active session names, states, model/appearance and the model
   catalog. It does not transfer ownership of existing heads. Never take over
   a matching name merely because it looks convenient.
4. If there is no manager, distinguish **absent** from a stale/unreachable
   descriptor. After explicit user opt-in, a genuinely absent manager can be
   started through `Verona.cmd` (opens the one GUI), or as this long-lived
   command when the agent does not need to open a browser:

   ```powershell
   Set-Location $VeronaRoot
   & $Python -m verona.manager --no-open
   ```

   Use your host's approved long-lived/background process facility and verify
   readiness with `list`. Do not run that blocking server as a short foreground
   probe, detach it contrary to host policy or claim it started without a
   response. The `create` CLI itself **does not autostart a manager**.
5. Session B later reuses the same manager and creates its own differently
   named/color-coded head. Do not launch a manager or cold host for every reply.
   The existing manager/head must not be reloaded, restarted or focused merely
   for discovery or this skill's installation.

An agent host can alternatively be started with
`& $Agent host --session $Name --model claire` in an explicitly owned long-lived
lane. It is an advanced independent owner, not the normal one-GUI flow.
Manager Exit does not close external hosts; explicitly close only your host.
Avoid this route just to bypass the manager's resource cap or a busy head.

## 4. Choose a model honestly

### Give this session a distinct local voice

Inventory actual voices on existing heads before selecting one. The manager
reserves unused startup voices automatically, preferring the optional28-style
English Kokoro pack. Use `create --voice "Kokoro Michael"` for an explicit unused
choice; occupied/absent startup choices fail. Windows voices remain available.
Do not silently revoice another owner's head. Manual later collisions are
allowed but visibly marked **shared voice** on manager cards; choose another
unused voice for this session. Omitted CLI `say --voice` respects its current
native selection rather than resetting it to Hazel.

Voice names/options on a ready head are authoritative, not this skill's example.
The optional pack needs explicit owner-authorized setup documented in the
prototype guide; a fresh machine may have only Windows voices. Runtime never
downloads models. One CPU model is loaded lazily per local-speaking head and
reused across styles, not one model per voice. Windows synthesis releases a
previous local child; closing the head releases it. Several warm neural heads
multiply memory. Cold synthesis is noticeable; do not claim instant or realtime
responses, perceptually unique voices or accepted pronunciation without evidence.

Kokoro supports speed/bass/treble, not implemented pitch/emphasis. Selecting it
visibly resets and disables those controls; unsupported API settings fail.
Facial emotions do not imply expressive vocal synthesis. Cancellation discards
in-flight output but does not immediately interrupt synchronous inference.
Optional phonemization includes GPL components; no cloud, cloning or recordings.

### Head geometry

| Model ID | Actual choice and limits |
|---|---|
| `claire` | Original Claire; preserved CPU neural speech face. |
| `mpfb` | Native MPFB topology; bounded Claire-to-native fitting followed by native geometric exaggeration. |
| `mark` | Actual Mark v2.3 topology, network, PCA and conditioning; not Male-SharpJawline. |
| `reference-structure` | Strong MPFB-reference structural fit over Claire motion/topology. |
| `reference-shell` | Historical subtle reference fit, preserved after visual rejection. |
| `male-sharp` | Owner-named Male-SharpJawline, preserved complete-pose sculpt. |

These are six selectable shapes over two neural identities, not six independently
trained speech models or accepted gender identities. Display names are Aster
(`claire`), Rowan (`mpfb`), Kestrel (`mark`), Vale (`reference-structure`),
Linden (`reference-shell`) and Onyx (`male-sharp`). CLI requests use the IDs,
not display names. Aster's review label is owner-assigned Female; do not infer
gender for other models or use it to choose a voice.

Lyra/Elara, Mira/Selene and Neris/Thalia are six separate supplied-GLB review
candidates, not manager/CLI choices. Akari is a seventh, original Claire-based
anime review study with enlarged eyes, attached upper lashes and a violet bob.
Its isolated review renderer restores banded toon skin/hair lighting; that
does not add an anime shader toggle or Akari to production. Never pass these
review names as `--model`, import/download a GLB, or replace a head to imitate
them. Current studies and their limits are documented in chapter09 and the
research documentation; review/capture is not owner selection or installation.
The README omits supplied-GLB studies and lists Akari inline as review-only.

Every selectable head shares Surface
(legacy ID `claire`), FaceMesh, FaceDot and UniformPolygons, full/head-neck
framing, neck depth, XYZ/cursor motion, zoom, colors, four procedural
hairstyles and natural blinking. Surface supports transparent polygons and
shaded color/makeup. Native shape is uniformly aligned, not replaced by Claire.
Hair, eyelids and makeup remain cosmetic approximations, not accepted anatomy.
New Mark players start with Textured curls fade (`curly-fade`) and hair on in
all four presentations. Swept quiff fade (`swept-quiff`) is the second short
design. Both have skin-to-stubble tapered sides; the rejected `quiff` and
`side-part` IDs are removed, not aliases. Original waves
and Spiral curls remain available. Other models retain their original
startup style/visibility. Never restart or reconfigure an existing head
merely to apply a new default.
The README uses Onyx for the owner's women hairstyle examples and Mark for men;
this is showcase direction, not a runtime gender/voice restriction.

MPFB (catalog name Rowan) fits conditioned and same-audio neutral geometry
separately, then applies half the shared2x/4x setting: effective1x/2x.
Its selector shows effective values; API/agent requests retain the shared
setting and metadata records requested/effective values separately. Other
models retain their prior gains. Final exaggerated geometry can exceed the
native 0..1 rig envelope; it is not contact-corrected or a lossless reproduction
of unsupported Claire detail. Mark uses only its own network/PCA/conditioning;
Claire heads never load Mark. Sideways cheekiness adds a procedural asymmetric
lip pull only on cheekiness clips. Its live checkbox/strength slider can disable
the cue or restore it without inference/uploads; Stop clears it.
Do not invent a Female/Male selector or gender-dependent voice policy.
The session name, head variant, mouth-transparency and performance-only policy are fixed at creation;
create a new owned head to change them. Normal heads are the default. Do not
enable performance sleep automatically: only an explicit user choice at
creation permits `create --performance-mode` or `host --performance-mode`.
The New session checkbox starts unchecked. Opted-in heads become10%opaque
while silent and100%while playing; cursor/blink/idle work sleeps. There is no
live performance toggle or settings mutation. Normal opacity remains a quick
setting, overridden by an opted-in head's10%/100%policy. Do not close somebody
else's head to switch models or policy.

Idle life now owns thirty local actions, including five eye-focused actions
and ten multi-feature composites. The tool chooses/times them, never the chat.
Look-around moves eyes in either cursor mode. Yawns retain the original opaque
mouth by default; only creation-time mouth opt-in permits a wide native-rim
transparent aperture. They use explicitly prepared ignored local effects selected by
voice style (head fallback if unknown). Sneezes use supplied recordings too;
neither effect falls back to synthesis.
Manager `idle-sounds`/`idle-volume` controls mute/level independently of speech
(defaults true/"20", maximum"20"); never raise idle audio above20%.
Automatic yawn audio is rare:10%chance with a minimum ten-minute gap.
Most visual yawns are silent; explicit previews bypass rarity. Missing local
files produce a visible error, never a synthesized-yawn fallback or download.
Keep recordings/derived clips ignored, never push or package them.
The ten-minute interval starts only after successful audio start; explicit
previews also advance it. The history is RAM-only and resets on reload.
Source releases contain no supplied yawn or sneeze recordings. On a fresh checkout,
leave idle sound muted until explicitly authorized local files are prepared
using `scripts\prepare-idle-yawns.cjs` and the prototype guide. The helper
defaults to yawn (at most4.2s); `--kind=sneeze` uses a2.7s bound. Keep existing
yawns intact when adding the two prepared sneeze files. Idle motion
does not require those files. Do not silently replace missing clips or infer
redistribution permission from permission to play/trim them locally.
Do not poll or trigger gestures from the session.
Visual yawn has3x eligible weight, not a guaranteed wall-clock frequency. Performance
sleep suppresses both idle motion and sound; ordinary heads remain the default.

The owner withdrew the old armored character and its Blender study. Do not
recreate it, select its retired ID or restore it from an old release or chat.
Claire and the Claire-only Blender export remain available.

## 5. Mandatory color identity policy for agents

The user wants heads to be **obviously different at a glance**, not merely
different hex strings. Keep the application's freedom to choose every color;
this is an agent selection discipline, not a global palette restriction.
It applies across all active heads, even when their underlying models differ.

- Set all five colors deliberately: mesh, eyes, hair, lips and eyebrows.
  Prefer vivid, strongly saturated, clearly named color families. Do not
  automatically select pale/pastel, washed-out or nearly neutral identities.
  "Solid" here means decisive RGB color choices, not changing FaceMesh into an
  opaque material or removing the transparent desktop background.
- Never solve a collision by choosing a lighter/darker version of an occupied
  hue. Sky blue versus royal blue, pale pink versus hot pink, or scarlet versus
  burgundy is not the requested distinction. Rotate to a genuinely different
  hue family, and check the rendered result.
- Inventory **all five assignments on every other active head**, not only
  mesh, not only your own model, and not only completed/idle heads. Starting
  heads' requested colors also occupy choices. Avoid matching or near-matching
  accents as well as the dominant mesh. Within your own head, use clearly
  contrasting feature colors instead of five shades of the same family.
- A `null` color means original/model-specific rendering, **not an unused or
  transparent color**. Original Claire's cyan mesh/red optics
  can already collide with your proposal. Do not treat unknown original
  colors as safe; inspect the actual head/source defaults or mark the choice
  unverified. Hidden hair, covered lips or tiny eyes are not reliable identifiers.
- Make mesh the strongest identity cue. Then contrast the eyes and visible
  accents against the mesh, each other and other heads' assignments. Different
  model shape/name/voice is useful additional identity, never an excuse for
  indistinguishable colors. Do not turn on hair or change a user's presentation
  without permission merely to expose a chosen color.
- Family candidates include strong red `#E6194B`, blue `#4363D8`, green
  `#3CB44B`, orange `#F58231`, purple `#911EB4` and cyan `#00C8D7`. These are
  **examples to evaluate**, not reserved slots, an approved automatic palette
  or a requirement to use them. Check occupancy first; arbitrary RGB choices
  remain available. No fixed sequence is safe for every new session.
- A numerical aid can convert sRGB to a perceptual space such as OKLab/OKLCH
  and maximize the minimum distance to occupied colors. Also reject the same
  hue family even when lightness differs. Raw RGB distance, hex inequality,
  contrast ratio alone or a single unqualified distance threshold does not
  prove distinguishability. Lighting/glow, background, feature size and color
  vision matter. State whether you actually inspected a native preview.
- There is no promise that 40 colored features across eight heads can all be
  unmistakable. If distinct choices cannot be established, do not quietly
  reuse shades or claim success. Report the conflict; ask the user to choose
  a compromise or reduce heads. Never close/recolor other heads yourself.
  An explicit user-requested color wins; explain any resulting collision
  rather than silently replacing that request.

### Inventory, create, recheck: simultaneous-agent reconciliation

Before creating, retain the inventory of existing names/appearances and choose
a five-color proposal against it. Create with all five explicit values; wait
for your head's confirmed appearance, then run `list` again. Recheck after
customization and whenever another head appears or its appearance changes
during an actual interaction. Do not install a polling service or scheduler.

`list` plus `create` is **not an atomic color reservation**. Two agents can
inventory simultaneously and choose the same colors. Do not claim that names,
one initial check or this instruction file prevents that race.

For cooperating agents created concurrently after their inventories, the
lexicographically smaller normalized session name keeps a conflicting choice;
the other agent changes **only its own** colors and verifies again. A head
already present in your pre-create inventory, an explicit user choice or an
unknown owner's head takes precedence over your new proposal. Never assume
you may recolor another chat, or that its owner follows this skill.
Bound reconciliation to three attempts; on continued conflict report it
without announcing a distinct identity. The GUI/ordinary CLI do not enforce
this policy and can change appearances later. This is cooperative checking,
not a lock, reservation database, security boundary or human-vision guarantee.

## 6. Create once, confirm ready, then speak

After selecting your unique name and **checked** colors:

```powershell
# Set these to your own name and inventory-checked RGB choices first.
& $Agent create --session $Name --model $Model `
  --mesh-color $Mesh --eyes-color $Eyes --hair-color $Hair `
  --lips-color $Lips --eyebrows-color $Eyebrows
```

Mouths default to the original opaque surface: no added black cavity or
transparent neutral seam. Only when the user explicitly requests it, append
`--mouth-transparency` to `create` (or an explicitly owned direct `host`).
The manager API equivalent is the creation boolean `mouthTransparency: true`;
false/omitted keeps the default. The native-rim cutout is then permitted only
at least 0.65 cm beyond neutral outer-lip separation, not at every opening.
This is not a live `configure`/settings option, normal head opacity, oral
retopology or anatomical contact correction. Do not silently enable it for
speech or idle yawns, and never recreate an existing head just to apply this
default. Continuous model-aware lip masks follow rest-space coordinates
through motion; their symmetry is not a guarantee of symmetric projection,
extreme-pose fit or owner-accepted anatomy.

`starting` is not ready. Wait with bounded backoff (for example 0.5-2 seconds,
up to 90 seconds), stop on failed/unavailable, and inspect errors rather than
repeatedly creating. During startup, use the protected manager `inspect` route
shown below: it knows about manager-owned starting heads even before their
individual descriptor exists. Direct CLI `status` needs that descriptor and
can fail while a newly created head is still starting. Once present,
`& $Agent status --session $Name` checks the host directly.
Verify `"ready": true` and the confirmed model/appearance;
recheck the color policy before announcing your identity.
Do not expose descriptor contents or the capability URL.

Speech is UTF-8 plain text on **stdin**, not a text command-line argument:

```powershell
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$JobId = [guid]::NewGuid().ToString('N')
'The build is ready.' | & $Agent say --session $Name --id $JobId
```

Keep the request ID before submitting. Safely quote text; never evaluate
speech as a shell command. Use 1-280 characters and at most 25 seconds of padded
speech. Summarize longer answers; no automatic chunker/backlog is provided.
The head is busy while generating/playing/cancelling and rejects overlap.
Serialize your own replies instead of interrupting another request.

`say` waits for the real audio player's `ended` event. Exit 0 means completed,
not just accepted/generated/playing. It is not proof the user heard or liked
it. Failed/cancelled jobs return nonzero. Keep the written answer and report
failed/unavailable narration honestly; do not silently substitute cloud TTS.

## 7. Customize without rebuilding the head

The single manager GUI discovers sessions and exposes five color pickers/hex
fields, speech controls and each selected model's actual native controls.
**Editable now** contains available live inputs. **Read-only settings**
distinguishes immutable session/model from temporarily unavailable controls;
the latter may unlock in a different mode or after speech.
Never infer that every grey input must be set at creation.

Live CLI appearance changes:

```powershell
& $Agent configure --session $Name --mesh-color $Mesh --eyes-color $Eyes `
  --hair-color $Hair --lips-color $Lips --eyebrows-color $Eyebrows
& $Agent status --session $Name
& $Agent list
```

RGB accepts `#RGB`/`#RRGGBB`; CLI `default` removes an override. The app allows
originals, but agents must reassess collisions before restoring shared
defaults. Color changes are atomic validated patches and do not regenerate
motion/audio. Confirm the returned appearance, not merely your submitted hex.

Every current model shares these five feature controls and the presentation,
neck, hairstyle, gaze, zoom and blinking inputs. Lip/brow masks and native hair
placement remain approximate; a setting existing is not aesthetic acceptance.
Discover each live control rather than guessing its availability.

Per-utterance CLI flags include `--voice` (exact installed English voice name),
`--expression`, `--intensity` (0..0.6), `--gain` (2 or 4), `--voice-only` and
`--timeout` (1..600 seconds, default180). Neutral/intensity0.35/gain4 are CLI
defaults; omitted `--voice` keeps the head's current voice. Voice-only requires neutral.
Expressions are `neutral`, `surprised`, `angry`, `cheekiness`, `disgust`, `fear`,
`grief`, `happy`, `outofbreath`, `pain`, `sad`. Do not invent emotion combinations.
Expression conditioning changes the face, not the voice's emotion.

The CLI has **no generic `--settings` flag**. For volume, pitch/rate/bass/
treble/emphasis, orientation/zoom, supported presentation or pinning, use the
GUI or the existing protected manager API through Verona's client. Discover
the exact current control ID/type/range/options first; change one setting.

```powershell
Set-Location $VeronaRoot
@'
import json
from verona.agent import call, manager_path, read_descriptor
# Replace with YOUR owned head name. Never print the descriptor.
name = "YOUR_OWN_SESSION"
manager = read_descriptor(manager_path())
head = call(manager, {"action": "inspect", "session": name})
if not head.get("ready"):
    raise RuntimeError(f"Head is not ready: {head.get('state')}")
print(json.dumps(head["controls"]))
# Example only: after confirming "volume" is enabled and supports this value:
# result = call(manager, {"action": "settings", "session": name,
#                         "settings": {"volume": "0.5"}})
'@ | & $Python -
```

Checkbox settings are booleans; select/range settings use the schema's string
values. Do not force disabled controls or infer their bounds. Check confirmed
metadata and errors after applying. Apply only to your owned head.
New heads default Always on top on; pin checkbox and session/model name live
inside the collapsed **...** menu. This is ordinary Windows topmost behavior,
not precedence over secure desktops/fullscreen or every other topmost app.
Controls/colors are not persistent preferences across head recreation.

## 8. Best performance without pretending the face is real-time inference

Current loading contract (vr-57, extended by vr-65/66): FaceMesh is a
presentation, not a second neural identity. The manager does not load a model
or numerical/inference libraries; each warm head loads either Mark's own
network/PCA or Claire's, plus only its selected adapter. Unselected head
assets are not loaded from the catalog. Hidden hair/inactive view
GPU buffers are released. Unlit views keep motion only in the GPU, without
a CPU motion copy or normal slots; switching to lit Claire reads the same
samples back once and can briefly stall. Do not promise zero model memory.
The chapter07 vr-57 audit measures manager private memory near19MiB and head
startup peak near288MiB in its isolated CPU probe; these exclude the full
Electron process tree. Its75.3% reduction is geometry-buffer allocation after
view cycling, not total VRAM or total application RAM. No universal speed,
latency or eight-head guarantee follows. Never restart an existing head just
to apply the optimization; use the next normally requested owned launch.

- Keep one warm head per opted-in chat; reuse its engine and Windows speech
  worker. Never cold-start per answer or create several heads for one chat.
  Close your unused head. Each extra head costs substantial CPU/RAM/Chromium.
- Use short useful sentences, await completion and avoid simultaneous neural
  generation where practical. Do not globally tune thread counts or monopolize
  the CPU; manager-owned children already bound BLAS/OMP threads to two.
- When the user values narration latency over moving lips, explicitly choose
  voice-only: `'A quick update.' | & $Agent say --session $Name --voice-only`.
  It skips neural motion and leaves a static head. Never describe that as
  synchronized animated speech or silently use it when animation is expected.
- Warm latest-only caches can reuse exact-repeat clips/synthesis; an
  expression-only change can reuse speech. Arbitrary new text still needs
  synthesis/inference. Do not keep saying old text just to manufacture a cache
  hit. Stop/cancellation/reload can discard the current clip/sample.
- For graphics pressure, inspect the model's supported controls: lower mesh
  detail, disable unneeded hair/points/edges or cursor following, and avoid
  unnecessary views. Change only with user permission and actual available
  controls. Keep the owner's FaceMesh/bright-spokes/4x preference unless asked
  otherwise; do not degrade it silently for a benchmark.
- Historical pre-vr-57 measurements are examples, not SLAs: six-model cold readiness
  about7.3-12.5seconds; one ready snapshot about738MiB Claire/864MiB MPFB summed
  working set, including shared pages, not peak or unique memory. One warm
  voice-only run acknowledged playing at0.910seconds; total4.212seconds includes
  playback. New animated sentences can take several seconds. The eight-head
  cap is a defensive limit, **not qualified eight-way performance**.
- Read actual `secondsToPlayback`, `secondsTotal`, `clientSeconds` and cache
  fields when returned; distinguish preparation from playback duration.
  Do not call submission time GPU completion, claim locked60fps from one
  sample, or infer listening/phonetic acceptance from successful playback.

## 9. Stop, close, errors and recovery

```powershell
& $Agent stop --session $Name --id $JobId
& $Agent status --session $Name
# Only when this chat no longer needs its head:
& $Agent close --session $Name
```

Cancel only your known request ID. A stop acknowledgement requests cancellation;
it is not proof cleanup has ended. Wait for terminal state. Native playback
pauses after delivery; generation reaches its batch checkpoint; synchronous
Windows synthesis must return (worker timeout45seconds). A busy head remains
busy until terminal acknowledgement. Ctrl+C/timeout in `say` requests
cancellation for that same request; it does not close all heads.

After lost connection, inspect your status before any retry. Reusing the
**current** ID with identical inputs does not replay; changing inputs under
that ID fails. Only the latest job exists. There is no durable exactly-once
history, automatic retry or safe replay of a forgotten/replaced ID.
Never narrate a reply twice merely because the first response was lost.

Closing your head removes its descriptor/disposable profile and speech RAM.
Manager Exit/Ctrl+C closes manager-created heads, including other chats, so
**do not exit a shared manager** just because your chat is done.
Closing its browser tab does not stop it. Unexpected manager death stops its
owned heads; external hosts are independent. Restart is explicit, never a
hidden recovery replay or authority to interrupt another user's runtime.

Descriptors under `%LOCALAPPDATA%\Verona` contain private per-run capabilities.
Do not print, copy, publish or hand-edit them. Stale/unreachable descriptors
are errors, not permission to delete somebody else's files or kill processes
by name. Verify exact owned process identity and follow the checkout's
recovery contract; coordinate any unavoidable interruption. WebGL/audio/
device/voice/asset failures remain explicit. No arbitrary file serving,
automatic cloud fallback, transcript log or device activation.

## 10. Installation, verification and source of truth

This is one self-contained `SKILL.md`, so a compatible agent may read it
directly without installing supporting code. Copilot CLI1.0.114 documents:

```powershell
# Run from a trusted Verona checkout; installs the local file personally:
copilot skill add .github\skills\verona\SKILL.md
# Or add --project to install that file into another project's .github\skills.
```

That CLI materializes a file-source skill at
`~\.copilot\skills\verona\SKILL.md`. Project discovery also supports
`.github\skills\verona\SKILL.md`; other hosts need their own compatible loader.
Inspect an existing installation before replacing it. Verify the installed
content and discovery; do not restart another active session to refresh skills
or claim every already-open host automatically loaded new instructions.
Local installation needs no GitHub credentials. A private-repository checkout
or model asset access is a separate permission/setup concern.

### Use from another Agency session, including an already-open chat

The owner's library copy is:
`C:\devdesk\homedesk\skill-library\skills\verona\SKILL.md`.
It is the complete skill, with no companion references/scripts needed to read
its operating instructions. It is not a portable Verona runtime. The prepared
checkout and its source docs/assets still have to be accessible locally.

1. In the other local Agency chat, paste this request (replace paths if moved):

   > Read `C:\devdesk\homedesk\skill-library\skills\verona\SKILL.md` completely,
   > then use Verona for this chat from `C:\devdesk\homedesk\Verona`. I opt in
   > to concise spoken summaries while keeping written answers. Create or
   > reuse only this chat's uniquely named head; reuse the shared manager.
   > Inventory other heads and choose vivid, obviously different colors for
   > all five features, not lighter/darker shades of occupied hues. Do not
   > change, restart or close another chat's head.

2. The agent must actually read the file and verify local command access and
   prepared dependencies. Approve only the required scoped file/process access
   when its host asks. Do not disable sandboxing or broadly grant all paths
   merely to make discovery work.
3. Expect the agent to start/reuse the one manager, retain its own unique head
   name, check model/readiness/confirmed colors and recheck other heads.
   Session B follows the same instructions but uses its own identity and
   contrasting colors. The user need not manually launch Verona first.
4. The manager lists/selects the heads for inspection/customization. Ask the
   owning chat to stop its own narration or close its own head when finished;
   do not Exit the shared manager while other chats need it.

This explicit-path handoff does not depend on skill autodiscovery. If a
compatible host already discovers the skill, "Use the Verona skill for this
chat" is shorthand, not proof it loaded the correct file. Copilot CLI1.0.114
documents `copilot skill list --json` and interactive `/skills reload`; those
commands are **not verified as Agency commands**. Do not invent an Agency
installation/reload flow or restart another active chat. A remote agent with
no execution access to this Windows machine cannot drive these local heads.

Before an opted-in speech handoff, verify: correct checkout/manager, owned
unique name, ready head/model, five confirmed inventory-checked colors,
same-head actual controls, own job ID and successful terminal result.
Report color conflicts, unverified preview or failed speech honestly.

The checkout's `book\README.md` index includes the separately frozen
Living-Face Journal v2 with a clickable 150-topic ELI5 appendix. Frozen books
retain their own historical cutoff; use current source/guide for later
behavior. Author-checkout local review HTML/GIFs are not installed head
assets or guaranteed files in a fresh clone. Old raw capture sequences were
intentionally pruned during cleanup; do not restore obsolete runtimes or
download sources merely to reproduce an old receipt.

**Runtime baseline:** reviewed through vr-87/88 at
`3d5bc5fcdc9d96319a8628697d98aba145722847`: opaque-default creation policy,
continuous model-aware lip cosmetics, Rowan's effective gain and attached
Akari lashes. The subsequent vr-92 toon restoration affects the separate
anime review renderer only (commit `25cb953`); vr-93 refreshes public previews. v0.3.1 is an
older release, not evidence that these later source changes shipped in it.
Recheck current checkout behavior
before assuming commands/defaults stayed unchanged. Authoritative mechanisms:
`verona\agent.py:main`, `SessionManager.create/list/command` in
`verona\manager.py`, `MODELS/COLOR_KEYS/colors_patch` in
`verona\session_config.py`, `manager.js:showControls`, `agent-player.mjs:startAgent`
and `session-controls.mjs:attachSessionControls` under `verona\web`,
`desktop\main.cjs`, `docs\prototype-guide.md` and chapter10 under `docs\chapters`.
Idle behavior and sound are owned by `idle-life.mjs:createIdleClock`,
`idle-sound.mjs:createIdleSound`, `performance-mode.mjs` and the authenticated
routes backed by `verona\idle_audio.py`; chapter11 explains their boundaries.
This instruction file adds no runtime color lock, global narration hook,
model, reservation service, installer, release or deployment.
