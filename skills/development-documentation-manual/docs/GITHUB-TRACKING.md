# Cross-repository TODO, issue and Project tracking

## Authority and implementation boundary

The user explicitly requires this tracking model across repositories. Retain
local contracts, numbered `.todo` files and the eight workstream fields.
The procedures below describe the required outcomes and a proposed reusable
implementation. This package contains no synchronizer, installed scheduler or
Actions integration. Loading the skill does not migrate repositories or grant
permission to publish their contents.

One shared tool plus a per-repository adoption record is the proposed default.
Repositories may share one Project or choose separate Projects. Every adoption
must specify repository, TODO directory, Project owner/number, mapping, permitted
content, source of truth, triggers and backlink commit policy.

## Identity and content

Maintain one actual workstream <-> one issue in its owning repository <->
one item containing that issue in the configured Project. Do not create a
duplicate Project draft. A Project can span repositories.

Use repository identity plus a stable workstream ID, not title matching.
Persist the issue URL in the workstream without dropping the eight fields;
record Project/item IDs in the tool's chosen documented mapping. A machine
marker in the issue can support recovery after interrupted backlink writes.
Do not renumber completed files. A rename must retain identity.

Mirror the workstream description, tasks, dependencies, acceptance criteria,
evidence and dated updates, subject to the approved visibility boundary.
Relative file links need repository-aware URLs; local machine paths are not
useful public backlinks. Leave issue comments untouched. If an issue body has
human-authored notes, use an explicitly bounded managed section or stop for
reconciliation; never replace unrelated content silently.

Indexes and perpetual development ledgers are navigation/history, not ordinary
feature issues. Exclude them from the proposed default inventory and show this
exclusion for approval. Reusable procedures need deliberate treatment: their
definition being complete does not mark future executions complete.

## Status is two separate remote dimensions

Map actual local vocabulary, not substrings or assumed GitHub option names:

| Workstream condition | Issue state/reason | Project Status |
|---|---|---|
| Not started or explicitly deferred | Open | Backlog |
| Explicitly ready | Open | Ready |
| Active implementation | Open | In progress |
| Awaiting review | Open | In review |
| Defined outcome completed with evidence | Closed / completed | Done |
| Blocked | Open | Keep agreed stage; use blocked label/field |
| Cancelled or superseded | Closed / not planned | Explicit local policy; do not imply completed |

Discover the real Project ID, Status field ID and option IDs. Report missing
options rather than creating fields or guessing identifiers. Read-only access
does not establish edit capability.

Historical composite statuses require review. "DONE locally; publication
BLOCKED" cannot be mapped by searching for either word: determine whether
publication belongs to that workstream's acceptance criteria or a separate
follow-through. Preserve human approval, technical result and remote delivery
as distinct evidence dimensions.

Reopening a workstream reopens the issue and updates the Project according to
the agreed mapping. Deleted files, removed Project items and manually closed
issues require an explicit policy; never infer permission to delete remotely.

## Ownership and conflicts

Recommended initial mode: local TODOs own managed descriptions and completion.
This is a proposal until adopted for the repository. Board movements do not
silently rewrite local files in this mode.

Two-way status synchronization is a separate opt-in design. It needs a saved
last-synchronized baseline for local status, issue state and Project status.
Detect changes on both sides; do not use last-writer-wins timestamps alone.
If changes disagree, report a conflict and leave the affected mapping unchanged
until reconciled. Preserve issue comments and unrelated body content.

One-way mode must still detect unexpected remote edits before overwriting them.
Never turn a failed read into an empty baseline or an apparent deletion.

## Credentials and privacy

Use **Zanark**, the owner-required account (CM-01), for authorized commits and
GitHub operations. Do not silently substitute another signed-in account. A token
inherits that account's permissions; additional scopes do not bypass account
restrictions. Never request token text in chat or store it in source, TODOs,
context stores, logs, receipts, issue bodies or shell command arguments.

As checked against official documentation on 2026-11-06, fine-grained PATs do
not support user-owned Projects. For that setup, the supported classic-PAT
scopes are `project` plus `public_repo` for public-only repositories, or `repo`
when private repositories are included. `workflow` is not needed for ordinary
issue/Project operations. The owner additionally opts into `workflow` access
for authorized workflow maintenance (GH-03); use it when the task requires
creating or updating Actions definitions, not as a prerequisite for issue sync.
Recheck current support before new deployments.

Classic scopes are broad, not issue-only or limited to an approved repository
list. A tool allowlist is not a token security boundary. Use expiration,
rotation/revocation and an appropriate secret store. Organization-owned
automation may have a suitable GitHub App design; do not assume that solves
the current user-owned Project constraint.

For local provisioning, `TODO_SYNC_GITHUB_TOKEN` is a proposed dedicated
environment-variable convention. A tool should map it to `GH_TOKEN` only for
its GitHub child processes. Copilot also consumes `GH_TOKEN`; globally replacing
it can override Copilot sign-in. Do not change shared authentication.
A variable set in a different terminal is not inherited by an already-running
agent. Verify presence without printing the value, then identity, repository
permissions, scopes and Project edit capability using read-only requests.
This proves advertised access, not successful issue/Project mutation.

### Persistent access across local sessions

The owner requires default credential availability across repositories and
sessions, without repeatedly assigning a token (GH-03). This is a local
credential-discovery policy, not permission to migrate every repository or
grant access to other Windows users, machines, hosted agents or Actions.

### Preferred owner-selected source: ignored local .env

The owner's later choice (GH-05) is a plaintext `.env` inside this skill's
canonical support root, not beside the installed SKILL.md. The file is local
configuration, never public source. A blank ignored file is provisioned locally;
fresh clones must create it themselves. The owner edits the value locally:

```dotenv
TODO_SYNC_GITHUB_TOKEN=
```

For the current checkout the exact location is
`C:\devdesk\homedesk\skill-library\skills\development-documentation-manual\.env`.
Use the installed skill's rebased support root when the checkout is elsewhere;
never search unrelated repositories for `.env` files.

**Agents must not view, print, search, summarize, attach or copy this file.**
Use the credential runner instead; it reads the file within its process and
passes the value only in the trusted child's environment. From any repository:

```powershell
python "C:\devdesk\homedesk\skill-library\skills\development-documentation-manual\scripts\with_github_token.py" -- gh api user --jq .login
```

Replace the command after `--` with the authorized `gh` or sync command. Keep
the target repository's working directory; the runner resolves its own
support-root credential regardless of that directory. It sets
`TODO_SYNC_GITHUB_TOKEN` and `GH_TOKEN` only for the child, disables `GH_DEBUG`,
preserves the child's exit code and does not change parent/global auth.
Only run reviewed, trusted commands: a child can deliberately print or
exfiltrate its environment. Do not use environment dumps, shell tracing,
credential-inspection commands or untrusted repository code.

The loader accepts one `TODO_SYNC_GITHUB_TOKEN` assignment, optional matching
single/double quotes, blank lines and whole-line comments. It does not evaluate
shell syntax or expand variables. Duplicate/unknown keys, empty values and
invalid formatting fail without echoing the line. An existing `.env` must be
ignored and untracked before it is read. An empty or invalid file is an explicit
provisioning error; it never silently falls back to a potentially stale token.

If `.env` does not exist, the runner falls back to the process variable and
then, on Windows, the current account's persistent User environment value.
This keeps the earlier persistent setup compatible without repeated assignment.
The preferred source is `.env` once present; editing it does not update or
revoke older environment/encrypted copies. Rotation must reconcile all copies.

### Git and packaging boundary

The library's root `.gitignore` excludes `.env` and `.env.*` at every depth.
Never add an exception, use `git add -f`, include the file in an archive, or
copy it into installed/portable skill payloads. Normal Git pushes do not upload
ignored, untracked files. The library validator rejects tracked environment
files; portable catalogue build/verification rejects them before hashing or
including them, including forced-tracked files and supplied catalogue entries.
The existing support packager also rejects `.env` selections.

These are accidental-disclosure safeguards, **not an absolute secrecy guarantee**:
gitignore does not block forced staging, bypassed checks, manual uploads,
backups or other programs reading local plaintext. Do not claim that a checked
catalogue scans arbitrary file contents for every possible secret. Keep this
file out of chat, logs, receipts, TODOs, context stores and generated output.
If ever committed, immediately revoke/rotate the credential; deleting the
current file does not erase Git history.

### Other local storage and inheritance limits

This fallback matters when an agent's parent was started before provisioning.
Child-process assignment does not update the running agent's parent: each
independent invocation needing the credential must resolve it, or use an
implemented shared helper. New sessions inherit environment from their parent;
fully restart a long-running terminal/IDE host if it still has stale values.
Do not require the owner to paste or manually reassign an already provisioned
credential. Missing, revoked or expired credentials remain explicit blockers.

A persistent User environment variable survives terminal closure and reboots
but is stored **unencrypted** in the account's Windows environment configuration.
It is a user-approved convenience option, not a secret vault: same-user code
and inheriting child processes can access it. Never set machine-wide variables,
dump the environment, persist `GH_TOKEN`, or include a token in a profile,
tracked repository content, generated payload or documentation. Provision/rotate through a
hidden local prompt or an existing authorized secret source; verify presence
and access without displaying the value. Remove or replace obsolete stored
copies when rotating.

Encrypted Windows credential storage is an alternative, not equivalent to
automatic inheritance. A SecureString exported with Export-Clixml uses Windows
DPAPI and is bound to the same user and computer; an authorized loader must
decrypt it at runtime. Do not silently downgrade an encrypted-only policy to a
plaintext User variable for a different owner. Neither local storage approach
provisions a remote Actions secret or synchronizes credentials between machines.

### Zanark identity for commits and GitHub operations

Commit cadence and checkpoint criteria are in manual section 4.5. Before each
authorized commit, verify both the effective Git author and committer belong to
Zanark. A configured display name alone proves neither account ownership nor
GitHub attribution. Use the owner's confirmed account-associated email or
owner-approved GitHub noreply address, scoped to this repository or command.
Check environment overrides as well as repository config; never overwrite
global identity or relabel someone else's work. If the identity cannot be
established, leave the reviewed changes uncommitted and report the blocker.

A local `git commit` does **not** use a PAT. For authorized GitHub API or remote
operations, run the support-root credential runner with this read-only check:

```powershell
python "C:\devdesk\homedesk\skill-library\skills\development-documentation-manual\scripts\with_github_token.py" -- gh api --hostname github.com user --jq .login
```

Require `Zanark` (case-insensitive); stop on failure or a different login. Repeat
after a credential-source change. Use that same runner for the authorized
operation, never a different ambient token or a global sign-in switch. This
helper supplies child environment only: `GH_TOKEN` does not, by itself, select
credentials for native Git HTTPS or replace an SSH key.

For an authorized push, verify the expected repository/host and the actual
transport credential path. An HTTPS Git command can use a reviewed per-command
`gh auth git-credential` helper under the runner, clearing inherited helpers
for that invocation only; do not persist a shared helper or put tokens in URLs
or arguments. An SSH remote authenticates with its SSH identity, not this PAT;
do not claim Zanark authentication from the token check or rewrite the remote
silently. Resolve a mismatched transport explicitly before pushing.

After a commit, verify its author/committer, intended file scope and required
trailers; record its actual hash and relevant evidence in the existing ledger.
After a separately authorized push, verify the exact remote ref. No account
check, credential capability or local commit grants push, release, workflow
activation or deployment permission.

For approved Actions automation, store the credential as an Actions secret.
The ordinary repository `GITHUB_TOKEN` cannot access Projects. Never expose a
PAT to untrusted pull-request code, scripts or fork workflows. Choose triggers,
checkout refs and write permissions deliberately. Do not enable a workflow
merely because its documentation exists.

Check source and destination visibility before mirroring. Private TODO content
must not be copied to public issues or an unsuitable shared Project. Never
mirror `.agent-context`, raw logs or secrets. If redaction would make a verbatim
mirror impossible, use an approved public-safe source/managed projection or
block that item; do not silently publish or claim an exact copy.

## Authorized workflow-scope use

The owner's selected classic PAT includes `workflow` so an agent can maintain
Actions YAML as part of an authorized task. Scope availability is capability,
not blanket authority to enable automation, dispatch jobs, publish releases,
deploy, change repository permissions or store remote secrets. Keep ordinary
issue/Project operations on their existing path; do not add a workflow just to
demonstrate the scope.

For an approved CI or TODO-sync workflow:

1. Read the actual definitions, called scripts and repository adoption record.
   Establish whether the request covers authoring only, push/activation,
   manual dispatch, recurring triggers and any publication side effects.
2. Verify account/repository access and the required token scopes without
   printing credentials. `workflow` permits workflow-definition changes; it
   does not itself grant Project access or replace repository permissions.
3. Use trusted checkout refs and reviewed code. Never give the PAT to fork or
   untrusted pull-request code, including through `pull_request_target` followed
   by checkout of the contributor's head. Pin third-party actions to reviewed
   immutable revisions according to the repository's policy.
4. Declare minimum job-level `permissions`. Use the job's ordinary
   `GITHUB_TOKEN` for supported repository operations; supply a separately
   provisioned Actions secret only to the step requiring Project/PAT access.
   Never assume the workstation's environment exists on a hosted runner.
5. Reuse an existing synchronizer with preview/apply, stable mappings and
   conflict checks. Serialize writers per repository/Project as appropriate;
   do not cancel a partially completed mutation run without recovery.
   Prevent backlink-commit trigger loops and concurrent local/hosted writes.
   A PAT-generated push can trigger other workflows, so review that chain.
6. Validate YAML and action syntax with existing tooling, plus affected script
   tests. Review trigger branches, paths, input interpolation, checkout ref,
   secret exposure, write scopes and retry behavior. An Actions secret missing
   at runtime must fail explicitly, not report a successful empty sync.
7. If push/dispatch is authorized, verify the exact source SHA and run, intended
   job conclusions and real issue/Project/backlink effects. Record any remaining
   qualification separately from local checks; a green lint is not a hosted run.

The adoption record must name workflow path, trigger policy, credential source
name, permissions, trusted refs, concurrency/recovery policy, backlink-write
policy and run evidence. This manual does not install a workflow or supply its
runtime. Local persistent availability is not unattended hosted automation.

## Rollout, retries and failure handling

1. Inventory opted-in repositories and actual workstreams without remote writes.
   Preview inclusion/exclusion, completion mappings, visibility, existing issues,
   proposed creates/updates, Project membership and backlink changes.
2. Resolve ambiguous historical states and approve the mapping/import scope.
3. Pilot one bounded workstream. Verify its actual issue body/state, Project
   membership/status and persistent local backlink.
4. Repeat the pilot sync: it must update/reuse the same issue and Project item,
   not create duplicates. Test agreed reopening/conflict behavior.
5. Backfill approved history; then opt in additional repositories explicitly.

Creating an issue, adding it to a Project, updating fields and writing a local
backlink are separate operations, not a transaction. Record each successful
step and resume safely. After an uncertain timeout, look up the stable mapping
before retrying a create. Surface permission errors, rate limits and partial
completion; do not mark the entire sync successful after only issue creation.
Do not undo successful remote work destructively as automatic rollback.

A local backlink is not committed or pushed unless separately authorized.
Record actual issue URLs, item identity, states, source revision and remaining
steps in the execution receipt, without credentials.

## Triggers and completion gates

Agents can invoke an implemented tool on TODO creation/update. A shared skill
provides instructions, not a background service. Actions only see the content
available to their checked-out revision; local uncommitted changes need a local
runner. Manual triggers, push triggers, schedules and reverse synchronization
are separate adoption decisions, not automatically enabled defaults.

A sync implementation must cover idempotent reruns, partial failure recovery,
closed/reopened states, conflicts, ambiguous statuses, excluded/private content
and verified backlinks. Fixture tests establish tool behavior; an authorized
live pilot establishes target integration. Neither establishes every repository
has been migrated.

## Sources and review limits

Requirement sources **GH-01**, **GH-03**, **GH-05** and external references **GH-02**, **GH-04** are registered
in [Sources](SOURCES.md). This is contract/design guidance, not a new token
provisioning or migration receipt. Consult current official documentation:

- [PAT support and limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Projects API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [Projects with Actions](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/automating-projects-using-actions)
- [Classic scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
- [GitHub CLI environment](https://cli.github.com/manual/gh_help_environment)
- [Windows persistent environment variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables)
- [Windows encrypted credential export](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/export-clixml)
