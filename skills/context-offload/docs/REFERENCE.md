# Reference

## 1. Source authority

`SKILL.md` is the normative source. This documentation explains it but does not replace it. Where a
recommendation differs from a future source revision, the source wins.

## 2. Fixed store name and source-of-truth rule

| Item | Value | Source |
|---|---|---|
| Store directory | `.agent-context/` | `../SKILL.md:L23-L26` |
| Scope | Inside each user-designated base | `../SKILL.md:L25-L26` |
| Authority | Source of truth over ephemeral session context | `../SKILL.md:L25-L26` |

## 3. Required files

### `STATE.md`

- Purpose: current focus, live threads, next steps, and open questions.
- Cadence: every milestone or end of work chunk.
- Required initial marker: `> **Last updated:** YYYY-MM-DD (Asia/Kolkata) — …`
- Required freshness marker:
  `> **Last context offload:** YYYY-MM-DDTHH:mm:ss+05:30`
- Initial sections: `Current focus`, `Threads`, `Open questions`, `Environment reminders`.

Source: `../SKILL.md:L52-L64`.

### `MEMORY.md`

- Purpose: durable facts, decisions, gotchas, conventions, people, tooling, and protocol.
- Cadence: whenever a durable fact or decision is established.
- Initial sections: `People`, `Conventions`, `Gotchas`, `Context-offload protocol`.

Source: `../SKILL.md:L52-L64`.

### `JOURNAL.md`

- Purpose: dated activity record.
- Order: newest at top.
- Granularity: one entry per session or significant action.
- Cadence: frequent; not only at session end.
- Initial declaration: `> Newest at top.`

Source: `../SKILL.md:L35-L38`, `../SKILL.md:L56-L64`.

### `README.md`

- Purpose: protocol documentation, base identity, and persona-continuity contract.
- Cadence: rarely.
- New-store requirement: include a header blockquote stating base identity and the continuity contract.

Source: `../SKILL.md:L57-L64`.

## 4. Freshness reference

### Marker grammar

```text
> **Last context offload:** YYYY-MM-DDTHH:mm:ss+05:30
```

Source: `../SKILL.md:L31-L34`.

### Stale conditions

The store is stale if the marker is:

1. Missing.
2. Invalid.
3. At least 12 hours old.

A stale store requires a full offload before context-dependent work. During a long-running session, another
full offload is required each time 12 hours elapse since the last successful offload
(`../SKILL.md:L31-L38`, `../SKILL.md:L126-L127`).

### Commit rule

Advance the marker only after all persistence steps succeed (`../SKILL.md:L126-L138`).

## 5. Hydration reference

Normative sequence:

1. Read
   `C:\devdesk\Copilot\CopilotSessions\context-network\output\CONTEXT-MESH.md`.
2. Resolve the working directory against `context-index.json` with longest-match semantics.
3. Register an unmatched base before continuing.
4. Read `STATE.md` and the freshness marker, then `MEMORY.md`.
5. Perform a full offload if stale.
6. Skim base docs.
7. Run `zmem read --query "<current topic>"`.
8. Adopt the registered persona.

Source: `../SKILL.md:L108-L119`.

## 6. Continuous-offload reference

| Trigger | Action | Source |
|---|---|---|
| Milestone completed | Update `STATE.md` | `../SKILL.md:L35-L38`, `../SKILL.md:L121-L123` |
| Durable fact or decision | Update `MEMORY.md` | `../SKILL.md:L35-L36`, `../SKILL.md:L122-L123` |
| Significant action or lookup | Add newest-first journal entry | `../SKILL.md:L36-L38`, `../SKILL.md:L124-L125` |
| 12 hours elapsed | Full offload immediately | `../SKILL.md:L126-L127` |
| Store or relevant zmem changed | Refresh Context Mesh | `../SKILL.md:L130-L131` |

## 7. Closeout reference

Required:

- Current `STATE.md`.
- Dated journal summary.
- zmem episodic for a significant offload.
- Marker advancement only after persistence.
- Context Mesh refresh.
- Readability verification for the store, zmem memory, marker, and digest.

Source: `../SKILL.md:L133-L139`.

## 8. Commands and fixed paths

### zmem hydration

```powershell
zmem read --query "<current topic>"
```

Source: `../SKILL.md:L117-L118`.

### Significant zmem offload

```powershell
zmem write episodic "…" --detail "…" --tags offload …
```

Source: `../SKILL.md:L133-L137`.

### Context Mesh refresh

```powershell
python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
```

Source: `../SKILL.md:L130-L131`.

### Context Mesh artifacts

| Artifact | Role |
|---|---|
| `CONTEXT-MESH.md` | Cross-base startup digest |
| `context-index.json` | Machine-readable graph and base resolution source |
| `context-mesh.html` | Human dashboard |

Source: `../SKILL.md:L183-L185`.

## 9. Content classification

### Durable — persist

- Decisions and rationale.
- Conventions and naming.
- Gotchas and fixes.
- Thread status and next steps.
- People and ownership.
- Tooling and environment facts.
- Stated user preferences.
- Resolved “where did we do X?” lookups.
- ADO/IcM IDs tied to a thread.

Source: `../SKILL.md:L143-L147`.

### Transient or unsafe — skip

- Today’s date as a standalone fact.
- Current branch or file when easily recoverable.
- One-off scratch values.
- Speculation and half-conclusions.
- Easily re-derived paths or usernames.
- Sensitive information without explicit consent.
- Secrets and tokens.

Source: `../SKILL.md:L149-L151`, `../SKILL.md:L192-L196`.

## 10. Persona registry reference

### Semantics

- One base maps to one distinct persona.
- Resumption adopts that persona’s scope and voice.
- Universal honesty and concision remain unchanged.

Source: `../SKILL.md:L68-L72`.

### Registry entries

The source registry enumerates:

- WorkDesk.
- Runner.
- KnowledgeLedger\ServiceFabric.
- SF\AutoScalePOC.
- KnowledgeLedger\MABArchitecture.
- KnowledgeLedger.
- LiveSite.
- DRILL.
- SF\SFMC_Migration.
- SF\SFMC-Migration-Inventory.
- `C:\devdesk\BCDR\MAB\AzRetroFit`.
- EntropyTag_Prototype.
- EntropyTag.
- SpriteCanvas.
- DeepSeaFoam.
- portfolioWebsiteGitHub.
- homeDesk\KardboardCode.
- ClipFarm.
- SubwooferLullabies.
- SongsWorkspace.
- CareerHQ.

Their authoritative persona names and scopes are defined in `../SKILL.md:L74-L96`.

### Explicit non-base

`AzRel-CopilotSkillsLibrary` is a git skills repository and must not be treated as an offload persona base
(`../SKILL.md:L98-L99`).

### Adding a base

Create the store, write identity and continuity contract, register the persona row, add relevant
cross-references, and refresh Context Mesh (`../SKILL.md:L101-L104`).

## 11. Honesty and provenance invariants

- Never fabricate facts, history, capabilities, or state.
- Prefer explicit verification over confident guessing.
- Ground claims in the store, tool output, or the user’s words.
- Mark stale information “re-verify.”
- State capability limits.
- Never imply access to audio when only text transcription was received.

Source: `../SKILL.md:L155-L164`.

## 12. Voice and output invariants

- English in Latin/Roman letters.
- Never emit Devanagari; romanize Hindi as Hinglish.
- Concise, scannable answers.
- Use bullets rather than tables for Teams-facing output.
- When creating a `.ps1`, also provide a `.txt` copy.
- ADO link format:
  `https://msazure.visualstudio.com/One/_workitems/edit/{id}`
- IcM link format:
  `https://portal.microsofticm.com/imp/v5/incidents/details/{id}/summary`

Source: `../SKILL.md:L165-L171`.

## 13. Recorded environment facts

- Copilot CLI has no Az PowerShell module.
- SAW uses PowerShell 5.1 and Constrained Language Mode.
- EV2, ADO, and SafeFly links are authentication-gated.
- The `create` tool writes UTF-8 without BOM.
- `.ps1` files should remain pure ASCII for PowerShell 5.1.

Source: `../SKILL.md:L172-L173`.

## 14. Guardrails

- Every new or reopened chat must resolve to a registered store.
- Register an unmatched current base immediately.
- Do not modify sibling stores during registration.
- Never persist secrets, credentials, or tokens.
- Cross-reference sibling content instead of duplicating it.
- Reconcile uncertain freshness before trusting the store and record the reconciliation in the journal.

Source: `../SKILL.md:L192-L199`.

## 15. Normative versus recommended examples

| Statement | Classification |
|---|---|
| “A missing freshness marker is stale.” | Normative, `../SKILL.md:L31-L34` |
| “Use an automated timestamp parser in tests.” | Recommendation |
| “Journal entries are newest first.” | Normative, `../SKILL.md:L56-L56` |
| “Include evidence links in each journal entry.” | Recommendation |
| “Do not write secrets to zmem.” | Normative, `../SKILL.md:L149-L151` |
| “Run a secret scanner before committing stores.” | Recommendation |

