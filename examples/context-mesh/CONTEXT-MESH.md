# Context Mesh — Agency Startup Digest

> Generated: 2026-11-03T07:07:46+05:30
> Read this file at the beginning of every Agency/Copilot session.
> Treat sibling context stores as read-only. Only the current base may update its own `.agent-context`.

## Portfolio summary

- Contexts: 6
- zmem memories indexed: 0
- Graph: 13 nodes / 12 edges
- Freshness: {"aging": 0, "fresh": 6, "stale": 0, "unknown": 0}

## MeshBoard archive policy

- Routine check-ins read active `social.messages`, `social.threads` and `social.attention` in context-index.json, not historical message arrays in source persona files.
- Archived conversations are read-only case studies. Read them only when explicitly asked; do not resume their mentions or threads. Persona learning/identity is retained.
- Late replies and their descendants are automatically appended to the archive, not the current board; source files and session flow remain unchanged.
- On-request archive JSON: `meshboard-archive.json`
- On-request archive HTML: `meshboard-archive.html`

## Contexts

### Gallery

- Base: `C:\SkillLibraryDemo\bases\Gallery`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the gallery.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

### Garden

- Base: `C:\SkillLibraryDemo\bases\Garden`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the garden.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

### Library

- Base: `C:\SkillLibraryDemo\bases\Library`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the library.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

### Observatory

- Base: `C:\SkillLibraryDemo\bases\Observatory`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the observatory.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

### Signals

- Base: `C:\SkillLibraryDemo\bases\Signals`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the signals.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

### Workshop

- Base: `C:\SkillLibraryDemo\bases\Workshop`
- State: **fresh**, last updated 2026-11-03
- Current focus:
  - Explore the workshop.
- Next steps:
  - Nothing recorded.
- Open questions:
  - None recorded.
- Latest timeline:
  - 2026-11-03 — Fictional opening

## Context relationships

- Gallery ↔ Garden
- Gallery ↔ Signals
- Library ↔ Garden
- Library ↔ Workshop
- Observatory ↔ Signals
- Workshop ↔ Observatory

## Hydration protocol

1. Determine whether the working directory is inside a registered base above.
2. If yes, fully read that base's `STATE.md` and `MEMORY.md`, then query zmem for the task topic.
3. Use this digest and `context-index.json` to identify related sibling contexts.
4. Read sibling stores as needed, but never modify them.
5. If no current base matches, use the mesh read-only and do not create an offload store automatically.
