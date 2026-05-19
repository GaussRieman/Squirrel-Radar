from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.routes import dashboard
from app.core.database import Base
from app.models.domain import CycleSnapshot, IndicatorData, IndicatorDefinition, RuleResult
from app.services.agent_service import generate_mock_interpretation, get_agent_status
from app.services.rule_engine import evaluate_month
from app.services.seed import seed_database
from app.services.test_data_service import apply_test_scenario, load_test_scenarios


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    return TestingSession()


def test_seed_database_creates_indicators_and_history():
    db = make_session()
    seed_database(db)

    assert db.query(IndicatorDefinition).count() == 12
    assert db.query(IndicatorData).count() == 12 * 24


def test_evaluate_month_creates_rule_results_and_snapshot():
    db = make_session()
    seed_database(db)
    month = db.scalar(select(IndicatorData.month).order_by(IndicatorData.month.desc()))

    results, snapshot = evaluate_month(db, month)

    assert len(results) >= 20
    assert db.query(RuleResult).filter(RuleResult.month == month).count() == len(results)
    assert snapshot.month == month
    assert "信用" in snapshot.modules
    assert any("execution_log" in result.evidence for result in results)


def test_dashboard_aggregates_current_month_data():
    db = make_session()
    seed_database(db)

    payload = dashboard(db=db)

    assert payload["month"] == payload["months"][0]
    assert len(payload["indicators"]) == 12
    assert len(payload["rule_results"]) >= 20
    assert payload["snapshot"].month == payload["month"]
    assert len(payload["history"]) == 12 * 24


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


def test_apply_test_scenario_updates_month_and_rules():
    db = make_session()
    seed_database(db)
    scenario = load_test_scenarios()[0]

    result = apply_test_scenario(db, scenario["scenario_id"])

    assert result["applied"] == 12
    assert result["month"] == scenario["month"]
    rows = db.query(IndicatorData).filter(IndicatorData.month == scenario["month"]).count()
    assert rows == 12
    assert db.query(RuleResult).filter(RuleResult.month == scenario["month"]).count() >= 20
