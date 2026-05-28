# Code Reuse Thinking Guide

Before adding a new helper, service, type, or UI component, search for an existing owner with `rg`.

## Backend Reuse Points

Python has factory exports and service classes that should be reused:

- data fetching: `agent/chain/stock/data/create_fetcher`
- data storage: `agent/chain/stock/data/create_storage` and `StockDataStorage`
- SQLAlchemy setup: `init_database` and `get_session_maker`
- rule assessment: `create_risk_agent`
- AI analysis: `create_ai_analyzer`
- enhanced assessment: `create_enhanced_risk_agent`
- goal-driven workflow: `create_stock_agent`
- wiki workflow: `create_wiki_agent`
- scheduling: `create_scheduler`

Do not create a second database session utility, date parser, fetch retry helper, or stock command dispatcher until checking the existing one.

Go has small abstractions intended for extension:

- `server.Executor` for command execution
- `tasks.Store` for task persistence
- `runner.PythonRunner.Command` for task-to-Python mapping
- `query.Repository` for SQL-to-JSON read models

Add behavior to these seams instead of creating parallel task managers or RPC clients.

## Frontend Reuse Points

Use existing primitives and shared components:

- UI primitives in `front/src/renderer/src/components/ui/`
- `DataTable` for dense tables
- `DateRangePicker` for range inputs
- `Toast` for notifications
- `StatTile` for metric tiles
- `cn` for conditional class merging
- `@shared/eventKey` for IPC/RPC event names
- `@shared/logger` for logging
- `window.api.stockRpc.invoke` for stock RPC calls

Do not call gRPC directly from renderer components. Do not duplicate stock event strings outside `StockRpcEventKey`.

## Search Checklist

Before introducing a new concept, search for:

- command name or task type: `rg "assess_ai|agent_run|SubmitAssess"`
- database table or field: `rg "risk_assessment|high_days_value|rpc_tasks"`
- UI event key: `rg "StockRpcEventKey|EventKey.StockRpc"`
- date format conversion: `rg "YYYYMMDD|parse_date|normalizeRange"`
- validation/type shape: `rg "EMLimitUpData|HrLimit|zod"`
- config variable: `rg "MOONSHOT|STOCK_RPC|DATABASE_URL|STOCK_COOKIE"`

If the search finds an existing pattern, extend that pattern and update its tests/docs.

## When Duplication Is Intentional

Some duplication is currently intentional:

- `services/stock-rpc/proto/stock.proto` and the inline `STOCK_PROTO` string in `front/src/main/stockRpc/client.ts` mirror the same gRPC contract.
- Go query JSON shapes mirror frontend global types for compatibility with current table components.
- Python command names and Go task type strings are mapped rather than identical (`assess_ai` -> `assess-ai`, `agent_run` -> `agent`).

When touching these duplicated contracts, update both sides in the same change and mention the duplication in the change summary.

## Avoid New Abstractions For One-Offs

Do not add a shared abstraction just because two lines look similar. Add one only when:

- the same behavior appears in multiple components or commands
- the abstraction matches an existing local pattern
- it reduces cross-layer drift
- it is covered by a narrow test or obvious call-site simplification
