# Context Mesh

Context Mesh is the read-mostly portfolio layer above `context-offload`. It discovers per-base
`.agent-context/` stores, indexes their relationships and timelines, adds zmem nodes, and generates a startup
digest plus a human dashboard (`SKILL.md:L7-L13`).

## Documentation convention

- **Normative** behavior is explicitly required by `SKILL.md`.
- **Derived interpretation** explains consequences of the source without adding a requirement.
- **Recommendation** is optional operational or testing guidance.

All normative claims cite an explicit `SKILL.md:Lx-Ly` range.

## Responsibilities

Context Mesh provides three persistent views over context stores and zmem:

| Artifact | Purpose | Source |
|---|---|---|
| `CONTEXT-MESH.md` | Compact startup digest read at the beginning of a session | `SKILL.md:L15-L21`, `SKILL.md:L34-L39` |
| `context-index.json` | Structured index used to resolve bases and represent the graph | `SKILL.md:L15-L21`, `SKILL.md:L25-L26` |
| `context-mesh.html` | Dependency-free offline dashboard | `SKILL.md:L15-L21`, `SKILL.md:L61-L89` |

The generator discovers source stores and writes only the Context Mesh output directory
(`SKILL.md:L29-L32`).

## Access model

**Normative.**

1. Resolve the current base by comparing the working directory with `contexts[].basePath`.
2. Choose the longest matching path.
3. Allow the current base to read and write only its own `.agent-context`.
4. Treat every sibling context store as read-only.
5. During unregistered-base initialization, create only the new current base’s store.
6. Do not describe this instructional contract as operating-system enforcement.

Source: `SKILL.md:L23-L32`.

## Startup lifecycle

1. Read the entire startup digest.
2. Resolve the current base from the structured index.
3. If matched, invoke/follow `context-offload`, read the current state and memory, inspect the exact freshness
   marker, query zmem, and adopt the persona.
4. Use graph relationships to locate relevant siblings, reading them only as reference.
5. If unmatched, use `context-offload` to register the base, refresh the mesh, and restart hydration.
6. A missing, invalid, or at-least-12-hours-old marker requires a full offload before context-dependent work.

This sequence is normative (`SKILL.md:L34-L48`).

## Refresh

Run after any `.agent-context` milestone or zmem offload:

```powershell
python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
```

The build must report at least one context and produce all three output files. Failure must be reported plainly
rather than hidden behind a success-shaped fallback (`SKILL.md:L50-L59`).

## Dashboard capabilities

The offline dashboard provides:

- Context cards with freshness and working-state details.
- Search and freshness filters.
- Evidence-ranked Artifact Finder provenance.
- A conservative relationship graph.
- Optional context-memory, zmem, and low-confidence evidence detail.
- Evidence-backed node and connection inspection.
- Honest chronological animation.
- Stable context colors.
- Family-aware layout, pinning, viewport centering, and unpin-all behavior.

These behaviors are normative (`SKILL.md:L61-L83`).

## Data provenance

Every generated claim must come from indexed files or zmem export. Artifact matches are evidence-ranked;
“Likely origin” is reserved for creation, generation, or modification evidence. Excerpts remain concise and
secret assignments are redacted. Stale state stays visibly stale. Internal Copilot memory is not scraped
without a stable documented export (`SKILL.md:L91-L100`).

## Relationship to `context-offload`

- `context-offload` owns each base’s state, memory, history, identity, and persona.
- Context Mesh owns discovery, indexing, relationships, timeline views, artifact provenance, and generated
  portfolio outputs.
- A store or relevant zmem change triggers a mesh refresh.
- A later session consumes the refreshed digest and index before hydrating the current base.

The ownership split is explicit in the source (`SKILL.md:L7-L13`), and the hydration/refresh loop is defined in
`SKILL.md:L34-L59`.

## Documentation map

- [Architecture](docs/ARCHITECTURE.md) — components, inputs, outputs, graph, dashboard, and trust boundaries.
- [Workflow](docs/WORKFLOW.md) — hydration, base resolution, registration, refresh, provenance, and dashboard
  operations.
- [Reference](docs/REFERENCE.md) — fixed paths, commands, dashboard contract, evidence rules, and invariants.
- [Examples](docs/EXAMPLES.md) — worked resolution, refresh, graph, timeline, and artifact scenarios.
- [Operations and testing](docs/OPERATIONS-AND-TESTING.md) — runbooks, validation matrices, failure handling,
  security, and maintenance impact.

