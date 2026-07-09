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

- [ ] New/updated schema stores all `stock_list` members per `(date, block_code, stock_code)`.
- [ ] `block_top_stock` preserves reason, price/change, market/filter tags, limit-up times, and raw JSON for later analysis.
- [ ] Feishu board lines render `板块：股票A（3板）、股票B（1板）` when stored board stocks exist.
- [ ] Feishu board lines do not show `风口接口` or `涨停池聚合`.
- [ ] Historical rows without board stock details render count/change/leader summary rather than a fake one-stock list.
- [ ] Tests cover storage of multiple THS board stocks and Feishu formatting fallback behavior.

## Definition Of Done

- Python agent tests pass.
- Edited Python files compile.
- Trellis spec is updated if the implementation changes the persistent data contract.

## Out Of Scope

- Re-fetching historical data automatically.
- Changing frontend/RPC query shapes.
- Committing code in this round unless the user explicitly asks.

## Technical Notes

- Main files: `services/agent/chain/stock/data/storage.py`, `services/agent/chain/stock/models/database.py`, `services/agent/chain/stock/agents/feishu_notifier.py`.
- Schema seed files live in `services/agent/init.sql` and `services/agent/docker/mysql/init/01-schema.sql`.
- Migrations live under `services/agent/migrations/`.
