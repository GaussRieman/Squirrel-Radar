---
name: family-business
description: Explain what the current macro environment means for ordinary households and businesses. Use this skill when the user asks how the economy affects families, personal finances, household debt, business operations, hiring decisions, cash flow, or pricing strategy. Do NOT give specific asset recommendations, fund names, or yield targets.
---

# Household & Business Impact

## What this skill does

Translates macro cycle signals into plain-language implications for household financial decisions and business operating conditions. No investment advice — ever.

## Workflow

1. `→ get_cycle_snapshot(month)` — headline and six-module states for overall context
2. `→ get_indicators(month, category="居民")` — household indicators: `wage_income`, `household_mid_long_loan`, `core_cpi`
3. `→ get_indicators(month, category="企业")` — business indicators: `enterprise_mid_long_loan`, `private_investment`, `industrial_profit`, `ppi`
4. For each indicator, connect the current value movement to a concrete behavioral implication — what it means for decisions, not what it means for asset prices

## Output contract

```
**对普通家庭**
- 收入与就业：<wage_income movement → what it means for income stability — 1 sentence>
- 负债与购房：<household_mid_long_loan movement → what it means for borrowing appetite — 1 sentence>
- 日常消费：<core_cpi movement → what it means for purchasing power — 1 sentence>
- 关注重点：<what households should watch or consider regarding cash flow, large purchases, or debt — no specific asset advice>

**对企业经营**
- 融资环境：<enterprise_mid_long_loan movement → what it means for credit access — 1 sentence>
- 需求温度：<ppi + industrial_profit → what it means for pricing power and margins — 1 sentence>
- 扩张信号：<private_investment → what it means for expansion appetite — 1 sentence>
- 关注重点：<what businesses should watch — inventory levels, hiring pace, pricing strategy — no securities advice>
```

Forbidden: specific ticker symbols, fund names, yield promises, "建议买入/卖出", certainty language ("必然", "确定", "保证").
