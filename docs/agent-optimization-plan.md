# Agent 优化计划

## 目标

把左侧 Agent 从“单次问答框”升级为宏观周期分析助手：能识别用户意图，选择合适技能，使用工具读取数据，保留轻量会话记忆，并基于当前月份上下文回答。

## 第一版实现

- 意图判断：后端根据问题文本识别 `data_explain`、`rule_diagnosis`、`cycle_summary`、`risk_watch`、`family_business`。
- Skill 路由：每类意图绑定一段专门提示词，约束回答角度。
- Tool 使用：DeepAgent 暴露 `get_agent_context`、`get_memory`、`get_indicator_data`、`get_matched_rules`、`get_cycle_snapshot`、`get_rule_execution_logs`。
- Context：前端把最近对话传给后端，后端把意图、技能、前端上下文、历史记忆组成 Agent context。
- Memory：后端用 SQLite `agent_memory` 表保存问答摘要，按 `conversation_id` 隔离。
- 前端体验：左侧显示 Agent 能力标签、当前意图、当前技能、上下文摘要，并提供常用快捷问题。

## 后续任务

- [x] 把本地关键词意图判断升级为规则 YAML 驱动。
- [x] 支持点击右侧指标或规则后自动带入 Agent 上下文。
- [x] 将 Memory 从 JSON 文件迁移到 SQLite。
- [x] 增加工具调用过程展示，例如“读取指标”“检查规则”“生成结论”。
- [x] 对 Agent 输出做结构化渲染，而不是纯 Markdown 文本。

## 第二版实现

- `backend/app/prompts/agent_intents.yaml` 管理意图、关键词、技能提示词和展示步骤。
- `agent_memory` 表保存最近问答摘要，Agent 通过 `get_memory` 工具读取。
- 右侧指标和规则支持点击，前端通过事件把选中对象传入左侧 Agent。
- Agent 请求体增加 `selected_context`，后端把它合入 `get_agent_context`。
- Agent 响应增加 `steps` 和 `sections`，前端按步骤标签和折叠段落渲染。

## 第三版交互优化

- 中间 Agent 对话区成为主工作区，支持 token 流式输出和 Markdown 增量渲染。
- Agent 输出避免复制右侧已有的完整指标表或模块看板，只保留回答、推理链和关键事实。
- 右侧从“本轮对话画布”改为“当前周期数据看板”，长期展示周期状态、全部指标趋势、历史对比和真实来源。
- 右侧状态卡片点击后填入解释类问题，让用户从数据看板自然进入 Agent 对话。
