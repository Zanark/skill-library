# Shared real-engine procedure for grading format skills

These are composition-specific entry points into the existing color engine,
not parallel grading implementations. Read [the core grading skill](../clipfarm-color-grading/SKILL.md)
and the selected checkout's `docs\COLOR-GRADING.md` and [the runtime prerequisite](../../docs/CLIPFARM-SKILLS.md#current-checkout-requirement) before executing.
The native-portrait skill finishes a source-preserving video; the landscape A/B
skill produces **review evidence**, not a second approved final.

## Environment and protected runtime

Use the checkout containing `skills`, its declared `.venv\Scripts\python.exe`,
bundled FFmpeg and optional `.[grading]` PyAV dependency. Do not install packages
merely to read these instructions or alter a running Studio's environment.
The normal `-Grading` launcher/setup is documented in the color-room reference.
Missing libraries/filter capabilities fail explicitly; there is no replacement
CSS filter, cloud processor or silently simplified FFmpeg route.

Check the supplied Studio's loopback health and use `--studio ORIGIN` consistently.
The same single worker must own previews and final grading. Do not start another
standalone worker against its store. Without Studio, use one explicit
`--data-dir 'C:\Private\ColorRoom'` consistently instead. A lock conflict is a
blocker, not permission to remove the lock or stop an unknown process.

Read live-session state before every write. Returned versions change after jobs,
not just after recipe edits. Never reuse IDs/approval from a historical example.
Do not drive/reload the user's browser or edit the served UI to inspect a file.

## Inspect the actual source

```powershell
Set-Location -LiteralPath 'D:\Work\ClipFarm' # Replace with the actual checkout.
& '.\.venv\Scripts\python.exe' -m clipfarm grading --help
& '.\.venv\Scripts\python.exe' -m clipfarm grading presets
& '.\.venv\Scripts\python.exe' -m clipfarm grading inspect --video 'C:\Videos\source.mp4'
```

With live Studio use `grading --studio ORIGIN inspect --project PROJECT_ID`.
Reuse an already imported matching project, or import a new permitted source
once. `prepare --video` can import it through the chosen transport.

Inspect duration, displayed/coded dimensions, rotation, sample aspect, FPS/PTS,
color declarations, progressive status and audio/other tracks. Input must be
supported SDR. Known HDR/PQ/HLG, declared camera log, alpha, interlace, extra
tracks and conflicting unsupported color declarations are not waived by an
override. Unknown log encoding cannot be reliably diagnosed from appearance.

Automatic interpretation needs complete supported tags. An explicit Rec.709,
sRGB or BT.601 profile must have a genuine source basis. Missing color tags are
**not** evidence of Rec.709. An old request's disclosed unverified interpretation
is historical provenance, not a safe default for every future recording.

No transcript, 9:16 conversion, 30fps conversion, new captions, intro or soundtrack
is required. Preserve the selected original audio; do not silently discard or
transcode an unsupported codec to make browser MP4 succeed.

## Save and materialize an editable look

The native-portrait folder supplies a typed `GradingRecipe` example. Its
`input_profile: "auto"` deliberately does not pretend to know a new source's
encoding. The preset is a starting point, not measured artistic suitability.
Copy/edit it privately, preserve source correction versus creative look layers,
and choose the full source (`start: 0`, `end: null`) unless another range was
explicitly requested.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 prepare --video 'C:\Videos\source.mp4' --title 'New grade' --mode ai-assisted --brief 'ACTUAL USER BRIEF AND PRESERVATION CONSTRAINTS' --recipe 'C:\Private\recipe.json'
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 status --session SESSION_ID
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 recipe --session SESSION_ID
```

Replace all uppercase placeholders with returned identifiers/actual text before
execution. Save the **resolved recipe returned by the engine** before making
further changes; the preset's materialized parameters are part of provenance.
For an existing session, resume it rather than running `prepare` repeatedly.

Source corrections, look intensity, monotone curves, RGB controls, hard source-time
shot ranges and normalized protected rectangles are typed bounded data. They are
not semantic tracked masks, keyframes, RAW Kelvin calibration or arbitrary filter
scripts. Preserve burned-in UI/text with reviewed rectangles/neutral shot grades
only where warranted by the actual footage. Geometry/timing still stay intact.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 revise --session SESSION_ID --version CURRENT_VERSION --recipe 'C:\Private\candidate.json' --note 'ACTUAL FEEDBACK AND THE SPECIFIC CHANGE'
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 preview --session SESSION_ID --version CURRENT_VERSION --start SOURCE_SECONDS --duration 6
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 files --session SESSION_ID --job COMPLETED_PREVIEW_ID
```

CLI renders wait for their own job. Do not submit a duplicate when a job is still
running. A preview is at most 30 seconds; choose meaningful source ranges covering
light/dark material, people/neutrals, gradients and shot/protected-area boundaries.
Multiple previews can cover a longer source without pretending one proxy covers
every native-resolution defect.

## Inspect real evidence and iterate honestly

Each completed preview has a graded MP4, actual left-source/right-graded
`comparison.mp4`, matched source/graded PNGs, scopes and metadata. Source proxy
edges are at most720px; sample/scopes are reduced separately. Use the returned
manifest/paths/URLs, fetch local artifacts when needed and verify their identity.
Do not treat a file listing as a visual inspection.

Inspect actual moving transitions or multiple decoded frames with the limit
stated. Check skin/neutrals, clipping, highlight/shadow separation, hue stability,
banding, encoded text and every relevant shot join. Review PNGs are converted and
tagged sRGB; diagnostic scopes measure reduced decoded signal. Neither is
calibrated full-resolution colorist qualification or proof of direct listening.

Retain source, recipe/revision, processor/LUT, artifact hashes and exact source
windows. Source seconds, preview-relative time and final-relative time are not
interchangeable. Native browser seek mapping is approximate.

Present the actual candidate when the current request requires feedback. Save
real changes as immutable new revisions; restored old recipes are unapproved.
Pending feedback means stop safely with exact resumable IDs, not fabricated
approval or unattended attempts until an arbitrary score passes.

## Approval, final exports and handoff

The A/B-review skill stops with review files and **does not require or fabricate
look approval**. For a final grade follow the core skill's explicit exact-candidate
approval gate. The source, recipe/range/target, processor, regenerated LUT and
reviewed preview identities must still match.

```powershell
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 approve --session SESSION_ID --version CURRENT_VERSION --preview REVIEWED_PREVIEW_ID --confirmation approve-reviewed-look --note 'ACTUAL EXACT-CANDIDATE USER APPROVAL'
& '.\.venv\Scripts\python.exe' -m clipfarm grading --studio http://127.0.0.1:8741 export --session SESSION_ID --version CURRENT_VERSION
```

Read the current version again between these commands; placeholders are not
ready-to-run authorization. There can be several actual reviewed `--preview`
arguments. Successful encoding, a fixture, silence or "do the needful" is not
user aesthetic approval. Historical delegated export permission must remain
labelled as such and must never be copied into a new source's approval.

Final browser MP4 is lossy H.2648bit4:2:0 and requires compatible even geometry
and original AAC/MP3 or no audio. Supported MKV is lossy H.26410bit4:4:4 with
compatible original audio and is not guaranteed browser-playable or archival.
Final frame count/every relative PTS and original audio packet sequence/A/V clock
are verified by the engine. Range audio remains packet-boundary, not sample-accurate
new mixing. Container metadata/chapters are not comprehensively copied.

Give actual final paths plus source/recipe/output identity and honest review/color
limitations. There is no automatic cover, posting gallery, upload, certified
filmmaker emulation or human/professional acceptance. Preserve earlier editions.

## Recovery

On a version conflict, reload and reconcile rather than retrying an old write.
On missing/tampered evidence or changed processor/source, create fresh evidence
and obtain the approval required for that exact candidate; do not edit hashes.
On unsupported color/audio/geometry, report the actual gate, not a successful
fallback with discarded data. Resume with saved session/revision/job IDs.
Cancellation targets only the owned job; no broad process termination, old
producer replay or deletion of another session's artifacts.
