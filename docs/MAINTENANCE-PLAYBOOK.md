# Maintenance Playbook

## Refreshing one skill

1. Resolve the canonical source path from `source-inventory.json`.
2. Hash the canonical source and compare it with the archived snapshot.
3. If unchanged, do not rewrite the snapshot merely to refresh timestamps.
4. If changed, save the source diff and identify:
   - new trigger or routing rules;
   - changed inputs, tools, or paths;
   - changed persistence or external side effects;
   - new approvals, stop conditions, or safety gates;
   - superseded rules;
   - output schema or formatting changes.
5. Replace the snapshot only after confirming it is the intended canonical version.
6. Update all explanatory documents whose claims are affected.
7. Add regression cases for the changed behavior.
8. Update the inventory hash.
9. Run the repository validator.

## Reviewing documentation drift

Search documentation for each changed term, path, command, schema field, or fixed value. A source change commonly affects more than the obvious reference page:

- architecture changes affect `ARCHITECTURE.md`;
- stage or branching changes affect `WORKFLOW.md`;
- values and schemas affect `REFERENCE.md`;
- changed decisions affect `EXAMPLES.md`;
- changed gates affect `OPERATIONS-AND-TESTING.md`;
- changed purpose or routing affects the skill `README.md` and root catalogue.

## Handling superseding rules

Some skills, especially `clipfarm-leetcode`, retain historical requirements while declaring later rules authoritative.

1. Preserve chronology.
2. State which rule is current.
3. Explain the scope of the supersession.
4. Do not erase the older rule when it remains relevant to historical outputs.
5. Add a regression scenario proving the current rule wins for new work without rewriting old artifacts.

## Handling path changes

Fixed local paths may be part of the operational contract.

- Update a path only when the canonical source changes.
- Distinguish required paths from examples.
- Keep historical provenance paths in the inventory.
- If a path is unavailable, documentation should describe the failure honestly rather than inventing a fallback.

## Handling external-tool changes

When an MCP tool, CLI command, or runtime changes:

1. Verify the replacement exists.
2. Confirm input/output semantics, not only the new name.
3. Review authentication and authorization differences.
4. Update failure handling and examples.
5. Add a test for unavailable, unauthorized, empty, stale, and partial responses.
6. Do not claim compatibility until the complete workflow has been exercised.

## Adding a newly authored skill

1. Establish provenance and authorship.
2. Confirm it is not bundled, dependency-provided, or owned by a separate team repository.
3. Confirm it is not one of the explicit omissions.
4. Create the standard folder contract.
5. Copy the exact `SKILL.md`.
6. Record source path and SHA-256 in `source-inventory.json`.
7. Produce all required documentation files.
8. Add it to `..\README.md`, `CATALOGUE.md`, `catalogue.json`, `SKILL-RELATIONSHIPS.md`, and `GLOSSARY.md` as applicable.
9. Run validation.

## Removing a skill

Removal should be explicit. Do not remove a folder merely because the canonical path is temporarily unavailable.

Before removal:

- establish whether the skill was renamed, superseded, archived, or deleted;
- preserve history when the documentation remains useful;
- update relationship and catalogue references;
- remove its inventory entry only when the source is intentionally no longer part of the authored library.
