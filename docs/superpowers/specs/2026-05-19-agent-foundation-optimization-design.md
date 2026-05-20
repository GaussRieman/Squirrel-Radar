# Agent Foundation Optimization Design

**Date:** 2026-05-19

**Goal:** Make the current SquirrelRadar Agent foundation reliable before adding heavier Claude Code / Codex style streaming interactions. This pass fixes broken prompt plumbing, restores test health, improves skill routing inputs, preserves richer UI context, and makes model failure semantics honest.

## Current Problems

1. The canonical prompt has moved to `backend/app/prompts/AGENT.md`, but `backend/app/services/prompt_service.py` still points to the removed `agent_interpretation_prompt.md`.
2. Tests still assert the old prompt language and fail against the current `AGENT.md`.
3. `_run_deep_agent` prepends every user request with "generate a macro cycle interpretation", which biases routing toward `cycle-summary` even when the user asks for navigation, indicator explanation, or rule diagnosis.
4. The frontend passes useful selected context, but the backend only keeps a small subset of it. Important identifiers such as `code`, `rule_id`, `month`, and actual values are lost before the model sees them.
5. DeepAgent exceptions are returned as normal `deepagent` content, even though the status text says failures fall back to mock output.
6. `get_agent_status()` omits `navigate_to_month`, so runtime introspection is slightly misleading.

## Scope

This pass is intentionally small and foundation-focused.

In scope:

- Prompt service compatibility with `AGENT.md`
- Test updates for the current prompt contract
- Better user-message construction for DeepAgent
- Richer selected-context injection
- Honest model failure fallback
- Agent status accuracy

Out of scope for this pass:

- SSE / streaming token output
- Interruptible runs
- Full structured tool event timeline
- New right-panel action tools beyond the existing `navigate_to_month`
- Long-term project memory UI

## Backend Design

### Prompt Loading

`prompt_service.py` should read `AGENT.md`. The existing function name `load_agent_interpretation_prompt()` can remain for compatibility, but its implementation should point to the current operating manual.

### User Message Construction

The DeepAgent input should preserve the user's actual intent. Instead of always beginning with "please generate a macro cycle state interpretation", construct the message as:

- current dashboard month
- user original question, if present
- if no question is present, an explicit default request to generate the monthly summary
- selected context as compact JSON, if present

This keeps dashboard context available without forcing every request into summary mode.

### Selected Context

When the user clicks an indicator or rule on the right panel, the backend should pass the selected context through with its identifiers and values. This lets skills select the correct tool call:

- indicator context: `code`, `name`, `month`, values, status
- rule context: `rule_id`, `name`, `month`, `matched`, evidence, risk

### Failure Semantics

If DeepAgent raises an exception, `_run_deep_agent` should return no content plus an error string. `generate_interpretation()` should then return mock content with a short failure note appended, or otherwise mark the response as non-DeepAgent. This prevents "model failed" from being labeled as successful model output.

### Runtime Status

`get_agent_status().tools` should include every tool actually exposed to DeepAgent, including `navigate_to_month`.

## Tests

Update tests to assert the current `AGENT.md` sections:

- `SquirrelRadar`
- `Agent Operating Manual`
- `Intent Judgment`
- `Progressive Skill Loading`
- `Self-Check Before Responding`

Run `uv run pytest` from `backend/`.

## Acceptance Criteria

- Backend tests pass.
- `prompt_service.py` no longer references deleted prompt files.
- A user asking an indicator question is not pre-biased into a monthly summary.
- Selected indicator and rule context reaches the model with stable identifiers.
- Model failure does not return `mode: deepagent`.
- Agent status lists `navigate_to_month`.

## Next Pass

After this foundation pass, the next design should focus on Codex-like interaction events:

- streaming assistant text
- visible skill selection
- visible tool calls and tool results
- right-panel workspace actions such as highlighting indicators or opening rule detail
- a stable thread-level memory model independent from the selected month
