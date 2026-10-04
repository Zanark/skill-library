# Architecture

## 1. Purpose and architectural boundary

`context-offload` is the durable state layer for a collection of long-running working bases. Its prime
directive is persona continuity: a new session in a designated base reads the stored context and behaves with
the same knowledge, threads, tone, and conventions as the writer (`../SKILL.md:L13-L19`).

**Normative boundary.** The skill owns the protocol and content semantics of each base’s `.agent-context/`
store. Context Mesh is a separate read-mostly portfolio index over those stores and zmem
(`../SKILL.md:L177-L188`).

## 2. Layered memory model

### 2.1 Ephemeral session context

Session context is temporary and cannot be trusted as the sole record of work. The source explicitly says
never to rely on it alone (`../SKILL.md:L183-L188`).

**Derived interpretation.** Anything required for a later session to resume correctly must be promoted into
one or more durable layers before the ephemeral context disappears.

### 2.2 Per-base `.agent-context/`

The fixed directory name is `.agent-context/`, and it exists inside every designated base. It is the source of
truth over ephemeral session context (`../SKILL.md:L23-L30`).

The store separates four concerns:

| Component | Architectural concern | Normative source |
|---|---|---|
| `STATE.md` | Mutable working state: focus, live threads, next steps, open questions | `../SKILL.md:L52-L55` |
| `MEMORY.md` | Durable domain knowledge: facts, decisions, conventions, people, tooling, gotchas | `../SKILL.md:L55-L55` |
| `JOURNAL.md` | Ordered evidence of activity, newest first | `../SKILL.md:L56-L56` |
| `README.md` | Base identity, protocol, and persona-continuity contract | `../SKILL.md:L57-L57` |

This separation prevents three common forms of drift:

- Live status being mistaken for invariant knowledge.
- Durable decisions disappearing into a chronological log.
- Historical actions being mistaken for current state.

The source defines the distinctions and cadences; the drift analysis above is a **derived interpretation** of
those distinctions (`../SKILL.md:L48-L64`).

### 2.3 Base documentation

Base-level Markdown, handbooks, and PDFs are the mostly-static “textbook” layer
(`../SKILL.md:L177-L182`). They hold deep reference material that does not belong in a concise working-state
store.

**Recommendation.** Link from `STATE.md` or `MEMORY.md` to the exact authoritative document rather than
copying large sections into `.agent-context/`.

### 2.4 zmem

zmem is the cross-cutting, cross-base persistence layer for identity, conventions, and gotchas not owned by a
single base. It is read during hydration and written selectively (`../SKILL.md:L181-L182`).

This creates a deliberate scope split:

- Base-specific state and facts belong in `.agent-context/`.
- Cross-base knowledge belongs in zmem.
- A significant final offload may have both a local store update and a zmem episodic
  (`../SKILL.md:L133-L138`).

### 2.5 Context Mesh

Context Mesh is the generated portfolio layer. It presents:

- `CONTEXT-MESH.md` as a compact startup digest.
- `context-index.json` as the machine-readable graph.
- `context-mesh.html` as the human dashboard.

Those artifacts and their relationship to `context-offload` are normative
(`../SKILL.md:L183-L185`). Context Mesh must be refreshed after changing a context store or writing relevant
zmem memory (`../SKILL.md:L130-L131`).

## 3. Ownership model

### 3.1 Current base

The current working directory is resolved through Context Mesh to a registered base. That base is the active
persona and owns the store used for hydration and offload (`../SKILL.md:L27-L30`,
`../SKILL.md:L110-L119`).

### 3.2 Sibling bases

Sibling bases are domain owners, not shared scratchpads. Existing sibling stores remain read-only while a new
base is registered (`../SKILL.md:L27-L30`), and their information must be referenced instead of duplicated
(`../SKILL.md:L43-L44`).

**Derived interpretation.** A cross-base handoff changes pointers and ownership metadata; it does not grant
the current persona permission to rewrite the sibling’s state.

### 3.3 Registration authority

If no base matches, the source requires immediate registration of the current working directory, or a
different root explicitly named by the user. Registration consists of creating the four-file store, adding
the persona to the registry, adding relevant cross-references, and refreshing Context Mesh
(`../SKILL.md:L27-L30`, `../SKILL.md:L101-L104`).

## 4. Persona registry architecture

Each registry row has three semantic fields:

1. **Base identity** — the human-recognizable base name or path.
2. **Persona** — the role the assistant becomes when working in that base.
3. **Scope** — the domain boundaries and responsibilities of that persona.

The registry states that each base is a distinct persona and that resumption adopts that scope and voice while
retaining the same honest, concise underlying assistant (`../SKILL.md:L68-L72`). The authoritative mappings
are listed in `SKILL.md:L74-L96`.

### 4.1 Persona identity versus universal invariants

Persona scope can change by base, but these properties do not:

- Honesty and explicit sourcing.
- Capability limits.
- English in Latin/Roman script, with Hinglish rather than Devanagari.
- Concise, scannable communication.
- Teams-oriented formatting and link conventions.
- Recorded environment constraints.

These invariants are normative across every persona (`../SKILL.md:L155-L173`).

### 4.2 Persona continuity contract

The `README.md` inside each store carries the base identity and contract; its content changes rarely
(`../SKILL.md:L52-L64`). The contract is operationalized by:

- Hydrating before context-dependent work.
- Keeping state current throughout the session.
- Persisting milestones and durable knowledge in the correct files.
- Preserving the persona’s voice and conventions.

These responsibilities derive directly from the prime directive and continuous-offload rules
(`../SKILL.md:L13-L19`, `../SKILL.md:L31-L40`).

## 5. State and event architecture

### 5.1 `STATE.md` as a mutable snapshot

`STATE.md` answers “Where are we right now?” and must start with a `Last updated` line. New stores also include
the exact `Last context offload` marker and the standard sections `Current focus`, `Threads`,
`Open questions`, and `Environment reminders` (`../SKILL.md:L52-L64`).

### 5.2 `MEMORY.md` as durable knowledge

`MEMORY.md` answers “What is invariably true?” and is updated when a durable fact or decision is established
(`../SKILL.md:L55-L55`). The new-store template contains `People`, `Conventions`, `Gotchas`, and
`Context-offload protocol` sections (`../SKILL.md:L61-L64`).

### 5.3 `JOURNAL.md` as evidence timeline

`JOURNAL.md` is a dated, newest-first log with one entry per session or significant action
(`../SKILL.md:L56-L56`). The source requires frequent entries rather than a single late summary
(`../SKILL.md:L35-L38`, `../SKILL.md:L124-L125`).

### 5.4 `README.md` as identity contract

The base store’s `README.md` documents the protocol and the identity/persona contract and is updated rarely
(`../SKILL.md:L57-L57`). It is not the live status file.

## 6. Freshness architecture

The freshness clock is the exact ISO-8601 `Last context offload` marker in `STATE.md`
(`../SKILL.md:L31-L34`). The state categories are:

- **Fresh:** marker is valid and younger than 12 hours.
- **Stale:** marker is missing, invalid, or at least 12 hours old.
- **Pending persistence:** content may have been edited, but the marker must not advance until all offload
  steps succeed.

The first two categories are directly normative; “pending persistence” is a **derived state** from the rule
that the marker advances only after all persistence succeeds (`../SKILL.md:L126-L138`).

## 7. Provenance and trust model

The store is trusted by the next session, so the writer must not fabricate, infer fresh status from stale
material, or overstate capabilities (`../SKILL.md:L39-L42`, `../SKILL.md:L160-L164`). Durable content should
be grounded in:

- Tool output.
- The user’s explicit words.
- Existing verified store content.
- Authoritative base documentation.

The first three are explicitly named as acceptable grounding for claims (`../SKILL.md:L160-L162`); base docs
are the defined deep-reference layer (`../SKILL.md:L177-L180`).

## 8. Security and privacy architecture

Sensitive data is excluded by design:

- Do not offload sensitive content without explicit consent.
- Never write secrets or tokens into `.agent-context/` or zmem.
- Keep sibling stores read-only and avoid duplicating their domain content.

These controls are normative (`../SKILL.md:L149-L151`, `../SKILL.md:L192-L199`).

**Recommendation.** Before persistence, review candidate text for credential assignments, bearer tokens,
private keys, cookies, connection strings, customer payloads, and unnecessary personal data. This expands the
source guardrail into a practical review checklist; it is not a replacement for the source rule.

## 9. Cross-skill interaction

`context-offload` and `context-mesh` form a feedback loop:

1. Context Mesh resolves the current base.
2. `context-offload` hydrates the base and persona.
3. Work updates the current base store and possibly zmem.
4. Context Mesh regenerates the portfolio artifacts.
5. A later session consumes the refreshed digest and index.

The source defines every edge in this loop (`../SKILL.md:L108-L131`,
`../SKILL.md:L177-L188`).

