from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.domain import CycleSnapshot, IndicatorData, RuleResult

RULE_FILE = Path(__file__).resolve().parents[1] / "seeds" / "rules.seed.yaml"
ALLOWED_RULE_FIELDS = {"value", "yoy", "mom", "trend_3m", "percentile_24m"}
ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=="}


def load_rule_catalog() -> dict[str, Any]:
    payload = yaml.safe_load(RULE_FILE.read_text(encoding="utf-8"))
    for rule in payload["rules"]:
        _validate_rule(rule)
    return payload


def load_rules() -> list[dict[str, Any]]:
    payload = load_rule_catalog()
    return payload["rules"]


def _compare(left: float | None, op: str, right: float) -> bool:
    if left is None:
        return False
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == "==":
        return left == right
    raise ValueError(f"Unsupported operator: {op}")


def evaluate_month(
    db: Session,
    month: str,
    retry_on_integrity: bool = True,
) -> tuple[list[RuleResult], CycleSnapshot]:
    rows = db.scalars(
        select(IndicatorData)
        .options(joinedload(IndicatorData.indicator))
        .where(IndicatorData.month == month)
    ).all()
    by_code = {row.indicator.code: row for row in rows}
    results: list[RuleResult] = []

    for rule in load_rules():
        evidence = {}
        execution_log = []
        condition_results = []
        for condition in rule["conditions"]:
            row = by_code.get(condition["indicator"])
            actual = getattr(row, condition["field"], None) if row else None
            operator = condition["operator"]
            ok = _compare(actual, operator, condition["value"])
            evidence[condition["indicator"]] = {
                "field": condition["field"],
                "actual": actual,
                "expected": f"{operator} {condition['value']}",
                "matched": ok,
            }
            execution_log.append(
                {
                    "indicator": condition["indicator"],
                    "field": condition["field"],
                    "actual": actual,
                    "operator": operator,
                    "expected": condition["value"],
                    "matched": ok,
                    "reason": (
                        f"{condition['indicator']}.{condition['field']}={actual} "
                        f"{operator} {condition['value']} -> {'通过' if ok else '未通过'}"
                    ),
                }
            )
            condition_results.append(ok)
        matched = any(condition_results) if rule["logic"] == "any" else all(condition_results)
        status = rule["triggered_status"]

        existing = db.scalar(
            select(RuleResult).where(
                RuleResult.rule_id == rule["rule_id"],
                RuleResult.month == month,
            )
        )
        evidence_text = _render_evidence_template(rule["evidence_template"], by_code)
        payload = {
            "rule_id": rule["rule_id"],
            "month": month,
            "name": rule["name"],
            "module": rule["category"],
            "severity": status["severity"],
            "matched": matched,
            "explanation": rule["description"],
            "evidence": {
                "conditions": evidence,
                "risk": rule["risk"],
                "observed_indicators": rule["observed_indicators"],
                "triggered_status": status,
                "evidence_template": rule["evidence_template"],
                "evidence_text": evidence_text,
                "execution_log": execution_log,
            },
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            result = existing
        else:
            result = RuleResult(**payload)
            db.add(result)
        results.append(result)

    snapshot = build_snapshot(db, month, results, by_code)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not retry_on_integrity:
            raise
        return evaluate_month(db, month, retry_on_integrity=False)
    return results, snapshot


def build_snapshot(
    db: Session,
    month: str,
    results: list[RuleResult],
    by_code: dict[str, IndicatorData],
) -> CycleSnapshot:
    matched = [result for result in results if result.matched]
    modules = {
        "货币": _module_state("货币", "偏宽", "M2仍处相对高位，流动性条件不紧。"),
        "信用": _module_state("信用", "偏弱", "社融和贷款结构显示实体融资需求仍待修复。"),
        "居民": _module_state("居民", "防御", "居民贷款和收入预期共同约束风险偏好。"),
        "房地产": _module_state("房地产", "筑底未确认", "销售和价格尚未形成同步改善。"),
        "企业": _module_state("企业", "观望", "民间投资和利润修复偏温和。"),
        "价格": _module_state("价格", "低通胀", "核心CPI温和，PPI仍拖累名义增长。"),
    }
    module_map = {
        "credit": "信用",
        "household": "居民",
        "property": "房地产",
        "enterprise": "企业",
        "price": "价格",
        "policy": "货币",
        "cycle": "信用",
    }
    for result in matched:
        module_name = module_map.get(result.module)
        if not module_name:
            continue
        modules[module_name]["state"] = result.name
        modules[module_name].setdefault("signals", [])
        modules[module_name]["signals"].append(
            {
                "rule_id": result.rule_id,
                "name": result.name,
                "category": result.module,
                "severity": result.severity,
                "risk": result.evidence.get("risk"),
                "evidence_text": result.evidence.get("evidence_text"),
            }
        )

    headline = "宽货币、弱信用、弱预期的修复观察期"
    if not matched:
        headline = "宏观状态相对均衡，等待新信号确认"

    risks = [
        result.evidence.get("risk") or result.explanation
        for result in matched
    ]
    if by_code.get("ppi") and (by_code["ppi"].yoy or 0) < 0:
        risks.append("PPI仍为负，企业利润弹性可能受压。")

    watch_tasks = _build_watch_tasks(matched)
    agent_brief = "Agent接口预留：后续可接入模型，将规则命中、指标异常和历史分位生成自然语言月度解读。"

    existing = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == month))
    payload = {
        "month": month,
        "headline": headline,
        "summary": "当前系统根据12个核心指标和规则文件生成状态快照，仅用于宏观周期理解，不构成投资建议。",
        "modules": modules,
        "risks": risks,
        "watch_tasks": watch_tasks,
        "agent_brief": agent_brief,
    }
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing
    snapshot = CycleSnapshot(**payload)
    db.add(snapshot)
    return snapshot


def _module_state(module: str, state: str, description: str) -> dict[str, str]:
    return {"module": module, "state": state, "description": description}


def _build_watch_tasks(matched: list[RuleResult]) -> list[str]:
    indicator_labels = {
        "m2_yoy": "M2同比",
        "tsf_stock_yoy": "社融存量同比",
        "new_rmb_loan": "新增人民币贷款",
        "household_mid_long_loan": "居民中长期贷款",
        "enterprise_mid_long_loan": "企业中长期贷款",
        "core_cpi": "核心CPI",
        "ppi": "PPI",
        "secondhand_home_price_mom_70c": "70城二手房价格环比",
        "commodity_house_sales_area": "商品房销售面积",
        "wage_income": "居民工资性收入",
        "private_investment": "民间投资",
        "industrial_profit": "工业企业利润",
    }
    tasks: list[str] = []
    for result in matched:
        observed = result.evidence.get("observed_indicators") or []
        label = "、".join(indicator_labels.get(code, code) for code in observed[:3])
        if label:
            tasks.append(f"跟踪{label}，确认“{result.name}”是否延续或缓解。")
        if len(tasks) >= 4:
            break
    defaults = [
        "观察社融存量同比能否回升并缩小与M2的差距。",
        "跟踪居民中长期贷款是否转正，验证购房和加杠杆意愿。",
        "关注二手房价格环比与商品房销售面积能否同步改善。",
        "确认民间投资和工业企业利润是否形成同向修复。",
    ]
    for task in defaults:
        if len(tasks) >= 4:
            break
        if task not in tasks:
            tasks.append(task)
    return tasks


def _validate_rule(rule: dict[str, Any]) -> None:
    if rule["logic"] not in {"all", "any"}:
        raise ValueError(f"Unsupported rule logic: {rule['rule_id']}")
    for condition in rule["conditions"]:
        if condition["field"] not in ALLOWED_RULE_FIELDS:
            raise ValueError(
                f"Unsupported condition field: {rule['rule_id']} uses {condition['field']}"
            )
        if condition["operator"] not in ALLOWED_OPERATORS:
            raise ValueError(
                f"Unsupported condition operator: {rule['rule_id']} uses {condition['operator']}"
            )


def _render_evidence_template(template: str, by_code: dict[str, IndicatorData]) -> str:
    text = template
    for code, row in by_code.items():
        replacements = {
            f"{{{code}.value}}": _format_value(row.value),
            f"{{{code}.yoy}}": _format_value(row.yoy),
            f"{{{code}.mom}}": _format_value(row.mom),
            f"{{{code}.trend_3m}}": _format_value(row.trend_3m),
            f"{{{code}.percentile_24m}}": _format_value(row.percentile_24m),
        }
        for key, value in replacements.items():
            text = text.replace(key, value)
    return text


def _format_value(value: float | None) -> str:
    if value is None:
        return "数据不足"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
