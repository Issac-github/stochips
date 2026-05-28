# Backend Directory Structure

## Ownership Boundaries

Keep backend responsibilities split exactly as the current code does:

- `agent/main.py`: Python CLI boundary. It parses commands, dates, environment requirements, prints user-facing command output, and exits with `sys.exit(1)` on command failure.
- `agent/chain/stock/data/`: stock data acquisition and MySQL storage. `fetcher.py` owns upstream HTTP request shapes and retry behavior. `storage.py` owns normalization and upserts.
- `agent/chain/stock/models/database.py`: SQLAlchemy table definitions and indexes for stock data, risk assessment, and fetch logs.
- `agent/chain/stock/agents/`: rule assessment, AI analysis, enhanced assessment, goal-driven stock agent, and wiki agent factories.
- `agent/chain/stock/scheduler/`: APScheduler orchestration around existing fetch and assessment services.
- `agent/chain/rag/` and `agent/chain/wiki/`: optional RAG/wiki command surface. Keep heavyweight RAG dependencies behind the optional `rag` extra and `rag_agent` Docker profile.
- `services/stock-rpc/proto/stock.proto`: external gRPC contract.
- `services/stock-rpc/internal/server/`: RPC method handlers, task submission, and gRPC error mapping.
- `services/stock-rpc/internal/runner/`: maps RPC task types to existing `agent/main.py` commands.
- `services/stock-rpc/internal/tasks/`: task state abstractions and memory/MySQL implementations.
- `services/stock-rpc/internal/query/`: read-only SQL queries that shape database rows into JSON expected by the Electron frontend.

## Python Package Pattern

Python packages expose factory helpers through `__init__.py`. Follow the existing examples:

- `agent/chain/stock/data/__init__.py` exports `create_fetcher`, `create_storage`, `StockDataFetcher`, and `StockDataStorage`.
- `agent/chain/stock/agents/__init__.py` exports `create_risk_agent`, `create_ai_analyzer`, `create_enhanced_risk_agent`, `create_stock_agent`, and `create_wiki_agent`.

When adding a new backend capability, place the implementation under the owning package, then export only the stable factory or public type from that package's `__init__.py`.

## Go Package Pattern

`services/stock-rpc` uses small internal packages with narrow interfaces:

- `server.Executor` lets the gRPC server depend on command execution behavior without importing `runner.PythonRunner` directly.
- `tasks.Store` lets the server use `MemoryStore` by default and `SQLStore` when `DATABASE_URL` is configured.
- `query.Repository` encapsulates MySQL reads and JSON shape conversion.

Keep new Go packages under `internal/` unless they must be public API. Generated protobuf code belongs in `gen/stockv1/` and should be regenerated from `proto/stock.proto`, not edited by hand.

## Cross-Boundary Rule

The Go gateway may add RPC methods, task tracking, or query adapters, but stock fetching, storage writes, rule scoring, AI scoring, and report generation stay in Python. If a new RPC action is needed, add it to `proto/stock.proto`, map it in `internal/server/service.go`, and dispatch to an existing or new `agent/main.py` command through `internal/runner/python.go`.

Avoid placing Python business rules in Go query adapters. `internal/query/repository.go` may format rows for frontend compatibility, but it should not decide investment risk or mutate stock tables.
