# Worked Examples

Each example distinguishes required behavior from optional implementation advice.

## 1. Fresh-session hydration in a registered base

### Scenario

The current working directory resolves to `Runner`, and `STATE.md` has a valid offload marker from four hours
ago.

### Normative execution

1. Read the complete Context Mesh startup digest.
2. Resolve the current directory using the longest matching `basePath`.
3. Read Runner’s `STATE.md`, including the marker, then `MEMORY.md`.
4. Confirm the marker is younger than 12 hours.
5. Skim relevant Runner docs.
6. Run:

   ```powershell
   zmem read --query "runner monitor investigation"
   ```

7. Adopt the runner/synthetic-monitoring persona.
8. Continue from the stored threads without asking the user to restate established context.

The startup order and persona adoption are normative (`../SKILL.md:L108-L119`); Runner’s registered role is
defined in `../SKILL.md:L76-L77`.

### Recommendation

Record the evidence used to resolve the base and calculate freshness in diagnostic output when troubleshooting
hydration, but do not add noisy diagnostics to the durable store unless they are themselves useful later.

## 2. Stale store at startup

### Scenario

`Last context offload` is 13 hours old.

### Normative execution

1. Treat the store as stale because the threshold is “at least 12 hours.”
2. Do not perform context-dependent work yet.
3. Read the existing state and memory before editing.
4. Reconcile active threads against available evidence.
5. Mark unverified operational state “re-verify.”
6. Update state, memory, and journal.
7. Persist a significant zmem episodic if appropriate.
8. Advance the freshness marker only after persistence succeeds.
9. Refresh Context Mesh and verify all outputs are readable.

The threshold and remediation are defined in `../SKILL.md:L31-L40`; honesty and commit ordering are defined in
`../SKILL.md:L41-L42` and `../SKILL.md:L126-L138`.

### Incorrect behavior

- Treating “12 hours and 1 minute” as still fresh.
- Updating only the timestamp without reconciling content.
- Inventing a current ADO or incident status.
- Advancing the marker before the journal or zmem write succeeds.

Each conflicts with the cited freshness, honesty, or ordering rules.

## 3. Registering a new base

### Scenario

No `context-index.json` entry matches `C:\work\NewProduct`, and the user has not named another root.

### Normative execution

Create:

```text
C:\work\NewProduct\.agent-context\
  README.md
  STATE.md
  MEMORY.md
  JOURNAL.md
```

Seed:

```markdown
> This store belongs to NewProduct and preserves the NewProduct persona and working continuity.
```

Add the required `STATE.md` markers and sections, the required `MEMORY.md` sections, and the newest-first
journal declaration. Add a registry row that names the base, persona, and scope. Add relevant references
without copying sibling content. Refresh Context Mesh, then restart hydration.

The registration trigger and sibling read-only boundary are normative (`../SKILL.md:L27-L30`); file templates
are normative (`../SKILL.md:L59-L64`); registry and refresh actions are normative
(`../SKILL.md:L101-L104`).

### Recommendation

Choose a persona description that is narrow enough to establish ownership but broad enough to cover the
base’s expected long-running work.

## 4. Milestone during active work

### Scenario

A pipeline investigation identifies the authoritative owner, rules out one suspected cause, and creates a new
follow-up.

### Normative persistence

`STATE.md`:

```markdown
## Current focus

- Pipeline investigation completed; follow-up validation remains.

## Threads

- Validate the remaining deployment-stage hypothesis.
```

`MEMORY.md`:

```markdown
## People

- The verified pipeline owner is <name/source>.

## Gotchas

- The previously suspected cause was disproved by <evidence>.
```

`JOURNAL.md` at the top:

```markdown
## 2026-10-04 — Pipeline investigation milestone

- Confirmed ownership from <source>.
- Ruled out <hypothesis> using <evidence>.
- Added the remaining validation step.
```

Then refresh Context Mesh.

The required file selection and refresh behavior follow `../SKILL.md:L121-L131`. The example wording is
illustrative, not a mandated template.

## 5. Cross-base handoff without duplication

### Scenario

A WorkDesk thread grows into sustained Runner-domain work.

### Normative outcome

- Runner becomes the authoritative base for detailed runner status.
- WorkDesk retains a concise pointer to Runner.
- The operating session does not rewrite unrelated sibling context.
- Context Mesh is refreshed after the current base’s context change.

The source explicitly uses the WorkDesk-to-Runner move as the example of honest cross-reference behavior
(`../SKILL.md:L43-L44`, `../SKILL.md:L128-L131`).

### Incorrect outcome

Maintaining two independently edited copies of the same runner status. That violates the cross-reference rule
and creates competing sources of truth.

## 6. Significant end-of-session offload

### Scenario

A session completes a feature decision, updates a runbook, and leaves two verified follow-ups.

### Normative execution

1. Update `STATE.md` with completion, follow-ups, and current open questions.
2. Add durable decision and rationale to `MEMORY.md`.
3. Add a dated newest-first journal entry.
4. Write:

   ```powershell
   zmem write episodic "Feature decision completed" `
     --detail "Decision, rationale, evidence, and remaining follow-ups" `
     --tags offload feature
   ```

5. After those writes succeed, set the exact `Last context offload` marker.
6. Run:

   ```powershell
   python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
   ```

7. Read back the four store files, zmem entry, marker, and digest.

The closeout transaction is normative (`../SKILL.md:L133-L139`).

## 7. Unverified operational state

### Scenario

The store says a work item was active yesterday, but no current ADO lookup has been performed.

### Correct text

```markdown
- Historical state: Active as of the last verified lookup.
- Current state: re-verify before presenting as current.
```

### Why

The source forbids fabricating fresh ADO, sprint, or thread state and requires stale information to be marked
“re-verify” (`../SKILL.md:L41-L42`, `../SKILL.md:L160-L162`).

## 8. Sensitive value discovered during work

### Scenario

Command output includes a token or connection string.

### Normative execution

- Do not put the value in `STATE.md`, `MEMORY.md`, `JOURNAL.md`, `README.md`, or zmem.
- Persist only a non-sensitive statement if it is useful, such as “authentication failed; credential value
  intentionally omitted.”

The exclusion of sensitive content, secrets, and tokens is normative
(`../SKILL.md:L149-L151`, `../SKILL.md:L194-L196`).

### Recommendation

If an excerpt is required for diagnosis, redact both the secret and enough surrounding material to prevent
reconstruction.

## 9. Persona continuity after compaction

### Scenario

The chat compacts in KnowledgeLedger.

### Normative execution

Before compaction, reconcile and persist state, journal, significant zmem memory, freshness marker, and mesh.
After compaction, hydrate from those layers and resume as the MAB/ASR learning architect and tutor
(`../SKILL.md:L81-L81`, `../SKILL.md:L133-L139`).

### Acceptance criterion

The resumed session can identify the current lesson, the learner’s established preferences, completed
material, evidence, and next step without inventing missing history or asking for already-persisted facts.
This criterion is a **derived interpretation** of the persona-continuity contract
(`../SKILL.md:L13-L19`).

## 10. Twelve-hour rollover during one long session

### Scenario

A session starts with a fresh marker, works continuously, and reaches the 12-hour boundary.

### Normative execution

1. Pause context-dependent work at the boundary.
2. Complete the full offload transaction.
3. Advance the marker only after successful persistence.
4. Refresh and verify Context Mesh.
5. Resume work from the newly fresh state.

The 12-hour rule applies during long-running chats, not only at startup
(`../SKILL.md:L31-L38`, `../SKILL.md:L126-L127`).

