import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import IndicatorData, IndicatorDefinition
from app.services.data_sync.models import DataSyncError, RawIndicatorRow, SyncResult
from app.services.rule_engine import evaluate_month


def sync_indicator_rows(db: Session, raw_rows: list[RawIndicatorRow]) -> SyncResult:
    code_to_id = {row.code: row.id for row in db.scalars(select(IndicatorDefinition)).all()}
    parsed_rows: list[dict] = []
    errors: list[str] = []
    sources = set()
    for index, row in enumerate(raw_rows, start=1):
        prefix = _error_prefix(row, index)
        indicator_id = code_to_id.get(row.indicator_code)
        if not indicator_id:
            errors.append(f"{prefix}: indicator_code does not exist")
            continue
        try:
            _validate_month(row.month)
            parsed_rows.append(
                {
                    "indicator_id": indicator_id,
                    "month": row.month,
                    "value": _required_float(row.value),
                    "yoy": _float_or_none(row.yoy),
                    "mom": _float_or_none(row.mom),
                    "trend_3m": _float_or_none(row.trend_3m),
                    "percentile_24m": _float_or_none(row.percentile_24m),
                    "status": row.status or "neutral",
                }
            )
            if row.source_ref:
                sources.add(row.source_ref)
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
    if errors:
        raise DataSyncError(errors)

    imported = 0
    touched_months = set()
    for item in parsed_rows:
        existing = db.scalar(
            select(IndicatorData).where(
                IndicatorData.indicator_id == item["indicator_id"],
                IndicatorData.month == item["month"],
            )
        )
        if existing:
            for key, value in item.items():
                setattr(existing, key, value)
        else:
            db.add(IndicatorData(**item))
        imported += 1
        touched_months.add(item["month"])

    db.commit()
    for month in touched_months:
        evaluate_month(db, month)
    return SyncResult(imported=imported, months=sorted(touched_months), sources=sorted(sources))


def prune_months_after(db: Session, month: str) -> int:
    rows = db.scalars(select(IndicatorData).where(IndicatorData.month > month)).all()
    deleted = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return deleted


def _error_prefix(row: RawIndicatorRow, index: int) -> str:
    if row.source_ref and row.line_number:
        return f"{row.source_ref} line {row.line_number}"
    if row.line_number:
        return f"line {row.line_number}"
    return f"row {index}"


def _validate_month(month: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise ValueError("month must be YYYY-MM")
    month_num = int(month[-2:])
    if month_num < 1 or month_num > 12:
        raise ValueError("month must be between 01 and 12")


def _required_float(value) -> float:
    parsed = _float_or_none(value)
    if parsed is None:
        raise ValueError("value is required")
    return parsed


def _float_or_none(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
