# 项目完成情况

## 项目定位

本项目是“宏观周期状态雷达”的 MVP，用少量核心宏观指标、透明规则系统和 Agent 解读提示词，生成月度宏观周期状态理解结果。

它不是行情系统，不做爬虫，不做实时数据，不提供具体投资建议。

## 已完成

### 1. 工程结构

- `backend/`：FastAPI 后端
- `frontend/`：Next.js 前端
- `docker-compose.yml`：后端、前端一键启动
- `docs/`：项目文档

### 2. 后端

- 使用 FastAPI + SQLAlchemy + SQLite
- 启动时自动建表
- 提供指标定义、指标数据、规则结果、周期快照、首页聚合数据 API
- 支持 CSV 导入指标数据
- 支持手动录入指标数据

核心文件：

- `backend/app/models/domain.py`
- `backend/app/api/routes.py`
- `backend/app/services/seed.py`
- `backend/app/services/rule_engine.py`

### 3. 指标体系

已定义 12 个核心宏观指标：

- M2同比
- 社融存量同比
- 新增人民币贷款
- 居民中长期贷款
- 企业中长期贷款
- 核心CPI
- PPI
- 70城二手房价格环比
- 商品房销售面积
- 居民工资性收入
- 民间投资
- 工业企业利润

指标定义文件：

- `backend/app/seeds/indicators.seed.json`

每个指标包含定义、解释、风险提示、重要性、可信度、相关指标等信息。

### 4. 规则系统

已设计第一版透明规则系统，不使用机器学习。

规则文件：

- `backend/app/seeds/rules.seed.yaml`

当前包含 22 条规则，覆盖：

- 钱宽信用弱
- 信用扩张
- 居民防御状态
- 居民信心修复
- 房地产未确认见底
- 房地产初步企稳
- 企业观望
- 企业扩张
- 低通胀弱需求
- 成本推动型通胀
- 政策托底
- 内生修复

规则逻辑保持 MVP 简洁：条件比较 + `all/any` 组合。

### 5. 周期状态快照

后端会按月份生成周期状态快照，包含六个模块：

- 货币
- 信用
- 居民
- 房地产
- 企业
- 价格

快照会汇总规则命中、主要风险和下月观察任务。

### 6. Agent 解读提示词

已开发 Macro Cycle Agent，并基于 DeepAgent 构建运行时。

提示词文件：

- `backend/app/prompts/agent_interpretation_prompt.md`

Agent 目标是根据指标数据、规则命中和周期快照生成“宏观周期状态解读”，并遵守：

- 不做具体投资推荐
- 不承诺收益
- 必须引用输入数据
- 数据不足时明确说明
- 风格专业、简洁、深入浅出

Agent 能力：

- 使用 DeepAgent runtime
- 配置模型后可真实调用模型
- 未配置模型密钥时自动使用 mock fallback
- Agent 通过工具读取上下文，而不是只接收一段文本

Agent 工具：

- `get_indicator_data`：读取当前月份全部指标数据
- `get_matched_rules`：读取当前月份命中规则
- `get_cycle_snapshot`：读取周期状态快照
- `get_rule_execution_logs`：读取规则执行日志

Agent 工作台：

- `/agent`

未配置 `OPENAI_API_KEY` 时，工作台返回 mock 解读；配置后可通过 DeepAgent 调用真实模型，并强制 Agent 先调用工具读取指标、规则和快照。

### 6.1 测试数据

已提供 3 套测试场景：

- 钱宽信用弱 + 居民防御
- 内生修复
- 成本推动压力

测试数据文件：

- `backend/app/seeds/test_scenarios.seed.json`

后端接口：

- `GET /api/test-data/scenarios`
- `POST /api/test-data/scenarios/{scenario_id}/apply`

### 7. 前端首页与 AI 工作台

已完成一个可运行的 AI 宏观分析工作台：

- 左侧资产栏：最近分析和专题资产入口
- 中间 Agent 对话区：流式输出、Markdown 渲染、工具步骤展示和快捷问题
- 右侧周期数据看板：当前周期状态卡片、全部指标归一化趋势图、历史对比与来源表
- 状态卡片可点击并触发 Agent 解释输入
- Agent 对话不再重复完整指标表，结构化数据保留在右侧看板

核心文件：

- `frontend/app/page.tsx`
- `frontend/components/HomeChat.tsx`
- `frontend/components/AgentCanvas.tsx`
- `frontend/lib/api.ts`

### 8. 环境管理

Python 使用 uv 管理。

共享环境位置：

- `/Users/frank/Desktop/codes/.venv`

后端依赖文件：

- `backend/pyproject.toml`
- `backend/uv.lock`

## 启动方式

```bash
docker compose up --build
```

访问：

- 前端：http://127.0.0.1:3000
- API 文档：http://127.0.0.1:8000/docs
- Agent 工作台：http://127.0.0.1:3000/agent

## 已验证

- 后端 Python 代码可编译
- 后端 app 可导入
- 前端 `npm run build` / `npm run typecheck` 通过
- 指标 seed 文件校验通过
- 规则 seed 文件校验通过
- Agent 提示词结构完整
- 后端测试覆盖 seed、规则评估、dashboard、Agent mock、测试场景应用

## 尚未完成

- 已接入 DeepAgent 调用通道；真实调用需要配置模型密钥
- 已接入最新公开官方快照同步；后续可继续扩展更多官方数据适配器
- 未做用户权限
- 未做 Alembic 数据库迁移
- 未做复杂规则编排和回测
- 未做生产部署配置

## 下一步建议

当前研发任务以 `docs/task-list.md` 为准。

1. 增加 Agent 解读 API，先返回基于提示词的 mock 结果。
2. 给规则命中结果生成更可读的证据文本。
3. 增加指标数据录入页面。
4. 引入 Alembic 管理数据库结构变更。
5. 接入真实月度数据源或半自动 CSV 更新流程。
