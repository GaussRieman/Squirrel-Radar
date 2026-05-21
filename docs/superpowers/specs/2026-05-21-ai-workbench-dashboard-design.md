# AI Workbench Dashboard Design

## Goal

Turn the product from a dense BI-style macro dashboard into an AI analysis workbench.

The center column is the primary Agent conversation. The right column is not a second answer area; it is a persistent cycle dashboard for information that is awkward or wasteful inside chat: status cards, trend charts, historical comparison tables, and official source links.

## Layout Decision

The app uses three columns:

1. Asset sidebar: recent analyses and reusable topics.
2. Agent workspace: streaming conversation, workflow steps, and the main input.
3. Cycle dashboard: current-month data surface that updates with the selected month.

The right dashboard has exactly three vertical regions:

1. Current cycle status cards.
2. One combined trend chart for all indicators.
3. Historical comparison and source table.

Tabs were intentionally removed because they hid complexity instead of reducing it.

## Right Dashboard Content

### Top: Cycle Status Cards

Show only the current period's core module states. Each card is compact and clickable. Clicking a card fills the Agent input with an explanation request for that module.

The card should answer:

- What module is this?
- What is the current state?
- Can I ask the Agent to explain it?

It should not duplicate long rule explanations or indicator tables.

### Middle: Combined Indicator Trends

All indicators are shown in one normalized trend chart for quick comparison.

Normalization is `0-100` within each indicator's visible history window, so indicators with different units can be compared in one chart. Tooltips keep values short with roughly 4-5 significant digits to avoid unreadable hover panels.

The chart is the main reason the right side exists: it gives visual memory across the current cycle and recent history.

### Bottom: Historical Comparison Table

The table focuses on verification and comparison:

- current value
- previous period value
- 3-period average
- 24-period percentile
- status
- official source link

The source link must point to the real data page wherever available so the user can verify the indicator.

## Agent Output Rules

The Agent should not dump full indicator tables or module dashboards into the chat. Chat output should focus on:

- direct answer to the user's question
- short reasoning chain
- cited key facts
- next action when useful

Structured data remains on the right dashboard.

## Implementation Notes

- `frontend/components/AgentCanvas.tsx` now renders the cycle dashboard.
- `frontend/components/HomeChat.tsx` listens for dashboard context clicks and turns them into Agent prompts.
- `frontend/app/page.tsx` keeps the three-column workbench.
- `frontend/app/globals.css` defines the workbench, compact status cards, combined chart, and dashboard table styles.

## Validation

- Frontend typecheck must pass with `npm run typecheck`.
- Runtime database sidecar files such as `macro_cycle_radar.db-shm` and `macro_cycle_radar.db-wal` are development artifacts and should not be committed.
