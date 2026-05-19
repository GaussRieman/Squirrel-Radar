---
name: risk-watch
description: 聚焦当前主要风险和下月重点观察指标。当用户询问风险、下个月关注什么、需要警惕什么时使用。
---

# 风险观察技能

## 触发条件
用户询问当前风险、下月重点观察、预警信号、需要关注的指标。

## 工作流

1. 调用 `get_cycle_snapshot(month)` 读取 risks 和 watch_tasks
2. 调用 `get_matched_rules(month)` 读取命中规则的 risk 字段
3. 调用 `get_indicators(month)` 扫描 status=weak 的指标作为额外风险信号
4. 综合形成风险清单和观察任务

## 输出格式

```
**当前主要风险：**
1. <风险描述>（来源：规则 <name> / 指标 <name>）
2. ...

**下月重点观察指标：**
1. <指标名>：当前值 <value>，观察 <什么变化> 将改变判断为 <新状态>
2. ...

**风险等级**：基于命中规则的 severity 字段（warning / critical / positive）
```

## 约束
- 不做具体资产价格预测
- 观察任务必须说明"什么变化会改变判断"，不能只写"继续观察"
