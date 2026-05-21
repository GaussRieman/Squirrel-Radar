import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.domain import CycleSnapshot, IndicatorData, IndicatorDefinition
from app.services.data_sync.csv_file import load_csv_rows
from app.services.data_sync.models import DataSyncError, RawIndicatorRow
from app.services.data_sync.service import sync_indicator_rows
from app.services.seed import seed_database


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    return TestingSession()


def test_sync_indicator_rows_imports_and_evaluates_month():
    db = make_session()
    seed_database(db)

    result = sync_indicator_rows(
        db,
        [
            RawIndicatorRow(
                indicator_code="m2_yoy",
                month="2026-06",
                value="8.8",
                yoy="8.8",
                mom="0.1",
                trend_3m="8.7",
                percentile_24m="72",
                status="strong",
            )
        ],
    )

    indicator = db.scalar(select(IndicatorDefinition).where(IndicatorDefinition.code == "m2_yoy"))
    row = db.scalar(
        select(IndicatorData).where(
            IndicatorData.indicator_id == indicator.id,
            IndicatorData.month == "2026-06",
        )
    )
    snapshot = db.scalar(select(CycleSnapshot).where(CycleSnapshot.month == "2026-06"))
    assert result.imported == 1
    assert result.months == ["2026-06"]
    assert row.value == 8.8
    assert snapshot is not None


def test_sync_indicator_rows_updates_existing_row():
    db = make_session()
    seed_database(db)
    indicator = db.scalar(select(IndicatorDefinition).where(IndicatorDefinition.code == "m2_yoy"))
    before = db.scalar(
        select(IndicatorData).where(
            IndicatorData.indicator_id == indicator.id,
            IndicatorData.month == "2026-05",
        )
    )

    result = sync_indicator_rows(
        db,
        [
            RawIndicatorRow(
                indicator_code="m2_yoy",
                month="2026-05",
                value="9.9",
                yoy="9.9",
                status="strong",
            )
        ],
    )
    db.refresh(before)

    assert result.imported == 1
    assert before.value == 9.9
    assert before.yoy == 9.9


def test_load_csv_rows_reads_directory(tmp_path):
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    first.write_text(
        "indicator_code,month,value,yoy,mom,trend_3m,percentile_24m,status\n"
        "m2_yoy,2026-06,8.8,8.8,0.1,8.7,72,strong\n",
        encoding="utf-8",
    )
    second.write_text(
        "indicator_code,month,value,yoy,mom,trend_3m,percentile_24m,status\n"
        "core_cpi,2026-06,0.9,0.9,0.0,0.8,60,neutral\n",
        encoding="utf-8",
    )

    rows = load_csv_rows(tmp_path)

    assert [row.indicator_code for row in rows] == ["m2_yoy", "core_cpi"]
    assert rows[0].source_ref.endswith("a.csv")


def test_sync_indicator_rows_rejects_invalid_rows_without_partial_write():
    db = make_session()
    seed_database(db)

    with pytest.raises(DataSyncError):
        sync_indicator_rows(
            db,
            [
                RawIndicatorRow(indicator_code="m2_yoy", month="2026-06", value="8.8"),
                RawIndicatorRow(indicator_code="missing", month="2026-06", value="1"),
            ],
        )

    rows = db.scalars(select(IndicatorData).where(IndicatorData.month == "2026-06")).all()
    assert rows == []
