---
name: development-documentation-manual
description: Apply or enrich the living cross-project development and documentation manual. Covers numbered TODO workstreams, evidence, development journals, engineering books, source atlases, curricula, visual/media production, reports, publishing, context handoffs and using desktop/web apps while agents develop them. Use for "follow my development workflow", "documentation manual", "document this project like my other projects", "update the development manual", "capture this project's documentation techniques", or "keep using the app while you edit it". Not an authorization to publish, commit, deploy, collect private data or rewrite other projects.
---

# Development and Documentation Manual

This is a repository-authored synthesis, not an archived external skill. The
canonical support root is
`C:\devdesk\homedesk\skill-library\skills\development-documentation-manual`.
The library installer rebases that repository path to its actual checkout.
Supporting files remain in the checkout; they are not copied beside an installed
`SKILL.md`. If unavailable, report the missing checkout instead of inventing rules.

## Required entry reads

1. Read the support root's `README.md` and `MANUAL.md`.
2. Read `docs\WORKFLOW.md`, `docs\REFERENCE.md` and the target project's contributor
   instructions, current TODO index, relevant contracts and implementation.
3. Use `docs\EXAMPLES.md` to identify applicable modes, then read the corresponding
   manual sections. For enrichment also read `docs\EVOLUTION.md` and
   `docs\SOURCES.md`. Read `docs\OPERATIONS-AND-TESTING.md` before closing work.
4. Hydrate context through the installed `context-offload`/`context-mesh` protocols
   when applicable. This manual does not replace them or authorize a new store.

## Authority and honesty

- Current user scope, safety and repository-local rules take precedence over this
  manual's proposed defaults. Never silently normalize a project's deliberate
  exception. Resolve significant conflicts before implementation.
- Distinguish **observed pattern**, **project-specific contract**, **proposed
  reusable default**, and **not verified**. Source examples are not universal law.
- Discovery, a matching filename, a hash, a parser pass and generated page counts
  are not semantic review, visual review, user approval or publication clearance.
- Read-only sibling stores stay read-only. Excluded/restricted files stay excluded.
  Public examples must be independently public-safe; renaming internal entities
  does not make private architecture suitable for publication.

## Execution contract

1. Establish target, desired outcome, authority, existing dirty work and allowed
   write/output boundaries. Inspect before editing.
2. Select the smallest applicable modes. Do not generate a book, atlas, PDF,
   report, TODO system or new tooling solely because this manual describes one.
3. For an authorized planning/workstream system, retain `TODO\00_INDEX.todo`,
   stable numbered `.todo` files and a development ledger. Include Status,
   Milestone, Dependencies, Purpose, Tasks, Acceptance criteria, Completion
   evidence and Completion log. Reuse an existing documented alternative.
4. Implement a bounded change with its directly affected tests and documentation.
   Record actual failures and decisions; preserve unrelated work and old editions.
5. Verify the exact outcome at the relevant layer. Keep implementation, technical
   verification, environmental qualification, human acceptance and publication
   separate. A fixture is not a live system; a local file is not a sent message.
6. Update affected TODO/index, public docs/journal and owned private continuity
   according to their different audiences. Use full artifact paths in handoffs.
7. Do not commit, push, upload, publish, schedule, deploy, enable tools or change
   permissions merely because documentation is ready. Follow explicit authority.

## Commit cadence and identity

Follow MANUAL section 4.5: across projects, commit promptly at coherent, verified
milestones when commits are authorized. Prefer independently reviewable working
slices over end-of-project dumps; never use timers, file counts, empty commits
or unfinished fragments to manufacture activity. Include directly dependent
tests/docs, stage only owned intended changes and review the staged diff.
Always use the verified Zanark author and committer identity, with repository-local
or per-command settings; never change shared global identity or guess an email.
Local Git commits do not use a PAT. For authorized GitHub operations, use the
existing credential runner and verify its login is Zanark; follow
docs\GITHUB-TRACKING.md for Git transport and identity checks. Account mismatch
or missing identity is a blocker, not permission to use another signed-in account.
This cadence does not grant push/deployment authority or override local gates.

## Concurrent use while developing

When the user may be using the desktop app or website being edited, follow
MANUAL section 4.6 and `templates\15_RUNTIME_OWNERSHIP.md`. Protect the active
instance: no uncoordinated close, restart, reload, focus theft, reinstall or
overwrite of files it can load. Default to a known-good stable-use lane and a
separate development/test lane; live preview requires explicit selection and
does not promise uninterrupted use.
Record actual build/source identity, paths/URLs, verified process ownership,
mutable state and exclusive resources. Different ports, worktrees or a running
process do not establish isolation. Use disposable test profiles/data, bound
resource-heavy tests and stop only identified agent-owned processes. If isolation
is impossible, continue non-conflicting work and coordinate the narrow interruption.
Prepare and verify a complete candidate before an authorized switch, preserving
unsaved work and compatible recovery. Test concurrent behavior without driving
the user's session; never claim code rollback also reverses data migrations.
This guidance does not authorize restarting, migrating or deploying an application.

## GitHub tracking contract

The user's cross-repository requirement is one actual TODO workstream to one
repository issue and one configured Project item: mirror public-safe descriptions
and updates, backlink the issue URL, and match issue state to completion.
Preserve numbered `.todo` files and all eight fields. Read
`docs\GITHUB-TRACKING.md` before applying this mode.
Separate this requirement from implementation: this manual supplies no sync
runtime. Check per-repository adoption, credentials, visibility, status mapping
and authority before remote writes. Preview historical imports and use stable
identities for retries. Never silently overwrite conflicting local/remote edits,
export private context, request a PAT in chat, or claim synchronization succeeded
without verifying issues, Project membership/status and local backlinks.
Use `scripts\with_github_token.py` under the canonical support root to run
authorized GitHub/sync commands from any repository. It reads the ignored local
`.env` first, then process/current-Windows-user environment only if the file is
absent. Never view, print, search, copy or package `.env`; a blank/invalid or
tracked/unignored file is a blocker, not a fallback. Only trusted child commands
receive the credential; never persist/replace global `GH_TOKEN`. The owner also
opts into `workflow` access for authorized Actions-definition maintenance:
follow the support guide's trusted-ref, minimal-permission, secret-isolation and
exact-run verification gates. Available scopes do not authorize deployment,
dispatch, scheduling or activation outside the task's approved scope.

## Enrichment contract

For a genuinely new technique, review the actual source, classify its authority,
record a privacy-safe source receipt and case, update the manual and applicable
template, add an evolution entry, and reconcile navigation/catalogues/hashes.
Retain contradictions and supersession rather than overwriting history.
Use `templates\09_ENRICHMENT_RECORD.md`; do not store confidential source bodies.

## Stop conditions

Stop or narrow the claim on missing evidence, restricted/private source without
authorized handling, contradictory local contracts, conflicting unowned edits,
missing required render/runtime tools, failed validation or absent approval.
Report exactly what remains unverified. Never weaken security or fabricate
success to complete a checklist.
