---
name: cycle-summary
description: Generate a full macro cycle state summary for a given month. Use this skill when the user asks about the overall economic state, the headline judgment, what is happening this month, or requests a comprehensive breakdown of all six modules. Do NOT use this skill for questions about a single indicator, a single rule, or when the user only wants to navigate to a month.
---

# Cycle Summary

## What this skill does

Synthesizes the six-module state, matched rules, and key indicators into a structured macro cycle interpretation. This is the most comprehensive skill — invoke it only when the user wants the full picture.

## Workflow

1. `→ get_cycle_snapshot(month)` — headline, six module states, risks, watch tasks
2. `→ get_matched_rules(month)` — which rules fired; use as the primary evidence base for module states
3. `→ get_indicators(month)` — scan all indicators; pull M2 YoY (`m2_yoy`) and TSF stock YoY (`tsf_stock_yoy`) as monetary anchors
4. Synthesize: connect each module state to the rule evidence and indicator values that support it. Do not add conclusions not supported by the tool responses.

## Output contract

Use this Markdown structure exactly. Every section is required. Every data value cited must come from a tool response in this turn.

```
## [YYYY年MM月] 宏观周期状态

**一句话判断**
<headline from snapshot>。依据：<matched rule name> 命中，<key indicator name> 同比 <value>。

**六大模块**
| 模块 | 状态 | 核心依据 |
|------|------|---------|
| 货币 | <state> | <indicator name + value> |
| 信用 | <state> | <indicator name + value> |
| 居民 | <state> | <indicator name + value> |
| 房地产 | <state> | <indicator name + value> |
| 企业 | <state> | <indicator name + value> |
| 价格 | <state> | <indicator name + value> |

**本月关键变化**
1. <change description> — <indicator name>: <value>
2. <change description> — <indicator name>: <value>
3. <change description> — <indicator name>: <value>

**主要风险**
- <risk text from matched rule evidence or snapshot risks>

**下月观察重点**
- <indicator name>：当前 <value><unit>，若 <specific condition> 则判断将转为 <new state>
```

If a module has no data, write "数据不足" in both the 状态 and 核心依据 columns. Do not omit the row.
