# Reference

## 1. Fixed locations

| Item | Path | Source |
|---|---|---|
| Project | `C:\devdesk\Copilot\CopilotSessions\context-network` | `../SKILL.md:L15-L18` |
| Generator | `C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py` | `../SKILL.md:L17-L18` |
| Startup digest | `C:\devdesk\Copilot\CopilotSessions\context-network\output\CONTEXT-MESH.md` | `../SKILL.md:L19-L19` |
| Structured index | `C:\devdesk\Copilot\CopilotSessions\context-network\output\context-index.json` | `../SKILL.md:L20-L20` |
| Dashboard | `C:\devdesk\Copilot\CopilotSessions\context-network\output\context-mesh.html` | `../SKILL.md:L21-L21` |

## 2. Refresh command

```powershell
python C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py --check
```

Run after any `.agent-context` milestone or zmem offload (`../SKILL.md:L50-L56`).

## 3. Refresh success contract

- Reports at least one context.
- Produces all three output files.
- Reports failure plainly if generation fails.
- Does not leave a success-shaped fallback.

Source: `../SKILL.md:L58-L59`.

## 4. Open-dashboard command

```powershell
Start-Process C:\devdesk\Copilot\CopilotSessions\context-network\output\context-mesh.html
```

Source: `../SKILL.md:L85-L89`.

## 5. Base resolution

### Input field

```text
contexts[].basePath
```

### Algorithm

1. Compare current working directory with each base path.
2. Keep matching paths.
3. Select the longest matching path.

Source: `../SKILL.md:L25-L26`.

## 6. Access contract

| Rule | Source |
|---|---|
| Current base may read/write only its own `.agent-context` | `../SKILL.md:L27-L27` |
| Sibling stores are read-only | `../SKILL.md:L28-L28` |
| Existing stores remain read-only during new-base initialization | `../SKILL.md:L29-L30` |
| Create only the new current base’s store during registration | `../SKILL.md:L29-L30` |
| Generator reads stores and writes only Context Mesh output | `../SKILL.md:L31-L31` |
| Boundary is instructional, not OS-enforced | `../SKILL.md:L32-L32` |

## 7. Hydration contract

1. Read the digest completely.
2. Resolve the base from the structured index.
3. If matched, follow `context-offload`.
4. Use relationships to find relevant siblings.
5. Read siblings only as references.
6. If unmatched, register through `context-offload`, refresh, and restart hydration.
7. Enforce the exact freshness marker and 12-hour rule.

Source: `../SKILL.md:L34-L48`.

## 8. Freshness contract

A marker is stale when it is:

- Missing.
- Invalid.
- At least 12 hours old.

Staleness requires a full offload before context-dependent work. Long-running sessions repeat the check and
offload every 12 hours (`../SKILL.md:L46-L48`).

The dashboard and generated summaries must continue to label stale state as stale
(`../SKILL.md:L98-L98`).

## 9. Dashboard feature reference

### Context cards

Fields include freshness, identity, focus, threads, next steps, open questions, memory, and timeline
(`../SKILL.md:L65-L65`).

### Filters

- Search.
- Freshness.

Source: `../SKILL.md:L66-L66`.

### Artifact Finder

- Search by full path or filename.
- Normalize browser copy suffixes.
- Rank original creation/generation above later inspection or mention.
- Show chat name.
- Show session ID.
- Show working directory.
- Show timestamps.
- Show observed paths.
- Show concise evidence excerpts.
- Show nearby prompt context.

Source: `../SKILL.md:L67-L69`.

### Default graph

- Context nodes.
- High-confidence structural relationships.
- Explicitly declared handoff relationships.

Source: `../SKILL.md:L70-L71`.

### Optional graph detail

- Context-memory nodes.
- zmem nodes.
- Low-confidence incidental references through an evidence filter.

Source: `../SKILL.md:L72-L73`.

### Inspection

Every connection explanation includes:

- Confidence.
- Relationship class.
- Exact persisted file/line excerpt.

Path/name presence alone is not strong evidence (`../SKILL.md:L74-L75`).

### Chronological animation

- One-shot playback.
- Replay.
- Stop.
- Context date from earliest dated journal evidence.
- zmem date from creation timestamp.
- Inherited/unknown dates labelled.
- No false precision.

Source: `../SKILL.md:L76-L78`.

### Visual identity

- Stable, distinct context-node circumference colors.
- Zoom-independent stroke width.

Source: `../SKILL.md:L79-L80`.

### Family-aware layout

- Connected components at central anchors.
- Isolated contexts and unscoped memory farther out.
- Pin-after-drag relocates family anchor.
- Pinning centers the viewport.
- Unpin-all resets custom family anchors.

Source: `../SKILL.md:L81-L83`.

## 10. Provenance labels

### “Likely origin”

Allowed only when persisted evidence demonstrates:

- Creation.
- Generation.
- Modification.

It is not allowed solely from a filename match (`../SKILL.md:L93-L95`).

### Strong relationship

Requires more than path or name presence and must expose confidence, class, and exact persisted evidence
(`../SKILL.md:L74-L75`).

### Date provenance

- Context: earliest dated journal evidence.
- zmem: creation timestamp.
- Inherited/unknown: explicitly labelled.

Source: `../SKILL.md:L76-L78`.

## 11. Data-source honesty

- Source every claim from indexed files or zmem export.
- Keep local session-state excerpts concise.
- Redact common secret assignments.
- Never embed complete transcripts.
- Preserve stale labels.
- Do not scrape internal Copilot memory without a stable documented export.
- Never emit credentials, secrets, tokens, or sensitive incident payloads in summaries.

Source: `../SKILL.md:L91-L100`.

## 12. Normative versus recommended examples

| Statement | Classification |
|---|---|
| “Use the longest matching base path.” | Normative, `../SKILL.md:L25-L26` |
| “Normalize path separators before comparison.” | Recommendation |
| “The dashboard works offline.” | Normative, `../SKILL.md:L61-L64` |
| “Test in two browsers.” | Recommendation |
| “A filename match cannot prove origin.” | Normative, `../SKILL.md:L93-L95` |
| “Show an evidence score beside every result.” | Recommendation unless already implemented by the required confidence UI |
| “Do not claim OS-level enforcement.” | Normative, `../SKILL.md:L32-L32` |

## 13. Relationship to zmem

Context Mesh adds zmem nodes (`../SKILL.md:L11-L13`), allows optional zmem detail in the dashboard
(`../SKILL.md:L72-L73`), uses zmem creation timestamps for chronological animation
(`../SKILL.md:L76-L78`), and accepts zmem export as a claim source (`../SKILL.md:L91-L95`).

## 14. Relationship to `context-offload`

- `context-offload` owns durable state and persona.
- Context Mesh discovers and indexes that state.
- Matching bases hydrate through `context-offload`.
- Unmatched bases register through `context-offload`.
- Store or zmem milestones trigger mesh refresh.

Source: `../SKILL.md:L7-L13`, `../SKILL.md:L34-L56`.

