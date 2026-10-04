---
name: dri-workplan
description: Generate a formatted DRI (livesite) workplan with live IcM incidents in a time-blocked schedule. Use when user asks about DRI duties, IcM status, livesite plan, or incident workload. Keywords - DRI plan, IcM workplan, livesite schedule, incident status, DRI day, active incidents, mitigated incidents.
license: Apache-2.0
---

# DRI Workplan Generator (IcM / Livesite Only)

Generates a formatted, time-blocked workplan for **DRI livesite duties only** — IcM incidents, investigation, mitigation, and handoff tasks.

> **This skill does NOT include ADO sprint work.** For ADO tasks use `ado-workplan`. For combined output use `dayplan`.

## 🛑 CRITICAL RULES — DATE & TIME

- **DATE**: MUST be fetched from the internet (use a web tool or system clock). Must be accurate as per **IST (India Standard Time, UTC+5:30)**. NEVER guess the date.
- **TIME**: When workplan is requested, it should **always start from 11:00 AM IST** (work start time) — NOT from current time, UNLESS the user explicitly says "starting now" or "from current time".
- **Current time** displayed anywhere in the output MUST always be in **IST**.

## When to use this skill

- User asks for "DRI plan", "livesite plan", "IcM workplan"
- User asks "show incidents", "what's active", "DRI status"
- DRI week context — user is on-call and needs incident overview
- Any request specifically about IcM/livesite duties

## Data Sources

1. **IcM MCP** — `icm-search_incidents` with `assignedTo: "mishrad"`, severities [2,3,4], states ["Active","Mitigating","Mitigated"]
2. **Session SQL** — `user_preferences` table for schedule and DRI context

## User Preferences (from SQL)

Always read these before rendering:

| Key | Purpose |
|-----|---------|
| `daily_routine` | Work hours and time blocks (11:00–18:00 IST) |
| `workplan_style` | Exact visual format specification |
| `dri_week` | Current DRI week context (dates, day count) |

## Output Format

Uses the **shared two-column box layout** (same as ado-workplan and dayplan).

### Structure

```
 ┌───────────────────────────────────────────────────────────┐
 │  🚨 DRI WORKPLAN — {Day}, {Date} · DRI Week (Day X/5)    │
 │  🕚 Hours: 11:00–18:00 IST · ~50% DRI overhead           │
 │  🔥 Active: {count} │ 🟡 Mitigated: {count}              │
 ├───────────┬──────────────────────────────────────────────┤
 │           │                                              │
 │ HH:MM     │ {emoji} Block Title                          │
 │           │  ➤ Sub-item detail                          │
 │           │                                              │
 │- - - - - -│- - - - - - - - - - - - - - - - - - - - - - - │
```

 - {status_emoji} [#{id}](url) — Incident title

```
 │           │                                             │
 ├───────────┴─────────────────────────────────────────────┤
 │  💡 Insight or tip line                                 │
 │  📌 PENDING CLOSE                                       │
```

 - 🟡 [#{id}](url) — Mitigated incident title

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
8. **Footer** with 💡 tip + 📌 PENDING CLOSE section
9. **Closing `└───┘`** in its own code fence after pending links

### Link Emoji Legend

| Emoji | Meaning |
|-------|---------|
| 🔥 | Sev2 IcM (Active) |
| ⚠️ | Sev3 IcM (Active) |
| 📋 | Sev4 IcM (Active) |
| 🟡 | Mitigated IcM (pending close) |

### URL Format

- **IcM**: `https://portal.microsofticm.com/imp/v5/incidents/details/{id}/summary`

## Schedule Template (IST) — DRI Blocks

| Time | Block |
|------|-------|
| 11:00 | 🟢 Start Day — IcM sweep + email triage |
| 11:30 | 🔵 Standup (DRI update) |
| 12:00 | 🔴 Investigation Block 1 — active Sev2/3 |
| 14:00 | ⚪ Lunch |
| 15:00 | 🔴 Investigation Block 2 — follow-ups |
| 16:00 | 🟠 Break |
| 16:30 | 🟡 Mitigation / RCA / Close-out |
| 18:00 | 🔴 Wrap Up — handoff notes |

## Workflow

1. **Fetch current date** from internet — MUST be accurate IST
2. **Read user preferences** from SQL (`daily_routine`, `dri_week`)
3. **Fetch IcM incidents** — parse by severity and state
4. **Classify incidents** into time blocks:
   - Active Sev2 → Investigation Block 1 (highest priority)
   - Active Sev3/4 → Investigation Block 2
   - Mitigated → PENDING CLOSE section
5. **Group related IcMs** by root cause (e.g., all SFRP-ACIS together)
6. **Render** using the exact format above
7. **Include actionable insight** in footer 💡 line

## Important Notes

- **NEVER question working hours** or say "it's weekend"
- **DRI Week**: Mon=Day 1 through Fri=Day 5
- **IcM MCP times out frequently** — use last known data if timeout, note staleness
- **Group related IcMs** by root cause
- **Handoff context**: note DRI handoff day/time if within 24h
