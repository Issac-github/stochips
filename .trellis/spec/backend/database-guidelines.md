# Database Guidelines

## Schema Source Of Truth

Python SQLAlchemy models in `agent/chain/stock/models/database.py` define the application schema used by the stock agent:

- `continuous_limit_up`
- `block_top`
- `limit_up_pool`
- `eastmoney_zt_pool`
- `risk_assessment`
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
  - `python main.py assess [YYYYMMDD]`: rule risk assessment into `risk_assessment`.
  - `python main.py assess-ai [YYYYMMDD]`: rule plus Moonshot/Kimi enhanced assessment into `risk_assessment`.
  - `python main.py notify-feishu [YYYYMMDD]`: builds and sends the Feishu report from MySQL rows.
  - `python main.py schedule`: workday scheduler that dispatches the above commands in order.
- THS upstream endpoints:
  - `/dataapi/limit_up/continuous_limit_up` -> `continuous_limit_up`
  - `/dataapi/limit_up/block_top` -> `block_top`
  - `/dataapi/limit_up/limit_up_pool` -> `limit_up_pool`
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
- `limit_up_pool` is the THS 涨停强度 table. It stores limit-up type, time, open count, seal strength/amount, volume ratio, turnover rate, market value, concept/reason, and optional block name.
- `eastmoney_zt_pool` is the Eastmoney 涨停池 table. Feishu uses its `block_name` as the industry/sector dimension and reports all grouped industries, not Top 10.
- `fetch_all_data` must not save or advance stale holiday data. If the target date is a weekend, or THS payload timestamps prove the upstream returned a different trading date, return `skipped=True` with `skip_reason`; `save_all_data` writes `data_fetch_log.status='skipped'` for every data type and does not upsert stock rows.
- Feishu report ownership:
  - THS tables drive short-term structure: limit-up overview, 连板梯队, 核心连板, 早盘强势, 分歧弱板, 涨停前高突破, and 同花顺板块热度.
  - Eastmoney drives the independent `东财行业涨停` section by grouping `eastmoney_zt_pool.block_name`.
  - Board/industry sections are all-item summaries; only stock-level sections such as 核心连板, 分歧弱板, 高风险, and 机会观察 use Top 10.
  - `东财行业涨停` should render all grouped industries and all limit-up stocks within each industry. Use compact stock labels with board count, not codes or `前三`: `行业：股票A（3板）、股票B（1板）`.
  - `核心连板` should group by `continuous_days` rather than render one line per stock, e.g. `5板：国华退(000004)、*ST东智(002175)`.
- Rule risk assessment ownership:
  - `assess` and the rule side of `assess-ai` evaluate `continuous_limit_up` rows with `continuous_days >= 2`.
  - Rule factors are `continuous_days` 35%, `limit_up_time/latest_limit_up_time` 15%, seal strength 20%, turnover rate 20%, and open count 10%.
  - Sealing-time risk treats early sealing as lower risk and late sealing as higher risk; parse `HH:MM`, `HH:MM:SS`, `92500`, and Unix-second timestamp values when available.
- Scheduler default:
  - 16:03 fetch; scheduled fetch adds `STOCK_FETCH_START_JITTER_MIN/MAX` seconds before upstream calls.
  - `fetch_all_data` calls THS/Eastmoney sources sequentially and waits `STOCK_FETCH_SOURCE_DELAY_MIN/MAX` seconds between sources.
  - THS paginated `limit_up_pool` waits `STOCK_FETCH_PAGE_DELAY_MIN/MAX` seconds between pages.
  - 16:10 rule assessment
  - 16:20 AI enhanced assessment when `MOONSHOT_API_KEY` is configured
  - 16:37 Feishu report when `FEISHU_WEBHOOK_URL` is configured
  - all scheduled jobs run Monday-Friday only.
  - assessment, AI assessment, and Feishu report jobs must check `data_fetch_log.status='skipped'` for the target date and exit when fetch marked the day as non-trading/stale.

### 4. Validation & Error Matrix
- `block_top` rows exist but `stock_count=0`, `change_percent IS NULL`, and leader fields are blank -> inspect raw THS `block_top` payload and update alias mapping in `StockDataStorage.save_block_top`; do not add columns unless the existing schema cannot represent the value.
- `block_top` has no usable counts and `limit_up_pool.block_name` is also blank -> Feishu should show `同花顺板块热度` as unavailable and direct users to `东财行业涨停`.
- `limit_up_pool.open_count=0` -> do not include the stock in `分歧弱板`; high turnover alone is not a weak-board signal.
- `limit_up_pool.limit_up_time` is blank -> `早盘强势` may be empty; do not infer times from unrelated tables unless a new explicit mapping is added.
- `risk_assessment` count is zero -> Feishu should keep stock rows but label risk as 未评估/无评分 and emit a data warning.
- `data_fetch_log.status='skipped'` exists for the target date -> do not run rule assessment, AI assessment, or Feishu report for that date.

### 5. Good/Base/Bad Cases
- Good: THS `block_top` payload with `limit_up_num=43`, `change=2.377`, and `stock_list[0]` leader data writes a complete `block_top` row and Feishu can show 同花顺板块热度.
- Base: THS short-term structure is usable, Eastmoney industry grouping is usable, but AI assessment has not run; Feishu reports data plus risk warnings.
- Bad: Treat Eastmoney `block_name` as a replacement for THS 最强风口. It is an industry/sector grouping and must remain a separate report section.
- Bad: Save Eastmoney rows under the requested holiday date when THS proves the upstream response belongs to the previous trading day.
- Bad: Store derived Feishu-only signals in new tables before the rule is stable. Prefer real-time derivation from existing fact tables until frontend query, backtest, or rule-version requirements exist.

### 6. Tests Required
- Storage mapping tests should assert THS `block_top` aliases:
  - `limit_up_num` becomes `stock_count`
  - `change` becomes `change_percent`
  - `stock_list[0].code/name` becomes leader fields
- Feishu report tests should assert:
  - `同花顺板块热度` and `东财行业涨停` are separate sections
  - board/industry section titles do not say Top 10
  - Eastmoney industry rows do not include `前三` or `N 只涨停`, and render every stock as `名字（几板）`
  - 核心连板 groups stocks by board count instead of repeating per-stock risk text
  - `分歧弱板` requires `open_count > 0`
  - 涨停前高突破 uses weekday trading-date windows and renders gap as trading days
- Fetch guard tests should assert:
  - weekend target dates return `skipped=True` before network calls
  - THS timestamp dates different from the requested date skip save/downstream flow
  - THS empty plus Eastmoney non-empty is treated as unverified/stale and skipped
  - source fetches run sequentially with configured source delays, not `asyncio.gather`
  - paginated THS fetches use configured page delays between pages
- Rule assessment tests should assert:
  - sealing time participates in the score and reason
  - early sealing lowers risk relative to late sealing
  - `latest_limit_up_time` is used when `limit_up_pool.limit_up_time` is missing
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
