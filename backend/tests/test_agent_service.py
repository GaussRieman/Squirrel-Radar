from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    return testing_session()


def test_load_system_prompt_returns_agent_md_content():
    from app.services.agent_service import _load_system_prompt
    content = _load_system_prompt()
    assert "SquirrelRadar" in content
    assert "Agent Operating Manual" in content
    assert "Intent Judgment" in content
    assert "Progressive Skill Loading" in content
    assert "Self-Check Before Responding" in content


def test_load_system_prompt_uses_agent_md(tmp_path, monkeypatch):
    from app.services import agent_service
    prompts_dir = Path(agent_service.__file__).resolve().parents[1] / "prompts"
    monkeypatch.setattr(
        agent_service,
        "_load_system_prompt",
        lambda: (prompts_dir / "AGENT.md").read_text(encoding="utf-8"),
    )
    result = agent_service._load_system_prompt()
    assert isinstance(result, str)
    assert len(result) > 0


def test_parse_data_view_month_supports_short_chinese_year():
    from app.services.agent_service import _parse_data_view_month

    assert _parse_data_view_month("给我25年3月的数据") == "2025-03"
    assert _parse_data_view_month("查看2025年03月数据") == "2025-03"
    assert _parse_data_view_month("打开 2025-3") == "2025-03"


def test_parse_data_view_month_skips_analysis_requests():
    from app.services.agent_service import _parse_data_view_month

    assert _parse_data_view_month("分析一下25年3月的数据") is None
    assert _parse_data_view_month("怎么看2025年3月风险") is None


def test_data_view_response_uses_task_list_format():
    from app.services.agent_service import build_data_view_response
    from app.services.seed import seed_database

    db = make_session()
    seed_database(db)
    result = build_data_view_response(db, "查看26年3月的")

    assert result is not None
    assert result["navigate_month"] == "2026-03"
    assert "- [x] 检查可用月份" in result["content"]
    assert "→" not in result["content"]
