import json
import os
import re
import sqlite3 as _sqlite3
from pathlib import Path

from deepagents.backends.state import create_file_data
from langchain_core.messages import HumanMessage, SystemMessage
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


def _load_skill_files() -> dict[str, object]:
    files: dict[str, object] = {}
    for skill_md in _SKILLS_DIR.glob("*/SKILL.md"):
        skill_name = skill_md.parent.name
        path = f"/skills/{skill_name}/SKILL.md"
        files[path] = create_file_data(skill_md.read_text(encoding="utf-8"))
    return files


def _build_model() -> ChatOpenAI:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
    model_name = settings.agent_model.removeprefix("openai:")
    extra_body = {"enable_thinking": False}
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        streaming=True,
        extra_body=extra_body,
    )


def _build_tools(db: Session):
    from langchain_core.tools import tool

    from app.core.database import SessionLocal

    def _db():
        return SessionLocal()

    @tool
    def get_available_months() -> str:
        """返回数据库中有指标数据的所有月份列表（降序）。"""
        with _db() as session:
            months = session.scalars(
                select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))
            ).all()
            return json.dumps(list(months), ensure_ascii=False)

    @tool
    def get_cycle_snapshot(month: str) -> str:
        """返回指定月份的周期状态快照，包含 headline、六大模块状态、风险列表和观察任务。"""
        with _db() as session:
            evaluate_month(session, month)
            snapshot = session.scalar(select(CycleSnapshot).where(CycleSnapshot.month == month))
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
        with _db() as session:
            stmt = (
                select(IndicatorData)
                .options(joinedload(IndicatorData.indicator))
                .where(IndicatorData.month == month)
                .order_by(IndicatorData.indicator_id)
            )
            rows = session.scalars(stmt).all()
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
        with _db() as session:
            defn = session.scalar(select(IndicatorDefinition).where(IndicatorDefinition.code == code))
            if not defn:
                return json.dumps({"error": f"Unknown indicator code: {code}"}, ensure_ascii=False)
            data = session.scalar(
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
        with _db() as session:
            rows = session.scalars(
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
        with _db() as session:
            row = session.scalar(
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

    _navigate_month: list[str] = []

    @tool
    def navigate_to_month(month: str) -> str:
        """切换右侧数据面板到指定月份（格式 YYYY-MM）。当用户说"查看 X 月数据"或"切换到 X 月"时调用此工具。调用后在回复中告知用户已切换。"""
        import re
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            return json.dumps({"error": f"月份格式错误，应为 YYYY-MM，收到：{month}"}, ensure_ascii=False)
        available = db.scalars(
            select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))
        ).all()
        if month not in available:
            return json.dumps({"error": f"{month} 无数据，可用月份：{list(available)}"}, ensure_ascii=False)
        _navigate_month.append(month)
        return json.dumps({"navigated": month, "message": f"已切换到 {month}"}, ensure_ascii=False)

    return [
        get_available_months,
        get_cycle_snapshot,
        get_indicators,
        get_indicator_detail,
        get_matched_rules,
        get_rule_detail,
        navigate_to_month,
    ], _navigate_month


def _load_system_prompt() -> str:
    prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "AGENT.md"
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
            "navigate_to_month",
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
    data_view_response = build_data_view_response(db, question)
    if data_view_response:
        return data_view_response

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
        content, navigate_month, error = _run_deep_agent(
            db, target_month, question, conversation_id, selected_context
        )
        if content:
            return {
                "month": target_month,
                "mode": "deepagent",
                "model": settings.agent_model,
                "content": content,
                "sections": _extract_sections(content),
                "navigate_month": navigate_month,
            }
        if error:
            content = _render_mock(db, target_month, question)
            content = "\n\n".join(
                [
                    content,
                    "## Agent 状态",
                    f"模型调用失败，已回退到本地 mock 解读。错误信息：{error}",
                ]
            )
            return {
                "month": target_month,
                "mode": "mock",
                "model": None,
                "content": content,
                "sections": _extract_sections(content),
                "navigate_month": None,
            }

    content = _render_mock(db, target_month, question)
    return {
        "month": target_month,
        "mode": "mock",
        "model": None,
        "content": content,
        "sections": _extract_sections(content),
        "navigate_month": None,
    }


def generate_mock_interpretation(db: Session, month: str | None = None) -> dict:
    return generate_interpretation(db, month, use_model=False)


def build_data_view_response(db: Session, question: str | None) -> dict | None:
    target_month = _parse_data_view_month(question)
    if not target_month:
        return None
    available_months = db.scalars(
        select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))
    ).all()
    if not available_months:
        return {
            "month": "",
            "mode": "mock",
            "model": None,
            "content": "当前数据不足以切换：没有可用的指标数据。",
            "sections": [],
            "navigate_month": None,
        }
    if target_month == "latest":
        target_month = available_months[0]
        label = f"最新月份 {target_month}"
    else:
        label = f"{target_month}"
    if target_month not in available_months:
        content = "\n".join(
            [
                "- [x] 检查可用月份",
                f"- [ ] 切换到 {target_month}",
                "",
                f"未找到 {target_month} 的数据。可选范围：{available_months[-1]} 至 {available_months[0]}。",
            ]
        )
        return {
            "month": target_month,
            "mode": "mock",
            "model": None,
            "content": content,
            "sections": _extract_sections(content),
            "navigate_month": None,
        }

    evaluate_month(db, target_month)
    snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == target_month))
    headline = snapshot.headline if snapshot else "当前数据不足以形成完整周期判断"
    content = "\n".join(
        [
            "- [x] 检查可用月份",
            f"- [x] 切换右侧数据区到 {target_month}",
            "- [x] 读取当月状态摘要",
            "",
            f"已切换到 {label}。当月判断：{headline}。",
        ]
    )
    return {
        "month": target_month,
        "mode": "mock",
        "model": None,
        "content": content,
        "sections": _extract_sections(content),
        "navigate_month": target_month,
    }


def _parse_data_view_month(question: str | None) -> str | None:
    if not question:
        return None
    text = question.strip()
    if re.search(r"(分析|解读|判断|风险|为什么|怎么看|如何)", text):
        return None
    has_view_intent = bool(re.search(r"(看|查看|打开|切换|给我|我要|数据)", text))
    if not has_view_intent:
        return None
    if "最新" in text:
        return "latest"

    year_month_match = re.search(r"(?P<year>\d{2,4})\s*年\s*(?P<month>\d{1,2})\s*月", text)
    if not year_month_match:
        year_month_match = re.search(r"(?P<year>\d{2,4})[-/.](?P<month>\d{1,2})", text)
    if not year_month_match:
        return None

    year = int(year_month_match.group("year"))
    month = int(year_month_match.group("month"))
    if year < 100:
        year += 2000
    if month < 1 or month > 12:
        return None
    return f"{year:04d}-{month:02d}"


def _run_deep_agent(
    db: Session,
    month: str,
    question: str | None,
    conversation_id: str,
    selected_context: dict | None,
) -> tuple[str | None, str | None, str | None]:
    try:
        agent, skill_files, navigate_month_ref = _create_agent_runtime(db)

        result = agent.invoke(
            {
                "messages": [{"role": "user", "content": _build_user_content(month, question, selected_context)}],
                "files": skill_files,
            },
            config={"configurable": {"thread_id": conversation_id}},
        )

        messages = result.get("messages", []) if isinstance(result, dict) else []
        if not messages:
            return None, None, None
        last = messages[-1]
        content = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
        navigate_month = navigate_month_ref[-1] if navigate_month_ref else None
        return content, navigate_month, None
    except Exception as exc:
        return None, None, str(exc)


def stream_deep_agent_deltas(
    db: Session,
    month: str,
    question: str | None,
    conversation_id: str,
    selected_context: dict | None,
):
    agent, skill_files, navigate_month_ref = _create_agent_runtime(db)
    stream_input = {
        "messages": [{"role": "user", "content": _build_user_content(month, question, selected_context)}],
        "files": skill_files,
    }
    config = {"configurable": {"thread_id": conversation_id}}
    for item in agent.stream(stream_input, config=config, stream_mode="messages"):
        message = item[0] if isinstance(item, tuple) else item
        message_class = type(message).__name__
        message_type = getattr(message, "type", "")
        if "AIMessage" not in message_class and message_type not in {"ai", "ai_chunk"}:
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str) and content:
            yield {"type": "delta", "text": content}
        elif isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"}:
                    text_parts.append(str(part.get("text", "")))
            if text_parts:
                yield {"type": "delta", "text": "".join(text_parts)}
    if navigate_month_ref:
        yield {"type": "action", "action": {"type": "navigate_month", "month": navigate_month_ref[-1]}}


def should_use_direct_stream() -> bool:
    return "deepseek" in settings.agent_model.lower()


def stream_direct_agent_deltas(
    db: Session,
    month: str,
    question: str | None,
    selected_context: dict | None,
):
    target_month = month or db.scalar(select(IndicatorData.month).order_by(desc(IndicatorData.month)))
    if not target_month:
        yield {"type": "delta", "text": "当前没有可用数据，无法判断。"}
        return

    evaluate_month(db, target_month)
    snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == target_month))
    matched_rules = db.scalars(
        select(RuleResult).where(RuleResult.month == target_month, RuleResult.matched.is_(True))
    ).all()
    indicator_detail = _resolve_indicator_context(db, target_month, question, selected_context)
    context = {
        "month": target_month,
        "snapshot": {
            "headline": snapshot.headline if snapshot else None,
            "summary": snapshot.summary if snapshot else None,
            "modules": snapshot.modules if snapshot else {},
            "risks": snapshot.risks if snapshot else [],
            "watch_tasks": snapshot.watch_tasks if snapshot else [],
        },
        "matched_rules": [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "module": rule.module,
                "severity": rule.severity,
                "risk": rule.evidence.get("risk"),
                "evidence_text": rule.evidence.get("evidence_text"),
            }
            for rule in matched_rules
        ],
        "selected_indicator": indicator_detail,
        "selected_context": selected_context,
    }
    system = SystemMessage(
        content=(
            "你是 SquirrelRadar Agent。只基于用户给定上下文回答。"
            "不要输出 Markdown 表格，不要输出完整核心指标清单。"
            "用简洁中文、短段落和项目符号回答。"
            "如果解释单个指标，先说明它对本月周期判断的影响，再给关键依据。"
        )
    )
    human = HumanMessage(
        content=(
            f"用户请求：{question or '解释当前月份状态'}\n\n"
            f"数据上下文：{json.dumps(context, ensure_ascii=False, default=str)}"
        )
    )
    for chunk in _build_model().stream([system, human]):
        content = getattr(chunk, "content", None)
        if isinstance(content, str) and content:
            yield {"type": "delta", "text": content}
        elif isinstance(content, list):
            text = "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
            )
            if text:
                yield {"type": "delta", "text": text}


def _resolve_indicator_context(
    db: Session,
    month: str,
    question: str | None,
    selected_context: dict | None,
) -> dict | None:
    code = selected_context.get("code") if selected_context else None
    indicators = db.scalars(select(IndicatorDefinition).order_by(IndicatorDefinition.importance.desc())).all()
    if not code and question:
        for indicator in indicators:
            if indicator.code in question or indicator.name in question:
                code = indicator.code
                break
    if not code:
        return None
    defn = db.scalar(select(IndicatorDefinition).where(IndicatorDefinition.code == code))
    if not defn:
        return None
    data = db.scalar(
        select(IndicatorData).where(IndicatorData.indicator_id == defn.id, IndicatorData.month == month)
    )
    return {
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
    }


def _create_agent_runtime(db: Session):
    from deepagents import create_deep_agent
    from deepagents.backends.state import StateBackend

    skill_files = _load_skill_files()
    skill_paths = list({f"/skills/{Path(p).parent.name}/" for p in skill_files})
    tools, navigate_month_ref = _build_tools(db)
    agent = create_deep_agent(
        model=_build_model(),
        tools=tools,
        skills=skill_paths,
        system_prompt=_load_system_prompt(),
        checkpointer=_get_checkpointer(),
        backend=StateBackend(),
    )
    return agent, skill_files, navigate_month_ref


def _build_user_content(month: str, question: str | None, selected_context: dict | None) -> str:
    user_content_parts = [f"当前右侧仪表盘月份：{month}。"]
    if question:
        user_content_parts.append(f"用户请求：{question.strip()}")
    else:
        user_content_parts.append(f"用户请求：请为 {month} 生成宏观周期状态解读。")
    if selected_context:
        context_json = json.dumps(selected_context, ensure_ascii=False, default=str)
        user_content_parts.append(
            "用户从右侧内容区选中的上下文如下；如果包含 code 或 rule_id，"
            f"优先用它定位工具参数：{context_json}"
        )
    return " ".join(user_content_parts)


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
