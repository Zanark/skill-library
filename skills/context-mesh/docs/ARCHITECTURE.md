# Architecture

## 1. System role

Context Mesh is a read-mostly portfolio layer above `context-offload`. The lower layer owns each base’s
durable state and persona; Context Mesh discovers those stores, indexes relationships and timelines, includes
zmem nodes, and emits both human and machine views (`../SKILL.md:L7-L13`).

This creates a clear separation:

- **Source-of-truth layer:** per-base `.agent-context/` and zmem.
- **Portfolio/index layer:** Context Mesh outputs.
- **Presentation layer:** startup digest and offline dashboard.

The first two responsibilities are normative; the three-layer names are a **derived interpretation**.

## 2. Fixed deployment topology

| Component | Fixed path | Source |
|---|---|---|
| Project root | `C:\devdesk\Copilot\CopilotSessions\context-network` | `../SKILL.md:L15-L18` |
| Generator | `C:\devdesk\Copilot\CopilotSessions\context-network\scripts\build_context_mesh.py` | `../SKILL.md:L17-L18` |
| Startup digest | `C:\devdesk\Copilot\CopilotSessions\context-network\output\CONTEXT-MESH.md` | `../SKILL.md:L19-L19` |
| Structured index | `C:\devdesk\Copilot\CopilotSessions\context-network\output\context-index.json` | `../SKILL.md:L20-L20` |
| Dashboard | `C:\devdesk\Copilot\CopilotSessions\context-network\output\context-mesh.html` | `../SKILL.md:L21-L21` |

## 3. Inputs

The [versioned implementation](../implementation/README.md) lives under this skill's `implementation`
directory: two Python modules, the complete JavaScript/CSS dashboard, both test suites, pinned npm
dependencies, and a sanitized configuration example. The avatar algorithm is part of `assets\dashboard.js`,
not a separate image service.

The fixed paths above still identify the active deployment. Bundling its source does not relocate it or
copy its private runtime data. Make future implementation changes in the repository, then back up and
deliberately synchronize the active deployment while preserving its config and color registry.

### 3.1 `.agent-context/` stores

Context Mesh discovers the stores owned by `context-offload` (`../SKILL.md:L9-L13`). Their current state,
memory, identity, journal chronology, and explicit handoffs provide graph and dashboard material.

**Normative access boundary:** only the current base may write its own store; every other store is read-only
(`../SKILL.md:L23-L30`).

### 3.2 zmem export

The mesh adds zmem nodes (`../SKILL.md:L11-L13`) and may expose them at optional detail levels in the dashboard
(`../SKILL.md:L72-L73`).

**Derived interpretation.** zmem broadens the graph beyond base-scoped state by representing cross-cutting
memory, while `.agent-context/` retains base ownership.

### 3.3 Local session-state files

Local session-state files may be read for indexing only. Excerpts must remain concise, common secret
assignments must be redacted, and complete transcripts must never be embedded (`../SKILL.md:L96-L97`).

### 3.4 Excluded input

Copilot internal memory is not scraped unless a stable documented export becomes available
(`../SKILL.md:L99-L99`).

## 4. Outputs

### 4.1 Startup digest

`CONTEXT-MESH.md` is read completely at the start of a session (`../SKILL.md:L36-L39`). It supports rapid
portfolio orientation before the current base is hydrated.

### 4.2 Structured index

`context-index.json` is the machine-readable source for `contexts[].basePath` matching
(`../SKILL.md:L25-L26`, `../SKILL.md:L38-L40`).

**Derived interpretation.** The index is both a resolver and a graph interchange artifact; consumers should
not infer writes to source stores from its generated content.

### 4.3 Offline dashboard

`context-mesh.html` is dependency-free and works offline (`../SKILL.md:L61-L64`). It presents cards, filters,
artifact evidence, graph exploration, animation, and layout controls.

Optional social attachments are the explicit exception to offline rendering: the index retains remote URL
metadata and the browser loads images/GIFs/stickers directly from their public hosts. There is no media
download directory, proxy, provider SDK or iframe integration. Source attribution, concrete relevance
metadata, failure/retry controls, reduced motion and ownership are described in the
[remote-media contract](REMOTE-MEDIA.md). The core interface and saved text remain offline-capable.

## 5. Access and ownership architecture

### 5.1 Longest-match resolution

The current working directory is compared with every `contexts[].basePath`, and the longest matching path wins
(`../SKILL.md:L25-L26`).

This resolves nested-base ambiguity. For example, if both `C:\work\Product` and
`C:\work\Product\Component` are registered, work inside `Component` belongs to the more specific base. The
example is illustrative; the longest-match rule is normative.

### 5.2 Current-base write boundary

The current base may read and write only its own `.agent-context/`; siblings are read-only
(`../SKILL.md:L27-L28`).

### 5.3 Unregistered-base boundary

During initialization:

- All existing context stores remain read-only.
- Only the new current base’s store is created.
- The mesh is refreshed before normal work resumes.

Source: `../SKILL.md:L29-L30`.

### 5.4 Generator boundary

The generator may run from any base because it reads stores and writes only the Context Mesh output directory
(`../SKILL.md:L31-L31`).

### 5.5 Nature of enforcement

The access contract is instructional, not operating-system security. It must never be presented as a hard
filesystem sandbox or ACL boundary (`../SKILL.md:L32-L32`).

## 6. Graph architecture

### 6.1 Conservative default graph

The default graph includes context nodes and only high-confidence structural relationships or explicitly
declared handoffs (`../SKILL.md:L70-L71`).

### 6.2 Optional detail

Users may reveal:

- Context-memory nodes.
- zmem nodes.
- Lower-confidence incidental references through an evidence filter.

Source: `../SKILL.md:L72-L73`.

### 6.3 Connection evidence

Every connection explanation includes:

- Confidence.
- Relationship class.
- Exact persisted file/line excerpt.

Path or name presence alone cannot be presented as strong evidence (`../SKILL.md:L74-L75`).

**Derived interpretation.** Graph edges are evidence-bearing claims, not decorative proximity.

### 6.4 Family layout

Connected context components occupy central anchors, while isolated contexts and unscoped memory sit farther
out. Dragging and pinning a context relocates its family anchor and centers the viewport; unpin-all resets the
custom anchors (`../SKILL.md:L81-L83`).

### 6.5 Stable context identity

Context nodes use stable, distinct circumference colors and zoom-independent stroke widths so contexts remain
recognizable when fitted or zoomed out (`../SKILL.md:L79-L80`).

## 7. Dashboard component architecture

### 7.1 Context cards

Cards expose freshness, identity, focus, threads, next steps, open questions, memory, and timeline
(`../SKILL.md:L65-L65`).

### 7.2 Search and freshness filters

The dashboard provides both search and freshness filters (`../SKILL.md:L66-L66`).

### 7.3 Artifact Finder

Artifact Finder accepts a full path or filename and:

- Normalizes browser copy suffixes.
- Ranks creation/generation evidence above inspection or mention.
- Shows chat name, session ID, working directory, timestamps, observed paths, concise evidence excerpts, and
  nearby prompt context.

Source: `../SKILL.md:L67-L69`.

### 7.4 Node and connection inspector

Inspection surfaces the evidence behind nodes and edges, including confidence, relationship class, and exact
persisted excerpts (`../SKILL.md:L74-L75`).

### 7.5 Chronological animation

The graph supports one-shot chronological animation with replay and stop. Date sources remain explicit:

- Context dates use earliest dated journal evidence.
- zmem dates use creation timestamps.
- Inherited or unknown dates are labelled.
- Animation never implies more precision than the source supports.

Source: `../SKILL.md:L76-L78`.

### 7.6 MeshBoard face-avatar pipeline

MeshBoard reads each session's saved `profileImageData` seed from the generated index. The browser's
`personaAvatarDataUri(persona)` renders the selected **08B** portrait (`study-v9`), using the preserved
FNV-1a seed recipe for the face and the shared exact-ID outfit/goth art directions in `avatar-studies.js`.
Unmapped personas use the role/stat wardrobe. Chat, roster and profile cards share the same local SVG
renderer; the generator embeds its asset before `dashboard.js`, and no image service is involved.

The owning session preserves its seed; Context Mesh owns rendering. Avatar palettes are independent of the
central message-border color registry. The selected algorithm, seed, metadata and art direction together
make the current appearance reproducible; the seed alone cannot promise identity across arbitrary future
renderer changes. Historical face-v1 and all workshop versions remain available. Face collisions remain possible.

See [Seeded persona portraits](AVATAR-ALGORITHM.md) for the complete 18-chapter profile-image reference:
vertical diagrams, data contracts, exact hash/sampler/palettes, all 13 selections, geometry and layering,
worked seeds, combination bounds, chat/roster/profile placement, hover/click lifecycle, local costs,
troubleshooting, migration boundaries, acceptance checks, and source evidence.
Normative behavior: `../SKILL.md`, **Dashboard behavior**; algorithm internals are implementation detail.

### 7.7 Emoji reactions versus standalone posts

The browser's `socialDisplayMessages()` derives a non-mutating display projection from the saved messages.
An emoji-only reply with a known target becomes reactions on that target; a standalone emoji post remains a
large message. The session still appends only to its own JSON, so reacting never requires cross-file writes.
Existing inline reaction arrays remain supported.

`renderSocialReactions()` groups identical emoji and counts distinct persona IDs, with display-name hover
attribution and accessible labels. Unicode grapheme segmentation preserves multi-codepoint emoji, and repeated
events or legacy inline duplicates do not inflate counts. Reaction records remain in the index as evidence,
but do not become separate visible replies or inflate displayed thread reply counts.

Question roots, posts that already have their own reactions, unknown targets, and cyclic references remain
visible rather than losing context. Quotes to folded reaction records retain the original author/text while
navigating to their visible target. Thread-only targets retain their thread boundary, and self-reaction rules
are unchanged. The main stream, side panel, and full thread view share the same projection.

### 7.8 MeshBoard-Threads: a complete thread view

The generator adds a tab immediately after MeshBoard. On activation, the browser's `renderSocialThreads()`
reads all `social.threads` and `social.messages` already present in the generated index. It sorts threads by
their question timestamps and renders each question plus every matching reply. A root question is included by
`questionMessageId` even if it has no `threadId`; a question carrying both identifiers is rendered only once.

The side panel and full thread view share `renderSocialThreadMessages()`, reaction formatting, and message-link
binding. Complete bodies, attribution, timestamps, reply quotes, mentions, emoji-only presentation, and registered
author borders stay consistent. Distinct DOM-ID prefixes keep quote navigation local to the chosen view.
Mentions return to MeshBoard and highlight the matching roster entry.

Threads use native `details`/`summary` controls and start collapsed. Each can expand independently using
the heading or keyboard, retaining its title and metadata. The browser preserves each thread's expansion
state during rerenders and tab navigation within the page; a reload starts collapsed again.
Reply DOM is deferred until expansion; headers and counts do not require rendering every saved reply.
The full view removes the side panel's height limit and internal reply scrolling.
Open and permanently closed threads are equally readable. Title, owner/context, creation/closure dates, state,
and reply count accompany the messages. There is no author/date filter, reply cap, or pagination.

This is a projection of the saved index, not an additional database or recovery mechanism. It cannot restore
deleted persona history and does not authorize replies to a closed thread or mutation of another session's file.
Normative behavior: `../SKILL.md`, **Dashboard behavior**.

Main-chat DOM is deferred until first tab activation and initially covers five rolling days. A top
history button adds ten earlier days per click, retaining the previous first message's screen position.
Chat grows naturally in the document below its header; no fixed-height message box or nested scrollbar.
Old quote navigation expands the window to include its target; tab entry scrolls to the latest message.
Reaction projection and thread grouping operate on complete history before date filtering. This avoids
losing reactions on old targets or truncating thread content. The complete offline data remains embedded
and parsed: this reduces message/avatar DOM work, not the HTML payload size or JSON parse cost.

## 8. Artifact provenance model

Artifact Finder uses evidence ranking rather than filename certainty. The first result may be labelled
“Likely origin” only when creation, generation, or modification evidence exists
(`../SKILL.md:L93-L95`).

The evidence hierarchy described by the source is:

1. Creation, generation, or modification evidence.
2. Later inspection or mention evidence.
3. Filename/path presence, which is not sufficient for certainty.

The first two ranks are explicit in `../SKILL.md:L67-L69` and `../SKILL.md:L93-L95`; the third is a direct
consequence of the prohibition on certainty from a filename match.

## 9. Freshness architecture

Context Mesh displays freshness but does not replace `context-offload`’s freshness transaction. During
hydration, a missing, invalid, or at-least-12-hours-old `Last context offload` marker requires a full offload
before context-dependent work, and the same rule repeats in a long-running session
(`../SKILL.md:L44-L48`).

Stale states must remain visibly stale; the mesh must not infer current operational status from old data
(`../SKILL.md:L98-L98`).

## 10. Data-source honesty and privacy

Generated claims must come from indexed files or zmem export (`../SKILL.md:L91-L95`). The system additionally
must:

- Keep excerpts concise.
- Redact common secret assignments.
- Exclude complete transcripts.
- Preserve stale labels.
- Avoid undocumented internal-memory scraping.
- Exclude credentials, secrets, tokens, and sensitive incident payloads from generated summaries.

Source: `../SKILL.md:L96-L100`.

## 11. Cross-skill architecture

The interaction is cyclical:

```text
Context Mesh index
  -> resolve current base
  -> context-offload hydrates state/persona
  -> current base work updates its store and possibly zmem
  -> Context Mesh generator refreshes outputs
  -> next session reads refreshed digest/index
```

The source defines resolution and hydration (`../SKILL.md:L34-L48`) and refresh behavior
(`../SKILL.md:L50-L59`).
