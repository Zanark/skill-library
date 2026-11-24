# Operations and verification

## What this package does and does not run

The package is primarily Markdown and reusable templates. Its optional
credential runner uses Python's standard library and local Git, with no pip
dependencies. It has no browser requirement or synchronizer of its own.
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

For credential-runner or payload-boundary changes, also run:

```powershell
python -m unittest discover -s tests -p test_github_credentials.py
python -m unittest discover -s tests -p test_portability.py
```

Use dummy fixture values only. Never open/hash the real `.env` to prove
exclusion; inspect ignore/tracking metadata and catalogue paths instead.
Both the validator and portable tooling must reject forced-tracked `.env`
files, without needing their contents. An empty provisioned file is not proof
of successful token access; the owner must supply its value locally.

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
11. GitHub tracking guidance preserves eight-field workstreams, stable identity,
    separate issue/Project states, privacy and credential boundaries. Adoption
    records are not runnable configurations; documented sync is not executed sync.
12. Persistent credential lookup handles absent/stale process inheritance without
    printing secrets or claiming encrypted User environment storage. Workflow
    scopes, task authority, hosted secrets and actual run evidence stay distinct.
13. Local `.env` stays ignored/untracked and outside generated payloads. Runner
    diagnostics do not echo secrets, malformed files fail instead of using
    stale credentials, and parent authentication remains unchanged.
14. Concurrent-use guidance preserves a stable user instance by default, makes
    live preview opt-in and distinguishes source/process separation from actual
    file/profile/backend/resource isolation. Coexistence evidence is not inferred
    from two launches or a separate port, nor tested on the user's active session.
15. Promotion needs authority and a coordinated save point. Recovery covers data
    compatibility and later writes, not just old binaries. Process ownership is
    rechecked before stopping specific agent helpers; unavoidable interruptions
    and fixture-only qualification remain explicit.
16. Commit guidance requires frequent coherent verified milestones, not arbitrary
    counts or unfinished fragments. Author/committer attribution and Zanark PAT
    login/transport authentication are separate checks; shared settings,
    unrelated staging and implicit push authority are prohibited. This manual
    update is not evidence that any project committed or adopted the policy.

## Applying concurrent-use acceptance to an application

These are checks to perform when adopting section 4.6 in a target application,
not outcomes established by updating this Markdown package:

- Record protected/candidate build identities, paths/URLs, verified process
  ownership and all shared mutable state/resources using template 15.
- In isolated representative sessions, save and reopen actual workflow state
  while rebuilding, testing and restarting the candidate; induce a bounded
  candidate failure and verify the protected session and served files survive.
- Verify effective desktop profiles/single-instance behavior or website
  storage/cookies/service workers/API/database routing, not flags/ports alone.
- Confirm resource contention has a safe alternative or coordinated pause.
  Keep the user's actual browser profile, documents and devices out of automation.
- For an authorized switch, preserve work, verify selected build/state and
  exercise compatible recovery only in an authorized disposable setup. Record
  any migration/rollback path not exercised and distinguish user acceptance.

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
