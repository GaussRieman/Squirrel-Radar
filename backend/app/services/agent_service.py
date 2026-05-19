import json
import os
from pathlib import Path

import yaml
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.domain import AgentMemory, CycleSnapshot, IndicatorData, RuleResult
from app.services.prompt_service import load_agent_interpretation_prompt
from app.services.rule_engine import evaluate_month


def generate_interpretation(
    db: Session,
    month: str | None = None,
    use_model: bool = False,
    question: str | None = None,
    conversation_id: str = "default",
    history: list[dict] | None = None,
    selected_context: dict | None = None,
) -> dict:
    agent_context = _prepare_agent_context(db, question, conversation_id, history or [], selected_context)
    target_month = month or db.scalar(select(IndicatorData.month).order_by(desc(IndicatorData.month)))
    if not target_month:
        return {
            "month": "",
            "prompt_version": "agent_interpretation_prompt.md",
            "mode": "mock",
            "model": None,
            "tools": AGENT_TOOL_NAMES,
            "intent": agent_context["intent"],
            "skill": agent_context["skill"]["name"],
            "context_summary": agent_context["context_summary"],
            "steps": agent_context["steps"],
            "sections": [],
            "content": "当前数据不足以生成解读：没有可用的指标数据。",
        }

    evaluate_month(db, target_month)
    snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == target_month))
    indicators = db.scalars(
        select(IndicatorData)
        .options(joinedload(IndicatorData.indicator))
        .where(IndicatorData.month == target_month)
        .order_by(IndicatorData.indicator_id)
    ).all()
    rules = db.scalars(
        select(RuleResult).where(RuleResult.month == target_month).order_by(RuleResult.rule_id)
    ).all()

    by_code = {row.indicator.code: row for row in indicators}
    matched_rules = [rule for rule in rules if rule.matched]
    prompt = load_agent_interpretation_prompt()
    input_payload = _build_agent_input(target_month, indicators, rules, snapshot, agent_context)

    if use_model and settings.enable_model_calls:
        content = _call_deep_agent(prompt, input_payload, question, agent_context)
        if content:
            _remember_turn(db, conversation_id, target_month, question, content, agent_context)
            return {
                "month": target_month,
                "prompt_version": "agent_interpretation_prompt.md",
                "prompt_excerpt": prompt[:320],
                "mode": "deepagent",
                "model": settings.agent_model,
                "tools": AGENT_TOOL_NAMES,
                "intent": agent_context["intent"],
                "skill": agent_context["skill"]["name"],
                "context_summary": agent_context["context_summary"],
                "steps": agent_context["steps"],
                "sections": _extract_sections(content),
                "content": content,
            }

    content = _render_markdown(target_month, snapshot, by_code, matched_rules, question)
    _remember_turn(db, conversation_id, target_month, question, content, agent_context)
    return {
        "month": target_month,
        "prompt_version": "agent_interpretation_prompt.md",
        "prompt_excerpt": prompt[:320],
        "mode": "mock",
        "model": settings.agent_model if use_model else None,
        "tools": AGENT_TOOL_NAMES,
        "intent": agent_context["intent"],
        "skill": agent_context["skill"]["name"],
        "context_summary": agent_context["context_summary"],
        "steps": agent_context["steps"],
        "sections": _extract_sections(content),
        "content": content,
    }


def generate_mock_interpretation(db: Session, month: str | None = None) -> dict:
    return generate_interpretation(db, month, use_model=False)


AGENT_TOOL_NAMES = [
    "get_indicator_data",
    "get_matched_rules",
    "get_cycle_snapshot",
    "get_rule_execution_logs",
    "get_agent_context",
    "get_memory",
]

INTENT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "agent_intents.yaml"


def get_agent_status() -> dict:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
    return {
        "runtime": "DeepAgent",
        "model": settings.agent_model,
        "model_calls_enabled": settings.enable_model_calls,
        "api_key_configured": bool(api_key),
        "base_url_configured": bool(base_url),
        "tools": AGENT_TOOL_NAMES,
        "fallback": "未配置密钥或模型调用失败时返回本地 mock 解读。",
    }


def _prepare_agent_context(
    db: Session,
    question: str | None,
    conversation_id: str,
    history: list[dict],
    selected_context: dict | None,
) -> dict:
    catalog = _load_intent_catalog()
    intent_config = _detect_intent(question or "", catalog)
    memory = _load_memory(db, conversation_id)
    history_summary = _summarize_history(history)
    memory_summary = _summarize_memory(memory)
    selected_summary = _summarize_selected_context(selected_context)
    context_summary = "；".join(
        item
        for item in [
            f"意图：{intent_config['intent']}",
            f"技能：{intent_config['skill']}",
            selected_summary,
            history_summary,
            memory_summary,
        ]
        if item
    )
    return {
        "intent": intent_config["intent"],
        "skill": {
            "name": intent_config["skill"],
            "instruction": intent_config["instruction"],
        },
        "steps": intent_config.get("steps", []),
        "conversation_id": conversation_id,
        "history": history[-6:],
        "memory": memory[-6:],
        "selected_context": selected_context or {},
        "context_summary": context_summary,
    }


def _load_intent_catalog() -> list[dict]:
    payload = yaml.safe_load(INTENT_FILE.read_text(encoding="utf-8"))
    return payload.get("intents", [])


def _detect_intent(question: str, catalog: list[dict]) -> dict:
    text = question.lower()
    fallback = catalog[-1]
    for item in catalog:
        keywords = item.get("keywords") or []
        if keywords and any(keyword.lower() in text for keyword in keywords):
            return item
    return fallback


def _summarize_history(history: list[dict]) -> str:
    if not history:
        return ""
    latest = history[-3:]
    turns = [f"{item.get('role', 'unknown')}:{str(item.get('content', ''))[:40]}" for item in latest]
    return "前端上下文：" + " | ".join(turns)


def _summarize_memory(memory: list[dict]) -> str:
    if not memory:
        return ""
    latest = memory[-3:]
    turns = [f"{item.get('intent')}:{str(item.get('question', ''))[:36]}" for item in latest]
    return "历史记忆：" + " | ".join(turns)


def _summarize_selected_context(selected_context: dict | None) -> str:
    if not selected_context:
        return ""
    context_type = selected_context.get("type")
    name = selected_context.get("name") or selected_context.get("title")
    if context_type == "indicator":
        return f"选中指标：{name}"
    if context_type == "rule":
        status = "命中" if selected_context.get("matched") else "未命中"
        return f"选中规则：{name}（{status}）"
    return f"选中上下文：{name or context_type}"


def _load_memory(db: Session, conversation_id: str) -> list[dict]:
    rows = db.scalars(
        select(AgentMemory)
        .where(AgentMemory.conversation_id == conversation_id)
        .order_by(desc(AgentMemory.id))
        .limit(20)
    ).all()
    return [
        {
            "question": row.question,
            "answer_excerpt": row.answer_excerpt,
            "intent": row.intent,
            "skill": row.skill,
            "context": row.context,
        }
        for row in reversed(rows)
    ]


def _remember_turn(
    db: Session,
    conversation_id: str,
    month: str,
    question: str | None,
    answer: str,
    agent_context: dict,
) -> None:
    if not question:
        return
    db.add(
        AgentMemory(
            conversation_id=conversation_id,
            month=month,
            question=question[:1000],
            answer_excerpt=answer[:1000],
            intent=agent_context["intent"],
            skill=agent_context["skill"]["name"],
            context=agent_context.get("selected_context") or {},
        )
    )
    db.commit()


def _call_deep_agent(
    prompt: str,
    input_payload: dict,
    question: str | None = None,
    agent_context: dict | None = None,
) -> str | None:
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    os.environ["OPENAI_API_KEY"] = api_key
    base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
    try:
        from deepagents import create_deep_agent

        tools = _build_agent_tools(input_payload)
        agent = create_deep_agent(
            model=_build_chat_model(api_key, base_url),
            system_prompt=(
                prompt
                + "\n\n## 当前技能\n"
                + input_payload["agent_context"]["skill"]["instruction"]
                + "\n\n## Agent 工作流\n"
                "1. 先调用 get_agent_context 读取意图、技能、前端上下文和记忆。\n"
                "2. 再按意图选择工具：数据解释用 get_indicator_data；规则诊断用 get_rule_execution_logs；周期总结用 get_cycle_snapshot 和 get_matched_rules。\n"
                "3. 回答必须引用工具返回的数据，不要脱离数据发挥。\n"
                + "\n\n你拥有以下工具读取输入上下文。生成最终解读前，必须至少调用："
                "get_agent_context，以及 get_indicator_data、get_matched_rules、get_cycle_snapshot 中至少一个。"
                "需要解释规则依据时调用 get_rule_execution_logs。"
            ),
            tools=tools,
        )
        user_question = question.strip() if question else ""
        question_text = f"用户追问：{user_question}。" if user_question else ""
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"请为 {input_payload['month']} 生成宏观周期状态解读。"
                            f"{question_text}"
                            f"当前识别意图：{input_payload['agent_context']['intent']}。"
                            "不要直接猜测数据，先使用工具读取指标、规则和快照。"
                            "必须遵守系统提示词的输出结构和安全约束。"
                        ),
                    }
                ]
            }
        )
        messages = result.get("messages", []) if isinstance(result, dict) else []
        if not messages:
            return None
        last = messages[-1]
        return getattr(last, "content", None) or last.get("content")
    except Exception as exc:
        return f"模型调用失败，已返回错误信息供排查：{exc}"


def _build_chat_model(api_key: str, base_url: str | None):
    from langchain_openai import ChatOpenAI

    model_name = settings.agent_model.removeprefix("openai:")
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
    )


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
    return [section for section in sections if section["body"]][:8]


def _build_agent_tools(input_payload: dict):
    from langchain_core.tools import tool

    @tool
    def get_agent_context() -> str:
        """返回当前会话的意图、技能、前端上下文和历史记忆摘要。"""
        return json.dumps(input_payload["agent_context"], ensure_ascii=False)

    @tool
    def get_memory() -> str:
        """返回当前会话最近的历史记忆，用于保持多轮追问的一致性。"""
        return json.dumps(input_payload["agent_context"]["memory"], ensure_ascii=False)

    @tool
    def get_indicator_data() -> str:
        """返回当前月份的全部宏观指标数据，包含value、yoy、mom、trend_3m、percentile_24m和status。"""
        return json.dumps(input_payload["indicator_data"], ensure_ascii=False)

    @tool
    def get_matched_rules() -> str:
        """返回当前月份已经命中的规则结果、风险和证据文本。"""
        matched = [rule for rule in input_payload["rule_results"] if rule["matched"]]
        return json.dumps(matched, ensure_ascii=False)

    @tool
    def get_cycle_snapshot() -> str:
        """返回当前月份周期状态快照，包含headline、六大模块、风险和观察任务。"""
        return json.dumps(input_payload["cycle_snapshot"], ensure_ascii=False)

    @tool
    def get_rule_execution_logs() -> str:
        """返回全部规则评估结果，用于解释某条规则为什么命中或未命中。"""
        return json.dumps(input_payload["rule_results"], ensure_ascii=False)

    return [
        get_agent_context,
        get_memory,
        get_indicator_data,
        get_matched_rules,
        get_cycle_snapshot,
        get_rule_execution_logs,
    ]


def _build_agent_input(
    month: str,
    indicators: list[IndicatorData],
    rules: list[RuleResult],
    snapshot: CycleSnapshot | None,
    agent_context: dict,
) -> dict:
    return {
        "month": month,
        "agent_context": agent_context,
        "indicator_data": [
            {
                "indicator_id": row.indicator.code,
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
            for row in indicators
        ],
        "rule_results": [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "category": rule.module,
                "matched": rule.matched,
                "severity": rule.severity,
                "risk": rule.evidence.get("risk"),
                "evidence_text": rule.evidence.get("evidence_text"),
                "triggered_status": rule.evidence.get("triggered_status"),
                "execution_log": rule.evidence.get("execution_log"),
            }
            for rule in rules
        ],
        "cycle_snapshot": {
            "headline": snapshot.headline if snapshot else None,
            "modules": snapshot.modules if snapshot else {},
            "risks": snapshot.risks if snapshot else [],
            "watch_tasks": snapshot.watch_tasks if snapshot else [],
        },
    }


def _render_markdown(
    month: str,
    snapshot: CycleSnapshot | None,
    by_code: dict[str, IndicatorData],
    matched_rules: list[RuleResult],
    question: str | None = None,
) -> str:
    headline = snapshot.headline if snapshot else "当前数据不足以形成完整周期判断"
    rule_names = "、".join(rule.name for rule in matched_rules[:3]) or "暂无关键规则命中"
    m2 = _metric(by_code, "m2_yoy", "yoy")
    tsf = _metric(by_code, "tsf_stock_yoy", "yoy")

    sections = [
        "## 1. 本月一句话判断",
        f"{month} 的一句话判断：{headline}。依据是 M2同比为 {m2}，社融存量同比为 {tsf}，规则侧命中：{rule_names}。",
    ]
    if question:
        sections.extend(
            [
                "",
                f"用户追问：{question}",
                "以下回答仍以当前月份指标数据、规则命中和周期快照为依据。",
            ]
        )
    sections.extend(
        [
            "",
            "## 2. 六大模块状态",
        ]
    )

    module_guides = {
        "货币": ["m2_yoy"],
        "信用": ["tsf_stock_yoy", "new_rmb_loan", "household_mid_long_loan", "enterprise_mid_long_loan"],
        "居民": ["household_mid_long_loan", "wage_income", "core_cpi"],
        "房地产": ["secondhand_home_price_mom_70c", "commodity_house_sales_area", "household_mid_long_loan"],
        "企业": ["enterprise_mid_long_loan", "private_investment", "industrial_profit", "ppi"],
        "价格": ["core_cpi", "ppi"],
    }
    modules = snapshot.modules if snapshot else {}
    for module, codes in module_guides.items():
        state = modules.get(module, {}).get("state", "数据不足")
        description = modules.get(module, {}).get("description", "当前数据不足以判断该模块。")
        evidence = "；".join(_indicator_summary(by_code, code) for code in codes if code in by_code)
        evidence = evidence or "该模块关键指标缺失。"
        sections.extend(
            [
                f"### {module}",
                f"- 状态：{state}",
                f"- 依据：{evidence}",
                f"- 解读：{description}",
                "",
            ]
        )

    changes = _top_changes(by_code, matched_rules)
    sections.extend(["## 3. 本月最重要的3个变化", *changes, ""])

    risks = [rule.evidence.get("risk") for rule in matched_rules if rule.evidence.get("risk")]
    if snapshot:
        risks.extend(snapshot.risks)
    sections.extend(["## 4. 当前主要风险"])
    for idx, risk in enumerate((risks or ["当前数据不足以识别主要风险。"])[:3], 1):
        sections.append(f"- 风险{idx}：{risk}")
    sections.append("")

    watch_tasks = snapshot.watch_tasks if snapshot else []
    if not watch_tasks:
        watch_tasks = [
            "观察社融存量同比能否改善，以确认信用修复。",
            "观察居民中长期贷款，以确认居民部门是否从防御转向修复。",
            "观察商品房销售面积和二手房价格，以确认房地产是否企稳。",
            "观察PPI和工业企业利润，以确认企业盈利环境。",
        ]
    sections.extend(["## 5. 下个月重点观察指标"])
    for task in watch_tasks[:4]:
        sections.append(f"- {task}")
    sections.append("")

    sections.extend(
        [
            "## 6. 对普通家庭资产配置的含义",
            "当前解读只说明宏观环境含义，不提供具体投资建议。若居民收入、贷款和房地产数据仍偏弱，普通家庭更需要关注现金流稳定性、负债压力和大额支出的可承受性；若这些指标连续改善，则说明家庭部门信心可能在修复。",
            "",
            "## 7. 对企业经营决策的含义",
            "当前解读只说明经营环境含义，不提供证券或商品建议。企业应重点观察需求、价格和利润是否同步改善：若民间投资、PPI和工业企业利润仍弱，经营决策宜重视现金流和库存纪律；若三者同步改善，扩张和用工决策的宏观约束会有所减轻。",
        ]
    )
    return "\n\n".join(sections)


def _metric(by_code: dict[str, IndicatorData], code: str, field: str) -> str:
    row = by_code.get(code)
    if not row:
        return "数据不足"
    value = getattr(row, field)
    return "数据不足" if value is None else f"{value}{row.indicator.unit}"


def _indicator_summary(by_code: dict[str, IndicatorData], code: str) -> str:
    row = by_code[code]
    yoy = "-" if row.yoy is None else f"{row.yoy}{row.indicator.unit}"
    mom = "-" if row.mom is None else f"{row.mom}{row.indicator.unit}"
    return f"{row.indicator.name}同比 {yoy}、环比 {mom}、24月分位 {row.percentile_24m}%"


def _top_changes(by_code: dict[str, IndicatorData], matched_rules: list[RuleResult]) -> list[str]:
    changes = [
        f"1. 规则信号：本月命中 {len(matched_rules)} 条规则，重点包括 {('、'.join(rule.name for rule in matched_rules[:3]) or '暂无关键规则命中')}，说明状态判断主要来自规则系统而非主观描述。",
        f"2. 信用线索：M2同比为 {_metric(by_code, 'm2_yoy', 'yoy')}，社融存量同比为 {_metric(by_code, 'tsf_stock_yoy', 'yoy')}，两者关系决定宽货币能否传导到实体融资。",
        f"3. 需求线索：核心CPI为 {_metric(by_code, 'core_cpi', 'yoy')}，PPI为 {_metric(by_code, 'ppi', 'yoy')}，价格指标用于判断内需和工业品需求温度。",
    ]
    return changes
