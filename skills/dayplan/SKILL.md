---
name: dayplan
description: Generate a complete day plan combining DRI livesite (IcM) and ADO sprint work into a unified time-blocked schedule. Use when user wants the full picture of their day. Keywords - day plan, full plan, gimme plan, my day, complete schedule, everything today, combined workplan.
license: Apache-2.0
---

# Day Plan Generator (Combined DRI + ADO)

Generates a **unified, time-blocked day plan** combining both DRI livesite duties (IcM incidents) and ADO sprint tasks into a single cohesive schedule.

> **This is the combined output of `dri-workplan` + `ado-workplan`.** Use this when the user wants the full picture. For IcM-only or ADO-only, use those individual skills.

## 🛑 CRITICAL RULES — DATE & TIME

- **DATE**: MUST be fetched from the internet (use a web tool or system clock). Must be accurate as per **IST (India Standard Time, UTC+5:30)**. NEVER guess the date.
- **TIME**: When workplan is requested, it should **always start from 11:00 AM IST** (work start time) — NOT from current time, UNLESS the user explicitly says "starting now" or "from current time".
- **Current time** displayed anywhere in the output MUST always be in **IST**.

## When to use this skill

- User asks for "day plan", "full plan", "gimme plan", "plan my day"
- User asks "what's on my plate", "everything today"
- User asks for "workplan" without specifying DRI or ADO specifically
- Morning planning or end-of-day summary

## Data Sources

1. **IcM MCP** — `icm-search_incidents` with `assignedTo: "mishrad"`, severities [2,3,4], states ["Active","Mitigating","Mitigated"]
2. **ADO MCP** — `ado-msazure-wit_my_work_items` or `ado-msazure-wit_get_work_items_batch_by_ids`
3. **Session SQL** — `user_preferences` table for schedule, display rules, formatting
4. **Session SQL** — `work_items` table for cached item state

## User Preferences (from SQL)

Always read these before rendering:

| Key | Purpose |
|-----|---------|
| `daily_routine` | Work hours and time blocks (11:00–18:00 IST) |
| `workplan_style` | Exact visual format specification |
| `ado_display_rule` | PBI/Task hierarchy display rules |
| `dri_week` | Current DRI week context (if active) |

## Output Format

Uses the **shared two-column box layout** — single unified schedule with both IcM and ADO interleaved by priority.

### Structure

```
 ┌───────────────────────────────────────────────────────────┐
 │  📋 DAY PLAN — {Day}, {Date}                              │
 │  🕚 Hours: 11:00–18:00 IST {DRI context if active}        │
 │  🚨 IcMs: {summary} │ 🔵 ADO: {count} active             │
 ├───────────┬──────────────────────────────────────────────┤
 │           │                                              │
 │ HH:MM     │ {emoji} Block Title                          │
 │           │  ➤ Sub-item detail                          │
 │           │                                              │
 │- - - - - -│- - - - - - - - - - - - - - - - - - - - - - - │
```

 - {status_emoji} [#{id}](url) — Item title

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

### Link Emoji Legend (all combined)

| Emoji | Meaning |
|-------|---------|
| 🔥 | Sev2 IcM (Active) |
| ⚠️ | Sev3 IcM (Active) |
| 📋 | Sev4 IcM (Active) |
| 🟡 | Mitigated IcM (pending close) |
| 🔵 | Active ADO task (In Progress) |
| 🔍 | In Review ADO task |
| ⬚ | Queued / To Do / low-priority |
| 🅿️ | Parked |
| ✅ | Done |

### URL Formats

- **IcM**: `https://portal.microsofticm.com/imp/v5/incidents/details/{id}/summary`
- **ADO**: `https://msazure.visualstudio.com/One/_workitems/edit/{id}`

### ADO Display Rules

- If PBI has child tasks → show PBI as header, tasks nested below with `├─` / `└─`
- If PBI has NO child tasks → show PBI standalone
- Only `#number` is hyperlinked, title is plain text after em-dash

## Schedule Template (IST) — Combined

| Time | Block | Content |
|------|-------|---------|
| 11:00 | 🟢 Start Day | Email/Teams triage + IcM sweep |
| 11:30 | 🔵 Standup | Yesterday/Today/Blocker |
| 12:00 | 🟣/🔴 Focus Block 1 | IcM fires first, then sprint tasks |
| 14:00 | ⚪ Lunch | — |
| 15:00 | 🟣 Focus Block 2 | Sprint tasks / code reviews |
| 16:00 | 🟠 Break | — |
| 16:30 | 🟣 Focus Block 3 | Remaining tasks / IcM close-out |
| 18:00 | 🔴 Wrap Up | Update ADO, handoff notes |

## Workflow

1. **Fetch current date** from internet — MUST be accurate IST
2. **Read user preferences** from SQL
3. **Fetch IcM incidents** — parse by severity and state
4. **Fetch ADO items** — get active sprint tasks
5. **Merge and prioritize**:
   - Active Sev2 IcM → ALWAYS first (Block 1)
   - Active Sev3/4 IcM → Block 1 or 2
   - In Progress ADO tasks → Focus Blocks
   - In Review ADO → later blocks
   - Mitigated IcMs + To Do ADO → QUEUED/PENDING
6. **If DRI week is active**: allocate ~50% time to IcM blocks, reduce ADO expectations
7. **If NOT DRI week**: minimal IcM section (or omit if 0 active), full ADO focus
8. **Render** using the exact format above
9. **Include actionable insight** in footer 💡 line

## Important Notes

- **NEVER give plans for the weekend** DO NOT PERMIT WORK ON WEEKENDS — if date is Saturday or Sunday, output a message saying "It's the weekend! Time to recharge. No work scheduled."
- **Advanced plans for the next week** are allowed - If the user asks to plan the comming Monday, the skill can provide a plan based on the current known schedule and typical patterns, but must include a disclaimer that it's a forecast and may change.
- **DRI Week**: Mon=Day 1 through Fri=Day 5
- **FRIDAY Energy for workplan**: If it's Friday, include a note about expected lower energy and focus, and suggest prioritizing critical tasks and leaving buffer time.
- **Non-DRI Week**: IcM section only if there are assigned incidents
- **IcM MCP times out frequently** — use last known data if timeout, note staleness
- **Group related IcMs** by root cause
- **Standup format**: ➤ Yesterday: ... / ➤ Today: ... / ➤ Blocker: ...
- **Show "✅ Completed today"** if user mentions done items
