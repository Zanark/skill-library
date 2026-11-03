# Evolution: how the manual becomes richer

## Versioning and admission policy

The canonical authored files live in this repository. Do not edit an installed
copy and forget the source. Version 1.0 is a first broad synthesis, not an
exhaustive archive.

Proposed version convention:

- Patch: wording/navigation corrections that do not change the working contract.
- Minor: a new supported technique, case, template or compatible procedural detail.
- Major: a materially changed authority/schema/execution contract requiring
  readers to revisit prior assumptions.

Use the repository's existing release policy if one is later established. This
convention does not authorize creating tags or releases.

## Triggers for enrichment

Add material when a project supplies:

1. A genuinely new documentation/development mode.
2. A stronger concrete example of an existing technique.
3. An important exception or failure that refines guidance.
4. A superseding local contract or better validated procedure.
5. A new reproducibility, privacy, accessibility or verification lesson.

Routine feature progress, a new screenshot or a file-count increase alone is
not enough. Avoid turning the manual into a chronological dump of every project.

## Exact procedure

### 1. Establish source and authority

Read the governing instruction and the actual representative artifact. Record
the project label, canonical role/path, reviewed range/date and revision/hash
when material. Determine whether the statement is observed practice, a scoped
requirement, a proposal or unverified.

Check whether the source is private, stale, generated, frozen or a duplicate.
Do not use source availability as permission to publish it.

### 2. Identify the delta

State the new technique in one sentence, then compare it with existing sections.
Ask: does it add a mechanism, decision rule, failure boundary or useful
counterexample? If it merely renames the same pattern, add at most a case/source
reference, not another near-duplicate chapter.

### 3. Resolve contradictions explicitly

Keep both scoped rules if they apply to different projects. If a newer rule
supersedes an older one in the same project, record the relationship and date.
Never infer consensus from one example or rewrite older history.

Example: a strict publication allowlist and an older chapter auto-discovery
builder can coexist as different contracts. The manual may recommend the
allowlist for publication without falsely claiming every older book uses it.

### 4. Author the reusable form

Update the relevant manual section with when/why/how, input/output, authority,
step order, failure conditions, evidence and transfer limits. Add or update a
case, safe source receipt and template only when useful. Preserve original
asset/tool licenses and do not paste confidential source bodies.

### 5. Reconcile the package

Update README/navigation, REFERENCE routing, EXAMPLES, SOURCES and this change
log. Update templates and validation gates affected by the new contract.
If SKILL changes, update the exact inventory hash. If skill catalogue meaning
changes, update both human and JSON catalogue entries and relationships.
Regenerate portable checksums with existing tooling.

### 6. Verify and hand off

Run appropriate structural checks, review semantic consistency and validate any
new example's actual outcome where claimed. A procedure described but not run
must remain labeled as such. Record omissions and unresolved source drift.
Persist owned continuity and give a concise full-path handoff.

Use [the enrichment record](../templates/09_ENRICHMENT_RECORD.md).

## Deprecation

Mark obsolete guidance with replacement and reason; avoid deleting useful
historical context. Keep current instructions unambiguous. Archived/frozen
editions remain immutable; a new manual version can explain their limitations
without editing their historical artifact receipts.

## Change log

| Version | Date | Change | Evidence and limits |
|---|---|---|---|
| 1.0 | 2026-11-03 | Initial skill/manual, workflow/reference, sixteen case studies, source register and reusable templates | 33 mesh entries structurally inventoried; 1,077 discovered text artifacts; canonical contracts and representative documents reviewed, not every paragraph; private operations retained as process-only synthesis |

Do not add future completion entries until the stated work actually happened.
