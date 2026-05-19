# Agent 重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前"假工具闭包 + 关键词意图检测"的 Agent 实现，重构为使用 DeepAgent 真实 tool-use loop、SqliteSaver 多轮持久化、SKILL.md 技能文件的真正 Agent 架构。

**Architecture:** 工具函数直接查 SQLite 数据库（不预取），通过 `StateBackend + files=` 注入 5 个 SKILL.md 技能文件；`SqliteSaver` checkpointer 存入同一个 `macro_cycle_radar.db`，以 `conversation_id` 作为 `thread_id` 实现跨请求多轮持久化；删除 `AgentMemory` 表和所有关键词意图检测代码。

**Tech Stack:** DeepAgent 0.6.1, LangGraph SqliteSaver, langchain-openai, FastAPI, SQLAlchemy, Alembic

---

## 文件变更地图

| 操作 | 路径 | 职责 |
|------|------|------|
| 修改 | `backend/app/services/agent_service.py` | 核心重构：真实工具 + DeepAgent + checkpointer |
| 修改 | `backend/app/prompts/agent_interpretation_prompt.md` | 去掉 JSON schema 示例，改为工具说明 |
| 新建 | `backend/app/skills/cycle-summary/SKILL.md` | 周期状态综合技能 |
| 新建 | `backend/app/skills/rule-diagnosis/SKILL.md` | 规则诊断技能 |
| 新建 | `backend/app/skills/data-explain/SKILL.md` | 数据解释技能 |
| 新建 | `backend/app/skills/risk-watch/SKILL.md` | 风险观察技能 |
| 新建 | `backend/app/skills/family-business/SKILL.md` | 家庭企业含义技能 |
| 修改 | `backend/app/models/domain.py` | 删除 AgentMemory 类 |
| 修改 | `backend/app/schemas/domain.py` | 简化 AgentInterpretationRead，删除 intent/skill/steps/context_summary |
| 新建 | `backend/alembic/versions/20260519_0002_drop_agent_memory.py` | 删除 agent_memory 表 |
| 修改 | `backend/pyproject.toml` | 添加 langgraph-checkpoint-sqlite 依赖（已安装，补声明） |
| 修改 | `backend/tests/test_cycle_flow.py` | 更新 Agent 相关测试 |

---

## Task 1: 写入 SKILL.md 技能文件（5 个）

**Files:**
- Create: `backend/app/skills/cycle-summary/SKILL.md`
- Create: `backend/app/skills/rule-diagnosis/SKILL.md`
- Create: `backend/app/skills/data-explain/SKILL.md`
- Create: `backend/app/skills/risk-watch/SKILL.md`
- Create: `backend/app/skills/family-business/SKILL.md`

- [ ] **Step 1: 创建技能目录**

```bash
mkdir -p backend/app/skills/cycle-summary
mkdir -p backend/app/skills/rule-diagnosis
mkdir -p backend/app/skills/data-explain
mkdir -p backend/app/skills/risk-watch
mkdir -p backend/app/skills/family-business
```

- [ ] **Step 2: 写入 cycle-summary/SKILL.md**

```markdown
---
name: cycle-summary
description: 综合六大模块、命中规则和关键指标，生成宏观周期状态判断。当用户问本月状态、宏观环境、整体判断时使用。
---

# 周期状态综合技能

## 触发条件
用户询问本月宏观周期状态、整体判断、一句话摘要或综合解读。

## 工作流

1. 调用 `get_available_months` 确认可用月份范围
2. 调用 `get_cycle_snapshot(month)` 读取 headline、六模块状态、风险和观察任务
3. 调用 `get_matched_rules(month)` 读取命中规则作为判断依据
4. 调用 `get_indicators(month)` 读取全部指标，提取货币（m2_yoy）和信用（tsf_stock_yoy）作为核心锚点
5. 综合以上数据按输出格式生成解读

## 输出格式

按以下 Markdown 结构输出，必须包含全部 7 个部分：

```
## 1. 本月一句话判断
引用至少 2 个数据或规则作为依据。

## 2. 六大模块状态
### 货币 / 信用 / 居民 / 房地产 / 企业 / 价格
- 状态：
- 依据：（引用具体指标数值）
- 解读：

## 3. 本月最重要的 3 个变化
1. 变化一（指标依据 → 宏观含义）
2. 变化二
3. 变化三

## 4. 当前主要风险
- 风险一（引用规则或指标）

## 5. 下个月重点观察指标
- 指标一：为什么观察，什么变化会改变判断

## 6. 对普通家庭资产配置的含义
只解释宏观含义，不给具体投资建议。

## 7. 对企业经营决策的含义
只解释经营环境含义，不给证券或商品建议。
```

## 约束
- 所有结论必须引用工具返回的数据，不得编造
- 数据不足时写"该模块数据不足"，不强行推断
- 禁止输出：买入/卖出建议、收益承诺、"确定反转"等确定性预测
```

- [ ] **Step 3: 写入 rule-diagnosis/SKILL.md**

```markdown
---
name: rule-diagnosis
description: 解释某条规则为什么命中或未命中，提供条件、数据和执行证据。当用户询问规则命中原因、为什么判断某状态、某规则的依据时使用。
---

# 规则诊断技能

## 触发条件
用户询问规则为什么命中、为什么未命中、某判断的依据是什么。

## 工作流

1. 调用 `get_matched_rules(month)` 获取已命中规则列表，定位用户询问的规则
2. 调用 `get_rule_detail(rule_id, month)` 读取完整执行日志和 evidence
3. 对于未命中规则，调用 `get_indicators(month, category)` 读取相关模块指标，逐条核对条件

## 输出格式

```
**规则名称**：<name>
**命中状态**：命中 / 未命中

**条件核查：**
- 条件一：要求 <字段> <运算符> <阈值>，实际值为 <value>，结果：✓ / ✗
- 条件二：...

**结论**：说明规则整体为何命中或未命中，引用关键数据点。
**风险含义**：引用 evidence 中的 risk 字段（命中时）。
```

## 约束
- 必须逐条核查条件，不能笼统说"条件不满足"
- 引用 execution_log 中的实际数值
```

- [ ] **Step 4: 写入 data-explain/SKILL.md**

```markdown
---
name: data-explain
description: 解释宏观指标的字段口径、定义和当前数值含义。当用户询问某个指标是什么意思、同比/环比/分位数的含义时使用。
---

# 数据解释技能

## 触发条件
用户询问指标含义、字段口径（同比/环比/分位/趋势）、某指标当前值说明了什么。

## 工作流

1. 调用 `get_indicator_detail(code, month)` 读取指标完整定义、interpretation 和 risk_note
2. 若用户未指定指标代码，先调用 `get_indicators(month)` 列出所有指标供定位
3. 解释字段口径，再结合当前数值说明含义

## 字段口径说明（内置知识，无需调工具）

- **yoy（同比）**：与去年同期相比的变化率，反映中长期趋势
- **mom（环比）**：与上月相比的变化率，反映短期动能
- **trend_3m**：近 3 个月均值，平滑短期波动
- **percentile_24m**：当前值在过去 24 个月中的百分位，反映历史相对位置（> 70 偏高，< 30 偏低）
- **status**：strong / neutral / weak，由规则引擎根据阈值判定

## 输出格式

```
**指标名称**：<name>（代码：<code>）
**定义**：<definition>
**当前值**：<value><unit>，同比 <yoy>，环比 <mom>，24 月分位 <percentile_24m>%
**状态**：<status>
**解读**：<interpretation 中的内容，结合当前数值具体化>
**风险提示**：<risk_note>
```

## 约束
- 先解释概念，再引用当前数据，不能只列数字
```

- [ ] **Step 5: 写入 risk-watch/SKILL.md**

```markdown
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
```

- [ ] **Step 6: 写入 family-business/SKILL.md**

```markdown
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
```

- [ ] **Step 7: 验证文件结构**

```bash
find backend/app/skills -name "SKILL.md" | sort
```

期望输出：
```
backend/app/skills/cycle-summary/SKILL.md
backend/app/skills/data-explain/SKILL.md
backend/app/skills/family-business/SKILL.md
backend/app/skills/risk-watch/SKILL.md
backend/app/skills/rule-diagnosis/SKILL.md
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/skills/
git commit -m "feat: add 5 DeepAgent skill files (SKILL.md)"
```

---

## Task 2: 更新 system prompt

**Files:**
- Modify: `backend/app/prompts/agent_interpretation_prompt.md`

- [ ] **Step 1: 替换 agent_interpretation_prompt.md**

将文件完整替换为以下内容（去掉旧的 JSON schema Input 示例，改为工具说明）：

```markdown
# Macro Cycle Interpretation Agent Prompt

## Role

你是"宏观周期状态雷达"的解读 Agent。你的任务是根据工具获取的当月指标数据、规则命中结果和周期状态快照，生成专业、简洁的"宏观周期状态解读"，帮助非专业用户理解当前经济状态、判断依据和观察重点。

你必须把指标变化、规则命中和结论连接起来。不预测市场，不给投资建议。

## 可用工具

- `get_available_months()` — 返回有数据的月份列表
- `get_cycle_snapshot(month)` — 周期快照：headline、六模块状态、风险、观察任务
- `get_indicators(month, category=None)` — 指标列表，category 可选（货币/信用/居民/房地产/企业/价格）
- `get_indicator_detail(code, month)` — 单指标完整字段 + 定义 + 解读
- `get_matched_rules(month)` — 本月命中规则 + evidence
- `get_rule_detail(rule_id, month)` — 单条规则完整执行日志

## 推理原则

1. **先取数，再推理**：必须先调工具读取数据，不得凭记忆或猜测填写指标数值
2. **引用具体数据**：每个核心结论都要引用工具返回的具体数值或规则名称
3. **技能路由**：根据用户问题选择对应技能（skills 目录中），按技能工作流执行
4. **数据不足时**：明确写"该模块数据不足"，不强行推断
5. **规则优先**：命中规则是状态判断的主要依据；未命中规则不得说成已发生

## Safety Constraints

禁止输出：
- "建议买入/卖出/加仓/减仓某类资产"
- "预计收益率""确定上涨""确定见底""确定反转"
- "保证""必然""一定"
- 未由工具数据支持的宏观事件、政策判断或市场行情

## Quality Checklist

输出前自检：
- 是否每个核心判断都引用了工具返回的数据？
- 是否说明了数据不足的地方？
- 是否避免了投资建议和收益承诺？
- 是否遵循了对应技能的输出格式？
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/prompts/agent_interpretation_prompt.md
git commit -m "refactor: update system prompt for real tool-use agent"
```

---

## Task 3: 删除 AgentMemory 模型，写 Alembic migration

**Files:**
- Modify: `backend/app/models/domain.py`
- Create: `backend/alembic/versions/20260519_0002_drop_agent_memory.py`

- [ ] **Step 1: 从 domain.py 删除 AgentMemory 类**

打开 `backend/app/models/domain.py`，删除以下整个类（第 73-83 行）：

```python
class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    month: Mapped[str | None] = mapped_column(String(7), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer_excerpt: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(64), index=True)
    skill: Mapped[str] = mapped_column(String(128))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
```

- [ ] **Step 2: 创建 Alembic migration**

新建文件 `backend/alembic/versions/20260519_0002_drop_agent_memory.py`：

```python
"""drop agent_memory table

Revision ID: 20260519_0002
Revises: 20260518_0001
Create Date: 2026-05-19
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = "20260519_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "agent_memory" in inspector.get_table_names():
        op.drop_table("agent_memory")


def downgrade() -> None:
    pass  # table was deleted by design, no restore needed
```

- [ ] **Step 3: 运行 migration 验证语法正确**

```bash
cd backend && uv run alembic upgrade head 2>&1
```

期望：看到 `Running upgrade 20260518_0001 -> 20260519_0002` 成功，无 error。

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/domain.py backend/alembic/versions/20260519_0002_drop_agent_memory.py
git commit -m "refactor: remove AgentMemory model and add drop migration"
```

---

## Task 4: 简化 AgentInterpretationRead schema

**Files:**
- Modify: `backend/app/schemas/domain.py`

- [ ] **Step 1: 更新 AgentInterpretationRead**

在 `backend/app/schemas/domain.py` 中，将 `AgentInterpretationRead` 替换为：

```python
class AgentInterpretationRead(BaseModel):
    month: str
    mode: str = "mock"
    model: str | None = None
    content: str
    sections: list[dict] = []
```

同时删除 `AgentInterpretationRequest` 中的 `history` 字段（LangGraph checkpointer 接管历史，不再需要前端传）：

```python
class AgentInterpretationRequest(BaseModel):
    month: str | None = None
    use_model: bool = False
    question: str | None = None
    conversation_id: str = "default"
    selected_context: dict | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/domain.py
git commit -m "refactor: simplify AgentInterpretationRead schema"
```

---

## Task 5: 重写 agent_service.py

**Files:**
- Modify: `backend/app/services/agent_service.py`

- [ ] **Step 1: 完整替换 agent_service.py**

```python
import json
import os
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.domain import CycleSnapshot, IndicatorData, IndicatorDefinition, RuleResult
from app.services.rule_engine import evaluate_month

_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
_DB_PATH = Path(__file__).resolve().parents[3] / "macro_cycle_radar.db"

# Shared checkpointer — one sqlite3 connection per process, check_same_thread=False for FastAPI
import sqlite3 as _sqlite3

_checkpointer: SqliteSaver | None = None


def _get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        conn = _sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        _checkpointer.setup()
    return _checkpointer


def _load_skill_files() -> dict[str, bytes]:
    """Load all SKILL.md files from the skills directory for StateBackend injection."""
    files: dict[str, bytes] = {}
    for skill_md in _SKILLS_DIR.glob("*/SKILL.md"):
        skill_name = skill_md.parent.name
        path = f"/skills/{skill_name}/SKILL.md"
        files[path] = skill_md.read_bytes()
    return files


def _build_model() -> ChatOpenAI:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
    model_name = settings.agent_model.removeprefix("openai:")
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
    )


def _build_tools(db: Session):
    """Return real DB-backed tools. Closed over db session."""
    from langchain_core.tools import tool

    @tool
    def get_available_months() -> str:
        """返回数据库中有指标数据的所有月份列表（降序）。"""
        months = db.scalars(
            select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))
        ).all()
        return json.dumps(list(months), ensure_ascii=False)

    @tool
    def get_cycle_snapshot(month: str) -> str:
        """返回指定月份的周期状态快照，包含 headline、六大模块状态、风险列表和观察任务。"""
        evaluate_month(db, month)
        snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == month))
        if not snapshot:
            return json.dumps({"error": f"No snapshot for month {month}"}, ensure_ascii=False)
        return json.dumps(
            {
                "month": snapshot.month,
                "headline": snapshot.headline,
                "summary": snapshot.summary,
                "modules": snapshot.modules,
                "risks": snapshot.risks,
                "watch_tasks": snapshot.watch_tasks,
            },
            ensure_ascii=False,
        )

    @tool
    def get_indicators(month: str, category: str = "") -> str:
        """返回指定月份的指标数据。category 可选（货币/信用/居民/房地产/企业/价格），为空返回全部。"""
        stmt = (
            select(IndicatorData)
            .options(joinedload(IndicatorData.indicator))
            .where(IndicatorData.month == month)
            .order_by(IndicatorData.indicator_id)
        )
        rows = db.scalars(stmt).all()
        result = []
        for row in rows:
            if category and row.indicator.category != category:
                continue
            result.append(
                {
                    "code": row.indicator.code,
                    "name": row.indicator.name,
                    "category": row.indicator.category,
                    "value": row.value,
                    "unit": row.indicator.unit,
                    "yoy": row.yoy,
                    "mom": row.mom,
                    "trend_3m": row.trend_3m,
                    "percentile_24m": row.percentile_24m,
                    "status": row.status,
                }
            )
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_indicator_detail(code: str, month: str) -> str:
        """返回指定指标在指定月份的完整数据，包含定义、解读口径和风险提示。"""
        defn = db.scalar(select(IndicatorDefinition).where(IndicatorDefinition.code == code))
        if not defn:
            return json.dumps({"error": f"Unknown indicator code: {code}"}, ensure_ascii=False)
        data = db.scalar(
            select(IndicatorData)
            .where(IndicatorData.indicator_id == defn.id, IndicatorData.month == month)
        )
        return json.dumps(
            {
                "code": defn.code,
                "name": defn.name,
                "category": defn.category,
                "unit": defn.unit,
                "definition": defn.definition,
                "interpretation": defn.interpretation,
                "risk_note": defn.risk_note,
                "value": data.value if data else None,
                "yoy": data.yoy if data else None,
                "mom": data.mom if data else None,
                "trend_3m": data.trend_3m if data else None,
                "percentile_24m": data.percentile_24m if data else None,
                "status": data.status if data else None,
            },
            ensure_ascii=False,
        )

    @tool
    def get_matched_rules(month: str) -> str:
        """返回指定月份命中的规则列表，包含规则名、模块、严重程度、风险描述和证据文本。"""
        rows = db.scalars(
            select(RuleResult)
            .where(RuleResult.month == month, RuleResult.matched.is_(True))
            .order_by(RuleResult.rule_id)
        ).all()
        return json.dumps(
            [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "module": r.module,
                    "severity": r.severity,
                    "risk": r.evidence.get("risk"),
                    "evidence_text": r.evidence.get("evidence_text"),
                }
                for r in rows
            ],
            ensure_ascii=False,
        )

    @tool
    def get_rule_detail(rule_id: str, month: str) -> str:
        """返回指定规则在指定月份的完整执行结果，包含匹配状态、所有条件的执行日志和证据。"""
        row = db.scalar(
            select(RuleResult).where(
                RuleResult.rule_id == rule_id, RuleResult.month == month
            )
        )
        if not row:
            return json.dumps(
                {"error": f"Rule {rule_id} not found for month {month}"}, ensure_ascii=False
            )
        return json.dumps(
            {
                "rule_id": row.rule_id,
                "name": row.name,
                "module": row.module,
                "severity": row.severity,
                "matched": row.matched,
                "explanation": row.explanation,
                "evidence": row.evidence,
            },
            ensure_ascii=False,
        )

    return [
        get_available_months,
        get_cycle_snapshot,
        get_indicators,
        get_indicator_detail,
        get_matched_rules,
        get_rule_detail,
    ]


def _load_system_prompt() -> str:
    prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "agent_interpretation_prompt.md"
    return prompt_file.read_text(encoding="utf-8")


def _extract_sections(content: str) -> list[dict]:
    sections: list[dict] = []
    current_title = "回答"
    current_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_lines:
                sections.append({"title": current_title, "body": "\n".join(current_lines).strip()})
            current_title = stripped.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"title": current_title, "body": "\n".join(current_lines).strip()})
    return [s for s in sections if s["body"]][:8]


def get_agent_status() -> dict:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
    return {
        "runtime": "DeepAgent",
        "model": settings.agent_model,
        "model_calls_enabled": settings.enable_model_calls,
        "api_key_configured": bool(api_key),
        "base_url_configured": bool(base_url),
        "tools": [
            "get_available_months",
            "get_cycle_snapshot",
            "get_indicators",
            "get_indicator_detail",
            "get_matched_rules",
            "get_rule_detail",
        ],
        "skills": [p.parent.name for p in _SKILLS_DIR.glob("*/SKILL.md")],
        "fallback": "未配置密钥或模型调用失败时返回本地 mock 解读。",
    }


def generate_interpretation(
    db: Session,
    month: str | None = None,
    use_model: bool = False,
    question: str | None = None,
    conversation_id: str = "default",
    selected_context: dict | None = None,
) -> dict:
    target_month = month or db.scalar(select(IndicatorData.month).order_by(desc(IndicatorData.month)))
    if not target_month:
        return {
            "month": "",
            "mode": "mock",
            "model": None,
            "content": "当前数据不足以生成解读：没有可用的指标数据。",
            "sections": [],
        }

    evaluate_month(db, target_month)

    if use_model and settings.enable_model_calls:
        content = _run_deep_agent(db, target_month, question, conversation_id, selected_context)
        if content:
            return {
                "month": target_month,
                "mode": "deepagent",
                "model": settings.agent_model,
                "content": content,
                "sections": _extract_sections(content),
            }

    content = _render_mock(db, target_month, question)
    return {
        "month": target_month,
        "mode": "mock",
        "model": None,
        "content": content,
        "sections": _extract_sections(content),
    }


def generate_mock_interpretation(db: Session, month: str | None = None) -> dict:
    return generate_interpretation(db, month, use_model=False)


def _run_deep_agent(
    db: Session,
    month: str,
    question: str | None,
    conversation_id: str,
    selected_context: dict | None,
) -> str | None:
    try:
        from deepagents import create_deep_agent
        from deepagents.backends.state import StateBackend

        skill_files = _load_skill_files()
        skill_paths = list({f"/skills/{Path(p).parent.name}/" for p in skill_files})

        agent = create_deep_agent(
            model=_build_model(),
            tools=_build_tools(db),
            skills=skill_paths,
            system_prompt=_load_system_prompt(),
            checkpointer=_get_checkpointer(),
            backend=StateBackend(),
        )

        user_content_parts = [f"请为 {month} 生成宏观周期状态解读。"]
        if question:
            user_content_parts.append(f"用户追问：{question.strip()}")
        if selected_context:
            ctx_type = selected_context.get("type", "")
            ctx_name = selected_context.get("name", "")
            if ctx_type == "indicator":
                user_content_parts.append(f"用户关注指标：{ctx_name}")
            elif ctx_type == "rule":
                status = "命中" if selected_context.get("matched") else "未命中"
                user_content_parts.append(f"用户关注规则：{ctx_name}（{status}）")

        result = agent.invoke(
            {"messages": [{"role": "user", "content": " ".join(user_content_parts)}], "files": skill_files},
            config={"configurable": {"thread_id": conversation_id}},
        )

        messages = result.get("messages", []) if isinstance(result, dict) else []
        if not messages:
            return None
        last = messages[-1]
        return getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
    except Exception as exc:
        return f"模型调用失败，已返回错误信息供排查：{exc}"


def _render_mock(db: Session, month: str, question: str | None) -> str:
    from sqlalchemy.orm import joinedload

    snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == month))
    indicators = db.scalars(
        select(IndicatorData)
        .options(joinedload(IndicatorData.indicator))
        .where(IndicatorData.month == month)
    ).all()
    rules = db.scalars(
        select(RuleResult).where(RuleResult.month == month, RuleResult.matched.is_(True))
    ).all()

    by_code = {row.indicator.code: row for row in indicators}
    headline = snapshot.headline if snapshot else "当前数据不足以形成完整周期判断"
    rule_names = "、".join(r.name for r in rules[:3]) or "暂无关键规则命中"

    def metric(code: str, field: str) -> str:
        row = by_code.get(code)
        if not row:
            return "数据不足"
        v = getattr(row, field)
        return "数据不足" if v is None else f"{v}{row.indicator.unit}"

    lines = [
        "## 1. 本月一句话判断",
        f"{month} 判断：{headline}。M2同比 {metric('m2_yoy', 'yoy')}，社融存量同比 {metric('tsf_stock_yoy', 'yoy')}，规则命中：{rule_names}。",
        "",
        "## 2. 六大模块状态",
    ]
    modules = snapshot.modules if snapshot else {}
    for mod in ["货币", "信用", "居民", "房地产", "企业", "价格"]:
        state = modules.get(mod, {}).get("state", "数据不足")
        desc = modules.get(mod, {}).get("description", "当前数据不足以判断该模块。")
        lines += [f"### {mod}", f"- 状态：{state}", f"- 解读：{desc}", ""]

    risks = [r.evidence.get("risk") for r in rules if r.evidence.get("risk")]
    if snapshot:
        risks += snapshot.risks
    lines += ["## 4. 当前主要风险"]
    for i, risk in enumerate((risks or ["当前数据不足以识别主要风险。"])[:3], 1):
        lines.append(f"- 风险{i}：{risk}")

    if question:
        lines += ["", f"**用户追问：{question}**", "（当前为 mock 模式，以上为基于数据库的本地渲染，不是模型回答。）"]

    return "\n\n".join(lines)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/agent_service.py
git commit -m "refactor: rewrite agent_service with real DB tools, DeepAgent loop, SqliteSaver"
```

---

## Task 6: 更新 API routes，删除 history 参数

**Files:**
- Modify: `backend/app/api/routes.py`

- [ ] **Step 1: 更新 routes.py 中的 agent 端点**

在 `backend/app/api/routes.py` 中，将 `create_agent_interpretation` 函数更新为：

```python
@router.post("/agent/interpretation", response_model=AgentInterpretationRead)
def create_agent_interpretation(
    payload: AgentInterpretationRequest,
    db: Session = Depends(get_db),
):
    return generate_interpretation(
        db,
        payload.month,
        use_model=payload.use_model,
        question=payload.question,
        conversation_id=payload.conversation_id,
        selected_context=payload.selected_context,
    )
```

同时删除 routes.py 顶部 import 中的 `AgentMemory` 相关引用（如果有）。

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/routes.py
git commit -m "refactor: update agent route to remove history param"
```

---

## Task 7: 更新前端，删除 history 传参

**Files:**
- Modify: `frontend/components/HomeChat.tsx`

- [ ] **Step 1: 删除 HomeChat 中的 history 传参**

在 `frontend/components/HomeChat.tsx` 中，找到 fetch body 中的 `history` 字段（第 90-93 行附近）：

```typescript
body: JSON.stringify({
  month,
  question,
  use_model: true,
  conversation_id: `macro-cycle-radar:${month}`,
  selected_context: selectedContext,
  history: nextMessages.slice(-8).map((message) => ({
    role: message.role,
    content: message.content,
  })),
}),
```

删除 `history` 字段，改为：

```typescript
body: JSON.stringify({
  month,
  question,
  use_model: true,
  conversation_id: `macro-cycle-radar:${month}`,
  selected_context: selectedContext,
}),
```

- [ ] **Step 2: 更新 ChatMessage 类型，删除不再使用的字段**

将文件顶部的 `ChatMessage` 类型从：

```typescript
type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  skill?: string | null;
  contextSummary?: string | null;
  steps?: string[];
  sections?: Array<{ title: string; body: string }>;
};
```

改为：

```typescript
type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sections?: Array<{ title: string; body: string }>;
};
```

- [ ] **Step 3: 删除 ChatMessage 渲染中已不存在的字段**

在 `HomeChat.tsx` 的消息渲染部分（`chat-messages` div 内），删除以下已不存在字段的渲染块：

```tsx
// 删除这一块 agent-meta
{message.role === "assistant" && (message.intent || message.skill) ? (
  <div className="agent-meta">
    {message.intent ? <span>{message.intent}</span> : null}
    {message.skill ? <span>{message.skill}</span> : null}
  </div>
) : null}

// 删除 agent-context
{message.role === "assistant" && message.contextSummary ? (
  <div className="agent-context">{message.contextSummary}</div>
) : null}

// 删除 agent-steps
{message.role === "assistant" && message.steps?.length ? (
  <div className="agent-steps">
    {message.steps.map((step) => (
      <span key={step}>{step}</span>
    ))}
  </div>
) : null}
```

同时更新 setMessages 中 assistant 消息的赋值，删除 intent/skill/contextSummary/steps 字段：

```typescript
setMessages((items) => [
  ...items,
  {
    role: "assistant",
    content: data.content,
    sections: data.sections,
  },
]);
```

- [ ] **Step 4: 更新初始消息，删除 intent/skill/contextSummary**

将 `useState` 初始值中的 assistant 消息改为：

```typescript
const [messages, setMessages] = useState<ChatMessage[]>([
  {
    role: "assistant",
    content: `已加载 ${month} 的指标、规则和周期快照。\n你可以继续追问，例如"为什么说信用偏弱？"或"下个月重点看什么？"。`,
  },
]);
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/HomeChat.tsx
git commit -m "refactor: remove history/intent/skill fields from HomeChat"
```

---

## Task 8: 更新 pyproject.toml，补充依赖声明

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 添加 langgraph-checkpoint-sqlite**

在 `backend/pyproject.toml` 的 `dependencies` 列表中添加：

```toml
"langgraph-checkpoint-sqlite>=3.1.0",
```

- [ ] **Step 2: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add langgraph-checkpoint-sqlite to dependencies"
```

---

## Task 9: 更新测试

**Files:**
- Modify: `backend/tests/test_cycle_flow.py`

- [ ] **Step 1: 更新 test_agent_mock_interpretation_uses_seed_data**

在 `backend/tests/test_cycle_flow.py` 中，将 Agent 相关测试替换为：

```python
def test_agent_mock_interpretation_uses_seed_data():
    db = make_session()
    seed_database(db)

    result = generate_mock_interpretation(db)

    assert result["month"]
    assert result["mode"] == "mock"
    assert "## 1. 本月一句话判断" in result["content"]
    assert isinstance(result["sections"], list)


def test_agent_status_exposes_runtime_and_tools():
    status = get_agent_status()
    assert status["runtime"] == "DeepAgent"
    expected_tools = {
        "get_available_months",
        "get_cycle_snapshot",
        "get_indicators",
        "get_indicator_detail",
        "get_matched_rules",
        "get_rule_detail",
    }
    assert set(status["tools"]) == expected_tools
    assert "skills" in status
```

- [ ] **Step 2: 更新 import**

将测试文件顶部的 import 从：

```python
from app.services.agent_service import AGENT_TOOL_NAMES, generate_mock_interpretation, get_agent_status
```

改为：

```python
from app.services.agent_service import generate_mock_interpretation, get_agent_status
```

- [ ] **Step 3: 运行测试套件**

```bash
cd backend && uv run pytest tests/ -v 2>&1
```

期望：所有测试 PASS，无 import error，无 `AGENT_TOOL_NAMES` 引用错误。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_cycle_flow.py
git commit -m "test: update agent tests for new tool names and schema"
```

---

## Task 10: 端到端验证

- [ ] **Step 1: 启动后端，验证服务正常**

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000 2>&1 &
sleep 3
curl -s http://localhost:8000/api/agent/status | python3 -m json.tool
```

期望输出包含：
```json
{
  "runtime": "DeepAgent",
  "tools": ["get_available_months", "get_cycle_snapshot", ...],
  "skills": ["cycle-summary", "rule-diagnosis", ...]
}
```

- [ ] **Step 2: 验证 mock 模式**

```bash
curl -s -X POST http://localhost:8000/api/agent/interpretation \
  -H "Content-Type: application/json" \
  -d '{"use_model": false, "conversation_id": "test-1"}' | python3 -m json.tool
```

期望：`mode: "mock"`，`content` 包含 `## 1. 本月一句话判断`，`sections` 是数组。

- [ ] **Step 3: 验证多轮持久化（mock 模式）**

```bash
# 第一轮
curl -s -X POST http://localhost:8000/api/agent/interpretation \
  -H "Content-Type: application/json" \
  -d '{"use_model": false, "question": "信用状态如何？", "conversation_id": "test-thread-1"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['mode'], len(d['content']))"

# 第二轮（同一 thread_id）
curl -s -X POST http://localhost:8000/api/agent/interpretation \
  -H "Content-Type: application/json" \
  -d '{"use_model": false, "question": "上面说的风险具体是什么？", "conversation_id": "test-thread-1"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['mode'], len(d['content']))"
```

期望：两轮都返回 200，无 500 错误。

- [ ] **Step 4: 最终 commit**

```bash
git add -A
git commit -m "feat: complete agent refactor with real tools, DeepAgent loop, SqliteSaver persistence"
```
