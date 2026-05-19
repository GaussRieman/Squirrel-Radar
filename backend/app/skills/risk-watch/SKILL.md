---
name: risk-watch
description: Surface current risks and next-month watch items. Use this skill when the user asks what risks exist now, what to monitor next month, what warning signs are present, or what could change the cycle judgment. Do NOT use this skill for historical comparisons or indicator definitions.
---

# Risk Watch

## What this skill does

Scans matched rules and weak-status indicators to produce a concise risk register and a forward-looking watch list with falsifiable conditions.

## Workflow

1. `→ get_cycle_snapshot(month)` — read `risks` and `watch_tasks` arrays from the snapshot
2. `→ get_matched_rules(month)` — read the `risk` field from each matched rule's evidence
3. `→ get_indicators(month)` — identify any indicators with `status=weak` not already covered by a matched rule
4. Deduplicate across all three sources. Rank by severity: `critical` first, then `warning`, then `caution`

## Output contract

```
**当前主要风险**
1. <risk description>（来源：规则「<rule name>」/ 指标「<indicator name>」）
2. ...

**下月重点观察**
1. <indicator name>：当前 <value><unit>，若 <specific measurable condition> 则判断将转为 <new state>
2. ...

**风险等级汇总**：critical <n> 条 | warning <n> 条 | caution <n> 条
```

Watch items must specify a falsifiable condition. "继续观察" is not an acceptable watch item — every item must say what specific change would alter the current judgment.
