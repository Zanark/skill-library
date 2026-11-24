# Concurrent-use runtime ownership <project>

Updated: `<actual time and timezone>`  
Authority/local contract: `<requested work, allowed actions and explicit limits>`  
User mode: `<stable use (default) / explicitly selected live preview>`  
Selection evidence: `<actual instruction; not inferred from an open tab>`  
Verification status: `<planned / fixture-only / target-qualified; actual limits>`

Use the smallest existing runbook/record that covers these fields; do not
create a new runtime or infrastructure merely to fill the form. Keep machine
paths and operational details private where appropriate. Never record secrets.
Unknown values are blockers to affected actions, not permission to guess.

## Lane identities

| Field | Protected user lane | Agent development/test lane |
|---|---|---|
| Build/revision, relevant dirty changes and capture time | `<known-good identity>` | `<candidate identity>` |
| Absolute executable/source/build/output path | `<actual paths>` | `<separate actual paths>` |
| URL/origin and API/backend endpoint, if applicable | `<actual values>` | `<actual values>` |
| Launch command and working directory (no credentials) | `<actual values>` | `<actual values>` |
| PID/process tree, command and ownership checked at | `<user-owned or unknown; do not stop>` | `<verified agent-owned processes>` |
| Effective app/browser profile and data directory | `<protected state>` | `<disposable test state>` |
| Database, files, saves, settings, caches and logs | `<actual locations>` | `<isolated locations or explicit safe sharing>` |
| Lifetime and cleanup ownership | `<preserve after handoff if needed>` | `<bounded helper or user-needed preview>` |

Separate ports and worktrees are not proof of isolation. A source-run process
can load changed files later. Do not silently convert the user's current runtime
to another lane; coordinate that transition first.

## Shared dependencies and contention

| Resource/dependency | Owner and readers/writers | Isolation or safe-sharing mechanism | Observed evidence, remaining risk and required pause |
|---|---|---|---|
| `<mutable files/database/API>` | `<actual ownership>` | `<disposable data/consistent snapshot/supported concurrency>` | `<actual result or not verified>` |
| `<camera/mic/GPU/ports/locks>` | `<actual ownership>` | `<recorded fixture/bounded load/exclusive-use window>` | `<actual result or not verified>` |

Desktop checks: effective profile, app ID, mutex/single-instance forwarding,
IPC, updater, plugins and lazily loaded assets. Do not replace running binaries.

Website checks: retained complete build, HMR/watch reload, proxy/static assets,
API/database writes, storage, cookies (not isolated by port) and service workers.
Do not serve the user's stable preview from a directory builds clean/overwrite.

## Coexistence acceptance receipt

Representative disposable setup: `<paths/profiles/input and relevant limits>`  
Protected workflow and save/reopen action: `<actual exercise>`  
Concurrent candidate build/test/restart and bounded failure: `<actual commands>`  
Observed protected process/state/served-file continuity: `<evidence>`  
Effective profile/backend/resource separation: `<evidence, not flags alone>`  
Resource-heavy job limits and non-conflicting fallback: `<actual controls>`  
Untested boundaries: `<including exclusive resources and fixture-only limits>`  
Human acceptance: `<not requested/pending/actual explicit decision>`

Never automate the user's active session to fill this receipt. Two successful
launches do not prove coexistence. Do not fabricate results for unused fields.

## Coordinated switch and recovery

- Candidate complete-build identity and verification receipt: `<actual values>`.
- Promotion/restart/reload authority and agreed save point: `<actual approval;
  documentation readiness is not approval>`.
- Work preservation and supported atomic/versioned switch: `<exact procedure>`.
- Data/schema compatibility, consistent backup and recovery plan: `<what older
  code can read; approval for any interruption/data loss; handling newer writes>`.
- Previous compatible version/state location: `<actual paths and limits>`.
- Post-switch selected-build and retained-state check: `<actual result or pending>`.
- Recovery rehearsal: `<authorized disposable result or explicitly not run>`.
- Cleanup/continuation: `<recheck exact PID and command; stop only owned helpers;
  leave required user-facing services available>`.

Code rollback alone does not undo a data migration. Do not restore over newer
user work or promise uninterrupted use when a shared resource prevents it.
