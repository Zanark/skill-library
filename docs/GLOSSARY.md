# Cross-Skill Glossary

| Term | Meaning in this library |
|---|---|
| ADO | Azure DevOps work-item system used by the planning skills |
| Agent context | The fixed `.agent-context` directory containing per-base resumable state |
| Artifact provenance | Evidence linking a file or output to the session, source, or commit that created or changed it |
| Base | A registered working directory with its own context store and persona |
| Canonical source | The original locally verified `SKILL.md` location recorded in `source-inventory.json` |
| Clip | A reviewed media output produced from selected source-video segments |
| Context Mesh | Cross-base index and dashboard generated from context stores and zmem |
| Context offload | Persistence of live state, durable facts, and journal history into a base store |
| Coverage ledger | A record proving which source topics/problems were delivered or blocked |
| DRI | Designated Responsible Individual for livesite/on-call operations |
| Evidence | Persisted support for a claim, decision, relationship, score, or output |
| IcM | Incident Management system used by the livesite planning skills |
| Immutable draft | A rendered ClipFarm candidate that is revised by creating a new draft rather than overwriting history |
| IST | India Standard Time, UTC+05:30 |
| Knowledge base | Career Forensics' persistent, merge-oriented collection of evidence and generated reports |
| LTP | Last traded price used by the NSE research workflow |
| MCP | Model Context Protocol integration used to access systems such as ADO or IcM |
| Mesh edge | A relationship supported by explicit persisted evidence between graph nodes |
| Persona | The domain scope and continuity contract adopted when resuming a registered base |
| Recall evidence | User-provided memory recovered through questioning and explicitly marked as self-reported |
| Source snapshot | The archived `SKILL.md` whose hash is recorded in the inventory |
| SAPI | Windows Speech API used by the Copilot Speak MCP implementation |
| Speak MCP | The local stdio MCP server that exposes `speak` and `list_voices` tools |
| Supersession | A newer rule explicitly replacing an older rule while historical records remain preserved |
| Workplan | A time-blocked operational schedule generated from live or persisted work data |
| zmem | A separate durable-memory dependency used by the context system |
