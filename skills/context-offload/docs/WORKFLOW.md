# Workflow

## 1. Normative state machine

The lifecycle can be represented as:

```text
UNRESOLVED
  -> resolve current directory through Context Mesh
  -> MATCHED or UNREGISTERED

UNREGISTERED
  -> create only the new base's four-file store
  -> add persona registry entry and cross-references
  -> refresh Context Mesh
  -> MATCHED

MATCHED
  -> read STATE marker and MEMORY
  -> FRESH or STALE

STALE
  -> reconcile and complete full offload
  -> advance marker only after persistence succeeds
  -> refresh and verify
  -> FRESH

FRESH
  -> hydrate docs and zmem
  -> adopt persona
  -> ACTIVE

ACTIVE
  -> milestone updates / durable-memory updates / journal entries
  -> refresh mesh after store or relevant zmem changes
  -> ACTIVE

ACTIVE
  -> 12 hours elapsed
  -> STALE

ACTIVE
  -> compaction or end
  -> FINALIZING
  -> persist STATE/JOURNAL/zmem
  -> advance marker
  -> refresh and verify
  -> OFFLOADED
```

The transitions are a structured restatement of the startup, continuous-offload, and closeout rules
(`../SKILL.md:L108-L139`). “UNRESOLVED,” “MATCHED,” and similar names are explanatory labels, not source-defined
status strings.

## 2. Startup hydration

### Step 1 — Read the startup digest

Read:

```text
C:\devdesk\Copilot\CopilotSessions\context-network\output\CONTEXT-MESH.md
```

This is the first normative hydration step (`../SKILL.md:L110-L112`).

### Step 2 — Resolve the current base

Compare the current working directory against `context-index.json` and choose the longest matching base path
(`../SKILL.md:L113-L114`).

**Derived interpretation.** Longest-match resolution lets a nested registered base override a broader parent
base without ambiguity.

### Step 3A — Register an unmatched base

If no base matches:

1. Select the current working directory, unless the user explicitly names another root.
2. Create `<base>\.agent-context\`.
3. Seed `STATE.md`, `MEMORY.md`, `JOURNAL.md`, and `README.md` using the required schema.
4. Add the persona row to the registry.
5. Add relevant cross-references.
6. Refresh Context Mesh.
7. Restart hydration against the newly registered base.

Registration and its required artifacts are normative (`../SKILL.md:L27-L30`,
`../SKILL.md:L59-L64`, `../SKILL.md:L101-L104`, `../SKILL.md:L113-L115`).

During registration, existing sibling stores remain read-only (`../SKILL.md:L27-L30`).

### Step 3B — Read current-base state

Read `STATE.md`, including the exact `Last context offload` marker, then read `MEMORY.md`
(`../SKILL.md:L115-L116`).

**Recommendation.** Read the files in that order so the current task and freshness status frame the durable
facts that follow.

### Step 4 — Evaluate freshness

Parse:

```text
> **Last context offload:** YYYY-MM-DDTHH:mm:ss+05:30
```

Treat the store as stale when the marker is:

- Missing.
- Invalid.
- At least 12 hours old.

The stale conditions and full-offload requirement are normative (`../SKILL.md:L31-L34`,
`../SKILL.md:L115-L116`).

### Step 5 — Reconcile stale state

Before context-dependent work:

1. Read before writing.
2. Compare live evidence with the stored current state.
3. Mark uncertain or old operational facts “re-verify.”
4. Update state, memory, and journal as appropriate.
5. Complete the full persistence sequence.
6. Advance the freshness marker only after success.

These actions combine the source’s read-before-write, non-fabrication, stale-state, and marker-ordering rules
(`../SKILL.md:L39-L42`, `../SKILL.md:L126-L138`).

### Step 6 — Read deep references and zmem

Skim the base’s top-level docs or README as needed, then run:

```powershell
zmem read --query "<current topic>"
```

This is normative startup behavior (`../SKILL.md:L117-L118`).

### Step 7 — Adopt the persona

Adopt the registry’s scope and voice for the resolved base and continue as if the previous session had not
been interrupted (`../SKILL.md:L68-L72`, `../SKILL.md:L119-L119`).

## 3. Continuous offload while working

### 3.1 Milestone decision table

| Event | Required persistence | Source |
|---|---|---|
| Sub-task completed | Update `STATE.md` | `../SKILL.md:L121-L123` |
| Plan changed | Update `STATE.md` | `../SKILL.md:L121-L123` |
| Durable fact or decision established | Update `MEMORY.md` and current state if operationally relevant | `../SKILL.md:L122-L123` |
| Lookup resolved or thread advanced | Add newest-first `JOURNAL.md` entry | `../SKILL.md:L124-L125` |
| User preference stated | Add journal evidence; add to memory if durable | `../SKILL.md:L124-L125`, `../SKILL.md:L145-L147` |
| Context store changed | Refresh Context Mesh | `../SKILL.md:L130-L131` |
| Relevant zmem memory written | Refresh Context Mesh | `../SKILL.md:L130-L131` |
| 12 hours elapsed | Perform a full offload immediately | `../SKILL.md:L126-L127` |

### 3.2 File selection algorithm

Ask four questions:

1. Does this describe the current working position? Put it in `STATE.md`.
2. Is it expected to remain true across future sessions? Put it in `MEMORY.md`.
3. Is it evidence of what happened and when? Put it in `JOURNAL.md`.
4. Does it define the base identity or protocol? Put it in `README.md`, rarely.

This algorithm is a **derived interpretation** of the normative file roles
(`../SKILL.md:L48-L64`).

### 3.3 Cross-base content

When a thread belongs to another base:

- Keep the authoritative detail in the owning base.
- Replace copied material in the current base with a reference or handoff.
- Do not edit a sibling store while operating under the current base.

Cross-reference rather than duplicate is normative (`../SKILL.md:L43-L44`), and the source gives the
WorkDesk-to-Runner handoff as the model (`../SKILL.md:L128-L129`).

## 4. Full offload transaction

A full offload is best treated as an ordered transaction:

1. **Read and reconcile.** Never write from a stale mental model.
2. **Update `STATE.md`.** Make focus, threads, next steps, and open questions reflect reality.
3. **Update `MEMORY.md`.** Add only verified durable facts, decisions, gotchas, conventions, people, and
   tooling facts.
4. **Update `JOURNAL.md`.** Add a dated newest-first entry describing the significant activity.
5. **Write zmem if significant and cross-cutting.** At closeout, use an episodic entry when appropriate.
6. **Confirm persistence succeeded.**
7. **Advance `Last context offload`.**
8. **Refresh Context Mesh.**
9. **Verify store, zmem memory, marker, and digest are readable.**

The ordering is normative at closeout (`../SKILL.md:L133-L139`). Steps 1–4 also follow the continuous-offload
and file-role rules (`../SKILL.md:L35-L40`, `../SKILL.md:L48-L64`).

### Why the marker is late

The source requires advancing the marker only after all persistence steps succeed
(`../SKILL.md:L126-L138`). Therefore the marker is a commit indicator, not a “started offload” timestamp.

## 5. End-of-session or compaction workflow

Before ending or compaction:

1. Re-read current `STATE.md`.
2. Remove completed work from active focus or label it completed.
3. Ensure next steps and open questions are truly current.
4. Add the dated journal summary.
5. Write the significant zmem episodic:

   ```powershell
   zmem write episodic "…" --detail "…" --tags offload …
   ```

6. Set the exact freshness marker only after the previous writes succeed.
7. Run the mesh refresh:

   ```powershell
   python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
   ```

8. Read back the local files, zmem result, marker, and generated digest.

The required content and command are normative (`../SKILL.md:L130-L138`). Reading back all persisted layers
is explicitly required (`../SKILL.md:L137-L138`).

## 6. Content admission workflow

### Offload

Persist decisions and rationale, conventions, gotchas and fixes, thread status and next steps, people and
ownership, tooling facts, stated preferences, resolved provenance lookups, and thread-related ADO/IcM IDs
(`../SKILL.md:L143-L147`).

### Skip

Do not persist transient date/branch/file state, scratch values, speculation, half-conclusions, easily
re-derived values, or sensitive information without explicit consent (`../SKILL.md:L149-L151`).

### Uncertain information

Do not make uncertainty disappear through confident wording. Mark stale state “re-verify,” cite its source,
and leave a clear next verification action (`../SKILL.md:L39-L42`, `../SKILL.md:L160-L164`).

## 7. Registration workflow detail

For each of the four new files, seed a blockquote describing:

- The base identity.
- The persona-continuity contract.

Then seed:

```text
STATE.md
  > Last updated
  > Last context offload
  ## Current focus
  ## Threads
  ## Open questions
  ## Environment reminders

MEMORY.md
  ## People
  ## Conventions
  ## Gotchas
  ## Context-offload protocol

JOURNAL.md
  > Newest at top.
  [empty dated structure]

README.md
  protocol + base identity + persona-continuity contract
```

This exact initial schema is normative (`../SKILL.md:L59-L64`).

## 8. Failure-state transitions

### Mesh resolution unavailable

**Normative principle:** startup begins by resolving through Context Mesh (`../SKILL.md:L110-L114`).

**Recommendation:** report the unavailable input plainly and avoid guessing the current base. Do not edit a
sibling store while resolution is uncertain.

### Invalid freshness marker

Treat it as stale and complete a full offload before context-dependent work
(`../SKILL.md:L31-L34`).

### Partial write

Do not advance the marker. Re-read the affected files, repair the incomplete persistence, then repeat refresh
and verification. The source’s commit-order rule supports this recovery behavior
(`../SKILL.md:L126-L138`).

### Unverified live status

Label it “re-verify” rather than inventing an update (`../SKILL.md:L41-L42`,
`../SKILL.md:L160-L162`).

### Sensitive material detected

Exclude it from both `.agent-context/` and zmem (`../SKILL.md:L149-L151`,
`../SKILL.md:L194-L196`).

