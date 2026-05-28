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
- business-key upserts through `_upsert_by_keys`
- per-data-type save counts and fetch logs
- session commit/rollback/close behavior

Do not use `session.merge` for records keyed by `(date, code)` or `(date, block_code)`. The current project uses explicit business-key lookup because `merge` only reasons about primary keys and can create duplicates.

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
