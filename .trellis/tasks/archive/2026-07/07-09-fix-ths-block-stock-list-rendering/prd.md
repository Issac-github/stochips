# Fix THS block stock list rendering

## Goal

Make the Feishu `同花顺板块热度` section render real stocks from the THS `block_top.stock_list` payload instead of pretending the single leading stock is the full board stock list.

## What I Already Know

- The current Feishu rendering can output `芯片概念：华天科技`, because it falls back to `BlockTop.leading_stock_name` when no stock list is found.
- THS `block_top` records already contain a `stock_list` field in upstream payload examples.
- Current storage only extracts `stock_list[0]` into `leading_stock` and `leading_stock_name`; it does not persist the full list.
- Matching `BlockTop.block_name` against `LimitUpPool.block_name` is unreliable because concept board names and stock pool board names do not have a stable one-to-one match.
- User asked to proceed with the storage-backed fix and previously asked not to commit code in this round.

## Requirements

- Persist every stock from THS `block_top.stock_list` during `save_block_top`.
- Persist analysis-friendly fields from every `stock_list` item, including limit-up times, height text/code, price/change, reason labels/details, market/filter tags, and raw JSON.
- Use the persisted THS board stock list for Feishu `同花顺板块热度`.
- Remove the misleading fallback that displays one `leading_stock_name` as if it were the whole board list.
- Keep a graceful fallback for historical rows without stock-list details: show the original count/change/leader summary without any source label.
- Do not use `LimitUpPool.block_name` as the primary source for THS board stock expansion.

## Acceptance Criteria

- [x] New/updated schema stores all `stock_list` members per `(date, block_code, stock_code)`.
- [x] `block_top_stock` preserves reason, price/change, market/filter tags, limit-up times, and raw JSON for later analysis.
- [x] Feishu board lines render `板块：股票A（3板）、股票B（1板）` when stored board stocks exist.
- [x] Feishu board lines do not show `风口接口` or `涨停池聚合`.
- [x] Historical rows without board stock details render count/change/leader summary rather than a fake one-stock list.
- [x] Tests cover storage of multiple THS board stocks and Feishu formatting fallback behavior.

## Definition Of Done

- Python agent tests pass.
- Edited Python files compile.
- Trellis spec is updated if the implementation changes the persistent data contract.

## Out Of Scope

- Re-fetching historical data automatically.
- Changing frontend/RPC query shapes.
- Committing code in this round unless the user explicitly asks.

## Follow-on Requirement: Codex Daily Market Review

The user wants to replace the current per-stock rule score plus AI score/factor flow with
one daily Codex review. Codex must receive both the raw trading-system reference at
`services/agent/chain/wiki/raw/001-连板龙头交易体系.md` and the structured daily material
currently assembled for the Feishu report, then make its own qualitative market analysis.

Known implications:

- The current `assess-ai` command evaluates individual continuous-limit-up stocks and writes
  `risk_score`, `rule_score`, `ai_score`, `risk_factors`, and `ai_factors` to `risk_assessment`.
- The existing Feishu report already aggregates board heat, limit-up structure, continuous
  leaders, weak boards, breakouts, risks, opportunities, and fetch logs.
- The target design removes custom scoring/factor output from the new Codex flow.

Confirmed decision:

- Produce one persisted qualitative Codex review per trading date and append it to Feishu.
- Keep historical `risk_assessment` schema/rows for compatibility, but stop generating and
  displaying custom scores, risk levels, suggestions, and factors in the Codex daily flow.
- Keep `assess-ai [date] [--force-ai]` as the operational command: reuse the saved daily review
  by default and regenerate it with one fresh Codex call when `--force-ai` is present.
- The Codex SDK thread must use the Agent project directory as its read-only working directory,
  read `chain/wiki/raw/001-连板龙头交易体系.md` itself, and analyze the daily material assembled
  from the non-AI Feishu sections.
- Codex must also receive both THS stock reason fields: `reason_type` as the concise label and
  the unshortened `reason_info` as the detailed evidence. Keep the Feishu board list compact.
- The Feishu card keeps the factual market sections and appends the persisted Codex review.
- The scheduler runs one daily Codex review before the Feishu send; it no longer runs the old
  per-stock rule/AI score pipeline.
- The scheduler uses one ordered job: fetch complete data, finish Codex review, then send Feishu.
  No independent Feishu cron may race the analysis.
- Scheduled Feishu delivery uses a non-exact odd-minute send window after Codex completes.

Acceptance criteria:

- [x] One Codex call produces one daily report rather than one call per stock.
- [x] The Codex prompt instructs the read-only agent to read the trading-system Markdown file.
- [x] The prompt includes the same factual board/stock/log material used by the Feishu card.
- [x] The Codex-only reason supplement includes both `reason_type` and full `reason_info`.
- [x] Daily review text, actual provider/model metadata, and source material digest are persisted
  under a unique trading-date key.
- [x] Feishu no longer shows risk-score or suggestion distributions and appends the Codex review.
- [x] `--force-ai` replaces the persisted review; normal execution reuses it.
- [x] Existing historical risk tables remain readable but are not required by the new flow.
- [x] Scheduled Feishu delivery waits for successful, complete fetch and Codex review.
- [x] Scheduled Feishu delivery avoids exact-minute sends and prefers odd minutes.

## Technical Notes

- Main files: `services/agent/chain/stock/data/storage.py`, `services/agent/chain/stock/models/database.py`, `services/agent/chain/stock/agents/feishu_notifier.py`.
- Schema seed files live in `services/agent/init.sql` and `services/agent/docker/mysql/init/01-schema.sql`.
- Migrations live under `services/agent/migrations/`.
