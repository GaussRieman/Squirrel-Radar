from app.services.prompt_service import load_agent_interpretation_prompt
from app.services.rule_engine import load_rule_catalog, load_rules
from app.services.seed import _load_indicator_seed


def test_indicator_seed_has_expected_shape():
    indicators = _load_indicator_seed()
    assert len(indicators) == 12
    assert {item["indicator_id"] for item in indicators} >= {
        "m2_yoy",
        "tsf_stock_yoy",
        "industrial_profit",
    }
    assert all(1 <= item["importance"] <= 5 for item in indicators)


def test_rule_catalog_has_version_and_rules():
    catalog = load_rule_catalog()
    assert catalog["version"] == 1
    assert catalog["updated_at"] == "2026-05-18"
    assert len(load_rules()) >= 20


def test_rules_use_supported_condition_fields():
    allowed_fields = {"value", "yoy", "mom", "trend_3m", "percentile_24m"}
    for rule in load_rules():
        assert rule["logic"] in {"all", "any"}
        for condition in rule["conditions"]:
            assert condition["field"] in allowed_fields


def test_agent_prompt_contains_required_sections():
    prompt = load_agent_interpretation_prompt()
    for section in [
        "本月一句话判断",
        "六大模块状态",
        "当前主要风险",
        "对普通家庭资产配置的含义",
        "对企业经营决策的含义",
    ]:
        assert section in prompt
