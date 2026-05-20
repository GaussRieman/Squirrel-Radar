---
name: cycle-summary
description: Generate a concise macro cycle state summary for a given month. Use this skill when the user asks about the overall economic state, the headline judgment, what is happening this month, or requests a comprehensive breakdown of all six modules. Do NOT use this skill for questions about a single indicator, a single rule, latest-data viewing, or when the user only wants to navigate to a month.
---

# Cycle Summary

## What this skill does

Synthesizes the six-module state, matched rules, and key indicators into a structured macro cycle interpretation. This is the most comprehensive skill — invoke it only when the user wants the full picture.

## Workflow

1. `→ get_cycle_snapshot(month="YYYY-MM")` — headline, six module states, risks, watch tasks
2. `→ get_matched_rules(month="YYYY-MM")` — which rules fired; use as the primary evidence base for module states
3. `→ get_indicators(month="YYYY-MM")` — scan all indicators; pull M2 YoY (`m2_yoy`) and TSF stock YoY (`tsf_stock_yoy`) as monetary anchors
4. Synthesize: connect each module state to the rule evidence and indicator values that support it. Do not add conclusions not supported by the tool responses.

If `m2_yoy` or `tsf_stock_yoy` codes are not found in the indicators response, use the indicator with the highest `percentile_24m` in the 货币 category as the anchor instead.

## Output contract

Use this Markdown structure exactly. Every section is required. Every data value cited must come from a tool response in this turn.
Do not output a core indicator table or a six-module table. The right-side panel already displays the full data. Use short lists that stream cleanly.

```
## [YYYY年MM月] 宏观周期状态

**一句话判断**
<headline from snapshot>。依据：<matched rule name> 命中，<key indicator name> 同比 <value>。

**六大模块**
- 货币：<state>，核心依据：<one short evidence item>
- 信用：<state>，核心依据：<one short evidence item>
- 居民：<state>，核心依据：<one short evidence item>
- 房地产：<state>，核心依据：<one short evidence item>
- 企业：<state>，核心依据：<one short evidence item>
- 价格：<state>，核心依据：<one short evidence item>

**本月关键变化**
1. <change description> — <indicator name>: <value>
2. <change description> — <indicator name>: <value>
3. <change description> — <indicator name>: <value>

**主要风险**
- <risk text from matched rule evidence or snapshot risks>

**下月观察重点**
- <indicator name>：当前 <value><unit>，若 <specific condition> 则判断将转为 <new state>
```

If a module has no data, write "数据不足" for that module. Do not omit the row.
