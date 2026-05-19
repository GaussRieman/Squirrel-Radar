import json
from math import sin
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.domain import IndicatorData, IndicatorDefinition


INDICATOR_SEED_FILE = Path(__file__).resolve().parents[1] / "seeds" / "indicators.seed.json"


BASE_VALUES = {
    "m2_yoy": (8.6, 0.18),
    "tsf_stock_yoy": (8.2, 0.12),
    "new_rmb_loan": (9200, 480),
    "household_mid_long_loan": (1200, 180),
    "enterprise_mid_long_loan": (5200, 260),
    "core_cpi": (0.7, 0.05),
    "ppi": (-1.7, 0.16),
    "secondhand_home_price_mom_70c": (-0.35, 0.04),
    "commodity_house_sales_area": (-8.5, 0.7),
    "wage_income": (5.0, 0.12),
    "private_investment": (-0.8, 0.16),
    "industrial_profit": (3.4, 0.55),
}


def seed_database(db: Session) -> None:
    if db.scalar(func.count(IndicatorDefinition.id)):
        return

    definitions = [IndicatorDefinition(**_to_definition(item)) for item in _load_indicator_seed()]
    db.add_all(definitions)
    db.flush()

    for definition in definitions:
        base, step = BASE_VALUES[definition.code]
        previous = None
        values: list[float] = []
        for idx in range(24):
            year = 2024 + (idx + 5) // 12
            month_num = ((idx + 5) % 12) + 1
            month = f"{year}-{month_num:02d}"
            wave = sin(idx / 3) * step * 2
            drift = (idx - 12) * step * 0.18
            value = round(base + drift + wave, 2)
            if definition.unit == "亿元":
                value = round(base + drift * 100 + wave * 100, 0)
            yoy = value if definition.unit == "%" else round((value - base) / base * 100, 2)
            mom = None if previous is None else round(value - previous, 2)
            values.append(value)
            window = values[-3:]
            trend_3m = round(sum(window) / len(window), 2)
            sorted_window = sorted(values[-24:])
            rank = sorted_window.index(value) + 1
            percentile = round(rank / len(sorted_window) * 100, 1)
            status = "neutral"
            if percentile >= 70:
                status = "strong"
            elif percentile <= 30:
                status = "weak"
            db.add(
                IndicatorData(
                    indicator_id=definition.id,
                    month=month,
                    value=value,
                    yoy=round(yoy, 2),
                    mom=mom,
                    trend_3m=trend_3m,
                    percentile_24m=percentile,
                    status=status,
                )
            )
            previous = value
    db.commit()


def _load_indicator_seed() -> list[dict]:
    return json.loads(INDICATOR_SEED_FILE.read_text(encoding="utf-8"))


def _to_definition(item: dict) -> dict:
    return {
        "code": item["indicator_id"],
        "name": item["name"],
        "category": item["category"],
        "frequency": item["frequency"],
        "source": item["source"],
        "unit": item["unit"],
        "importance": item["importance"],
        "confidence": item["trust_level"],
        "definition": item["definition"],
        "interpretation": item["interpretation"],
        "risk_note": item["warning"],
    }
