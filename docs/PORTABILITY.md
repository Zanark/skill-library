# Portable skills and private migration

The public repository contains ten skill definitions, their operating docs,
and the implementation projects behind Context Mesh, ClipFarm, Documentation
Mesh and Speak. It does **not** contain private conversations, recordings, career
evidence, credentials or Microsoft's internal zmem implementation.

## New Windows machine

Prerequisites: Windows x64, Python 3.13, Node.js 18+ with npm, Git, and an installed
Copilot CLI. Microsoft Edge is needed only for browser tests. Network access is
needed for the explicit dependency restore; bundled HTML demos work offline.
Consolas and Windows SAPI voices are operating-system prerequisites, not copied
font/voice licenses. Different hardware/codecs/voices need not render identically.

From the cloned repository:

```powershell
python .\scripts\verify_portable_payload.py
python .\scripts\install_skill_library.py --install-dependencies
.\scripts\Validate-SkillLibrary.ps1
```

By default, runtime projects go under `%LOCALAPPDATA%\SkillLibrary`, and skills
under `%USERPROFILE%\.copilot\skills`. The installer prints their full resolved
paths. It rewrites installed skill references to the selected runtime, clone,
private KB and report locations; source snapshots remain unchanged.

Use `--runtime-root` and `--skills-directory` to select other destinations.
Differing runtime files are never overwritten: choose a new runtime root.
Differing installed skills stop installation unless `--replace-skills` is
explicitly selected; that option saves backups first. Dependency installation
requires `--install-dependencies`. Without it, payloads and instructions are
installed but missing Node/Python dependencies are **not** supplied.

The installer never edits agent permissions, trusted directories, authentication
or global MCP registration. Review `mcp.speak.template.json` in the installed
runtime and register that server through the host's normal configuration UI.
This copy-only template does not enable tools by itself.

## What's supplied

| Skill | Public support | Separate prerequisite/state |
|---|---|---|
| ado-workplan | Skill, examples and operating docs | Authenticated ADO/WorkIQ services and private reports |
| career-forensics | Complete recovery/report instructions | Private CareerKB, source documents and protocols |
| clipfarm-leetcode | Python engine, static UI, tests, workflow docs, launch/install scripts, exact observed dependency versions | Original media, artwork rights, models, production ledgers and frozen producers |
| context-mesh | Generator, graph/chat/avatar renderers, tests, npm lockfile, config example, fictional offline snapshot | Context stores, stable color registry, archives, session-history inputs and optional private zmem |
| context-offload | Complete continuity/persona/social protocols and docs | Each base's own private context store; external zmem if used |
| dayplan | Skill and operating docs | Authenticated ADO/IcM/WorkIQ providers |
| development-documentation-manual | Detailed Markdown manual, workflow/reference, source-scoped cases, enrichment protocol and thirteen templates | The checkout supplies support files; no runtime or private portfolio data is bundled |
| documentation-mesh | .NET/Python source, templates, schemas, tests, build packaging, notices and checksum-verified Windows x64 executable | Source documentation, private workspace and optional Agency host |
| nse-advisor | Complete research/paper-trading instructions | Live research tools and user-provided data; no market-data service is bundled |
| speak | MCP server, dependency lockfile, plugin metadata and registration template | Windows PowerShell/SAPI and available local voices |

Documentation Mesh's executable is self-contained: running it needs no Python,
npm or .NET SDK. Rebuilding it requires the .NET 8 SDK. Its original MIT license
and third-party notices accompany the implementation. Other copied local
projects retain their existing metadata; this repository does not invent an
upstream license or make internal code publicly distributable.

ClipFarm's `constraints-windows-py313.txt` is an observed full environment freeze,
including auxiliary tools used by retained producers. The installer restores
that list plus the editable engine/workflow/dev extras. It does not copy a
machine-bound virtual environment or claim those packages will remain available
from upstream registries indefinitely.

The public ClipFarm TODO files are explicitly labelled workflow templates, so
the skill's required entry paths exist on a fresh machine. They do not claim
historical completion or replace the original private production catalogue.
The installer also binds the standalone Documentation Mesh skill directly to
its verified executable rather than assuming a plugin-relative directory.
Public editorial guides are sanitized derivatives; recording-based PDF/HTML
case studies, personal production histories and original manuals stay private.

The development/documentation manual is a new public-safe authored synthesis,
not a copy of those private originals. Its installed `SKILL.md` is rebased to
the current clone; the supporting manual/docs/templates remain in that clone,
not in the installed skill directory. Keep the clone available or deliberately
rebind through the guarded installer after moving it.

## Offline feature snapshot

Open `examples\context-mesh\context-mesh.html`. All six contexts, characters,
memories and messages are **fictional**. This uses the real renderer, including
the graph timeline, Play Battleground, portraits, profiles, chat and threads.
The archive remains hidden by default, just like the live interface. The sibling
`meshboard-archive.html` is a synthetic archive example, not real history.
Dependency notices are included beside these files.

Rebuild after installing dependencies:

```powershell
python .\scripts\build_portable_demo.py --mesh-runtime "$env:LOCALAPPDATA\SkillLibrary\context-mesh"
```

The fixture builder never reads the real zmem store, real context roots, live
archives or real session transcripts. These examples demonstrate features;
they are not a substitute for restoring actual identity/state.

## Private backup and exact duplicate mapping

The migration directory is deliberately Git-ignored. Transfer it separately
using an appropriately protected local drive or authorized private storage.
**Do not upload it to this public repository.** No encryption or confidentiality
guarantee is implied by `.gitignore`.

A complete archive contains:

- `manifest.json`: schema, completion flag, collections, counts and catalogue hash.
- `files.jsonl`: one entry per logical original file or explicit exclusion.
- `objects\<sha256>`: one object per unique retained content, including media.

Ignoring/untracking local context protects future commits, not old Git history
or copies previously published elsewhere. No history rewrite is performed.

Duplicate media paths reference the same object. SQLite databases use online
backups; their WAL/SHM/journal sidecars are excluded because replaying an old WAL
against a fresh backup is unsafe. Connections close before publishing snapshots.
These are per-file snapshots of running applications, not a simultaneous
transaction across every app.

Dependency trees, virtual environments, caches designated as recreatable,
directory links, live IPC endpoints and credential/trust/permission files are
explicitly accounted for rather than silently copied. Useful `.clipfarm`
producers, review artifacts, results, original artwork, archived output, context
stores, color registry, archived chat and historical session inputs belong in
the private archive. Referenced input discovery also inventories existing media
outside the project inside explicitly selected input roots; missing historical
references are recorded, not fabricated.

Credential filename exclusions and common-token redaction are defense in depth,
**not proof that private historical text or binaries contain no secrets**.
Text redaction is limited to UTF-8 files up to 20 MiB. Keep the entire private
archive confidential. Do not copy old authentication or permission grants.

Verify and restore to a **new isolated directory**, never directly over live data:

```powershell
python .\scripts\restore_skill_state.py --bundle "D:\private-migration\snapshot" --verify-only
python .\scripts\restore_skill_state.py --bundle "D:\private-migration\snapshot" --output "D:\restored-skill-state"
```

Restore verifies the complete catalogue and every unique blob before writing.
It rejects traversal, bad hashes, duplicate destinations and existing output
directories. Hashes detect corruption; they do not authenticate an untrusted
archive. Restoring does not run code, register personas or activate agents.
Collection, merging and restoration use Windows extended-length file APIs for
deep historical artifact paths, without changing logical paths or permissions.

## Reactivating private state

Keep the verified archive immutable and work from its restored copy.

1. Copy the `context-<id>` collections into chosen bases' `.agent-context`
   directories, preserving the existing persona IDs/seeds/reflections. Configure
   installed Context Mesh's `config.json` roots to those bases. Restore its
   `persona-colors.sqlite3` and both `meshboard-archive.*` files into that
   runtime's `output` together; do not merge them into a newly populated registry
   or overwrite existing state. Rebuild only after the roots are reviewed.
2. Keep historical `events.jsonl`/`workspace.yaml` inputs in an isolated
   `historical-sessions` directory and point `sessionStateRoot` there. Do not
   overwrite the new machine's live Copilot session state or imply that copying
   files guarantees native `copilot --resume` support. Original Poke GUIDs remain
   original creation-session identifiers; dormant agents are not auto-awakened.
3. Keep the complete restored ClipFarm tree, including `.clipfarm`, `results`,
   inputs, private TODO ledger and frozen producers. Before rerunning an old
   producer, reconcile its saved absolute media/export paths using the retained
   source inventory. The application accepts `--data-dir` for its SQLite/output
   root; that flag alone does not rewrite paths inside existing jobs.
4. Put private career/report collections at the rewritten installed skill
   locations, or deliberately update those skill paths to other chosen roots.
   Never interpret restoring a report as permission to publish it.
5. Restore the private zmem provider only through authorized internal access.
   Its source is not publicly available merely because package metadata says
   MIT. Inspect its supplied lockfile, restore its runtime dependencies, then use
   its documented store/import mechanisms. There is no assumed public
   `npm install -g zmem` distribution.

Moving bases changes path-derived context IDs; persona IDs and saved color
assignments must remain intact. Historical path citations stay historical.
Reconcile new roots and private producer references explicitly rather than
silently rewriting authored conversations, archive contents or old evidence.

Authenticate external services afresh. A repository clone can reproduce the
local implementations and examples; **a clone alone cannot reproduce private
history, missing original files, external service access, installed voices or
active CLI sessions**.

## Maintainer collection and verification

`package_skill_support.py --sources <private-config> --public` collects selected
source trees, refuses changed destination files and checks common credential
patterns. This heuristic does not replace source/privacy review. Local source
paths live only in ignored `skills-support.sources.json`.

Use `--private <new-directory-under-migration-private>` for a CAS snapshot;
`--resume` restarts only an incomplete snapshot and reuses checksum-verified
objects. `discover_skill_inputs.py` creates a private inventory of explicitly
referenced existing media. `merge_skill_state.py` merges complete archives into
one catalogue and one object per hash without another physical media copy on the
same filesystem.

`.gitattributes` disables Git newline conversion because the checksums cover
exact file bytes, including on Windows.

`portable-files.json` inventories the intended public payload. Regenerate it
after source/doc changes with `verify_portable_payload.py --build`; a fresh
copy can verify it without access to the original machine or its private state.
`source-inventory.json` now uses relative destinations; original absolute
`source` fields are historical provenance, not installer dependencies.

Ignoring an already tracked private context does not remove it from published
history. Untracking preserves local files but does not erase historical GitHub
copies. No history rewrite or remote publication is performed by these tools.
