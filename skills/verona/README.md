# Verona skill copy

`SKILL.md` is a complete copy of the skill authored in
`C:\devdesk\homedesk\Verona\.github\skills\verona\SKILL.md`.
Verona remains the source of truth; refresh this copy when that skill changes.
No companion skill references or scripts are required. This folder does not
bundle the Verona application, ignored model assets or CPU/Electron environment.

## Use in another local Agency chat

Paste:

> Read `C:\devdesk\homedesk\skill-library\skills\verona\SKILL.md` completely,
> then use Verona for this chat from `C:\devdesk\homedesk\Verona`. I opt in
> to concise spoken summaries while keeping written answers. Create or reuse
> only this chat's uniquely named head and reuse the shared manager. Inventory
> other heads and choose vivid, obviously different colors for all five
> features, not lighter/darker shades of occupied hues. Do not change, restart
> or close another chat's head.

The agent needs local command access and a prepared Verona checkout.
It reads the skill, checks dependencies, starts/reuses one manager and creates
its own head. Repeat in another chat for a separate, contrasting head.
No manual Verona launch is necessary. Approve only scoped required access.
Installation or reading alone does not activate narration or devices.
This explicit-path approach does not assume Agency has Copilot's commands or
that an already-open chat automatically refreshes its discovered skills.

For Copilot CLI 1.0.114, optional personal installation is:

```powershell
copilot skill add C:\devdesk\homedesk\skill-library\skills\verona\SKILL.md
copilot skill list --json
```

Inspect an existing installation before replacing it. Copilot documents
interactive `/skills reload`; this is not a verified Agency command.
