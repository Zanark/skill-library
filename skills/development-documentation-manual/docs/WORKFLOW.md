# Workflow: instructions for the executing agent

## Inputs

Identify target project, requested result, allowed edits, relevant local
instructions, current workstream and delivery audience. If the task is only a
question or audit, do not implement a documentation system as a side effect.
If the task asks for enrichment, also identify the new technique and source.

## Phase A - establish authority and evidence

1. Read the skill entry, manual and this workflow.
2. Resolve and hydrate the designated base through the installed context skills.
   Do not assume the initial terminal directory grants ownership of its siblings.
3. Inspect local instructions and current worktree. Preserve unrelated work.
4. Read the current index, affected workstream, documentation-maintenance
   contract and relevant source. Record explicit approval/publication boundaries.
5. Classify source roles: canonical, generated, frozen, fixture, context-only,
   worktree duplicate or private. Mark stale/unknown evidence.
6. Make a small change-impact map. Use the mode table in REFERENCE to select
   only relevant chapters. Do not require all modes on every project.
7. If the tool may be in active use, establish stable-use versus explicitly chosen
   live-preview mode and identify the protected instance before touching runtime
   files. Read manual section 4.6; record ownership/shared dependencies using
   template 15 or an existing equivalent. Do not restart or migrate it to prepare
   this record.

**Exit:** a concrete outcome and allowed write boundary, with unresolved material
ambiguity raised rather than guessed.

## Phase B - define the bounded unit

1. Reuse an existing workstream or add a stable numbered one if authorized.
2. Specify the eight fields and actual prerequisite IDs.
3. Write acceptance criteria at the user-visible boundary. Include relevant
   negative requirements such as no network, no private capture or no app change.
4. Decide which evidence is needed: focused tests, source review, actual GUI/
   browser behavior, native PDF pages, output ASR, encoded video or target-machine
   execution. Avoid testing only a convenient proxy.
5. Identify which approvals are required and which are not part of this task.
   For concurrent use, define separate build/output/profile/data/resource
   boundaries and coexistence acceptance. Ports/worktrees alone are insufficient;
   coordinate only the unavoidable conflicting check or switch.
   When commits are authorized, identify coherent working checkpoints within
   long workstreams (manual 4.5); never plan per-file or timer-driven spam.
6. For GitHub tracking, read GITHUB-TRACKING.md and the repository's adoption
   record. Establish identity, visibility, status/content ownership and write
   authority; preview imports. Missing tooling or credentials are explicit
   blockers, not permission to omit tracking silently.
   Resolve existing credentials automatically using the tracking guide before
   asking for provisioning. For workflow changes, separately establish scope,
   trusted refs, secret isolation, triggers and activation/dispatch authority.
   Use the support-root credential runner; never view or copy the ignored `.env`
   into tool output. An existing empty/invalid file needs local provisioning,
   not a silent fallback to older stored credentials.

**Exit:** the agent and a future maintainer can tell what DONE means without
guessing from a checkbox count.

## Phase C - implement or author

1. Follow existing code/content patterns. Reuse helpers and prior art.
2. Preserve type safety, explicit errors, original assets and unrelated edits.
3. Explain actual mechanisms and decisions, not only file names or aspirations.
4. Keep facts, proposals, simulations and unverified claims visibly distinct.
5. Update canonical sources rather than patching derived artifacts blindly.
6. Where a pipeline is necessary, run only the required stages with explicit
   input/output paths and failure behavior. Missing tools are blockers, not
   permission to invent output or bypass safeguards.
7. Keep edits, rebuilds and automation out of the stable instance and its mutable
   state. Only explicitly selected live-preview changes may flow into the user's
   preview; this does not authorize destructive tests or uncoordinated restarts.
   Bound resource contention, use disposable test profiles/data and recheck
   process identity before stopping only agent-owned helpers.
8. At each completed checkpoint, perform its focused verification and affected
   documentation/evidence updates, then commit promptly within authority rather
   than accumulating the entire project. Review intended staged hunks and
   verified Zanark author/committer identity; use GITHUB-TRACKING.md for existing
   credential and transport checks. Keep incomplete inseparable changes together.
   Preserve unrelated edits and record the actual commit hash; a commit is not
   a push, and a failed identity check is a blocker, not a fallback account.

**Exit:** the requested source/content exists and dependent surfaces agree.

## Phase D - verify the exact outcome

1. Run targeted existing tests/checks relevant to changed behavior.
2. Inspect real outputs at the relevant boundary.
3. Check expected failure/cancellation/partial-data behavior.
4. Distinguish structural checks from semantic, visual and environmental review.
5. Record observed commands/results and output identity. Do not turn old logs
   or source completion notes into a claim of a new test run.
6. Fix tightly coupled failures and rerun affected checks. Do not fix unrelated
   pre-existing issues without scope.
7. For concurrent use, exercise save/state preservation alongside candidate
   rebuild/test/restart/failure in an isolated representative setup. Verify
   actual state/backend separation; do not automate the user's session.
   Label fixture-only evidence and untested exclusive-resource limits honestly.

**Exit:** acceptance criteria have evidence, or explicit blocked/partial states.

## Phase E - reconcile the documentation system

1. Update affected workstream, index and development ledger.
2. Update relevant guides/book/source atlas/visual references and navigation.
3. Preserve failed hypotheses, original sources and superseded decisions.
4. Update owned private context without exporting it to public docs.
5. If the project adds a technique, follow EVOLUTION; routine feature progress
   alone need not create a new manual chapter.
6. Reconcile package/catalogue hashes for any registered skill changes.
7. Where GitHub sync is adopted and writes are authorized, synchronize the
   existing issue and Project item, verify body/state/status and local backlink,
   and record partial failures. A skill update is not a migration or a runner.

**Exit:** a new session can find the artifact and understand what happened,
why, what is verified and what remains.

## Phase F - handoff, not automatic publication

State the actual outcome and full absolute entry paths. Identify consequential
limitations plainly. Commit/push/upload/deploy only with existing explicit
authority. Do not schedule work, enable tools or wake other agents as a hidden
side effect of documentation.

For applications in concurrent use, hand off stable/candidate paths or URLs,
build and process ownership, data boundary, known limitations and the authorized
switch/recovery plan. Preserve services needed by the user. Promote only after a
coordinated save point; code rollback is not data recovery. See manual section 4.6.

## Recovery when interrupted

Persist current workstream/status, exact files touched, unfinished commands and
owned process IDs, last successful check, failed check, remaining criteria and
next bounded action. An interrupted tool is not presumed successful. On resume,
reconcile with disk before continuing. Never relaunch a completed render solely
because a historical note still says it was running.
