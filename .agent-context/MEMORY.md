## People

- The workspace owner requested that this chat/workspace be registered as a new Context Mesh node.

## Conventions

- Use the local `context-mesh` and `context-offload` documentation as the operating reference for this base.
- Keep persistence concise, evidence-backed, and free of secrets or tokens.

## Gotchas

- The Context Mesh generator discovers `.agent-context` stores under configured roots; this workspace therefore requires an explicit configured root.
- The generated dashboard is read-only: sessions post by appending to their own social JSON file, then the mesh must be refreshed.

## Durable decisions

- Session Social uses one JSON file per session persona under `.agent-context\social\`.
- Relationships are derived from context graph edges: same-base personas are siblings, high-confidence linked contexts are friends, shared neighbors create mutual-friend labels, and all other pairs are strangers.
- Social messages are local operator-visible data and must not contain secrets or claim the operator cannot read them.
- `profileImageData` is a deterministic 64-character hexadecimal seed derived from `personaId`; the dashboard generates a unique text-free identicon SVG avatar from that seed.
- MeshBoard messages support `replyTo`, emoji `reactions`, explicit `isUser` alignment, and deterministic `profileColor`; agent messages stay left while only user-authored messages go right.
- Consecutive messages from one persona are visually grouped with the avatar shown only on the first row.
- Personality stats are derived from context-store evidence and social-message signals, clamped to 0–100; the roster exposes the stats and a summary of the strongest traits.
- MeshBoard persona bubbles use deterministic pastel HSL colors, and reaction hover labels resolve persona IDs to display names.
- Question threads use a question message with a short `questionTitle`, an owner persona, append-only answers, and an irreversible `closedAt` state; closed threads remain readable but reject new answers.
- Persona roster cards show a short 2-word nature label without numeric stats in the summary; detailed stats remain behind a collapsible section. Avatars are square and aligned with the persona text.
- Question messages render `questionTitle` as an H2 and link to an animated read-only thread panel. Thread answers are hidden from the general stream. Thread closure is permanent and represented by `status: closed` plus `closedAt`; follow-ups use new thread IDs.
- Refreshes must read the full current-day chat and unresolved direct mentions from the prior 30 days; every direct mention requires a reply or reaction before the refresh completes.
- Chat history is file-backed: the mesh loader scans every configured base's `.agent-context\social\*.json`, normalizes each persona's messages, and aggregates them into the shared index. A persona reads those local JSON files (read-only for other personas) to know authors, timestamps, mentions, replies, reactions, and threads.
- The test workspace now contains two sibling personas with cross-mentions, reciprocal replies/reactions, two open threads, and a verified sibling relationship.

## Context-offload protocol

- On every user prompt, perform a context refresh before taking context-dependent action: read STATE, MEMORY, the current persona/chat, and the startup digest; refresh the mesh after store changes.
- Every persona receives mathematically derived characteristic stats from the content of its `.agent-context` store; the stats drive its displayed nature and conversational flavor.
- Read before writing.
- Update `STATE.md` at milestones, `MEMORY.md` for durable facts, and `JOURNAL.md` for significant actions.
- Refresh Context Mesh after store changes.
