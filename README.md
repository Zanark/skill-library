# Authored Skill Library

This repository is the documentation archive for the Copilot skills authored in Debashish Mishra's personal and project workstreams. It preserves each original `SKILL.md` as a source snapshot and surrounds it with operator-focused documentation: architecture, workflow, reference material, examples, validation, troubleshooting, and maintenance guidance.

## Scope

The inventory is provenance-based. A skill is included when it was authored as part of the user's own workstreams and has a locally verifiable source definition. Installed Microsoft skills, Agency plugin skills, the multi-author AzRel library, and team-authored BCDR skills are not presented as personal creations.

The following two authored skills were explicitly excluded from this repository:

- `daily-sev2-report`
- `outage-comms-formatted`

They are not copied, summarized, or documented here.

## Documented skills

| Skill | Domain | Primary role |
|---|---|---|
| [ado-workplan](skills/ado-workplan/README.md) | Work management | Builds the remaining-day ADO sprint schedule and updates the daily sprint note |
| [career-forensics](skills/career-forensics/README.md) | Career knowledge | Maintains an evidence-backed, persistent engineering career knowledge base |
| [clipfarm-leetcode](skills/clipfarm-leetcode/README.md) | Media engineering | Produces reviewed coding and system-design clips through ClipFarm |
| [context-mesh](skills/context-mesh/README.md) | Cross-session memory | Builds the portfolio-wide context graph, digest, and provenance dashboard |
| [context-offload](skills/context-offload/README.md) | Cross-session memory | Persists per-base state, durable memory, journal, and persona continuity |
| [dayplan](skills/dayplan/README.md) | Work management | Combines DRI/IcM and ADO work into one prioritized day schedule |
| [documentation-mesh](skills/documentation-mesh/README.md) | Documentation intelligence | Builds an offline evidence-backed graph and health report for Markdown collections |
| [nse-advisor](skills/nse-advisor/README.md) | Market research | Produces paper-trading NSE research and allocation scenarios |
| [speak](skills/speak/README.md) | Accessibility and voice | Makes Copilot CLI speak concise plain-text responses through a local Windows TTS MCP server |

## Documentation depth

The current archive contains:

- **9** authored skills;
- **63** per-skill files;
- **13,519** lines of skill source and explanatory Markdown;
- an exact source snapshot plus **six** dedicated documentation files for every skill;
- repository-level provenance, relationships, glossary, catalogue, maintenance, and validation material.

The depth is intentionally operational rather than promotional: each folder documents routing, architecture, detailed execution, fixed contracts, examples, edge cases, failure handling, regression tests, and maintenance impact.

## Standard folder contract

Every skill folder contains:

```text
skills/<skill-name>/
  SKILL.md
  README.md
  docs/
    ARCHITECTURE.md
    WORKFLOW.md
    REFERENCE.md
    EXAMPLES.md
    OPERATIONS-AND-TESTING.md
```

- `SKILL.md` is the preserved operational source. Documentation must never silently change its meaning.
- `README.md` is the entry point and executive operating guide.
- `ARCHITECTURE.md` explains boundaries, components, state, dependencies, and relationships.
- `WORKFLOW.md` expands the execution path, branches, gates, and side effects.
- `REFERENCE.md` is the exhaustive lookup surface for triggers, inputs, outputs, paths, rules, and contracts.
- `EXAMPLES.md` provides worked scenarios grounded in the source.
- `OPERATIONS-AND-TESTING.md` covers validation, regression scenarios, troubleshooting, and maintenance.

The nine source snapshots account for nine of the 63 files; the remaining 54 files are the dedicated documentation suite.

## How to read this library

1. Start with a skill's `README.md` to understand purpose, routing, and operating boundaries.
2. Read `ARCHITECTURE.md` before changing dependencies, persistence, file layouts, or cross-skill contracts.
3. Use `WORKFLOW.md` while executing or debugging a run.
4. Use `REFERENCE.md` for exact rules and fixed values.
5. Use `EXAMPLES.md` to understand expected decisions and outputs.
6. Run through `OPERATIONS-AND-TESTING.md` before publishing a source change.
7. Treat `SKILL.md` as the final normative authority whenever documentation and source disagree.

## Provenance and source integrity

[`source-inventory.json`](source-inventory.json) records the original local path, archived destination, and SHA-256 hash for every included source snapshot. This makes it possible to distinguish documentation edits from changes to the operational skill definition.

The inventory deliberately excludes:

- bundled skills under `C:\Users\mishrad\.agents\skills`;
- installed Agency plugin skills not authored in these workstreams;
- the multi-author `AzRel-CopilotSkillsLibrary`;
- team-authored skills in `BCDR-Skills`;
- dependency-provided and `node_modules` skills;
- the two explicitly omitted skills listed above.

Context Mesh provenance also identified historical or repository-owned candidates that were not imported:

- `deep-explanation` was a misattributed inspection record around creation of the now-removed `dri-workplan`;
- `my-new-skill` was only a placeholder path in setup guidance;
- `ev2-limits-validation` and `asc-sds-phase2` were authored by other engineers according to Git history;
- `speak` had direct high-confidence creation evidence and a current source, so it is included.

Repository-level documentation is consolidated under [`docs\`](docs/README.md):

- [Catalogue](docs/CATALOGUE.md)
- [Provenance and scope](docs/PROVENANCE.md)
- [Context Mesh discovery](docs/CONTEXT-MESH-DISCOVERY.md)
- [Documentation standard](docs/DOCUMENTATION-STANDARD.md)
- [Skill relationships](docs/SKILL-RELATIONSHIPS.md)
- [Maintenance playbook](docs/MAINTENANCE-PLAYBOOK.md)
- [Glossary](docs/GLOSSARY.md)
- [Machine-readable catalogue](docs/catalogue.json)

## Validation

Run:

```powershell
.\scripts\Validate-SkillLibrary.ps1
```

The validator checks the expected folder contract, required documentation sections, source inventory consistency, exclusion rules, broken relative Markdown links, and source hashes.
