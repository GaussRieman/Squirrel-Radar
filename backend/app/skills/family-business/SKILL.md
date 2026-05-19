---
name: family-business
description: 解释宏观环境对普通家庭资产负债和企业经营决策的含义。当用户询问家庭、资产、企业经营、现金流影响时使用。
---

# 家庭企业含义技能

## 触发条件
用户询问宏观环境对普通家庭或企业的含义、影响、决策参考。

## 工作流

1. 调用 `get_cycle_snapshot(month)` 读取 headline 和模块状态
2. 调用 `get_indicators(month, category="居民")` 读取居民相关指标（household_mid_long_loan, wage_income, core_cpi）
3. 调用 `get_indicators(month, category="企业")` 读取企业相关指标（enterprise_mid_long_loan, private_investment, industrial_profit, ppi）
4. 连接指标变化 → 行为含义 → 宏观影响

## 输出格式

```
**对普通家庭的含义：**
- 收入与就业：<wage_income 解读>
- 负债压力：<household_mid_long_loan 解读>
- 消费环境：<core_cpi 解读>
- 建议关注：<基于以上，家庭应关注什么（现金流/大额支出/负债）>

**对企业经营的含义：**
- 融资环境：<enterprise_mid_long_loan 解读>
- 需求温度：<ppi + industrial_profit 解读>
- 扩张信号：<private_investment 解读>
- 建议关注：<基于以上，企业应关注什么（库存/用工/定价）>
```

## 约束
- 只解释宏观环境含义，不给具体投资品种、买卖点位或仓位建议
- 不使用"必然""确定"等确定性语言
