# Reviewed coding and design clips

This is the sanitized public operating reference, not a production journal.
The complete original manual, case-study PDF/HTML, reviews, artwork policies,
frozen producers and request-specific decisions are preserved in the private
migration archive's `clipfarm\docs` and `.clipfarm` collections.

The canonical `clipfarm-leetcode` skill supplies the full editorial contract.
Use `python -m clipfarm workflow --help` and each subcommand's `--help` for the
packaged engine's exact CLI arguments; do not guess a plan or review schema.

## Setup and preparation

Install through the repository's portable installer. Alternatively, with the
studio stopped, run this implementation's `Start-ClipFarm.ps1 -Workflow -SetupOnly`
and `Install-ClipFarmSkill.ps1`. The portable installer is preferable because it
installs all nine skills and rebases their runtime paths together.

The video is the only required input. Source preparation creates a granular
local transcript with resumable chunks; supplied SRT, WebVTT, timed JSON and
timestamped TXT are also supported. Use the `source-transcribe` CLI family or the
skill's preparation flow. Models may download on first use; inference stays local.

Read the complete transcript before selection. Inspect actual source pixels,
not merely generated contact-sheet filenames or a tool's success message.
Do not invent speech, private history, performance measurements or user approval.

## Deliverable selection

Default to meaningful vertical topic clips and requested A/B/combined variants.
Keep separate problems separate and preserve complete causal explanations.
A concept excerpt is valid under a truthful scoped title; it is not automatically
a complete solve. Submission clips need the actual Submit outcome, Accepted
state and reported milliseconds; a successful testcase run is not a submission.

Choose the System Design workflow explicitly for design material. Author the
actual design question as `question_title`; preserve meaningful diagrams/slides
and do not mislabel it as a LeetCode solve. Horizontal design is not implied.

An explicit horizontal request selects [HORIZONTAL-SOLVES.md](HORIZONTAL-SOLVES.md).
An explicit stylized/music request selects [MUSIC-EDITS.md](MUSIC-EDITS.md).
Neither changes ordinary vertical defaults. Historical deliveries and parked
requests in the private archive are not instructions to restart production.

## Composition and editorial evidence

Use source-grounded avatar/content/results regions and actual displayed pixels.
Keep source aspect ratios, readable code/diagrams and caption clearance.
Camera-free plans must be explicit; do not silently substitute a camera or claim
every historical renderer supports the same layout.

Vertical covers are 1080x1920, with essential content inside the centered
1080x1440 region (`x=0..1080`, `y=240..1680`). Preserve full titles and reviewed
font/hierarchy. This authoring policy is not a universal platform-crop guarantee.
Custom audio-led and animated productions retain their separate
[preservation boundary](HASHMAP-AUDIO-VIDEO-PLAN.md).

Meaningful animation must show narrated operations when described: moving an
item, constructing a map, updating state and revealing results causally.
Maintain object identity and source-time mappings, inspect intermediate states,
transitions, arrowheads, shadows and caption clearance. Decorative motion,
numeric scores and static completed diagrams do not establish editorial quality.
Preserve original narration, meaningful silent work and material qualifications.
Do not replace an error with invented speech or manufacture source evidence.

Retained camera/avatar video must use the same source asset and time mapping as
the narration, including cuts, joins and explicitly authorized retiming.
Resolve actual presentation timestamps rather than assuming frame indexes equal
output time. Do not fetch a live camera or unrelated looping video.

## Draft, ASR and review

Use the packaged workflow's plan, draft, output-ASR, review and publication
commands in their documented order. Inspect their `--help` and generated plan/
review templates rather than bypassing a required gate.

Drafts, independent output transcripts, correction notes and review evidence
must bind to the exact media hashes and source-time mapping. Re-encode or change
the draft and the affected evidence must be regenerated. Preserve original media,
immutable job snapshots and old receipts rather than overwriting them.

Read the independent output transcript against the full intended source.
Inspect representative actual frames, all joins and important action/results
moments. Check BRB/privacy footage, crop readability, caption placement, omitted
qualifications, corrections and intelligible chronology. Encoding success alone
is not editorial review or user listening/visual acceptance.

Publish only through the ordinary immutable workflow gates. Never change a
review flag, signature or permission setting merely to make publication succeed.
Do not upload to social platforms automatically.

## Session galleries and posting

One creation request has one timestamped session gallery, with individual
exports beneath it. Preserve its original request timestamp across continuation,
honest timestamp provenance, source coverage and immutable receipts.
Use the ordinary exporter/Explorer helper instead of inventing a different
directory structure. Keep multiple reviewed plans in the same requested session.

Provide separate Caption, Hashtags, Thumbnail alt text and required Credits
fields with genuine one-click copy controls. Captions describe the actual
takeaway in a natural creator voice; do not invent lived experience, unaided
authorship, rights or completed demonstrations.

Keep captions free of hashtags/music credits. Use at most five relevant unique
lowercase hashtags and at most 1,000 characters including spaces and `#`.
Do not pad with generic tags. Preserve full required attribution separately and
explain licence-specific posting placement; local credits do not waive rights.
Show copy failures honestly, never report clipboard success after denial.

Keep original media/downloads, source provenance and review evidence accessible.
Do not resurrect archived media or overwrite a request-specific gallery layout
when revising posting text. Restoring private historical files is not approval
to rerun them.

## Engineering

Preserve revision checks, the single cancellable worker, atomic publication,
CPU-only OpenCV initialization and owned-process cancellation.
Never install both OpenCV GUI and headless providers in the same environment.
Run focused tests with `.venv\Scripts\python.exe -m pytest` after engine changes.
Use the public TODO workflow templates for new work; their TEMPLATE status does
not represent completed production or restored user approval.
