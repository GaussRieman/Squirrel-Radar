# Macro Cycle Radar

宏观周期状态雷达是一个 AI 宏观分析工作台，用核心宏观指标、文件驱动规则、真实来源链接和 Agent 解读生成月度宏观周期状态快照。

## 技术栈

- 前端：Next.js + React + TypeScript + Recharts
- 后端：FastAPI + SQLAlchemy
- 数据库：SQLite
- 规则：`backend/app/seeds/rules.seed.yaml`
- 指标定义：`backend/app/seeds/indicators.seed.json`
- Agent 提示词：`backend/app/prompts/AGENT.md`
- Agent 工作台：首页三栏工作台 + `/agent`
- 数据输入：手动 API 录入 + CSV 导入接口
- Agent：DeepAgent runtime，支持工具调用、会话记忆、意图路由和流式输出

## 项目文档

- 当前完成情况：`docs/project-status.md`
- 当前研发任务列表：`docs/task-list.md`

## Agent 工作台

访问：

- http://127.0.0.1:3000/agent

可在页面中：

- 选择测试场景
- 一键应用测试数据
- 选择月份
- 使用 mock 解读
- 查看 Agent runtime、模型状态和工具列表
- 配置密钥后调用 DeepAgent 真实模型

Macro Cycle Agent 使用 DeepAgent runtime，并提供 4 个工具：

- `get_indicator_data`
- `get_matched_rules`
- `get_cycle_snapshot`
- `get_rule_execution_logs`

## 首页 AI 工作台

首页采用三栏结构：

- 左侧：资产栏，展示最近生成和专题资产。
- 中间：Agent 对话区，负责流式回答、解释、报告生成和用户输入。
- 右侧：周期数据看板，负责持续展示当前周期状态卡片、全部指标归一化趋势图、历史对比表和真实来源链接。

右侧看板只保留不适合塞进聊天气泡里的内容。状态卡片可点击，点击后会把对应解释问题带入 Agent 输入框。

## 快速启动

```bash
docker compose up --build
```

打开：

- 前端：http://127.0.0.1:3000
- 后端 API：http://127.0.0.1:8000/api/health
- OpenAPI 文档：http://127.0.0.1:8000/docs

后端启动时会自动创建表，并写入 12 个指标定义、24 个月样例数据。访问首页时会自动评估规则并生成当前月份快照。

## 本地开发

### 共享 uv 环境

Python 环境统一放在上层 `codes/.venv`，子项目通过 `UV_PROJECT_ENVIRONMENT` 复用这个环境并按各自的 `pyproject.toml` 增量安装依赖。

首次创建共享环境：

```bash
cd /Users/frank/Desktop/codes
uv venv .venv --python 3.12
```

后端安装和启动：

```bash
cd backend
UV_PROJECT_ENVIRONMENT=/Users/frank/Desktop/codes/.venv uv sync
source /Users/frank/Desktop/codes/.venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

本地开发不需要启动数据库服务。默认使用 `backend/macro_cycle_radar.db` 作为 SQLite 数据库文件；将 `backend/.env.example` 复制为 `backend/.env` 后可按需修改连接串。

如需真实调用 DeepAgent 模型，在 `backend/.env` 配置：

```bash
OPENAI_API_KEY=你的模型密钥
OPENAI_BASE_URL=你的OpenAI兼容接口地址
AGENT_MODEL=openai:gpt-5.4
ENABLE_MODEL_CALLS=true
```

未配置密钥时，Agent 工作台仍可使用 mock 解读。

## CSV 导入格式

接口：`POST /api/indicator-data/import-csv`

CSV 表头：

```csv
indicator_code,month,value,yoy,mom,trend_3m,percentile_24m,status
m2_yoy,2026-05,8.9,8.9,0.1,8.8,72,strong
```

本地真实数据同步也可以直接指向一个 CSV 文件或目录：

```bash
cd backend
uv run python -m app.services.data_sync.cli ../data/real_macro_data.csv
```

或通过 API：

```bash
curl -X POST http://127.0.0.1:8000/api/data-sync/local-csv \
  -H "Content-Type: application/json" \
  -d '{"path":"../data/real_macro_data.csv"}'
```

也可以直接同步当前内置的最新公开官方快照，并清理本地未发布的 seed 月份：

```bash
cd backend
uv run python -m app.services.data_sync.cli --official-latest --prune-newer
```

## 核心 API

- `GET /api/indicators`：指标定义列表
- `POST /api/indicators`：新增指标定义
- `GET /api/indicator-data?month=2026-05`：指标数据
- `POST /api/indicator-data`：手动录入指标数据
- `POST /api/indicator-data/import-csv`：CSV 导入
- `POST /api/data-sync/local-csv`：从本地 CSV 文件或目录同步真实数据
- `POST /api/data-sync/official-latest`：同步最新公开官方快照
- `GET /api/rules`：查看规则文件内容
- `POST /api/rules/evaluate/{month}`：评估指定月份规则
- `GET /api/rule-results?month=2026-05`：规则结果
- `GET /api/snapshots/{month}`：周期状态快照
- `GET /api/dashboard`：首页聚合数据

## 项目结构

```text
macro-cycle-radar/
  backend/
    app/
      api/          API 路由
      core/         配置和数据库连接
      models/       SQLAlchemy 模型
      prompts/      Agent 解读提示词
      schemas/      Pydantic schema
      seeds/        指标和规则种子文件
      services/     seed 和规则引擎
  frontend/
    app/            Next.js App Router 页面
    components/     图表组件
    lib/            API 类型和请求
  docker-compose.yml
```

## 说明

这个 MVP 只用于宏观周期状态理解，不构成投资建议。第一版刻意保留简单架构：规则直接读 YAML 文件，数据库表由应用启动创建，方便后续再引入 Alembic、真实 Agent、数据源同步和权限系统。
