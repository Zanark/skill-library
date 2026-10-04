---
name: ado-workplan
description: Generate a formatted ADO sprint workplan with work items in a time-blocked schedule. Use when user asks for workplan, sprint plan, task schedule, or daily work summary. Keywords - workplan, schedule, plan my day, what's on my plate, show plan, updated plan, morning plan, afternoon refresh, sprint tasks, ADO items.
license: Apache-2.0
---

# ADO Workplan Generator (Sprint Tasks Only)

Generates a formatted, time-blocked workplan for **ADO sprint work only** — PBIs, tasks, code reviews, and engineering work.

> **This skill does NOT include IcM/DRI duties.** For livesite work use `dri-workplan`. For combined output use `dayplan`.

## 🛑 CRITICAL RULES — DATE & TIME

- **DATE**: MUST be fetched from the internet (use a web tool). Must be accurate as per **IST (India Standard Time, UTC+5:30)**. NEVER guess the date.
- **TIME**: When workplan is requested, it should **start from current time** — show only remaining time blocks from now until 18:00 IST. Skip blocks that have already passed.
- **Current time** displayed anywhere in the output MUST always be in **IST**.

## Previous-day completion reconciliation (mandatory)

Standing user preference, 2026-09-17: always read yesterday's actual sprint note to see what the user marked complete.

1. Before planning, read yesterday's daily Markdown file from the existing Zettelkasten sprint folder, plus today's file if present. If yesterday's file is absent, use the most recent preceding note and state its actual date. Follow existing folder names (for example, `SPRINT_SEPT_26`), not a newly invented alternate spelling.
2. Treat checked `[x]` / `[X]` actions as user-recorded completion evidence for their stated scope. Carry forward only unfinished actions; never reset checked actions, recreate tasks the user removed from the note, or copy a whole checklist blindly. For partial completion, retain the unfinished children without reopening completed siblings.
3. Reconcile with live ADO status. Exclude Done/Closed/Removed items from pending work. If note and ADO status disagree, describe the discrepancy; do not change ADO state merely because a checkbox was checked.
4. Keep yesterday's note, evidence tables, and checkmarks untouched. If showing prior completion, label it "Completed yesterday" or use the actual source date, never "Completed today." Do not infer a deletion/rollout occurred when that action remains unchecked.
5. Preserve existing Obsidian `[[wikilinks]]`, link today's note to the carry-forward source, and add today's return link to the relevant `2 Areas` topic notes. If today's note already exists, preserve its edits/checkmarks and deduplicate by ADO ID and action.

## When to use this skill

- User asks for "workplan", "daily plan", "schedule", "what's on my plate"
- User asks "show plan", "updated plan", "gimme workplan"
- Morning start or afternoon refresh requests
- Any request to summarize today's ADO/sprint work

## Data Sources

1. **ADO MCP** — `ado-msazure-wit_my_work_items` or `ado-msazure-wit_get_work_items_batch_by_ids` for active sprint tasks
2. **Session SQL** — `user_preferences` table for schedule, display rules, and formatting
3. **Session SQL** — `work_items` table for cached item state
4. **Zettelkasten daily notes** — yesterday's actual user-edited checklist and today's existing note, read before scheduling. If optional SQL tables are unavailable, use persisted WorkDesk preferences rather than inventing cached state.

## User Preferences (from SQL)

Always read these before rendering:

| Key | Purpose |
|-----|---------|
| `daily_routine` | Work hours and time blocks (11:00–18:00 IST) |
| `workplan_style` | Exact visual format specification |
| `ado_display_rule` | PBI/Task hierarchy display rules |

## Output Format

Uses the **shared two-column box layout** (same as dri-workplan and dayplan).

### Structure

```
 ┌───────────────────────────────────────────────────────────┐
 │  📋 ADO WORKPLAN — {Day}, {Date}                          │
 │  🕚 Hours: 11:00–18:00 IST                                │
 │  🔵 Active: {count} │ 🔍 In Review: {count}               │
 ├───────────┬──────────────────────────────────────────────┤
 │           │                                              │
 │ HH:MM     │ {emoji} Block Title                          │
 │           │  ➤ Sub-item detail                          │
 │           │                                              │
 │- - - - - -│- - - - - - - - - - - - - - - - - - - - - - - │
```

 - {status_emoji} [#{id}](url) — Task title

```
 │           │                                             │
 ├───────────┴─────────────────────────────────────────────┤
 │  💡 Insight or tip line                                 │
 │  📌 QUEUED                                              │
```

 - ⬚ [#{id}](url) — Queued item title

```
 └─────────────────────────────────────────────────────────┘
```

### Key Rules

1. **Box inside code fences** — preserves monospace alignment
2. **Lines kept SHORT (~55 chars)** — avoids terminal wrapping
3. **Two-column**: time │ content with emoji
4. **Dashed separators**: `│- - - - - -│- - - - - - - - -│`
5. **Sub-items**: `➤` prefix inside box
6. **Links as markdown bullets OUTSIDE code fences** — between box segments so they're clickable
7. **Multiple code fence blocks** broken up by link bullets
8. **Footer** with 💡 tip + 📌 QUEUED section
9. **Closing `└───┘`** in its own code fence after queued links

### Link Emoji Legend

| Emoji | Meaning |
|-------|---------|
| 🔵 | Active ADO task (In Progress) |
| 🔍 | In Review ADO task |
| ⬚ | Queued / To Do / low-priority |
| 🅿️ | Parked / Committed but not started |
| ✅ | Done (only shown in "completed today" section) |

### URL Format

- **ADO**: `https://msazure.visualstudio.com/One/_workitems/edit/{id}`

### ADO Display Rules

- If PBI has child tasks → show PBI as header, tasks nested below with `├─` / `└─`
- If PBI has NO child tasks → show PBI standalone
- Only `#number` is hyperlinked, title is plain text after em-dash

## Schedule Template (IST) — Sprint Blocks

| Time | Block |
|------|-------|
| 11:00 | 🟢 Start Day — email/Teams triage |
| 11:30 | 🔵 Standup (Yesterday/Today/Blocker format) |
| 12:00 | 🟣 Focus Block 1 — high-priority tasks |
| 14:00 | ⚪ Lunch |
| 15:00 | 🟣 Focus Block 2 — code reviews / continued work |
| 16:00 | 🟠 Break |
| 16:30 | 🟣 Focus Block 3 — remaining tasks |
| 18:00 | 🔴 Wrap Up — update ADO, push code |

## File Output — Zettelkasten Sprint Log

After rendering the workplan to console, **always update the Zettelkasten daily checklist file**.

### Folder Structure
```
C:\notedesk\zettelkasten\1 Project\SPRINT_{MONTH}_{YY}\{YYYY-MM-DD}.md
```

### Naming Convention
- **Sprint folder**: `SPRINT_{MONTH}_{YY}` — e.g., `SPRINT_JUL_26`, `SPRINT_AUG_26`
  - `{MONTH}` = 3-letter uppercase month abbreviation
  - `{YY}` = 2-digit year
- **Day file**: `{YYYY-MM-DD}.md` — e.g., `2026-07-08.md`

### File Content Format
The file groups tasks **by work item**, each with a header, ADO link, and checklist. Format:

```markdown
# Disable auto-mitigation on Runner monitors

[ADO #38148429](https://msazure.visualstudio.com/One/_workitems/edit/38148429)

- [ ] Identify all monitors with auto-mitigation enabled
- [ ] Disable auto-mitigation on each

# Support ADLS BLOB runners with config updates

[ADO #38709398](https://msazure.visualstudio.com/One/_workitems/edit/38709398)

- [ ] Update runner config for ADLS BLOB
```

### Rules
1. Create the sprint folder if it doesn't exist
2. If the day `.md` file **already exists** — **append** new work item sections that aren't already in the file (match by ADO ID to avoid duplicates, don't overwrite existing content)
3. If the day `.md` file **doesn't exist** — create it with work item sections
4. New unfinished checklist items are `- [ ]` by default. Never convert yesterday's completed items back to unchecked; omit them from today's pending checklist and preserve existing checkmarks in today's file.
5. Only include items that are **In Progress**, **Active**, or **In Review** — NOT To Do/New/queued items
6. Each work item gets an `# H1 header` with the short task name
7. Below the header: `[ADO #{id}](link)` on its own line
8. Below the link: one or more `- [ ]` checklist items describing sub-tasks (infer from the title/context, keep them actionable and short)
9. Separate each work item section with a blank line
10. Console output remains the full two-column box workplan (unchanged)

## Workflow

1. **Fetch current date** from internet — MUST be accurate IST
2. **Read user preferences** from SQL (`daily_routine`, `ado_display_rule`)
3. **Read yesterday's note and today's existing note** — reconcile checked/unchecked actions using the mandatory previous-day rules above.
4. **Fetch ADO items** — get active sprint tasks with parent PBI context; reconcile with the notes without writing ADO state.
5. **Classify only unfinished work** into time blocks:
   - In Progress (high priority) → Focus Block 1
   - In Review → Focus Block 2
   - To Do / low-pri → QUEUED section
   - Parked → 🅿️ in QUEUED
6. **Render** using the exact format above
7. **Include actionable insight** in footer 💡 line
8. **Label completed work by its actual source date** — use "Completed today" only for today's evidence.
9. **Save to file** — update `C:\notedesk\zettelkasten\1 Project\SPRINT_{MONTH}_{YY}\{YYYY-MM-DD}.md` using the existing sprint folder name; preserve source notes and refresh topic backlinks.

## Important Notes

- **NEVER give plans for the weekend** DO NOT PERMIT WORK ON WEEKENDS — if date is Saturday or Sunday, output a message saying "It's the weekend! Time to recharge. No work scheduled."
- **Standup format**: ➤ Yesterday: ... / ➤ Today: ... / ➤ Blocker: ...
- **Priority ordering**: In Progress > In Review > To Do > Parked
- **If DRI week is active**: note reduced capacity (~50% overhead) in header
- **FRIDAY Energy for workplan**: If it's Friday, include a note about expected lower energy and focus, and suggest prioritizing critical tasks and leaving buffer time.
