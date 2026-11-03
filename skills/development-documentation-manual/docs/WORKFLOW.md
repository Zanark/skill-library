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

**Exit:** acceptance criteria have evidence, or explicit blocked/partial states.

## Phase E - reconcile the documentation system

1. Update affected workstream, index and development ledger.
2. Update relevant guides/book/source atlas/visual references and navigation.
3. Preserve failed hypotheses, original sources and superseded decisions.
4. Update owned private context without exporting it to public docs.
5. If the project adds a technique, follow EVOLUTION; routine feature progress
   alone need not create a new manual chapter.
6. Reconcile package/catalogue hashes for any registered skill changes.

**Exit:** a new session can find the artifact and understand what happened,
why, what is verified and what remains.

## Phase F - handoff, not automatic publication

State the actual outcome and full absolute entry paths. Identify consequential
limitations plainly. Commit/push/upload/deploy only with existing explicit
authority. Do not schedule work, enable tools or wake other agents as a hidden
side effect of documentation.

## Recovery when interrupted

Persist current workstream/status, exact files touched, unfinished commands and
owned process IDs, last successful check, failed check, remaining criteria and
next bounded action. An interrupted tool is not presumed successful. On resume,
reconcile with disk before continuing. Never relaunch a completed render solely
because a historical note still says it was running.
