# Database Guidelines

## Schema Source Of Truth

Python SQLAlchemy models in `agent/chain/stock/models/database.py` define the application schema used by the stock agent:

- `continuous_limit_up`
- `block_top`
- `limit_up_pool`
- `lower_limit_pool`
- `eastmoney_zt_pool`
- `risk_assessment`
- `daily_market_review`
- `daily_job_run`
- `data_fetch_log`

Migrations live in `agent/migrations/`. The Go task table is added by `agent/migrations/20260522_add_rpc_tasks.sql`, and `services/stock-rpc/internal/tasks/sql_store.go` depends on that `rpc_tasks` schema.

When adding a column or table, update all relevant places together:

- SQLAlchemy model in `agent/chain/stock/models/database.py`
- migration SQL under `agent/migrations/`
- storage normalization in `agent/chain/stock/data/storage.py` if Python writes the data
- Go query JSON adapters in `services/stock-rpc/internal/query/repository.go` if the frontend reads the data
- frontend global types and validators if the JSON contract changes

## Storage Writes

Use `StockDataStorage` for stock data writes. It already centralizes:

- safe numeric conversion through `_safe_decimal` and `_safe_int`
- field alias handling through `_first_value`
- nested list fallback extraction through `_first_list_item` when an upstream row embeds leader stocks
- business-key upserts through `_upsert_by_keys`
- per-data-type save counts and fetch logs
- session commit/rollback/close behavior

Do not use `session.merge` for records keyed by `(date, code)` or `(date, block_code)`. The current project uses explicit business-key lookup because `merge` only reasons about primary keys and can create duplicates.

## Scenario: Stock Data Fetch, Storage, And Feishu Report Flow

### 1. Scope / Trigger
- Trigger: changing THS/Eastmoney fetchers, storage normalization, MySQL report tables, scheduled daily jobs, or Feishu daily report content.
- Python owns the whole business flow. Go RPC may dispatch Python commands or read rows, but must not reimplement stock fetch, scoring, or report-generation rules.

### 2. Signatures
- CLI:
  - `python main.py fetch [YYYYMMDD]`: fetches all configured stock data and upserts MySQL rows.
  - `python main.py assess-ai [YYYYMMDD] [--force-ai]`: generate or reuse one qualitative Codex daily review in `daily_market_review`.
  - `python main.py assess` and `python main.py ai-analyze`: compatibility aliases for the same daily review command.
  - `python main.py notify-feishu [YYYYMMDD]`: builds and sends the Feishu report from MySQL rows.
  - `python main.py schedule`: workday scheduler that dispatches the above commands in order.
- THS upstream endpoints:
  - `/dataapi/limit_up/continuous_limit_up` -> `continuous_limit_up`
  - `/dataapi/limit_up/block_top` -> `block_top`
  - `/dataapi/limit_up/limit_up_pool` -> `limit_up_pool`
  - `/dataapi/limit_up/lower_limit_pool` -> `lower_limit_pool`
- Eastmoney upstream endpoint:
  - `fetch_eastmoney_zt_pool` -> `eastmoney_zt_pool`

### 3. Contracts
- `continuous_limit_up` is the source for 连板梯队, 核心连板, 最高板, and historical chain segments used by the 涨停前高突破 signal.
- `block_top` is the THS 最强风口 table. It should store:
  - `code` -> `block_code`
  - `name` -> `block_name`
  - `limit_up_num` -> `stock_count`
  - `change` -> `change_percent`
  - `stock_list[0].code` -> `leading_stock`
  - `stock_list[0].name` -> `leading_stock_name`
  - `stock_list[0].first_limit_up_time` -> `avg_limit_up_time` fallback
- `block_top_stock` stores every member from THS `block_top.stock_list`, keyed by `(date, block_code, code)`. It is the source for expanding `同花顺板块热度` stock lists in Feishu and should preserve analysis fields: first/last limit-up time, `continue_num`, `high`, `high_days`, `change_rate`, `latest`, `reason_type`, `reason_info`, `concept`, `market_id`, `market_type`, `is_new`, `is_st`, `change_tag`, and raw JSON.
- `limit_up_pool` is the THS 涨停强度 table. It stores limit-up type, first/last limit-up time, `open_num` as open count (`null` means no open-count data), seal strength/amount, volume ratio, turnover rate, `currency_value` as circulating market value, `reason_type` as the concise reason label, `reason_info` as the detailed reason, and optional block name.
- `lower_limit_pool` is the THS 跌停池 table, keyed by `(date, code)`. Store first/last limit-down time, change rate, turnover rate, circulating market value, market flags, `time_preview`, and raw JSON. A successful fetch with zero rows is a valid market fact; an upstream error must write `data_fetch_log.status='failed'`, never a zero-row success.
- `eastmoney_zt_pool` is the Eastmoney 涨停池 table. Feishu uses its `block_name` as the industry/sector dimension and reports all grouped industries, not Top 10.
- `fetch_all_data` must not save or advance stale holiday data. If the target date is a weekend, or THS payload timestamps prove the upstream returned a different trading date, return `skipped=True` with `skip_reason`; `save_all_data` writes `data_fetch_log.status='skipped'` for every data type and does not upsert stock rows.
- Feishu report ownership:
  - THS tables drive short-term structure: limit-up overview, limit-down overview and full 跌停池, 连板梯队, 核心连板, 一字板明细, 早盘强势, 分歧弱板, 涨停前高突破, 昨日高标反馈, 同花顺板块热度, and 热点板块交集. 东财只提供独立的行业涨停交叉视图。
  - Eastmoney drives the independent `东财行业涨停` section by grouping `eastmoney_zt_pool.block_name`.
  - Board/industry, early-strength, weak-board, and overlap sections are all-item summaries. 涨停前高突破 renders every qualifying stock, grouped into non-overlapping windows of `<=5`, `6-10`, `11-30`, and `31-60` trading days after the previous limit-up chain.
  - `同花顺板块热度` should keep the board summary and then render every stock available from `block_top_stock` for each THS board. Use compact labels with board count, not source labels: `板块：31 家涨停，涨幅 3.22%，股票A（3板）、股票B（1板）`. Do not match `block_top.block_name` against `limit_up_pool.block_name` to infer concept-board membership; those names are not a stable one-to-one contract.
  - `热点板块交集` derives from `block_top_stock` codes only. It reports every significant pairwise member intersection and each board's overlap ratio, so Codex does not sum overlapping concept labels as independent market capacity.
  - Prefer THS `stock_list[].high` as the Feishu stock label when available, e.g. `华天科技（3天2板）`; fall back to `continue_num` as `N板`.
  - If historical `block_top` rows have no `block_top_stock` details yet, Feishu should render the count/change/leader summary without source labels. Do not present `leading_stock_name` alone as if it were the full stock list.
  - `东财行业涨停` should render all grouped industries and all limit-up stocks within each industry. Use compact stock labels with board count, not codes or `前三`: `行业：股票A（3板）、股票B（1板）`.
  - Card presentation uses a scan-first Markdown summary followed by native Card 2.0 tables for THS board heat, continuous ladders, Eastmoney industries, and the lower-limit pool. Tables contain every available row and show at most 10 rows per page; they do not change the underlying facts.
  - `核心连板` should group by `continuous_days` rather than render one line per stock, e.g. `5板：国华退(000004)、*ST东智(002175)`.
  - `block_top_stock.limit_up_type` values such as `3天2板` are phase-height labels, not `continuous_days`. Codex may discuss them separately, but must not place them in continuous-board ladders or call them consecutive 2-board stocks.
- Daily review ownership:
  - `FeishuStockNotifier.build_analysis_material` renders the complete factual material for Codex input. `build_card` has a separate condensed presentation layer so card tables do not truncate or alter Codex facts.
  - `FeishuStockNotifier.build_codex_reason_material` adds analysis-only THS stock reasons without expanding the Feishu card: `reason_type` is the concise reason label and `reason_info` is the complete detailed reason. Preserve both and do not shorten `reason_info` before Codex receives it.
  - Include reason fields from both `block_top_stock` and all same-day `limit_up_pool` rows. `早盘强势` sorts THS `first_limit_up_time`; `分歧弱板` first uses THS `open_count`, then may render an explicitly labeled inferred sample when THS first/last limit-up times show a later final seal.
  - Codex also receives a previous-trading-day comparison: prior overview, structure, core continuous stocks, all hot boards, all same-name board count changes versus today, plus the complete prior-day factual and reason material. Do not treat yesterday's facts as today's facts.
  - `DailyMarketReviewAgent` must read the complete document configured by `DAILY_REVIEW_STRATEGY_PATH` in Python and include it in the Codex prompt before analyzing the factual material. The strategy text is analysis methodology rather than market fact, and missing intraday fields must remain observation conditions.
  - The active daily flow must not calculate or display programmatic scores, weights, risk factors, risk levels, or suggestion distributions.
  - Historical `risk_assessment` rows remain compatibility data only; active CLI, scheduler, StockAgent, and Feishu paths do not write or consume them.
- Scheduler default:
  - 16:03 starts one ordered workflow; scheduled fetch adds `STOCK_FETCH_START_JITTER_MIN/MAX` seconds before upstream calls.
  - `fetch_all_data` calls THS/Eastmoney sources sequentially and waits `STOCK_FETCH_SOURCE_DELAY_MIN/MAX` seconds between sources.
  - THS paginated `limit_up_pool` waits `STOCK_FETCH_PAGE_DELAY_MIN/MAX` seconds between pages.
  - Only after fetch succeeds with complete data, run one Codex daily review when `AI_PROVIDER=codex`.
  - Only after that review returns successfully, send the Feishu report when `FEISHU_WEBHOOK_URL` is configured; Feishu has no independent cron job. Formal reports, failure status cards, and webhook rate-limit retries send immediately only in a non-exact odd minute; otherwise they wait for the next odd minute plus a small random offset.
  - `daily_job_run` persists the date-keyed workflow stage (`fetch`, `review`, `notify`), status, attempts, retry time, and last error. The scheduler retries every failed stage twice after 5 minutes and 15 minutes, and startup requeues today's interrupted/retrying row from its saved stage. Do not replay a prior trading date after recovery.
  - Each intermediate failure sends a Feishu status card with the planned retry time. Use `FEISHU_ALERT_WEBHOOK_URL`/`FEISHU_ALERT_WEBHOOK_SECRET` for failure cards when configured; otherwise fall back to the formal report bot. Final failure sends a status card and skips the formal report.
  - all scheduled jobs run Monday-Friday only.
  - Codex review and Feishu report jobs must check `data_fetch_log.status='skipped'` for the target date and exit when fetch marked the day as non-trading/stale.

### 4. Validation & Error Matrix
- `block_top` rows exist but `stock_count=0`, `change_percent IS NULL`, and leader fields are blank -> inspect raw THS `block_top` payload and update alias mapping in `StockDataStorage.save_block_top`; do not add columns unless the existing schema cannot represent the value.
- `block_top` has no usable counts and `limit_up_pool.block_name` is also blank -> Feishu should show `同花顺板块热度` as unavailable and direct users to `东财行业涨停`.
- `limit_up_pool.open_count=0` -> do not include the stock in `分歧弱板`; high turnover alone is not a weak-board signal.
- `limit_up_pool.limit_up_time` is blank -> `早盘强势` may be empty; render `暂无早盘强势数据` and a data warning. Basic fetch completeness does not mean analysis fields are complete.
- `daily_market_review` has no target-date row -> Feishu should keep all factual sections and mark the Codex review as not generated.
- `data_fetch_log.status='skipped'` exists for the target date -> do not run the Codex review or Feishu report for that date.

### 5. Good/Base/Bad Cases
- Good: THS `block_top` payload with `limit_up_num=43`, `change=2.377`, and `stock_list[0]` leader data writes a complete `block_top` row and Feishu can show 同花顺板块热度.
- Base: THS short-term structure and Eastmoney industry grouping are usable, but the Codex review has not run; Feishu reports facts and marks the review unavailable.
- Bad: Treat Eastmoney `block_name` as a replacement for THS 最强风口. It is an industry/sector grouping and must remain a separate report section.
- Bad: Save Eastmoney rows under the requested holiday date when THS proves the upstream response belongs to the previous trading day.
- Bad: Store derived Feishu-only signals in new tables before the rule is stable. Prefer real-time derivation from existing fact tables until frontend query, backtest, or rule-version requirements exist.

### 6. Tests Required
- Storage mapping tests should assert THS `block_top` aliases:
  - `limit_up_num` becomes `stock_count`
  - `change` becomes `change_percent`
  - `stock_list[0].code/name` becomes leader fields
  - all `stock_list` members and their analysis fields are persisted to `block_top_stock`, including `reason_info` and raw JSON
- Feishu report tests should assert:
  - `同花顺板块热度` and `东财行业涨停` are separate sections
  - board/industry section titles do not say Top 10
  - `同花顺板块热度` rows do not include source labels such as `风口接口` or `涨停池聚合`, and render every `block_top_stock` member as `名字（几板）`
  - Card 2.0 tables keep the full source row list while setting `page_size` to at most 10, and the Markdown summary plus persisted review metadata remain present.
  - `同花顺板块热度` fallback rows summarize count/change/leader instead of showing a one-stock fake list
  - Eastmoney industry rows do not include `前三` or `N 只涨停`, and render every stock as `名字（几板）`
  - 核心连板 groups stocks by board count instead of repeating per-stock risk text
  - `分歧弱板` requires `open_count > 0`
  - 涨停前高突破 uses successful `data_fetch_log` `limit_up_pool` dates as the trading-date sequence (with historical pool-date fallback), looks back 60 trading days, renders all qualifying stocks in the four trading-day windows, and renders the gap as trading days
  - THS `first_limit_up_time`, `last_limit_up_time`, `reason_type`, and `reason_info` map into the stored pool fields and Codex material; early-strength ordering must not depend on Eastmoney time fields
- Fetch guard tests should assert:
  - weekend target dates return `skipped=True` before network calls
  - THS timestamp dates different from the requested date skip save/downstream flow
  - THS empty plus Eastmoney non-empty is treated as unverified/stale and skipped
  - source fetches run sequentially with configured source delays, not `asyncio.gather`
  - paginated THS fetches use configured page delays between pages
- Daily review tests should assert one Codex call per date, cached reuse, forced replacement, strategy-file instruction, factual-material inclusion, and no legacy score schema.
- Docker/scheduler changes should still pass `docker compose config --quiet` and `python3 -m py_compile` for edited Python files.
- Scheduler tests should assert default data fetch and Feishu report cron times stay away from exact hour/half-hour peaks.

### 7. Wrong vs Correct

Wrong:

```python
"stock_count": self._safe_int(self._first_value(item, "stock_count", "count"))
"leading_stock": self._safe_str(self._first_value(item, "stock_code"))
```

Correct:

```python
leader = self._first_list_item(item, "stock_list")
"stock_count": self._safe_int(self._first_value(item, "stock_count", "count", "limit_up_num"))
"change_percent": self._safe_decimal(self._first_value(item, "change_percent", "change"))
"leading_stock": self._safe_str(leader.get("code"))
"leading_stock_name": self._safe_str(leader.get("name"))
```

Wrong:

```text
板块热度 Top 10
东财行业涨停 Top 10
```

Correct:

```text
同花顺板块热度
东财行业涨停
专用设备：测试设备（3板）、龙头设备（1板）
核心连板
5板：国华退(000004)、*ST东智(002175)
```

## Scenario: Codex Daily Market Review

### 1. Scope / Trigger
- Trigger: changing the daily Codex review, shared Feishu material, persistence, CLI, or schedule.

### 2. Signatures
- Primary provider: `AI_PROVIDER=codex`; optional fallback: `AI_FALLBACK_PROVIDER=moonshot`.
- Python clients: `CodexSubscriptionClient.review(prompt) -> str` and the OpenAI-compatible `MoonshotReviewClient.review(prompt) -> str`, both with no output schema.
- Moonshot fallback uses `MOONSHOT_MODEL`, whose default is `kimi-k2.5`, and `MOONSHOT_CONTEXT_WINDOW=262144`. It uses the same source material and prompt as the Codex primary call, but must reserve `MOONSHOT_MAX_TOKENS` and fail clearly when its conservative input budget estimate exceeds the remaining context.
- The Kimi daily-review fallback always sends `temperature=1`; it must not inherit `MOONSHOT_TEMPERATURE`, which remains a legacy-analysis setting. Kimi K2.5 rejects any other temperature.
- Agent: `DailyMarketReviewAgent.run(date, force=False) -> DailyMarketReviewResult`.
- CLI: `python main.py assess-ai [date] [--force-ai]`; `assess` and `ai-analyze` are compatibility aliases.
- Strategy document: required `DAILY_REVIEW_STRATEGY_PATH`; relative paths resolve from the Agent project root and absolute paths are accepted.
- DB: `daily_market_review` has one unique row per `date`, with `content`, `provider`, `model`, `strategy_path`, and `source_material_digest`.

### 3. Contracts
- `Codex()` owns the local app-server connection and ChatGPT OAuth under the `/root/.codex` Docker volume. Python must not log OAuth tokens, browser cookies, or subscription Bearer headers.
- Codex runs with `Sandbox.read_only`, `ApprovalMode.deny_all`, an ephemeral thread, and the Agent project root as `cwd`, so it can read the strategy Markdown included in the Docker image.
- The program obtains the strategy path only from configuration, checks that it exists, reads its complete UTF-8 content, and includes only the content in the prompt. This avoids relying on Codex file-tool sandboxing inside Docker while preserving the SDK `read_only` sandbox and denied approvals. The digest covers both the strategy text and factual material so persisted metadata changes when either input changes.
- The prompt must wrap strategy text in a path-free internal-methodology tag and forbid mentioning the methodology, document source, filename, path, or original content in model output. Every review conclusion must cite daily factual material; strategy-dependent fields absent from that material remain `数据不足` or `盘中/竞价待观察`.
  - `build_analysis_material` is the compact factual text contract shared by model input and Feishu. Codex additionally receives `build_codex_reason_material`, which deduplicates all same-day THS board and pool stocks while retaining every distinct `reason_type` and full `reason_info`, then lists every THS `limit_up_pool` row with its change, board type, first/last limit-up time, open count, and turnover rate. Neither material includes saved review text, scores, factors, or suggestions.
- Codex returns concise free-form Markdown, not JSON. Persist the actual provider/model and render that saved metadata in Feishu.
- Normal execution reuses the target-date row. `--force-ai` makes exactly one new Codex call and replaces that row.
- Historical `risk_assessment` data is not dropped, but it is not part of the active daily review.

### 4. Validation & Error Matrix
- `AI_PROVIDER` is not `codex` -> CLI exits clearly and scheduler skips the review.
- `DAILY_REVIEW_STRATEGY_PATH` missing or blank -> fail before the model call with a clear configuration error.
- Strategy file missing -> fail before the model call with the resolved missing path.
- Codex login/runtime unavailable, timeout, subscription limit, or empty text -> when `AI_FALLBACK_PROVIDER=moonshot` and `MOONSHOT_API_KEY` are configured, retry the exact same full prompt with Moonshot; otherwise fail without replacing a saved report. Never downgrade to the legacy Moonshot scorer.
- Both Codex and Moonshot fallback fail -> raise one error containing both provider failures; do not save a partial review.
- Moonshot prompt estimate exceeds `MOONSHOT_CONTEXT_WINDOW - MOONSHOT_MAX_TOKENS` -> fail before the HTTP request with the estimated input, available input, context window, and output reservation; never silently truncate material.
- Moonshot fallback request -> send `temperature=1`; do not send the configurable legacy `MOONSHOT_TEMPERATURE` value.
- Codex default-model lookup fails after successful analysis -> keep the analysis and render `Model: default`.
- Existing target-date `daily_market_review` -> reuse it unless `--force-ai` is present.

### 5. Good/Base/Bad Cases
- Good: logged-in Codex receives the complete strategy text plus Feishu factual material, returns one Markdown review, and writes one date-keyed row.
- Good: `AI_PROVIDER=codex python main.py assess-ai 20260710 --force-ai` replaces the date-keyed report with one fresh call.
- Base: Feishu runs before a review exists -> factual sections remain complete and the card says the Codex review is unavailable.
- Bad: call Codex once per stock or ask it for risk score, confidence, factor weights, or a rigid JSON score schema.
- Bad: call ChatGPT web/internal endpoints directly or copy OAuth tokens into `.env`.

### 6. Tests Required
- Use a fake Codex client to assert environment-driven strategy loading, complete strategy inclusion, path-free prompt content, strategy-path metadata, shared factual input, both THS reason fields, one-call caching, and forced replacement without a live model call.
- Moonshot fallback unit tests assert its completion request sends `temperature=1`.
- Codex client tests assert `review()` does not pass the legacy score `output_schema`.
- Feishu tests assert score/suggestion sections are absent and persisted review/provider/model are appended.
- Scheduler tests assert one ordered daily job at 16:03, forced review after fetch, fetch -> review -> Feishu execution order, cancellation before review when data is incomplete, Codex retry timing/failure broadcasts, and odd-minute Feishu delay behavior.
- Run agent pytest, `docker compose config --quiet`, and verify no token/header strings are present in source or configuration examples.

### 7. Wrong vs Correct

Wrong:

```python
CodexSubscriptionClient().analyze(messages)  # legacy per-stock score schema
```

Correct:

```python
CodexSubscriptionClient(working_directory="/app").review(prompt)
```

```python
strategy_path = Path(os.environ["DAILY_REVIEW_STRATEGY_PATH"])
strategy = strategy_path.read_text(encoding="utf-8")
digest = sha256(f"{strategy}\n\n{material}".encode("utf-8"))
prompt = build_prompt(strategy=strategy, material=material)
```

## Dates And Keys

The stock domain uses trading-date keys heavily. Keep these conventions:

- CLI input accepts `YYYYMMDD` and `YYYY-MM-DD` via `agent/main.py:parse_date`.
- Python model columns use SQL `Date`.
- Go query APIs accept string ranges and normalize them in `internal/query`.
- Frontend request payloads use camelCase (`startDate`, `endDate`, `taskId`) and the main-process gRPC client maps them to proto snake_case.

Unique indexes in `database.py` are important application contracts. Preserve uniqueness for `(date, code)` stock records and `(date, data_type)` fetch logs.

## Read Models For Frontend

`services/stock-rpc/internal/query/repository.go` intentionally returns JSON strings instead of strongly typed protobuf lists. It adapts MySQL rows into the frontend's current HR/EM shapes:

- HR fields such as `open_num`, `high_days`, `high_days_value`, and `time_preview`
- EM fields such as `c`, `qdate`, `zdp`, `lbc`, `fbt`, `lbt`, and `zttj`
- broken-board analysis derived from HR query results

When changing these JSON shapes, update `front/env.d.ts`, `front/src/shared/lib/validate.ts`, and the affected table components in the same change.

## Connection Configuration

The Python agent requires `DATABASE_URL` for command execution. The Go gateway can start without it, but then it uses in-memory task state and has no query repository. Production-like behavior needs `DATABASE_URL` so:

- `query.Repository` can serve data queries
- `tasks.SQLStore` can persist task status across restarts

Use the MySQL URL format documented in `agent/README.md`: `mysql+pymysql://stock:<password>@host:3306/stock_analysis?charset=utf8mb4`. Go converts this URL to a driver DSN through `query.MySQLURLToDSN`.
