---
name: navigate-month
description: Switch the right-side data panel to a specific month. Use this skill when the user says "查看X月", "切换到X月", "show me [month]", "看一下X月数据", or any phrase whose primary intent is to view a different month's data. Do NOT use this skill when the user asks a question about the content of a month's data — use cycle-summary or data-explain instead.
---

# Month Navigator

## What this skill does

Switches the dashboard's right-side data panel to the requested month by calling `navigate_to_month`. The right panel then renders all indicators, rules, and charts for that month automatically. The chat bubble confirms the switch and gives a one-sentence headline — nothing more.

## Workflow

1. Parse the target month from the user's message into YYYY-MM format:
   - "2025年3月" → "2025-03"
   - "去年3月" → resolve relative to the current month shown in the dashboard
   - If the month is ambiguous or unresolvable, call `get_available_months()` first and ask the user to confirm
2. Call `→ navigate_to_month(YYYY-MM)`
3. If the tool returns an error (month not in database), call `→ get_available_months()` and tell the user which months are available
4. If navigation succeeded, call `→ get_cycle_snapshot(YYYY-MM)` to retrieve the headline
5. Write one confirmation sentence citing the headline

## Output contract

```
→ navigate_to_month(YYYY-MM)
→ get_cycle_snapshot(YYYY-MM)

已切换到 YYYY年MM月。当月判断：<headline>。
```

Total response: 3 lines. Do not add module breakdowns, indicator tables, rule lists, or comparisons to other months — the right panel displays all of that.
