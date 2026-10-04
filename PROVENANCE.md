# Provenance and Scope Decisions

## Objective

This repository documents skills created in the user's own workstreams without misattributing separately maintained team, vendor, or bundled content.

## Discovery method

The inventory was assembled from locally verifiable skill roots:

1. `C:\Users\mishrad\.copilot\skills`
2. `C:\devdesk\tools\copilot\skills`
3. `C:\devdesk\Copilot\CopilotSessions\documentation-mesh-plugin\skills`
4. `C:\devdesk\BCDR\BCDR-Skills\skills`
5. `C:\devdesk\Copilot\CopilotSessions\AzRel-CopilotSkillsLibrary\.github\skills`
6. installed Agency and Azure skill roots

Repository history, plugin metadata, junction targets, and local source files were inspected to establish authorship and ownership.

## Inclusion decision

The nine included skills are tied to personal or directly authored project workstreams:

| Skill | Canonical source at inventory time | Basis |
|---|---|---|
| `ado-workplan` | `C:\devdesk\tools\copilot\skills\ado-workplan\SKILL.md` | Personal WorkDesk planning workflow |
| `career-forensics` | `C:\Users\mishrad\.copilot\skills\career-forensics\SKILL.md` | Personal persistent career operating system |
| `clipfarm-leetcode` | `C:\Users\mishrad\.copilot\skills\clipfarm-leetcode\SKILL.md` | Personal ClipFarm editorial workflow |
| `context-mesh` | `C:\Users\mishrad\.copilot\skills\context-mesh\SKILL.md` | Personal cross-session context system |
| `context-offload` | `C:\Users\mishrad\.copilot\skills\context-offload\SKILL.md` | Personal context and persona continuity protocol |
| `dayplan` | `C:\devdesk\tools\copilot\skills\dayplan\SKILL.md` | Personal combined workday planner |
| `documentation-mesh` | `C:\devdesk\Copilot\CopilotSessions\documentation-mesh-plugin\skills\documentation-mesh\SKILL.md` | Plugin metadata identifies Debashish Mishra as author |
| `nse-advisor` | `C:\Users\mishrad\.copilot\skills\nse-advisor\SKILL.md` | Personal paper-trading research workflow |
| `speak` | `C:\devdesk\tools\copilot-speak\skills\speak\SKILL.md` | Context Mesh records direct creation from the user's Copilot Speak request; plugin metadata identifies `mishrad` |

## Explicit omissions

The user explicitly requested that these skills be skipped:

- `daily-sev2-report`
- `outage-comms-formatted`

No documentation folder is created for either skill.

## Collections not imported

### BCDR-Skills

The BCDR repository is a shared extension collection. Git history shows most skills were authored by multiple team members. Only the two skills clearly initiated under Debashish Mishra's name were the two explicitly excluded skills, so the remaining team collection is not reclassified as personal work.

### AzRel-CopilotSkillsLibrary

The AzRel library is a curated multi-author repository with explicit per-skill owners. It is a reference collection, not a personal authored-skill set, and is therefore outside this archive.

### Bundled Azure and Agency skills

Skills installed under `.agents\skills` and `installed-plugins` are product/plugin payloads. Installation on the machine does not establish authorship.

### zmem

The local `zmem` link contains a host integration note that points to a skill shipped by the separate zmem project. It is a dependency used by the context skills, not treated here as an authored skill.

## Context Mesh follow-up inventory

The second provenance pass used `artifactProvenance.records` from Context Mesh and checked each candidate against current source files and repository history.

| Candidate | Decision | Evidence |
|---|---|---|
| `speak` | Included | High-confidence `created` record for `copilot-speak\skills\speak\SKILL.md`, direct user request, current source exists |
| `deep-explanation` | Excluded | The record was produced while inspecting skill infrastructure around the DRI workplan creation; the source no longer exists |
| `my-new-skill` | Excluded | Placeholder path used in sync-script usage guidance, not an implemented skill |
| `ev2-limits-validation` | Excluded | Git history attributes original creation to Suryansh Mishra |
| `asc-sds-phase2` | Excluded | Git history attributes the ASC migration skill collection to other engineers |
| `dri-workplan` | Removed by request | The user explicitly said this skill folder is not needed in this library |

## Snapshot policy

- `SKILL.md` is copied byte-for-byte from the canonical source at inventory time.
- `source-inventory.json` stores the source path and SHA-256.
- Documentation may explain the source but must not silently repair or reinterpret it.
- A future refresh must report hash changes before replacing a snapshot.
- Source paths are historical provenance, not a guarantee that the original location will remain available.
