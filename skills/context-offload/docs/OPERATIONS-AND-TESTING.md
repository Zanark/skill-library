# Operations and Testing

## 1. Operational objectives

Operations must preserve:

- Resumability as the same persona.
- Correct current-base ownership.
- Freshness within the 12-hour maximum.
- Continuous milestone persistence.
- Honest provenance and stale-state labels.
- Cross-base references without duplication.
- Secret-free stores and zmem.
- A refreshed and readable Context Mesh.

These objectives restate the prime directive, core rules, closeout workflow, and guardrails
(`../SKILL.md:L13-L19`, `../SKILL.md:L23-L44`, `../SKILL.md:L133-L139`,
`../SKILL.md:L192-L199`).

## 2. Startup runbook

### Required procedure

1. Read the full Context Mesh digest.
2. Resolve the current directory against `context-index.json` using the longest match.
3. If unmatched, register the base while leaving existing siblings read-only.
4. Read current `STATE.md`, freshness marker, and `MEMORY.md`.
5. If stale, complete a full offload before context-dependent work.
6. Skim relevant base docs.
7. Query zmem for the current topic.
8. Adopt the persona.

Source: `../SKILL.md:L108-L119`.

### Startup acceptance checks

- Exactly one most-specific base is selected.
- The selected store belongs to that base.
- `STATE.md` and `MEMORY.md` are readable.
- The freshness marker parses exactly.
- Age calculation treats 12:00:00 as stale.
- The adopted persona matches the registry.
- No sibling file is modified.

The first six checks test normative requirements; the “exactly one” phrasing is a **recommended assertion**
for validating longest-match behavior.

## 3. Offload runbook

### Milestone offload

1. Re-read current state.
2. Update current focus, threads, next steps, and questions.
3. Add durable facts to memory.
4. Add a newest-first journal entry.
5. Refresh Context Mesh after the store changes.

Source: `../SKILL.md:L121-L131`.

### Full offload

1. Complete the milestone steps.
2. Add a significant zmem episodic when applicable.
3. Confirm all persistence writes succeeded.
4. Advance the freshness marker.
5. Refresh Context Mesh.
6. Verify local store, zmem memory, marker, and digest readability.

Source: `../SKILL.md:L133-L139`.

## 4. Validation matrix

| Test ID | Condition | Expected result | Requirement |
|---|---|---|---|
| H-01 | Registered exact base path | Matching base selected | `../SKILL.md:L113-L114` |
| H-02 | Registered parent and nested base | Longest nested path selected | `../SKILL.md:L113-L114` |
| H-03 | No matching base | New base registered before normal work | `../SKILL.md:L27-L30`, `../SKILL.md:L113-L115` |
| H-04 | Marker absent | Store is stale | `../SKILL.md:L31-L34` |
| H-05 | Marker malformed | Store is stale | `../SKILL.md:L31-L34` |
| H-06 | Marker age 11:59:59 | Store may remain fresh | `../SKILL.md:L31-L34` |
| H-07 | Marker age 12:00:00 | Store is stale | `../SKILL.md:L31-L34` |
| H-08 | Long session crosses 12 hours | Full offload occurs immediately | `../SKILL.md:L126-L127` |
| S-01 | New base created | Exactly four required files and initial sections exist | `../SKILL.md:L48-L64` |
| S-02 | Milestone completed | `STATE.md` updated | `../SKILL.md:L121-L123` |
| S-03 | Durable decision made | `MEMORY.md` updated | `../SKILL.md:L122-L123` |
| S-04 | Significant action occurs | Newest-first journal entry added | `../SKILL.md:L124-L125` |
| S-05 | Store changed | Mesh refresh command runs | `../SKILL.md:L130-L131` |
| C-01 | Partial persistence failure | Marker remains unchanged | `../SKILL.md:L126-L138` |
| C-02 | Full persistence succeeds | Marker advances, mesh refreshes, outputs read back | `../SKILL.md:L133-L138` |
| P-01 | Stale ADO state | Text says “re-verify”; no invented status | `../SKILL.md:L41-L42` |
| P-02 | Sensitive token appears | Token omitted from store and zmem | `../SKILL.md:L149-L151`, `../SKILL.md:L194-L196` |
| X-01 | Sibling-owned detail referenced | Pointer exists; duplicate authoritative copy does not | `../SKILL.md:L43-L44` |
| X-02 | Registration occurs | Existing sibling stores remain unchanged | `../SKILL.md:L27-L30` |
| V-01 | Resumed persona writes output | Universal honesty and script invariants remain intact | `../SKILL.md:L155-L173` |

## 5. File-schema tests

### `STATE.md`

Verify:

- Starts with a `Last updated` line.
- Contains the exact `Last context offload` marker.
- Contains `Current focus`, `Threads`, `Open questions`, and `Environment reminders` for a newly created
  store.
- Current content does not present completed or stale work as active.

The first three checks are normative (`../SKILL.md:L54-L64`). The last is a recommended semantic check derived
from the honesty requirement (`../SKILL.md:L41-L42`).

### `MEMORY.md`

Verify:

- New stores contain `People`, `Conventions`, `Gotchas`, and `Context-offload protocol`.
- Entries are durable rather than momentary.
- Facts cite or name their evidence where practical.

The first two are normative (`../SKILL.md:L55-L64`, `../SKILL.md:L143-L151`). Evidence citation is a
recommendation supporting the source’s grounding invariant (`../SKILL.md:L160-L162`).

### `JOURNAL.md`

Verify:

- `> Newest at top.` exists in a new store.
- Entries are in reverse chronological order.
- Significant work has timely entries rather than only an end summary.

Source: `../SKILL.md:L35-L38`, `../SKILL.md:L56-L64`.

### `README.md`

Verify:

- Base identity is explicit.
- Persona-continuity contract is explicit.
- The file describes protocol rather than transient state.

Source: `../SKILL.md:L57-L64`.

## 6. Failure modes and recovery

### 6.1 Wrong base selected

**Risk:** writes go to the wrong persona’s source of truth.

**Recovery recommendation:**

1. Stop writes.
2. Re-run longest-path resolution.
3. Inspect whether any sibling file changed.
4. Restore unauthorized sibling changes from verified source control or backup.
5. Record the correction in the proper current base’s journal if durable.

The underlying normative boundary is current-base resolution and sibling read-only behavior
(`../SKILL.md:L27-L30`, `../SKILL.md:L113-L115`).

### 6.2 Timestamp-only freshness update

**Risk:** the marker claims freshness while the content remains stale.

**Recovery:** restore the prior marker if possible, perform the complete offload, then advance it only after
success (`../SKILL.md:L31-L40`, `../SKILL.md:L126-L138`).

### 6.3 Partial persistence

**Risk:** state, journal, zmem, and mesh disagree.

**Recovery:** leave the marker unchanged, reconcile every layer, rerun mesh refresh, and read back all outputs.
This follows the source’s required ordering and verification (`../SKILL.md:L133-L139`).

### 6.4 Fabricated or inferred current state

**Risk:** later sessions trust false status.

**Recovery:** replace the claim with sourced historical wording, label the current state “re-verify,” add the
needed validation step, and journal the correction (`../SKILL.md:L39-L42`,
`../SKILL.md:L160-L162`).

### 6.5 Cross-base duplication

**Risk:** two stores become competing authorities.

**Recovery:** choose the domain owner, retain the authoritative detail there, and replace the other copy with
a pointer (`../SKILL.md:L43-L44`, `../SKILL.md:L128-L129`).

### 6.6 Sensitive material persisted

**Risk:** credentials or private data become durable and indexed.

**Recovery recommendation:** stop propagation, remove the sensitive value from every writable persistence
layer, rotate exposed credentials through the appropriate secure process, and retain only a redacted incident
note if useful. The prohibition itself is normative (`../SKILL.md:L149-L151`,
`../SKILL.md:L194-L196`); rotation details are operational recommendations.

### 6.7 Mesh refresh fails

**Risk:** the store is current but portfolio discovery remains stale.

**Recovery recommendation:** report the failure plainly, keep the local store as the authoritative current-base
record, do not pretend the mesh is refreshed, repair the generator/input issue, rerun `--check`, and verify the
digest. Refresh is required by `../SKILL.md:L130-L138`.

## 7. Security and privacy checks

Before persistence:

- Search proposed content for secrets, credentials, tokens, private keys, cookies, connection strings, and
  sensitive payloads.
- Confirm personal information is necessary and consented.
- Prefer identifiers and links over copied payloads when the identifier is sufficient.
- Confirm sibling content is referenced, not copied.
- Confirm the store contains no speculative claims presented as fact.

The first, second, fourth, and fifth checks directly support normative guardrails
(`../SKILL.md:L39-L44`, `../SKILL.md:L149-L151`, `../SKILL.md:L192-L199`). The third is a recommendation.

## 8. Maintenance and change-impact matrix

| Source area changed | Required review impact |
|---|---|
| Prime directive or core rules (`L13-L44`) | Review every document, state machine, freshness test, and runbook |
| Store schema (`L48-L64`) | Update templates, file tests, examples, and registration procedure |
| Persona registry (`L68-L104`) | Update registry reference, base-resolution scenarios, and cross-skill docs |
| Workflow (`L108-L139`) | Update state machine, runbooks, closeout ordering, and acceptance tests |
| Admission rules (`L143-L151`) | Update content classification and privacy tests |
| Voice/honesty invariants (`L155-L173`) | Update provenance, persona, and output validation |
| Memory relationships (`L177-L188`) | Update layered architecture and Context Mesh/zmem interaction |
| Guardrails (`L192-L199`) | Update security, failure recovery, and sibling-boundary tests |

This matrix is a **recommendation** for maintaining derived documentation against the normative source.

## 9. Regression checklist

- [ ] All six documentation files still cite valid line ranges.
- [ ] No documentation describes a recommendation as mandatory source behavior.
- [ ] File names, marker format, fixed paths, and command text match `SKILL.md`.
- [ ] The 12-hour boundary uses `>= 12 hours`, not `> 12 hours`.
- [ ] Marker advancement remains after persistence success.
- [ ] Registration leaves sibling stores read-only.
- [ ] Cross-base examples use references rather than duplicated state.
- [ ] zmem is selective and cross-cutting, not a replacement for the base store.
- [ ] Context Mesh refresh follows store or relevant zmem changes.
- [ ] Security tests prohibit secrets in both `.agent-context/` and zmem.
- [ ] Persona behavior preserves universal honesty and script invariants.

## 10. Recommended review cadence

**Recommendation.** Re-run the regression checklist whenever `SKILL.md` changes, whenever a new base is added,
or whenever Context Mesh changes its resolution/output contract. The source mandates the behaviors being
checked but does not prescribe a review schedule.

