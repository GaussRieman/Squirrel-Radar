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
