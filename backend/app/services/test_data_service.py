import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import IndicatorData, IndicatorDefinition
from app.services.rule_engine import evaluate_month

SCENARIO_FILE = Path(__file__).resolve().parents[1] / "seeds" / "test_scenarios.seed.json"


def load_test_scenarios() -> list[dict]:
    return json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))


def apply_test_scenario(db: Session, scenario_id: str) -> dict:
    scenario = next(
        (item for item in load_test_scenarios() if item["scenario_id"] == scenario_id),
        None,
    )
    if not scenario:
        raise ValueError("scenario_id does not exist")

    code_to_indicator = {
        row.code: row for row in db.scalars(select(IndicatorDefinition)).all()
    }
    for code, values in scenario["data"].items():
        indicator = code_to_indicator.get(code)
        if not indicator:
            continue
        row = db.scalar(
            select(IndicatorData).where(
                IndicatorData.indicator_id == indicator.id,
                IndicatorData.month == scenario["month"],
            )
        )
        payload = {
            "indicator_id": indicator.id,
            "month": scenario["month"],
            "value": values["value"],
            "yoy": values.get("yoy"),
            "mom": values.get("mom"),
            "trend_3m": values.get("trend_3m"),
            "percentile_24m": values.get("percentile_24m"),
            "status": values.get("status", "neutral"),
        }
        if row:
            for key, value in payload.items():
                setattr(row, key, value)
        else:
            db.add(IndicatorData(**payload))
    db.commit()
    evaluate_month(db, scenario["month"])
    return {
        "scenario_id": scenario["scenario_id"],
        "name": scenario["name"],
        "month": scenario["month"],
        "applied": len(scenario["data"]),
    }
