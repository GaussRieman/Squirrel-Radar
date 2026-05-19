import csv
import re
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.domain import CycleSnapshot, IndicatorData, IndicatorDefinition, RuleResult
from app.schemas.domain import (
    AgentInterpretationRequest,
    AgentInterpretationRead,
    CycleSnapshotRead,
    DashboardRead,
    IndicatorDataCreate,
    IndicatorDataRead,
    IndicatorDefinitionCreate,
    IndicatorDefinitionRead,
    RuleResultRead,
)
from app.services.agent_service import generate_interpretation, get_agent_status
from app.services.rule_engine import evaluate_month, load_rule_catalog
from app.services.test_data_service import apply_test_scenario, load_test_scenarios

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/indicators", response_model=list[IndicatorDefinitionRead])
def list_indicators(db: Session = Depends(get_db)):
    return db.scalars(select(IndicatorDefinition).order_by(IndicatorDefinition.id)).all()


@router.post("/indicators", response_model=IndicatorDefinitionRead)
def create_indicator(payload: IndicatorDefinitionCreate, db: Session = Depends(get_db)):
    indicator = IndicatorDefinition(**payload.model_dump())
    db.add(indicator)
    db.commit()
    db.refresh(indicator)
    return indicator


@router.get("/indicator-data", response_model=list[IndicatorDataRead])
def list_indicator_data(month: str | None = None, db: Session = Depends(get_db)):
    stmt = select(IndicatorData).options(joinedload(IndicatorData.indicator))
    if month:
        stmt = stmt.where(IndicatorData.month == month)
    return db.scalars(stmt.order_by(IndicatorData.month, IndicatorData.indicator_id)).all()


@router.get("/months", response_model=list[str])
def list_months(db: Session = Depends(get_db)):
    return db.scalars(select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))).all()


@router.post("/indicator-data", response_model=IndicatorDataRead)
def create_indicator_data(payload: IndicatorDataCreate, db: Session = Depends(get_db)):
    try:
        _validate_month(payload.month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not db.get(IndicatorDefinition, payload.indicator_id):
        raise HTTPException(status_code=400, detail="indicator_id does not exist")
    row = db.scalar(
        select(IndicatorData).where(
            IndicatorData.indicator_id == payload.indicator_id,
            IndicatorData.month == payload.month,
        )
    )
    if row:
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
    else:
        row = IndicatorData(**payload.model_dump())
        db.add(row)
    db.commit()
    evaluate_month(db, payload.month)
    db.refresh(row)
    return row


@router.get("/indicator-data/template.csv", response_class=PlainTextResponse)
def csv_template():
    return "\n".join(
        [
            "indicator_code,month,value,yoy,mom,trend_3m,percentile_24m,status",
            "m2_yoy,2026-05,8.9,8.9,0.1,8.8,72,strong",
        ]
    )


@router.post("/indicator-data/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    required_headers = {
        "indicator_code",
        "month",
        "value",
        "yoy",
        "mom",
        "trend_3m",
        "percentile_24m",
        "status",
    }
    if not reader.fieldnames or not required_headers.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=400, detail="CSV headers are invalid")
    code_to_id = {row.code: row.id for row in db.scalars(select(IndicatorDefinition)).all()}
    parsed_rows = []
    errors = []
    for line_number, item in enumerate(reader, start=2):
        indicator_id = code_to_id.get(item.get("indicator_code", ""))
        if not indicator_id:
            errors.append(f"line {line_number}: indicator_code does not exist")
            continue
        try:
            _validate_month(item.get("month", ""))
            parsed_rows.append(
                {
                    "indicator_id": indicator_id,
                    "month": item["month"],
                    "value": _required_float(item.get("value")),
                    "yoy": _float_or_none(item.get("yoy")),
                    "mom": _float_or_none(item.get("mom")),
                    "trend_3m": _float_or_none(item.get("trend_3m")),
                    "percentile_24m": _float_or_none(item.get("percentile_24m")),
                    "status": item.get("status") or "neutral",
                }
            )
        except ValueError as exc:
            errors.append(f"line {line_number}: {exc}")
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    imported = 0
    touched_months = set()
    for item in parsed_rows:
        row = db.scalar(
            select(IndicatorData).where(
                IndicatorData.indicator_id == item["indicator_id"],
                IndicatorData.month == item["month"],
            )
        )
        if row:
            for key, value in item.items():
                setattr(row, key, value)
        else:
            db.add(IndicatorData(**item))
        imported += 1
        touched_months.add(item["month"])
    db.commit()
    for month in touched_months:
        evaluate_month(db, month)
    return {"imported": imported, "months": sorted(touched_months)}


@router.get("/rules")
def rules():
    return load_rule_catalog()


@router.post("/rules/evaluate/{month}", response_model=list[RuleResultRead])
def evaluate_rules(month: str, db: Session = Depends(get_db)):
    results, _ = evaluate_month(db, month)
    return results


@router.get("/rule-results", response_model=list[RuleResultRead])
def rule_results(month: str | None = None, db: Session = Depends(get_db)):
    stmt = select(RuleResult)
    if month:
        stmt = stmt.where(RuleResult.month == month)
    return db.scalars(stmt.order_by(RuleResult.month, RuleResult.rule_id)).all()


@router.get("/snapshots", response_model=list[CycleSnapshotRead])
def snapshots(db: Session = Depends(get_db)):
    return db.scalars(select(CycleSnapshot).order_by(desc(CycleSnapshot.month))).all()


@router.get("/snapshots/{month}", response_model=CycleSnapshotRead)
def snapshot(month: str, db: Session = Depends(get_db)):
    row = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == month))
    if not row:
        _, row = evaluate_month(db, month)
    return row


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(month: str | None = None, db: Session = Depends(get_db)):
    target_month = month or db.scalar(select(IndicatorData.month).order_by(desc(IndicatorData.month)))
    if not target_month:
        raise HTTPException(status_code=404, detail="No indicator data available")
    evaluate_month(db, target_month)
    snapshot_row = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == target_month))
    indicators = db.scalars(
        select(IndicatorData)
        .options(joinedload(IndicatorData.indicator))
        .where(IndicatorData.month == target_month)
        .order_by(IndicatorData.indicator_id)
    ).all()
    results = db.scalars(
        select(RuleResult).where(RuleResult.month == target_month).order_by(RuleResult.rule_id)
    ).all()
    history_rows = db.scalars(
        select(IndicatorData)
        .options(joinedload(IndicatorData.indicator))
        .order_by(IndicatorData.month, IndicatorData.indicator_id)
    ).all()
    history = [
        {
            "month": row.month,
            "code": row.indicator.code,
            "name": row.indicator.name,
            "value": row.value,
            "yoy": row.yoy,
            "mom": row.mom,
        }
        for row in history_rows
    ]
    return {
        "month": target_month,
        "months": db.scalars(
            select(IndicatorData.month).distinct().order_by(desc(IndicatorData.month))
        ).all(),
        "snapshot": snapshot_row,
        "indicators": indicators,
        "rule_results": results,
        "history": history,
    }


@router.get("/agent/interpretation", response_model=AgentInterpretationRead)
def agent_interpretation(month: str | None = None, db: Session = Depends(get_db)):
    return generate_interpretation(db, month, use_model=False)


@router.get("/agent/status")
def agent_status():
    return get_agent_status()


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
        history=payload.history,
        selected_context=payload.selected_context,
    )


@router.get("/test-data/scenarios")
def test_data_scenarios():
    return load_test_scenarios()


@router.post("/test-data/scenarios/{scenario_id}/apply")
def apply_scenario(scenario_id: str, db: Session = Depends(get_db)):
    try:
        return apply_test_scenario(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _float_or_none(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _required_float(value: str | None) -> float:
    if value in (None, ""):
        raise ValueError("value is required")
    return float(value)


def _validate_month(month: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise ValueError("month must use YYYY-MM format")
    month_num = int(month[-2:])
    if month_num < 1 or month_num > 12:
        raise ValueError("month must be between 01 and 12")
