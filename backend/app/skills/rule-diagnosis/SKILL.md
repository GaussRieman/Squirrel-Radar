---
name: rule-diagnosis
description: Explain why a specific rule fired or did not fire. Use this skill when the user asks why a rule matched, why a module is in a particular state, what the evidence is for a specific judgment, or why a specific rule did not trigger. Do NOT use this skill for general monthly summaries or indicator definitions.
---

# Rule Diagnosis

## What this skill does

Traces a single rule's execution: reads its conditions, checks each one against actual indicator values, and explains the verdict condition-by-condition. Precise and evidence-based.

## Workflow

1. Identify the rule the user is asking about — by name, module state label, or description from their message
2. `→ get_matched_rules(month="YYYY-MM")` — locate the `rule_id` if not already known from context
3. `→ get_rule_detail(rule_id="RULE_ID", month="YYYY-MM")` — read full execution log, all conditions, and evidence
4. For each condition in the rule: state the requirement, state the actual value from the tool response, state pass (✓) or fail (✗)
5. State the overall verdict and cite the risk implication if the rule fired

## Output contract

```
**规则：** <name>（<rule_id>）
**结果：** 命中 ✓ / 未命中 ✗

**条件核查**
| 条件 | 要求 | 实际值 | 结果 |
|------|------|--------|------|
| <indicator name> | <operator> <threshold><unit> | <actual value><unit> | ✓ / ✗ |

**结论**
<One sentence: why all conditions passed, or which condition failed and by how much.>

**风险含义**（命中时）
<risk field from evidence — omit this section if rule did not fire>
```

Do not paste raw JSON from tool responses. Parse conditions and render them in the table above.
