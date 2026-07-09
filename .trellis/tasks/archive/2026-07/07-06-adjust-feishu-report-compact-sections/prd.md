# Adjust Feishu Report Compact Sections

## Goal

Make Feishu daily report sections more compact and easier to scan.

## What I Already Know

- Eastmoney industry rows currently render stock leaders with the label `前三`.
- User wants the leader names kept, but without the literal `前三` label.
- User wants each Eastmoney industry to show all limit-up stocks in that industry.
- User wants stock labels formatted as `名字（几板）`.
- Core continuous-limit-up rows currently list every stock individually.
- User wants core continuous stocks grouped by board count instead of one stock per line.
- User wants rule risk assessment to include limit-up sealing time.

## Requirements

- Remove `前三` text from Eastmoney industry leader rendering.
- Remove `N 只涨停` text from Eastmoney industry row rendering.
- Render every stock in each Eastmoney industry as `名字（几板）`.
- Render `核心连板` grouped by `continuous_days`, such as `5板：国华退(000004)、*ST东智(002175)`.
- Add sealing-time risk factor to rule assessment.
- Rebalance rule assessment weights to keep total factor weight at 100%.
- Keep existing report data sources and sorting rules.
- Keep tests updated for Feishu card text.

## Acceptance Criteria

- [x] Feishu industry section no longer contains `前三`.
- [x] Feishu industry section renders every stock as `名字（几板）`.
- [x] Core continuous section groups stocks by board count.
- [x] Rule assessment includes sealing-time risk.
- [x] Existing Feishu report tests pass.
- [x] Full agent pytest suite passes.

## Out of Scope

- No database schema changes.
- No scheduling changes.

## Technical Notes

- Expected files: `services/agent/chain/stock/agents/feishu_notifier.py`, `services/agent/chain/stock/agents/risk_agent.py`, `services/agent/tests/`.
