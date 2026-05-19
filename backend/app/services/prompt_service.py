from pathlib import Path

PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "agent_interpretation_prompt.md"


def load_agent_interpretation_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")
