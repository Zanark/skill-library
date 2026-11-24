# External prompt inbox

This implements a durable local mailbox and an active-boundary hook adapter, **not** an Agency
user-message API. A deposit does not wake an idle session, interrupt an executing tool, grant
permissions, launch Copilot or appear as a normal typed message in its queue.
The normative contract is SKILL.md, **Optional external prompt inbox**.

## Components and isolation

- One opted-in canonical base/session UUID, never a display name or persona match.
- Immutable JSON envelopes in `.agent-context\inbox\<uuid>\messages`.
- SQLite transactions, ordered requests and an append-only metadata receipt history.
- Short-lived Python stdlib adapter, with no background services, threads, children or model calls.
- Two shared kernel-lock lanes; one unresolved delivery per session. A busy lane skips without claiming.
  SQLite contention fails explicitly; a later real boundary can retry if no offer was committed.
- Hooks have a five-second timeout; database waits are 50ms for hooks and one second for explicit commands.
  Host process startup is not bounded by the two active-work lanes; Python startup and filesystem work
  are real overhead. No zero-impact/performance or exactly-once-execution guarantee is made.

Ordinary requests wait for `agentStop`. Explicit `steer` requests use the next **successful** tool result,
or the normal stop boundary if no tool follows. FIFO prevents steering from overtaking earlier work.
One offer is allowed per actual submitted user turn, shared across modes. `stop_hook_active` continuations
never fetch another request. A backlog needs subsequent real turns, not an automatic drain loop.
Root events only; subagent IDs are ignored. Exact session and cwd/ancestor addressing prevents another
session in the same project from consuming the queue.

## Enable an exact session

Use the real session UUID; never resume an active session from another process to obtain it.
The example uses the designated skill-library base and a synthetic session UUID: replace that UUID.
Other bases need their own operator-approved registration and an existing context README.
Ensure `.agent-context\inbox\` is excluded from Git, backups intended for publication and artifact indexing.
The library already ignores `.agent-context`; this helper does not edit another repository's ignore rules.

```powershell
$inbox = 'C:\devdesk\homedesk\skill-library\skills\context-offload\scripts\prompt_inbox.py'
$base = 'C:\devdesk\homedesk\skill-library'
$session = '00000000-0000-4000-8000-000000000001'
python $inbox init --base $base --session $session
python $inbox install-hooks
```

`install-hooks` creates only `%COPILOT_HOME%\hooks\prompt-inbox.json` and two small lock files in
`%COPILOT_HOME%\prompt-inbox` (default `%USERPROFILE%\.copilot`). It preserves other hook files/settings
and refuses to overwrite a different existing inbox configuration. It records the actual Python executable
and helper path as direct executable/argv entries, not interpolated shell text.
Keep that checkout/Python available. No Python packages are needed.

Host activation is separate from installation: existing Agency sessions may have snapshotted hooks.
Do not restart/reload an active session without permission. A newly started supported CLI session can
discover the configuration, but portable config generation is not proof of this Agency runtime's support.
`sessionStart` adds a short capability notice only for the exact opted-in session.
Config-file `userPromptSubmitted` output is deliberately empty because that output is dropped by the host.
The adapter never installs permission hooks or modifies tool approval settings.

## Submit from another PowerShell

```powershell
$inbox = 'C:\devdesk\homedesk\skill-library\skills\context-offload\scripts\prompt_inbox.py'
$base = 'C:\devdesk\homedesk\skill-library'
$session = '00000000-0000-4000-8000-000000000001'
'When the current task is finished, explain the new inbox commands.' |
    python $inbox submit --base $base --session $session
python $inbox status --base $base --session $session
```

The returned UUID plus `pending` confirms durable local acceptance, not delivery. Save that UUID.
Supply `--id '<same-uuid>'` to retry an interrupted submission idempotently; keep text/mode/TTL unchanged.
An identical retry preserves its original expiry. `--mode steer` deliberately opts into a tool boundary.
Optional `--ttl-seconds 3600` expires only still-pending work. Prompts are at most 4096 UTF-8 bytes;
the complete rendered wrapper must also fit 9000 bytes. The cap leaves some of the host's shared 10KB
tool-context budget for other hooks, but cannot reserve that space; incomplete/truncated offers remain unresolved.
At most 64 unresolved requests are accepted. Completion/cancellation frees backlog capacity.

For Unicode/private local text, prefer an existing UTF-8 file with `--file 'C:\path\request.txt'`;
PowerShell pipeline encodings depend on the shell version. `--text` is convenient for harmless text but
may retain it in process arguments/shell history. Never put tokens/secrets/private incident bodies in prompts.
Submissions and status do not print text or receipt tokens. Payloads remain plaintext local files: this is
an instructional ownership boundary, not encrypted storage, ACL isolation or authenticated sender provenance.
Delivered text still goes to the session's configured model/provider and incurs normal token/tool costs.
The adapter explicitly emits UTF-8 JSON, including when its parent sets a different Python I/O encoding.
Artifact Finder excludes known external-inbox wrappers (including truncated ones), direct inbox
operations and their correlated tool results. Its cache version changes with this filter. That is not
a general data-loss-prevention classifier: do not copy request bodies or receipt tokens into unrelated
tool output, assistant messages, documentation or context notes.

## Receipts and recovery

| State | Actual evidence |
|---|---|
| `pending` | Immutable deposit and SQLite acceptance committed |
| `offered` | Token/attempt committed before returning hook JSON; consumption unknown |
| `consumed` | Explicit token acknowledgement before handling the complete request |
| `completed` / `failed` | Explicit outcome acknowledgement, not automatic success |
| `cancelled` / `expired` | Pending work withdrawn before offer |
| `uncertain` | Offered/consumed lease elapsed; prior effects may exist |

The hook supplies a direct receipt argv with exact base/session/ID/token. Use `ack --state consumed`,
then `completed` or `failed`, retaining the same token. Invalid/stale tokens and transitions are rejected.
Long tasks can repeat `consumed` at natural checkpoints to renew the 30-minute lease. Lease reconciliation
happens at the next actual operation, not on a timer. It is not proof a worker died. An uncertain request
blocks later delivery until the operator inspects actual prior effects and explicitly resolves it:

```powershell
python $inbox cancel --base $base --session $session --id '<pending-message-uuid>'
python $inbox recover --base $base --session $session --id '<uncertain-message-uuid>' --action fail --confirm-uncertain
# Only after verifying replay is safe and old work is no longer executing:
python $inbox recover --base $base --session $session --id '<uncertain-message-uuid>' --action requeue --confirm-uncertain
```

Recovery invalidates the old token. It does not roll back side effects or reset the per-turn delivery cap.
An offered request cannot be cancelled as if no work started. Disable stops future offers/deposits, not
already-running work. Receipt acknowledgements still work while disabled.

JSON fsync/atomic replacement and SQLite commit are separate durability boundaries. A crash before
acceptance can leave an immutable **unindexed deposit**, which status reports explicitly. It is never
automatically imported or offered. Retry with the same ID and matching original content/options to finish
acceptance; different content fails. Missing/tampered indexed envelopes stop delivery with an explicit error.
Power loss guarantees still depend on filesystem/storage durability. Do not manually reset states, edit
envelopes, delete in-flight rows or restore a database without its matching message files.

Terminal receipts/files are retained for audit rather than silently pruned; archive deliberately offline
only when no work is in flight. Per-boundary lookups use indexed state/expiry/lease queries.
Status is an explicit local inspection, not an automatically exported dashboard feed.

## Disable and remove

```powershell
python $inbox disable --base $base --session $session
# Re-enable the same exact registration when desired:
python $inbox enable --base $base --session $session
```

To remove the adapter globally, review and remove only the dedicated `prompt-inbox.json` in the
actual Copilot home hook directory; leave other hooks untouched. Disable affected mailboxes first.
Already-loaded hosts may retain their hook list until a normal restart, so mailbox disable is the
immediate control. Preserve queued/uncertain receipts until deliberately resolved. Lock files contain
no worker process; removing configuration needs no daemon shutdown or process-name killing.

## Verification and compatibility

```powershell
Set-Location 'C:\devdesk\homedesk\skill-library'
python -m unittest discover -s tests -p test_prompt_inbox.py -v
```

Coverage includes concurrent writers/claims, uncertainty/recovery, leases, cancellation, FIFO/turn caps,
expiry, idempotency, crash-deposit reconciliation, wrong targets/subagents, tampering, privacy-safe status,
hook preservation, direct installed-hook subprocess execution with Unicode, real CLI acknowledgements,
and forced-process-death lock release. Test workers are bounded and joined/killed by their exact child
handles. Fixtures establish adapter behavior, not host acceptance or Agency UI behavior.

The disposable standalone CLI qualification reached authentication preflight but did not make a model
request: its classic GitHub PAT authentication was rejected by CLI 1.0.109. No successful live echo,
native user-queue entry, Agency attachment or idle wake was demonstrated. Existing authentication and
the active Agency session were not changed. Installation and exact-session registration are separate
from this unverified live-host qualification; do not describe them as end-to-end delivery.

Protocol references:
[GitHub hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference) and
[use hooks](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks).
The implementation targets native camelCase hooks and the documented stop continuation guard.
Record disposable CLI build, payload/echo/receipt evidence and any Agency activation limits separately.
