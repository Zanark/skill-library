# Operations and verification

## What this package does and does not run

The package is Markdown and reusable templates. It has no application runtime,
browser requirement, Python dependency or cloud connection of its own.
The library's existing validator checks registration, required files, exact
skill hashes and relative file links. Those checks do not prove source accuracy,
anchor validity, editorial completeness or privacy clearance.

## Review gates for an ordinary documentation task

| Gate | Check |
|---|---|
| Scope | Requested artifact and permitted edits are explicit |
| Authority | Local contracts and exceptions are preserved |
| Source | Relevant text/implementation was actually read; source role/date clear |
| Meaning | Mechanisms, failures, trade-offs and limits are explained accurately |
| Navigation | Entry points, file links, stable IDs and section references agree |
| Evidence | Actual results separated from plans, history, fixtures and assumptions |
| Privacy | No secret/private body or unjustified public example is introduced |
| Output | If rendered output was requested, inspect it rather than only its source |
| Handoff | Full paths, exact achieved state and unresolved limitations |

Do not run unrelated runtime/media suites for a Markdown-only change. If a
documentation builder/test exists and the change affects it, use that gate.

## Maintaining this registered skill

From the library root:

```powershell
.\scripts\Validate-SkillLibrary.ps1
python .\scripts\verify_portable_payload.py --build
python .\scripts\verify_portable_payload.py
```

Before validation, update this skill's exact `SKILL.md` SHA-256 in
`source-inventory.json` if its bytes changed. Use a standard hash utility; do not
guess or copy an old value. The portable catalogue is generated tooling, not a
manual checklist. Rebuild only after the actual intended public files exist.

Inspect changed-file scope before/after. A large pre-existing staged worktree
must not be staged or committed indiscriminately.

## Semantic checks for this manual

1. Each named mode has a route, actual source basis, case, applicable evidence
   gate and transfer limit.
2. Each recommended schema is consistent across manual/reference/templates.
3. Source counts are labeled discovery, review or execution accurately.
4. Numeric constraints are attributed to their project/edition.
5. Proposed designs are not described as implemented.
6. Frozen and living artifacts have different update procedures.
7. No generic rule overrides an explicit front-page or local approval contract.
8. Context/social ownership rules defer to the dedicated installed skills.
9. Future enrichment has a repeatable source/novelty/supersession procedure.
10. All linked support files exist; anchors and catalogue routes are reviewed.

## Installation verification

The standard installer copies only `SKILL.md` for this definition and rebases
its support root to the clone. Test registration/portability using isolated
temporary destinations or focused binding tests; do not overwrite the user's
entire skill installation merely to check a new entry.

A valid installed entry must point to an existing checkout containing MANUAL,
docs and templates. Merely copying `SKILL.md` without its checkout path working
does not satisfy the support-file contract.

## Failures and recovery

- **Missing support root:** report it and restore/rebind the clone through the
  guarded installer. Do not invent a fallback manual.
- **Hash mismatch:** inspect actual source changes; update an authored skill
  deliberately, but do not silently repair archived external snapshots.
- **Broken relative link:** fix the source/navigation relationship, not the
  validator's exclusion list.
- **Source moved/stale:** record drift, re-review and update the receipt.
- **Private source needed:** retain a process-only statement or authorized private
  receipt; do not publish the source to make the manual look complete.
- **Output not inspected:** label it unverified; do not use structural checks as
  a substitute.

No action here grants commit, push, publication, permission changes or dependency
installation. Follow task authority and existing repository tooling.
