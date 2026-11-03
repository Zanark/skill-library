# Documentation Standard

## Authority model

The preserved `SKILL.md` is normative. The surrounding documents are explanatory. If they conflict, the source wins and the documentation must be corrected.

For repository-authored skills such as `development-documentation-manual`,
`SKILL.md` is authored canonically here rather than copied from an external
snapshot. Its routed manual/support contracts are maintained together; local
target-project instructions still outrank that manual's proposed defaults.

## Required coverage

Each skill documentation set must explain:

1. Purpose and non-goals.
2. Invocation phrases and routing boundaries.
3. Required and optional inputs.
4. Dependencies, tools, data sources, and fixed paths.
5. State model and persistence behavior.
6. End-to-end workflow, branches, approvals, and stop conditions.
7. Output and side-effect contracts.
8. Safety, privacy, honesty, and failure behavior.
9. Integration with related skills and systems.
10. Worked examples, edge cases, and anti-examples.
11. Test matrix and regression risks.
12. Maintenance guidance and known limitations.

## Citation rules

- Normative claims should cite `SKILL.md:Lx-Ly`.
- Implementation-specific claims may cite a verified repository file and line range.
- Do not cite generated documentation as proof of source behavior.
- Label recommendations as recommendations; do not present them as source requirements.
- Label historical paths and dates as snapshot facts.

## Change procedure

1. Compare the canonical source SHA-256 with `source-inventory.json`.
2. Review the complete source diff.
3. Replace the archived `SKILL.md` only when the source change is intentional.
4. Update every affected explanatory document.
5. Add or revise examples and regression scenarios for changed behavior.
6. Run `scripts\Validate-SkillLibrary.ps1`.
7. Review the final diff for accidental inclusion of excluded or third-party skills.

For a repository-authored skill, edit its canonical source deliberately instead
of replacing an external snapshot, then update its exact inventory hash and
affected support files. Do not apply that exception to archived external skills.

## Quality bar

Documentation is complete only when an operator can:

- decide whether the skill is the correct router for a request;
- identify every required input and dependency;
- execute the workflow without relying on hidden assumptions;
- understand all persistent writes and external actions;
- recognize stale, unsupported, or unsafe states;
- verify outputs against explicit acceptance criteria;
- maintain the skill without losing supersession or compatibility rules.

## Sensitive information

Document contracts and paths only when they are already part of the authored skill. Do not add credentials, tokens, private payloads, customer data, or complete local transcripts.
