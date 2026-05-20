---
name: data-explain
description: Explain what a macro indicator means and what its current value signals. Use this skill when the user asks what an indicator is, what YoY/MoM/percentile/trend means, or what a specific indicator's current reading tells us about the economy. Do NOT use this skill when the user asks about rules or wants an overall monthly state summary.
---

# Data Explainer

## What this skill does

Answers "what does this number mean?" — pulls the indicator's definition, interpretation, and risk note from the database, then contextualizes the current value in plain language.

## Workflow

1. Identify the indicator the user is asking about — by name or code from their message
2. If the indicator code is unknown, `→ get_indicators(month="YYYY-MM")` to scan names and locate the correct code
3. `→ get_indicator_detail(code="CODE", month="YYYY-MM")` — definition, interpretation, risk_note, and all current values
4. Explain: concept first, then current value in context of the interpretation field

## Field semantics (describes what each field name means — values still require a tool call)

- **yoy**: year-on-year change rate — reflects medium-term trend direction
- **mom**: month-on-month change rate — reflects short-term momentum
- **trend_3m**: 3-month rolling average — smooths single-month noise
- **percentile_24m**: where the current value sits within the past 24 months (>70 = historically high, <30 = historically low)
- **status**: `strong` / `neutral` / `weak` — assigned by the rule engine against fixed thresholds

## Output contract

Do not use Markdown tables. Use compact lines and short bullets so the answer streams cleanly.

```
**<indicator name>**（`<code>`）

定义：<definition field>
当前值：<value><unit> | 同比 <yoy> | 环比 <mom> | 24月分位 <percentile_24m>%
状态：<status>

解读：<interpretation field, contextualized to the actual current value — 2–3 sentences>
风险提示：<risk_note field>
```
