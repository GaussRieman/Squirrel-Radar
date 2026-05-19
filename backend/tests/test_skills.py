from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[1] / "app" / "skills"


def _load_skill(name: str) -> str:
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.exists(), f"SKILL.md not found for skill: {name}"
    return path.read_text(encoding="utf-8")


def test_navigate_month_skill_exists_with_frontmatter():
    content = _load_skill("navigate-month")
    assert content.startswith("---")
    assert "name: navigate-month" in content
    assert "navigate_to_month" in content
    assert "get_cycle_snapshot" in content


def test_navigate_month_skill_description_contains_routing_predicates():
    content = _load_skill("navigate-month")
    assert "查看" in content or "切换" in content
    assert "Do NOT" in content


def test_cycle_summary_skill_frontmatter_and_routing():
    content = _load_skill("cycle-summary")
    assert "name: cycle-summary" in content
    assert "Do NOT" in content
    assert "get_cycle_snapshot" in content
    assert "get_matched_rules" in content
    assert "get_indicators" in content


def test_cycle_summary_output_contract_has_required_sections():
    content = _load_skill("cycle-summary")
    assert "一句话判断" in content
    assert "六大模块" in content
    assert "主要风险" in content
    assert "下月观察" in content
