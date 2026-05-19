import json
import os
import sqlite3 as _sqlite3
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
_checkpointer: SqliteSaver | None = None


def _get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        conn = _sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        _checkpointer.setup()
    return _checkpointer


def _load_skill_files() -> dict[str, bytes]:
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
            select(IndicatorData).where(
                IndicatorData.indicator_id == defn.id, IndicatorData.month == month
            )
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
            {
                "messages": [{"role": "user", "content": " ".join(user_content_parts)}],
                "files": skill_files,
            },
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
        lines += [
            "",
            f"**用户追问：{question}**",
            "（当前为 mock 模式，以上为基于数据库的本地渲染，不是模型回答。）",
        ]

    return "\n\n".join(lines)
