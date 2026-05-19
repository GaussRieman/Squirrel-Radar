from pathlib import Path


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
