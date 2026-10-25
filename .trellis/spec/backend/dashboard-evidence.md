# Strategy evidence readiness

## 1. Scope / Trigger
`dashboard/strategy_evidence.py` measures modeled market coverage and describes existing report facts/candidates. It must not classify complete trading patterns, mutate market tables or confuse an unintegrated adapter with an empty database.

## 2. Signatures
- `GET /api/strategy-evidence?date=YYYY-MM-DD` requires the existing Feishu session.
- `ReportService.strategy_evidence(target_date)` reuses `report(target_date)` then calls `build_strategy_evidence(sessions,target_date,report)`.
- Response `{date,coverage,concepts}`. No new env keys or market schema.
- Catalog concepts declare `kind: fact|candidate|pattern|manual`, `sources: DatasetKey[]`, `requirements: string[]`, `checks: string[]`. Checks are a generic checklist, never evidence that data is actually missing.

## 3. Contracts
- `coverage[]`: `{source,label,rows,dates,stocks,first_date,last_date,positive_price_rows,positive_volume_rows}`. All SQL aggregates bound `date <= selected_date`; never use future observations. Dates are ISO/null, counts are nonnegative integers. Volume count null means this modeled source does not collect volume; zero means no positive values. Positive price/volume counts do not establish validity of shape, units or historical extremes.
- Modeled sources: continuous_limit_up, limit_up_pool, eastmoney_zt_pool, block_top_stock, lower_limit_pool. Pool event rows are not continuous per-stock OHLCV. Distinct observed dates are not complete trading-day coverage; sources may overlap.
- Capability state `available|partial|missing|not_integrated`. Historical positive volume/price observations remain partial because non-pool days and units/continuity are not verified. Zero positive volume is missing usable volume. No modeled daily-bars/auction/intraday adapter -> not_integrated, not a claim that every table in the DB was scanned or contains no such data.
- Each concept returns `{key,kind,status,explanation,source_counts:[{dataset,rows}],stock_count,requirements:[{key,label,state,detail}]}`. Related stock counts deduplicate six-digit codes; assist sources use candidate stock.code, not the leader. Source records/counts are not pattern matches or independent market capacity.
- Fact concepts with records -> facts_available; existing report candidates with codes -> candidate; empty fact/candidate observations -> no_observations, never a negative market conclusion. Manual risk notes -> manual. Pattern concepts with insufficient capabilities -> data_gap; even if all capabilities become available -> not_implemented until a real classifier is built. No automatic platform label from breakout_stocks, no volume inference from turnover.
- Labels distinguish existing fact, candidate pending validation, no related observations, evidence gap, unimplemented recognition and manual record. For complete patterns, retain explicit recognition-not-implemented explanation alongside evidence readiness. Required input coverage is not proof the semantic pattern exists.
- React validates response in strategyEvidenceData.ts, checks date, aborts stale requests, clears old coverage on load/failure and never falls back to static judgment. Failure leaves raw report/manual workflows usable and tags as state-unavailable. Parent date/refresh keys reset the state. Coverage table scrolls internally on mobile.
- No query body/config secrets are returned. API auth before access and no-store headers follow report routes. No new external fetching, trading orders, scores or provider calls.

## 4. Validation & Error Matrix
| Trigger | Behavior |
| --- | --- |
| Missing/blank/duplicate/invalid date | 400 |
| Unauthenticated session | 401 before any report/coverage queries |
| No report sources at date | 404 |
| Database/query unavailable | 503 generic error; no false missing-data result |
| Valid pools but missing volume | 200 measured zero positive-volume count |
| No full daily/auction/intraday adapter | not_integrated with explicit scope |
| UI request failure/date mismatch | Clear coverage and judgments; retry available |

## 5. Good / Base / Bad Cases
- Good: show nonzero related price/board/core facts while explaining no usable volume or integrated full candles for a platform assessment.
- Base: zero observations display as no related observations, without equating absence with a failed strategy condition.
- Bad: fixed 待人工核对 on every card, static DB-missing claims from catalog prose, claiming complete OHLC from three months of sparse pool records, classifying a platform solely from a prior chain high, counting future rows.

## 6. Tests Required
- `services/agent/.venv/bin/python -m pytest dashboard/test_strategy_evidence.py dashboard/test_server.py dashboard/test_auth.py dashboard/test_watchlist.py -q` checks bounded queries/SELECT-only, zero vs uncollected, sparse positive volume remaining partial, all catalog keys, no automatic full-pattern confirmation even with available inputs, distinct candidate codes, authenticated/no-store HTTP, bad dates and generic failure.
- `cd dashboard && npm run lint && npm run build && npm test`: shared metadata and evidence schema contracts, zero/null distinction and rejection of invented confirmation statuses.
- Browser: live coverage/fact/candidate/no-observation/gap states, switching dates and failed query clearing old results, 375px table/card layout and no page overflow.

## 7. Wrong vs Correct
Wrong: render `catalog.missing` as proof of DB absence and always show 待人工核对.

Correct: read the authenticated bounded coverage endpoint, distinguish unintegrated adapters from zero usable fields, display actual related facts and clearly separate readiness from unimplemented semantic recognition.
