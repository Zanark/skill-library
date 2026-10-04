# Workflow

## 1. End-to-end state machine

```text
START
  -> READ_DIGEST
  -> RESOLVE_BASE

RESOLVE_BASE
  -> MATCHED
  -> UNREGISTERED

MATCHED
  -> HYDRATE_CURRENT_BASE
  -> CHECK_FRESHNESS
  -> READ_RELEVANT_SIBLINGS
  -> ACTIVE

UNREGISTERED
  -> CONTEXT_OFFLOAD_REGISTRATION
  -> REFRESH_MESH
  -> READ_DIGEST

ACTIVE
  -> STORE_OR_ZMEM_MILESTONE
  -> REFRESH_MESH
  -> VALIDATE_OUTPUTS
  -> ACTIVE

ACTIVE
  -> INSPECT_DASHBOARD
  -> ACTIVE

REFRESH_MESH
  -> SUCCESS
  -> FAILURE_REPORTED
```

The named states are explanatory. Their transitions restate the normative hydration and refresh sequences
(`../SKILL.md:L34-L59`).

## 2. Session startup

### Step 1 — Read the digest completely

Read:

```text
C:\devdesk\Copilot\CopilotSessions\context-network\output\CONTEXT-MESH.md
```

Partial scanning does not satisfy the source, which says to read the file completely
(`../SKILL.md:L36-L39`).

### Step 2 — Resolve the current base

Load:

```text
C:\devdesk\Copilot\CopilotSessions\context-network\output\context-index.json
```

Compare the working directory with `contexts[].basePath`, using a case-appropriate path comparison for the
platform, and select the longest match (`../SKILL.md:L25-L26`, `../SKILL.md:L38-L40`).

The source requires longest matching path; the comparison implementation detail is a **recommendation**.

### Step 3A — Matched base

Invoke/follow `context-offload`:

1. Read the current base’s `STATE.md`.
2. Read the exact `Last context offload` marker.
3. Read `MEMORY.md`.
4. Skim relevant docs.
5. Run `zmem read --query "<current topic>"`.
6. Adopt the current persona.

The mesh source explicitly delegates this behavior to `context-offload`
(`../SKILL.md:L40-L41`, `../SKILL.md:L46-L48`).

### Step 3B — Unregistered base

Use `context-offload` immediately to:

1. Register the current working base.
2. Create its four-file store.
3. Add its persona entry.
4. Refresh Context Mesh.
5. Restart hydration from the new store.

Existing stores remain read-only, and only the new current base’s store is created
(`../SKILL.md:L29-L30`, `../SKILL.md:L44-L45`).

### Step 4 — Check freshness

If the exact marker is missing, invalid, or at least 12 hours old:

- Treat the base as stale.
- Perform a full offload before context-dependent work.
- Repeat the same rule after each 12-hour interval in a long session.

Source: `../SKILL.md:L46-L48`.

### Step 5 — Use relationships

Use the mesh graph to identify related sibling contexts. Read a sibling only when relevant, and treat it
strictly as reference material (`../SKILL.md:L42-L43`).

## 3. Refresh workflow

### Trigger

Refresh after:

- Any `.agent-context` milestone.
- Any zmem offload.

Source: `../SKILL.md:L50-L55`.

### Command

```powershell
python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
```

Source: `../SKILL.md:L52-L56`.

### Success gate

A successful build:

1. Reports at least one context.
2. Produces `CONTEXT-MESH.md`.
3. Produces `context-index.json`.
4. Produces `context-mesh.html`.

Source: `../SKILL.md:L58-L59`.

### Failure gate

If the build fails:

- Report failure plainly.
- Do not generate or present a success-shaped fallback.

Source: `../SKILL.md:L58-L59`.

**Recommendation.** Preserve the last known-good outputs rather than overwriting them with incomplete files,
if the generator implementation supports atomic publication. This is operational advice, not a source
requirement.

## 4. Dashboard workflow

### Open on Windows

```powershell
Start-Process C:\devdesk\Copilot\CopilotSessions\context-network\output\context-mesh.html
```

Source: `../SKILL.md:L85-L89`.

### Portfolio status

Use context cards and freshness filters to find:

- Stale contexts.
- Current focus and threads.
- Next steps and open questions.
- Memory and timeline.

These card and filter capabilities are normative (`../SKILL.md:L65-L66`).

### Relationship investigation

1. Start with the conservative default graph.
2. Select a node or connection.
3. Inspect confidence, relationship class, and persisted file/line evidence.
4. Enable context-memory or zmem detail only when needed.
5. Enable incidental-reference evidence only when lower-confidence discovery is useful.
6. Do not treat a path or name match as strong evidence.

Source: `../SKILL.md:L70-L75`.

### Layout workflow

- Connected families begin at central anchors.
- Isolated contexts and unscoped memory remain farther out.
- Drag and pin a context to relocate its family and center the viewport.
- Use unpin-all to reset custom anchors.

Source: `../SKILL.md:L81-L83`.

### Timeline workflow

1. Start the one-shot chronological animation.
2. Stop or replay as needed.
3. Interpret context dates as earliest dated journal evidence.
4. Interpret zmem dates as creation timestamps.
5. Respect inherited/unknown labels.
6. Do not infer precision beyond the displayed provenance.

Source: `../SKILL.md:L76-L78`.

## 5. Artifact Finder workflow

### Query

Search by:

- Full path.
- Filename.

The finder normalizes browser copy suffixes (`../SKILL.md:L67-L69`).

### Evaluate results

For each result, inspect:

- Evidence type.
- Chat name.
- Session ID.
- Working directory.
- Timestamp.
- Observed paths.
- Concise supporting excerpt.
- Nearby prompt context.

Source: `../SKILL.md:L67-L69`.

### Apply origin label

Use “Likely origin” only if the evidence shows creation, generation, or modification. A filename match, later
inspection, or mention is not sufficient (`../SKILL.md:L93-L95`).

### Recommendation

When multiple creation-strength results exist, present each with its evidence and avoid collapsing them into a
single certain origin unless the persisted evidence distinguishes them.

## 6. Data-provenance workflow

Before presenting a generated claim:

1. Identify the indexed file or zmem export that supports it.
2. Preserve freshness status.
3. Keep excerpts concise.
4. Redact common secret assignments.
5. Exclude complete transcripts.
6. Exclude credentials, tokens, secrets, and sensitive incident payloads.
7. Do not imply use of Copilot internal memory.

All seven controls are normative (`../SKILL.md:L91-L100`).

## 7. Cross-skill interaction workflow

### Context Mesh delegates

Context Mesh delegates current-base persistence and persona behavior to `context-offload`
(`../SKILL.md:L9-L13`, `../SKILL.md:L40-L45`).

### `context-offload` triggers mesh work

An offload milestone or zmem offload triggers generation (`../SKILL.md:L50-L56`).

### Ownership rule

- Context Mesh may regenerate portfolio outputs.
- It does not grant permission to edit sibling stores.
- New-base registration creates only the new base’s store.

Source: `../SKILL.md:L23-L32`.

## 8. Failure workflows

### Missing digest

**Recommendation:** report that startup hydration cannot complete from the required digest, run the checked
generator if source inputs are available, then read the regenerated digest completely. The digest-read and
refresh requirements are normative (`../SKILL.md:L36-L39`, `../SKILL.md:L50-L59`).

### Invalid structured index

**Recommendation:** do not guess a base. Run the checked generator, validate the rebuilt index, and restart
resolution.

### No matching base

Follow registration rather than selecting a “nearby” sibling (`../SKILL.md:L44-L45`).

### Refresh produces zero contexts

Treat the build as failed because at least one context is required (`../SKILL.md:L58-L59`).

### One output missing

Treat the build as failed because all three outputs are required (`../SKILL.md:L58-L59`).

### Evidence is only a filename match

Present it as a weak match, not as origin or a strong relationship
(`../SKILL.md:L74-L75`, `../SKILL.md:L93-L95`).

### State is stale

Keep the stale label and require `context-offload` reconciliation before context-dependent work
(`../SKILL.md:L46-L48`, `../SKILL.md:L98-L98`).

