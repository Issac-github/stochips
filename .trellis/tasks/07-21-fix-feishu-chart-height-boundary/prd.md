# Fix Feishu Chart Height Boundary

## Goal

Prevent Feishu from rejecting the daily limit-up report when a dense horizontal chart reaches the platform height limit.

## Requirements

- Cap generated horizontal chart heights at `999px`, the documented maximum accepted by the Feishu Card 2.0 chart component.
- Preserve the existing dynamic height formula and all chart data rows.
- Update tests and backend guidance so they describe the same boundary.

## Acceptance Criteria

- [x] `_horizontal_chart_height(32)` remains `"976px"`.
- [x] `_horizontal_chart_height(33)` returns `"999px"` instead of `"1000px"`.
- [x] Larger item counts also return `"999px"` without truncating chart data.
- [x] Focused Feishu notifier tests pass.

## Definition of Done

- Implementation, tests, and backend specification agree on the `999px` maximum.
- Relevant tests pass.

## Technical Approach

Change the upper bound in `_horizontal_chart_height` from `1000` to `999`, update its explanation, and strengthen the boundary test around 32/33 rows.

## Decision (ADR-lite)

**Context**: Feishu rejects `height: "1000px"` with error `200551`. Its Card 2.0 chart documentation permits `auto` or `[1,999]px`.

**Decision**: Use `999px` as the hard maximum while retaining the existing per-row sizing formula.

**Consequences**: Dense charts remain valid and retain all data, though their rendered labels may be more compact at the maximum height.

## Out of Scope

- Redesigning or paginating the report charts.
- Changing chart data selection or ordering.
- Sending a live Feishu webhook during tests.

## Technical Notes

- Implementation: `services/agent/chain/stock/agents/feishu_notifier.py`
- Tests: `services/agent/tests/test_feishu_notifier.py`
- Contract: `.trellis/spec/backend/error-handling.md`
- Official chart height range: <https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-json-v2-components/content-components/chart>
