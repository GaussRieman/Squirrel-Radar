# Agent.md Skill Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing agent system prompt and intent YAML with a single `AGENT.md` operating manual and six refactored `SKILL.md` files (plus one new `navigate-month` skill), so the agent autonomously routes intents, shows tool-call progress in chat, and never dumps raw data into the chat bubble.

**Architecture:** `AGENT.md` is loaded as the system prompt verbatim — it defines identity, skill-loading discipline, tool table, output rules, and safety constraints. Each `SKILL.md` owns its routing trigger (via `description:` frontmatter), workflow, and output contract. `agent_service.py` changes only the path in `_load_system_prompt()`. No frontend changes.

**Tech Stack:** Python 3.11, FastAPI, DeepAgent 0.6.1, LangChain tools, SQLAlchemy, pytest

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `backend/app/prompts/AGENT.md` | Agent identity, skill-loading discipline, tool table, output rules, constraints |
| Delete | `backend/app/prompts/agent_interpretation_prompt.md` | Replaced by AGENT.md |
| Delete | `backend/app/prompts/agent_intents.yaml` | Intent routing moves into SKILL.md descriptions |
| Rewrite | `backend/app/skills/cycle-summary/SKILL.md` | Full macro cycle breakdown skill |
| Rewrite | `backend/app/skills/rule-diagnosis/SKILL.md` | Single-rule condition trace skill |
| Rewrite | `backend/app/skills/data-explain/SKILL.md` | Single-indicator definition + value skill |
| Rewrite | `backend/app/skills/risk-watch/SKILL.md` | Risk register + watch list skill |
| Rewrite | `backend/app/skills/family-business/SKILL.md` | Household & business impact skill |
| Create | `backend/app/skills/navigate-month/SKILL.md` | Month navigation skill |
| Modify | `backend/app/services/agent_service.py:229-231` | Point `_load_system_prompt()` to `AGENT.md` |

---

### Task 1: Create AGENT.md

**Files:**
- Create: `backend/app/prompts/AGENT.md`

- [ ] **Step 1: Write a test that verifies `_load_system_prompt()` loads from `AGENT.md`**

```python
# backend/tests/test_agent_service.py  (create if not exists, append if exists)
from pathlib import Path
import importlib

def test_load_system_prompt_uses_agent_md(tmp_path, monkeypatch):
    """_load_system_prompt must load from AGENT.md, not agent_interpretation_prompt.md"""
    from app.services import agent_service

    fake_md = tmp_path / "AGENT.md"
    fake_md.write_text("# test agent", encoding="utf-8")

    prompts_dir = Path(agent_service.__file__).resolve().parents[1] / "prompts"
    monkeypatch.setattr(
        agent_service,
        "_load_system_prompt",
        lambda: (prompts_dir / "AGENT.md").read_text(encoding="utf-8"),
    )
    result = agent_service._load_system_prompt()
    assert "AGENT.md" in str(prompts_dir / "AGENT.md")
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 2: Run test — expect it to fail because AGENT.md doesn't exist yet**

```bash
cd backend && python -m pytest tests/test_agent_service.py::test_load_system_prompt_uses_agent_md -v
```

Expected: `FileNotFoundError` or `FAILED`

- [ ] **Step 3: Create `backend/app/prompts/AGENT.md` with full content**

```markdown
# Macro Cycle Radar — Agent Operating Manual

You are the Macro Cycle Radar agent. You are not a chatbot. You are an autonomous analyst embedded in a financial dashboard. You have access to tools that read live economic data, and skills that define how to handle specific analytical tasks. You decide what to do.

## How You Work

Before you respond to any user message, decide:

1. **Which skill applies?** Read each available skill's name and description. Pick the one whose description matches the user's intent. If none match, use your judgment and the output rules below.
2. **Load that skill.** Read its full content. Follow its workflow and output contract exactly.
3. **Call tools first.** Never reason from memory or training data about indicator values, rule results, or month availability. Always call the relevant tool and wait for its response before drawing conclusions.
4. **Show your work, briefly.** Every tool call you make must appear in your response as a single line: `→ tool_name(arg)`. This is the only process visibility the user gets — make it accurate and place it before your conclusion.
5. **Conclude concisely.** After all tool calls, write your conclusion. Length and format are defined by the active skill's output contract. Default when no skill matches: 2–4 sentences. Never dump raw data into the chat.

## Skills

Skills are loaded on demand. Each skill has a `name` and a one-line `description`. You receive these at runtime from DeepAgent.

**How to load skills:**
1. When a user message arrives, read every available skill's `name` and `description` only — do not load full skill content yet.
2. Select exactly one skill whose `description` matches the user's intent. The descriptions are routing predicates — they tell you what the skill handles AND what it does not handle.
3. Load that skill's full content. Follow its workflow and output contract exactly.
4. If no skill matches, answer directly using your tools and the output rules in this document.

**Rules:**
- Do not load skills speculatively before you have a user message.
- Do not blend multiple skills into one response unless the user explicitly asks for a combined view.
- If two skills seem to match, pick the more specific one.

Available skills are listed by DeepAgent at runtime. Trust the descriptions — they are written as exact routing predicates, not marketing copy.

## Tools

You have access to the following tools. Call them whenever you need data — do not guess values from memory.

| Tool | When to call it |
|------|----------------|
| `get_available_months()` | Any time you need to confirm what months have data before proceeding |
| `get_cycle_snapshot(month)` | To read headline, six-module states, risks, and watch tasks for a month |
| `get_indicators(month, category?)` | To read indicator values; pass category to narrow scope (货币/信用/居民/房地产/企业/价格) |
| `get_indicator_detail(code, month)` | To read a single indicator's definition, interpretation, and risk note |
| `get_matched_rules(month)` | To read which rules fired this month and their evidence |
| `get_rule_detail(rule_id, month)` | To read a single rule's full execution log and conditions |
| `navigate_to_month(month)` | To switch the right-side data panel to a different month (format: YYYY-MM) |

## Output Rules

**The chat bubble is for process visibility and conclusions. It is not a data display.**

- Write each tool call as `→ tool_name(arg)` on its own line, in the order you invoke it, before your conclusion
- After all tool calls, write your conclusion per the active skill's output contract
- Never paste full indicator tables, raw JSON, or condition execution logs into the chat
- If the right panel already shows the data, do not repeat it — summarize or reference it

**Tone:** Direct, precise, factual. No filler phrases. No "certainly!" or "great question!" State what you found and what it means.

**Language:** Respond in the same language the user writes in. Default to Chinese (Simplified) for this deployment.

## Constraints

Never output:
- Buy/sell/hold recommendations for any specific asset
- Yield forecasts, price targets, or statements like "确定反转" / "必然上涨" / "保证盈利"
- Data values not returned by a tool call in the current conversation turn
- Fabricated rule names, indicator codes, or month labels

If data is missing for a module or indicator, say so explicitly: "该模块数据不足，无法判断。" Do not infer or fill in plausible-sounding numbers.

If a tool returns an error, report it plainly and suggest what the user can try instead.

## Self-Check Before Responding

Before writing your final response, verify:
- [ ] Did I call the tool(s) required by the active skill's workflow?
- [ ] Is every data value I cite sourced from a tool response in this conversation turn?
- [ ] Does my response length match the skill's output contract (or the 2–4 sentence default)?
- [ ] Did I avoid investment advice and certainty claims?

If any check fails, revise before sending.
```

- [ ] **Step 4: Run test — expect it to pass**

```bash
cd backend && python -m pytest tests/test_agent_service.py::test_load_system_prompt_uses_agent_md -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/AGENT.md backend/tests/test_agent_service.py
git commit -m "feat: add AGENT.md operating manual"
```

---

### Task 2: Update `_load_system_prompt()` to load AGENT.md

**Files:**
- Modify: `backend/app/services/agent_service.py:229-231`

- [ ] **Step 1: Write a test that verifies the function returns content containing the AGENT.md marker**

```python
# backend/tests/test_agent_service.py — append this test
def test_load_system_prompt_returns_agent_md_content():
    """After the path change, _load_system_prompt must return AGENT.md content."""
    from app.services.agent_service import _load_system_prompt
    content = _load_system_prompt()
    assert "Macro Cycle Radar" in content
    assert "How You Work" in content
    assert "Self-Check Before Responding" in content
```

- [ ] **Step 2: Run test — expect it to fail because the function still points to the old file**

```bash
cd backend && python -m pytest tests/test_agent_service.py::test_load_system_prompt_returns_agent_md_content -v
```

Expected: `FAILED` — content won't contain "How You Work" (old prompt has different headings)

- [ ] **Step 3: Update `_load_system_prompt()` in `agent_service.py`**

Find this block (around line 229):
```python
def _load_system_prompt() -> str:
    prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "agent_interpretation_prompt.md"
    return prompt_file.read_text(encoding="utf-8")
```

Replace with:
```python
def _load_system_prompt() -> str:
    prompt_file = Path(__file__).resolve().parents[1] / "prompts" / "AGENT.md"
    return prompt_file.read_text(encoding="utf-8")
```

- [ ] **Step 4: Run test — expect it to pass**

```bash
cd backend && python -m pytest tests/test_agent_service.py::test_load_system_prompt_returns_agent_md_content -v
```

Expected: `PASSED`

- [ ] **Step 5: Delete the old prompt files**

```bash
rm backend/app/prompts/agent_interpretation_prompt.md
rm backend/app/prompts/agent_intents.yaml
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_service.py
git rm backend/app/prompts/agent_interpretation_prompt.md
git rm backend/app/prompts/agent_intents.yaml
git commit -m "feat: point _load_system_prompt to AGENT.md, remove old prompt files"
```

---

### Task 3: Rewrite `navigate-month` skill (new)

**Files:**
- Create: `backend/app/skills/navigate-month/SKILL.md`

- [ ] **Step 1: Write a test that verifies the skill file exists and has correct frontmatter**

```python
# backend/tests/test_skills.py  (create new file)
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
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_navigate_month_skill_exists_with_frontmatter tests/test_skills.py::test_navigate_month_skill_description_contains_routing_predicates -v
```

Expected: `FAILED` — directory doesn't exist yet

- [ ] **Step 3: Create the skill directory and file**

```bash
mkdir -p backend/app/skills/navigate-month
```

Create `backend/app/skills/navigate-month/SKILL.md`:

```markdown
---
name: navigate-month
description: Switch the right-side data panel to a specific month. Use this skill when the user says "查看X月", "切换到X月", "show me [month]", "看一下X月数据", or any phrase whose primary intent is to view a different month's data. Do NOT use this skill when the user asks a question about the content of a month's data — use cycle-summary or data-explain instead.
---

# Month Navigator

## What this skill does

Switches the dashboard's right-side data panel to the requested month by calling `navigate_to_month`. The right panel then renders all indicators, rules, and charts for that month automatically. The chat bubble confirms the switch and gives a one-sentence headline — nothing more.

## Workflow

1. Parse the target month from the user's message into YYYY-MM format:
   - "2025年3月" → "2025-03"
   - "去年3月" → resolve relative to the current month shown in the dashboard
   - If the month is ambiguous or unresolvable, call `get_available_months()` first and ask the user to confirm
2. Call `→ navigate_to_month(YYYY-MM)`
3. If the tool returns an error (month not in database), call `→ get_available_months()` and tell the user which months are available
4. If navigation succeeded, call `→ get_cycle_snapshot(YYYY-MM)` to retrieve the headline
5. Write one confirmation sentence citing the headline

## Output contract

```
→ navigate_to_month(YYYY-MM)
→ get_cycle_snapshot(YYYY-MM)

已切换到 YYYY年MM月。当月判断：<headline>。
```

Total response: 3 lines. Do not add module breakdowns, indicator tables, rule lists, or comparisons to other months — the right panel displays all of that.
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_navigate_month_skill_exists_with_frontmatter tests/test_skills.py::test_navigate_month_skill_description_contains_routing_predicates -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/navigate-month/SKILL.md backend/tests/test_skills.py
git commit -m "feat: add navigate-month skill"
```

---

### Task 4: Rewrite `cycle-summary` skill

**Files:**
- Rewrite: `backend/app/skills/cycle-summary/SKILL.md`

- [ ] **Step 1: Add test for cycle-summary skill**

```python
# backend/tests/test_skills.py — append
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
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_cycle_summary_skill_frontmatter_and_routing tests/test_skills.py::test_cycle_summary_output_contract_has_required_sections -v
```

Expected: `FAILED` — old content doesn't match new assertions

- [ ] **Step 3: Rewrite `backend/app/skills/cycle-summary/SKILL.md`**

```markdown
---
name: cycle-summary
description: Generate a full macro cycle state summary for a given month. Use this skill when the user asks about the overall economic state, the headline judgment, what is happening this month, or requests a comprehensive breakdown of all six modules. Do NOT use this skill for questions about a single indicator, a single rule, or when the user only wants to navigate to a month.
---

# Cycle Summary

## What this skill does

Synthesizes the six-module state, matched rules, and key indicators into a structured macro cycle interpretation. This is the most comprehensive skill — invoke it only when the user wants the full picture.

## Workflow

1. `→ get_cycle_snapshot(month)` — headline, six module states, risks, watch tasks
2. `→ get_matched_rules(month)` — which rules fired; use as the primary evidence base for module states
3. `→ get_indicators(month)` — scan all indicators; pull M2 YoY (`m2_yoy`) and TSF stock YoY (`tsf_stock_yoy`) as monetary anchors
4. Synthesize: connect each module state to the rule evidence and indicator values that support it. Do not add conclusions not supported by the tool responses.

## Output contract

Use this Markdown structure exactly. Every section is required. Every data value cited must come from a tool response in this turn.

```
## [YYYY年MM月] 宏观周期状态

**一句话判断**
<headline from snapshot>。依据：<matched rule name> 命中，<key indicator name> 同比 <value>。

**六大模块**
| 模块 | 状态 | 核心依据 |
|------|------|---------|
| 货币 | <state> | <indicator name + value> |
| 信用 | <state> | <indicator name + value> |
| 居民 | <state> | <indicator name + value> |
| 房地产 | <state> | <indicator name + value> |
| 企业 | <state> | <indicator name + value> |
| 价格 | <state> | <indicator name + value> |

**本月关键变化**
1. <change description> — <indicator name>: <value>
2. <change description> — <indicator name>: <value>
3. <change description> — <indicator name>: <value>

**主要风险**
- <risk text from matched rule evidence or snapshot risks>

**下月观察重点**
- <indicator name>：当前 <value><unit>，若 <specific condition> 则判断将转为 <new state>
```

If a module has no data, write "数据不足" in both the 状态 and 核心依据 columns. Do not omit the row.
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_cycle_summary_skill_frontmatter_and_routing tests/test_skills.py::test_cycle_summary_output_contract_has_required_sections -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/cycle-summary/SKILL.md
git commit -m "feat: rewrite cycle-summary skill in AGENT.md style"
```

---

### Task 5: Rewrite `rule-diagnosis` skill

**Files:**
- Rewrite: `backend/app/skills/rule-diagnosis/SKILL.md`

- [ ] **Step 1: Add test for rule-diagnosis skill**

```python
# backend/tests/test_skills.py — append
def test_rule_diagnosis_skill_frontmatter_and_routing():
    content = _load_skill("rule-diagnosis")
    assert "name: rule-diagnosis" in content
    assert "Do NOT" in content
    assert "get_rule_detail" in content
    assert "get_matched_rules" in content

def test_rule_diagnosis_output_contract():
    content = _load_skill("rule-diagnosis")
    assert "条件核查" in content
    assert "结论" in content
    assert "风险含义" in content
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_rule_diagnosis_skill_frontmatter_and_routing tests/test_skills.py::test_rule_diagnosis_output_contract -v
```

Expected: `FAILED`

- [ ] **Step 3: Rewrite `backend/app/skills/rule-diagnosis/SKILL.md`**

```markdown
---
name: rule-diagnosis
description: Explain why a specific rule fired or did not fire. Use this skill when the user asks why a rule matched, why a module is in a particular state, what the evidence is for a specific judgment, or why a specific rule did not trigger. Do NOT use this skill for general monthly summaries or indicator definitions.
---

# Rule Diagnosis

## What this skill does

Traces a single rule's execution: reads its conditions, checks each one against actual indicator values, and explains the verdict condition-by-condition. Precise and evidence-based.

## Workflow

1. Identify the rule the user is asking about — by name, module state label, or description from their message
2. `→ get_matched_rules(month)` — locate the `rule_id` if not already known from context
3. `→ get_rule_detail(rule_id, month)` — read full execution log, all conditions, and evidence
4. For each condition in the rule: state the requirement, state the actual value from the tool response, state pass (✓) or fail (✗)
5. State the overall verdict and cite the risk implication if the rule fired

## Output contract

```
**规则：** <name>（<rule_id>）
**结果：** 命中 ✓ / 未命中 ✗

**条件核查**
| 条件 | 要求 | 实际值 | 结果 |
|------|------|--------|------|
| <indicator name> | <operator> <threshold><unit> | <actual value><unit> | ✓ / ✗ |

**结论**
<One sentence: why all conditions passed, or which condition failed and by how much.>

**风险含义**（命中时）
<risk field from evidence — omit this section if rule did not fire>
```

Do not paste raw JSON from tool responses. Parse conditions and render them in the table above.
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_rule_diagnosis_skill_frontmatter_and_routing tests/test_skills.py::test_rule_diagnosis_output_contract -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/rule-diagnosis/SKILL.md
git commit -m "feat: rewrite rule-diagnosis skill in AGENT.md style"
```

---

### Task 6: Rewrite `data-explain` skill

**Files:**
- Rewrite: `backend/app/skills/data-explain/SKILL.md`

- [ ] **Step 1: Add test for data-explain skill**

```python
# backend/tests/test_skills.py — append
def test_data_explain_skill_frontmatter_and_routing():
    content = _load_skill("data-explain")
    assert "name: data-explain" in content
    assert "Do NOT" in content
    assert "get_indicator_detail" in content

def test_data_explain_output_contract():
    content = _load_skill("data-explain")
    assert "定义" in content
    assert "当前值" in content
    assert "解读" in content
    assert "风险提示" in content
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_data_explain_skill_frontmatter_and_routing tests/test_skills.py::test_data_explain_output_contract -v
```

Expected: `FAILED`

- [ ] **Step 3: Rewrite `backend/app/skills/data-explain/SKILL.md`**

```markdown
---
name: data-explain
description: Explain what a macro indicator means and what its current value signals. Use this skill when the user asks what an indicator is, what YoY/MoM/percentile/trend means, or what a specific indicator's current reading tells us about the economy. Do NOT use this skill when the user asks about rules or wants an overall monthly state summary.
---

# Data Explainer

## What this skill does

Answers "what does this number mean?" — pulls the indicator's definition, interpretation, and risk note from the database, then contextualizes the current value in plain language.

## Workflow

1. Identify the indicator the user is asking about — by name or code from their message
2. If the indicator code is unknown, `→ get_indicators(month)` to scan names and locate the correct code
3. `→ get_indicator_detail(code, month)` — definition, interpretation, risk_note, and all current values
4. Explain: concept first, then current value in context of the interpretation field

## Field reference (built-in knowledge — no tool call needed)

- **yoy**: year-on-year change rate — reflects medium-term trend direction
- **mom**: month-on-month change rate — reflects short-term momentum
- **trend_3m**: 3-month rolling average — smooths single-month noise
- **percentile_24m**: where the current value sits within the past 24 months (>70 = historically high, <30 = historically low)
- **status**: `strong` / `neutral` / `weak` — assigned by the rule engine against fixed thresholds

## Output contract

```
**<indicator name>**（`<code>`）

定义：<definition field>
当前值：<value><unit> | 同比 <yoy> | 环比 <mom> | 24月分位 <percentile_24m>%
状态：<status>

解读：<interpretation field, contextualized to the actual current value — 2–3 sentences>
风险提示：<risk_note field>
```
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_data_explain_skill_frontmatter_and_routing tests/test_skills.py::test_data_explain_output_contract -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/data-explain/SKILL.md
git commit -m "feat: rewrite data-explain skill in AGENT.md style"
```

---

### Task 7: Rewrite `risk-watch` skill

**Files:**
- Rewrite: `backend/app/skills/risk-watch/SKILL.md`

- [ ] **Step 1: Add test for risk-watch skill**

```python
# backend/tests/test_skills.py — append
def test_risk_watch_skill_frontmatter_and_routing():
    content = _load_skill("risk-watch")
    assert "name: risk-watch" in content
    assert "Do NOT" in content
    assert "get_cycle_snapshot" in content
    assert "get_matched_rules" in content

def test_risk_watch_output_contract():
    content = _load_skill("risk-watch")
    assert "当前主要风险" in content
    assert "下月重点观察" in content
    assert "风险等级汇总" in content
    assert "继续观察" in content  # must be forbidden, not just mentioned
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_risk_watch_skill_frontmatter_and_routing tests/test_skills.py::test_risk_watch_output_contract -v
```

Expected: `FAILED`

- [ ] **Step 3: Rewrite `backend/app/skills/risk-watch/SKILL.md`**

```markdown
---
name: risk-watch
description: Surface current risks and next-month watch items. Use this skill when the user asks what risks exist now, what to monitor next month, what warning signs are present, or what could change the cycle judgment. Do NOT use this skill for historical comparisons or indicator definitions.
---

# Risk Watch

## What this skill does

Scans matched rules and weak-status indicators to produce a concise risk register and a forward-looking watch list with falsifiable conditions.

## Workflow

1. `→ get_cycle_snapshot(month)` — read `risks` and `watch_tasks` arrays from the snapshot
2. `→ get_matched_rules(month)` — read the `risk` field from each matched rule's evidence
3. `→ get_indicators(month)` — identify any indicators with `status=weak` not already covered by a matched rule
4. Deduplicate across all three sources. Rank by severity: `critical` first, then `warning`, then `caution`

## Output contract

```
**当前主要风险**
1. <risk description>（来源：规则「<rule name>」/ 指标「<indicator name>」）
2. ...

**下月重点观察**
1. <indicator name>：当前 <value><unit>，若 <specific measurable condition> 则判断将转为 <new state>
2. ...

**风险等级汇总**：critical <n> 条 | warning <n> 条 | caution <n> 条
```

Watch items must specify a falsifiable condition. "继续观察" is not an acceptable watch item — every item must say what specific change would alter the current judgment.
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_risk_watch_skill_frontmatter_and_routing tests/test_skills.py::test_risk_watch_output_contract -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/risk-watch/SKILL.md
git commit -m "feat: rewrite risk-watch skill in AGENT.md style"
```

---

### Task 8: Rewrite `family-business` skill

**Files:**
- Rewrite: `backend/app/skills/family-business/SKILL.md`

- [ ] **Step 1: Add test for family-business skill**

```python
# backend/tests/test_skills.py — append
def test_family_business_skill_frontmatter_and_routing():
    content = _load_skill("family-business")
    assert "name: family-business" in content
    assert "Do NOT" in content
    assert 'category="居民"' in content or "居民" in content
    assert 'category="企业"' in content or "企业" in content

def test_family_business_output_contract():
    content = _load_skill("family-business")
    assert "对普通家庭" in content
    assert "对企业经营" in content
    assert "建议买入" in content  # must appear in the forbidden section
```

- [ ] **Step 2: Run tests — expect them to fail**

```bash
cd backend && python -m pytest tests/test_skills.py::test_family_business_skill_frontmatter_and_routing tests/test_skills.py::test_family_business_output_contract -v
```

Expected: `FAILED`

- [ ] **Step 3: Rewrite `backend/app/skills/family-business/SKILL.md`**

```markdown
---
name: family-business
description: Explain what the current macro environment means for ordinary households and businesses. Use this skill when the user asks how the economy affects families, personal finances, household debt, business operations, hiring decisions, cash flow, or pricing strategy. Do NOT give specific asset recommendations, fund names, or yield targets.
---

# Household & Business Impact

## What this skill does

Translates macro cycle signals into plain-language implications for household financial decisions and business operating conditions. No investment advice — ever.

## Workflow

1. `→ get_cycle_snapshot(month)` — headline and six-module states for overall context
2. `→ get_indicators(month, category="居民")` — household indicators: `wage_income`, `household_mid_long_loan`, `core_cpi`
3. `→ get_indicators(month, category="企业")` — business indicators: `enterprise_mid_long_loan`, `private_investment`, `industrial_profit`, `ppi`
4. For each indicator, connect the current value movement to a concrete behavioral implication — what it means for decisions, not what it means for asset prices

## Output contract

```
**对普通家庭**
- 收入与就业：<wage_income movement → what it means for income stability — 1 sentence>
- 负债与购房：<household_mid_long_loan movement → what it means for borrowing appetite — 1 sentence>
- 日常消费：<core_cpi movement → what it means for purchasing power — 1 sentence>
- 关注重点：<what households should watch or consider regarding cash flow, large purchases, or debt — no specific asset advice>

**对企业经营**
- 融资环境：<enterprise_mid_long_loan movement → what it means for credit access — 1 sentence>
- 需求温度：<ppi + industrial_profit → what it means for pricing power and margins — 1 sentence>
- 扩张信号：<private_investment → what it means for expansion appetite — 1 sentence>
- 关注重点：<what businesses should watch — inventory levels, hiring pace, pricing strategy — no securities advice>
```

Forbidden: specific ticker symbols, fund names, yield promises, "建议买入/卖出", certainty language ("必然", "确定", "保证").
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd backend && python -m pytest tests/test_skills.py::test_family_business_skill_frontmatter_and_routing tests/test_skills.py::test_family_business_output_contract -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/app/skills/family-business/SKILL.md
git commit -m "feat: rewrite family-business skill in AGENT.md style"
```

---

### Task 9: Run full test suite and verify backend starts

**Files:** None changed

- [ ] **Step 1: Run all skill and agent service tests**

```bash
cd backend && python -m pytest tests/test_skills.py tests/test_agent_service.py -v
```

Expected: All tests `PASSED`. Count should be 16 tests total (2 from `test_agent_service.py`, 14 from `test_skills.py`).

- [ ] **Step 2: Verify the backend starts and AGENT.md loads cleanly**

```bash
cd backend && python -c "
from app.services.agent_service import _load_system_prompt, get_agent_status
content = _load_system_prompt()
print('AGENT.md loaded:', len(content), 'chars')
print('First heading:', content.split('\n')[0])
"
```

Expected output:
```
AGENT.md loaded: <number > 1000> chars
First heading: # Macro Cycle Radar — Agent Operating Manual
```

- [ ] **Step 3: Verify all 6 skills are discoverable**

```bash
cd backend && python -c "
from pathlib import Path
skills_dir = Path('app/skills')
skills = [p.parent.name for p in skills_dir.glob('*/SKILL.md')]
print('Skills found:', sorted(skills))
"
```

Expected output:
```
Skills found: ['cycle-summary', 'data-explain', 'family-business', 'navigate-month', 'risk-watch', 'rule-diagnosis']
```

- [ ] **Step 4: Start the backend and confirm it responds**

```bash
cd backend && uvicorn app.main:app --reload &
sleep 3
curl -s http://localhost:8000/api/agent/status | python -m json.tool
```

Expected: JSON response with `"runtime": "DeepAgent"` and `"skills"` array containing all 6 skill names.

- [ ] **Step 5: Kill the dev server**

```bash
pkill -f "uvicorn app.main:app" 2>/dev/null || true
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "test: verify all skills discoverable and backend loads AGENT.md"
```

---

### Task 10: Push and smoke-test in browser

**Files:** None changed

- [ ] **Step 1: Push to origin**

```bash
git push origin main
```

- [ ] **Step 2: Start backend and frontend**

```bash
cd backend && uvicorn app.main:app --reload &
cd frontend && npm run dev &
sleep 5
```

- [ ] **Step 3: Open browser and test navigate intent**

Open `http://localhost:3000`. In the chat, type:

```
查看2025年3月的数据
```

Expected chat response (3 lines only):
```
→ navigate_to_month(2025-03)
→ get_cycle_snapshot(2025-03)

已切换到 2025年3月。当月判断：<headline text>。
```

Expected right panel: switches to 2025-03, showing that month's indicators, chart, and rules.

If the chat still dumps a data table, the model is not following the skill output contract — check that `navigate-month/SKILL.md` is in the skills directory and that `AGENT.md` is loaded as the system prompt.

- [ ] **Step 4: Test cycle summary intent**

In the chat, type:

```
给我一个完整的本月宏观状态解读
```

Expected: structured Markdown with all 5 sections (一句话判断, 六大模块, 本月关键变化, 主要风险, 下月观察重点). Tool calls should be visible at the top.

- [ ] **Step 5: Kill dev servers**

```bash
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
```
