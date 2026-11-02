# Context Offload and Persona Continuity

`context-offload` defines the durable, per-base memory protocol that lets a later session resume with the same
working knowledge, active threads, tone, conventions, and persona as the session that performed the offload.
The contract is stronger than note-taking: the store must make the next session resumable as “the same me”
(`SKILL.md:L13-L19`).

## Documentation convention

This suite separates requirements from operational advice:

- **Normative** means the behavior is required by `SKILL.md`.
- **Derived interpretation** explains the consequence of one or more source requirements without adding a new
  requirement.
- **Recommendation** is optional guidance for implementing, reviewing, or testing the normative behavior.

Every normative claim cites an explicit `SKILL.md:Lx-Ly` range. Recommendations are labelled and must not be
treated as source requirements.

## What the skill owns

**Normative.** Each user-designated base has a fixed-name `.agent-context/` directory. That directory is the
base-specific source of truth over ephemeral chat context (`SKILL.md:L23-L30`). It always contains:

- `STATE.md` — current focus, live threads, next steps, and open questions.
- `MEMORY.md` — durable facts, decisions, conventions, people, tooling, and gotchas.
- `JOURNAL.md` — newest-first dated activity history.
- `README.md` — protocol, base identity, and persona-continuity contract.
- `.agent-context\social\*.json` — one append-only social persona file per active session, with replies, emoji reactions,
  persona colors, and occasional humor/shitposts.

The file roles and update cadences are normative (`SKILL.md:L48-L64`). Social persona files follow the schema
and ownership rules in `SKILL.md`.

## Layered memory model

The protocol intentionally distributes knowledge across layers:

1. **Session context** is temporary and must never be the only persistence layer.
2. **`.agent-context/`** is the living state, memory, history, and identity of one base.
3. **Base documentation** is mostly-static, deep reference material.
4. **`zmem`** stores selective cross-base facts, conventions, identity, and gotchas.
5. **Context Mesh** indexes all bases and zmem into a startup digest, structured graph, and dashboard.

These roles are defined in the source (`SKILL.md:L177-L188`). The layers complement rather than replace one
another.

## Core lifecycle

**Hydrate**

1. Read the Context Mesh startup digest.
2. Resolve the current working directory using the longest matching base path.
3. Read the current base’s `STATE.md`, freshness marker, and `MEMORY.md`.
4. If the marker is missing, invalid, or at least 12 hours old, complete a full offload before doing
   context-dependent work.
5. Skim relevant base docs, query zmem, adopt the registered persona, and continue.

This order is normative (`SKILL.md:L108-L119`).

**Work and offload continuously**

- Update `STATE.md` at milestones.
- Add durable facts to `MEMORY.md` immediately.
- Add significant actions to the top of `JOURNAL.md`.
- Refresh Context Mesh after a context-store change or relevant zmem write.

The source defines continuous offload as the normal operating mode, not merely an end-of-session activity
(`SKILL.md:L31-L44`, `SKILL.md:L121-L131`).

**Close or compact**

- Reconcile current state, next steps, and open questions.
- Add a dated journal entry.
- Write a zmem episodic for a significant offload.
- Advance the exact freshness marker only after persistence succeeds.
- Refresh Context Mesh and verify every persisted layer is readable.

These completion requirements are normative (`SKILL.md:L133-L139`).

## Freshness rule

Every `STATE.md` carries this exact marker shape:

```text
> **Last context offload:** YYYY-MM-DDTHH:mm:ss+05:30
```

A missing marker, invalid marker, or marker that is **at least 12 hours old** is stale. A long-running session
must repeat a full offload whenever another 12 hours elapse (`SKILL.md:L31-L38`). The marker advances only
after all persistence steps succeed (`SKILL.md:L126-L138`).

## Ownership and read/write boundaries

**Normative.**

- The current base owns its own `.agent-context/`.
- Existing sibling stores remain read-only during registration of a new base.
- Cross-base knowledge is referenced rather than copied.
- No secrets, credentials, or tokens may be written to `.agent-context/` or zmem.

These boundaries are established by the registration, cross-reference, and guardrail rules
(`SKILL.md:L27-L30`, `SKILL.md:L43-L44`, `SKILL.md:L192-L199`).

## Persona semantics

A base maps to a distinct scope and persona. Resuming inside that base means adopting its registered role and
voice while retaining the universal honesty and concision invariants (`SKILL.md:L68-L72`). The source registry
contains the authoritative base-to-persona mappings (`SKILL.md:L74-L96`). Adding a base requires both a new
four-file store and a new registry entry (`SKILL.md:L101-L104`).

## Documentation map

- [Architecture](docs/ARCHITECTURE.md) — memory layers, components, ownership, persona model, and trust.
- [Workflow](docs/WORKFLOW.md) — hydration, registration, continuous offload, closeout, and state machines.
- [Reference](docs/REFERENCE.md) — schemas, markers, invariants, registry, commands, and content rules.
- [Examples](docs/EXAMPLES.md) — worked lifecycle and cross-base scenarios.
- [Operations and testing](docs/OPERATIONS-AND-TESTING.md) — runbooks, validation matrices, failure handling,
  security, and maintenance impact.

## Safety and honesty summary

The store must contain verified durable information, not plausible reconstruction. Stale operational state is
labelled “re-verify”; capabilities are not overstated; source attribution remains explicit; sensitive data is
excluded; and a resumed persona preserves the user’s language and output conventions
(`SKILL.md:L39-L44`, `SKILL.md:L143-L173`, `SKILL.md:L192-L199`).

