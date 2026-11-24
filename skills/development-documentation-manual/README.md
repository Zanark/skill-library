# Development and Documentation Manual

A living, agent-readable field manual of development and documentation techniques
observed across the project's wider portfolio. It is an authored synthesis with
explicit source limits, not a claim that every discovered file was fully reviewed.

**Start with [MANUAL.md](MANUAL.md).** It explains the working system, why each
artifact exists, when to use it, exact procedures, examples, failure modes and
completion boundaries. [SKILL.md](SKILL.md) is the executable instruction entry.

| Supporting file | Use |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Authority, artifact layers and dependencies |
| [Workflow](docs/WORKFLOW.md) | An agent's start-to-finish execution procedure |
| [GitHub tracking](docs/GITHUB-TRACKING.md) | Cross-repository TODO/issue/Project contract, safe adoption and automation limits |
| [Reference](docs/REFERENCE.md) | Mode routing, schemas, statuses and evidence vocabulary |
| [Examples](docs/EXAMPLES.md) | Project-specific techniques and transfer limits |
| [Operations and testing](docs/OPERATIONS-AND-TESTING.md) | Content, output, portability and maintenance gates |
| [Sources](docs/SOURCES.md) | Actual source basis, review scope and omissions |
| [Evolution](docs/EVOLUTION.md) | How new projects make the manual richer |
| [Templates](templates/README.md) | Copyable workstreams, journals, books and evidence receipts |
| [Runtime ownership](templates/15_RUNTIME_OWNERSHIP.md) | Protect user instances while developing/testing desktop apps and websites; manual section 4.6 |

## Scope and first edition

Current version **1.5**, updated 2026-11-10 with frequent, substantial commit
checkpoints and mandatory verified Zanark identity within existing authority.
Retains concurrent-use guidance: stable-use/development lanes, opt-in live
preview, runtime/state ownership, coexistence acceptance and coordinated recovery.
Retains the ignored local `.env` credential runner, Git/portable-payload
exclusion gates and authorized Actions workflow-maintenance guidance.
First edition authored 2026-11-03. Portfolio discovery covered 33 Context Mesh
entries, including worktrees, context-only desks and an embedded provenance copy.
A bounded inventory found 1,077 textual tracking/documentation artifacts.
Canonical contracts and representative documents were read; **1,077 is not the
number of documents semantically reviewed**, and 33 is not a product count.

The public manual excludes private operational details, raw conversations,
personal evidence, recordings and unreleased source bodies. A source location
does not imply that a reader has access or redistribution rights.

## Installation and ownership

Registered in this library's source inventory and catalogues. The standard library
installer installs its skill instructions and rebases support paths to the clone.
Keep that clone available: this manual has no separate runtime or dependency
installation. Merely adding the skill does not activate existing sessions.

The optional credential runner uses Python's standard library and local Git.
It reads only the canonical support root's ignored `.env` and launches a
trusted command without printing its token. Credentials are not installed,
packaged or synchronized with this public skill; see
[GitHub tracking](docs/GITHUB-TRACKING.md) for provisioning and limits.

Future changes are authored here, reviewed under [Evolution](docs/EVOLUTION.md)
and recorded in its change log. Historical external skill snapshots elsewhere in
the library retain their own byte-for-byte provenance policy.
