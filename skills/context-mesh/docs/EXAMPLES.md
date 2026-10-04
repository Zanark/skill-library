# Worked Examples

## 1. Resolve a nested registered base

### Index entries

```json
{
  "contexts": [
    { "basePath": "C:\\work\\Product" },
    { "basePath": "C:\\work\\Product\\Component" }
  ]
}
```

### Current directory

```text
C:\work\Product\Component\src
```

### Result

Select `C:\work\Product\Component` because it is the longest matching path. Only that base’s
`.agent-context/` is writable; the parent store is a read-only sibling.

Longest-match and write-boundary behavior are normative (`../SKILL.md:L25-L28`). The paths are illustrative.

## 2. Start in an unregistered base

### Scenario

No `contexts[].basePath` matches the working directory.

### Normative execution

1. Do not select a similar sibling.
2. Follow `context-offload` to create the current base’s four-file store and persona entry.
3. Leave every existing store read-only.
4. Refresh Context Mesh.
5. Read the newly generated digest and index.
6. Restart hydration from the new current store.

Source: `../SKILL.md:L29-L30`, `../SKILL.md:L44-L45`.

## 3. Refresh after a state milestone

### Scenario

The current base updates `STATE.md` after completing a significant task.

### Command

```powershell
python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
```

### Acceptance

- Command reports at least one context.
- `CONTEXT-MESH.md` exists.
- `context-index.json` exists.
- `context-mesh.html` exists.
- The updated state is represented without changing a sibling store.

The trigger, command, and output gate are normative (`../SKILL.md:L50-L59`); checking representation of the
new state is a recommended semantic verification.

## 4. Refresh failure

### Scenario

The generator exits unsuccessfully or produces only two outputs.

### Correct response

```text
Context Mesh refresh failed. The checked build did not produce all three required outputs.
```

Do not synthesize a placeholder dashboard, report success, or hide the failure. All three outputs and a
plainly reported failure are required (`../SKILL.md:L58-L59`).

## 5. Find an artifact by full path

### Query

```text
C:\work\Product\reports\summary.html
```

### Evidence A

```text
Generated C:\work\Product\reports\summary.html from the verified report inputs.
```

### Evidence B

```text
Opened summary.html to inspect the final layout.
```

### Result ordering

Evidence A ranks above B because creation/generation evidence outranks later inspection. The result can be
labelled “Likely origin” only for A, not merely because both excerpts mention the filename
(`../SKILL.md:L67-L69`, `../SKILL.md:L93-L95`).

## 6. Find an artifact with browser copy suffixes

### Scenario

The user searches for `diagram (1).png`, while persisted evidence records `diagram.png`.

### Expected behavior

Artifact Finder normalizes browser copy suffixes and evaluates evidence for the normalized candidate. It still
must not claim origin without creation, generation, or modification evidence
(`../SKILL.md:L67-L69`, `../SKILL.md:L93-L95`).

## 7. Inspect a relationship

### Scenario

Two contexts share a path string, but no handoff or structural relationship is persisted.

### Expected behavior

- Do not show the relationship as high confidence solely because of the shared string.
- If surfaced through the incidental-evidence filter, label it with appropriate low confidence.
- Show relationship class and exact persisted excerpt.

Source: `../SKILL.md:L70-L75`.

## 8. Explicit handoff relationship

### Evidence

One context’s state explicitly says that a workstream moved to another context.

### Expected behavior

The conservative default graph may include the edge because explicitly declared handoffs are permitted. The
connection inspector shows confidence, relationship class, and exact file/line evidence
(`../SKILL.md:L70-L75`).

## 9. Chronological animation with incomplete dates

### Scenario

- Context A has a journal entry dated 2026-09-01.
- zmem node B has creation timestamp 2026-09-03T10:00:00Z.
- Context C has no supported date.

### Expected behavior

- Animate A from its earliest dated journal evidence.
- Animate B from its zmem creation time.
- Label C as unknown or inherited, as applicable.
- Do not invent a day or time for C.

Source: `../SKILL.md:L76-L78`.

## 10. Stale context card

### Scenario

A current-state marker is older than 12 hours.

### Expected behavior

- Card remains labelled stale.
- Startup hydration requires a full `context-offload` before context-dependent work.
- The dashboard does not infer a fresh incident, sprint, deployment, or work-item status.

Source: `../SKILL.md:L46-L48`, `../SKILL.md:L98-L98`.

## 11. Inspecting related siblings

### Scenario

The current base has a high-confidence relationship to two siblings, but only one is relevant to the task.

### Normative execution

Read only the relevant sibling as reference material. Do not edit either sibling store
(`../SKILL.md:L42-L43`, `../SKILL.md:L27-L28`).

## 12. Secret assignment in local session evidence

### Evidence

```text
API_TOKEN=<sensitive value>
Generated report successfully.
```

### Expected output

```text
API_TOKEN=[REDACTED]
Generated report successfully.
```

Keep the excerpt concise and do not embed the complete transcript. The source requires redaction of common
secret assignments and prohibits complete transcripts and secret-bearing summaries
(`../SKILL.md:L96-L100`).

## 13. Open and rearrange the dashboard

### Open

```powershell
Start-Process C:\devdesk\Copilot\CopilotSessions\context-network\output\context-mesh.html
```

### Interaction

1. Fit the graph and identify contexts by their stable circumference colors.
2. Drag and pin a context to reposition its connected family and center the viewport.
3. Use unpin-all to restore generated anchors.

The open command and interaction behaviors are normative (`../SKILL.md:L79-L89`).

## 14. zmem node in detailed view

### Scenario

A cross-cutting convention exists in zmem but is not tied to one base.

### Expected behavior

- It may appear when zmem detail is enabled.
- It sits farther out if unscoped.
- Its animation date comes from its creation timestamp.
- Claims derived from it cite the zmem export.

Source: `../SKILL.md:L72-L73`, `../SKILL.md:L76-L83`, `../SKILL.md:L91-L95`.

## 15. Internal-memory limitation

### Scenario

A user asks whether the dashboard includes undocumented Copilot internal memory.

### Correct answer

No. Internal memory is not scraped unless a stable documented export becomes available
(`../SKILL.md:L99-L99`).

