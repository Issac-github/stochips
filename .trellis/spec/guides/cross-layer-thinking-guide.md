# Cross-Layer Thinking Guide

Use this whenever work touches more than one runtime layer.

## Map The Owner First

StoChips has clear owners:

- Python `agent/` owns stock business logic, data writes, risk scoring, AI analysis, wiki/RAG commands, and scheduled jobs.
- Go `services/stock-rpc/` owns gRPC API, task state, query adapters, and command dispatch.
- Electron main owns IPC handlers, local LLM/MCP server startup, and the Node gRPC client.
- Preload owns the small `window.api` bridge.
- React renderer owns presentation, local UI state, polling, and table/dashboard composition.

Before coding, identify which layer owns the behavior and which layers only adapt or display it.

## Schema Or Data Shape Changes

For stock data shape changes, check all of these:

- `agent/chain/stock/models/database.py`
- `agent/migrations/`
- `agent/chain/stock/data/storage.py`
- `services/stock-rpc/internal/query/repository.go`
- `front/env.d.ts`
- `front/src/shared/lib/validate.ts`
- `front/src/renderer/src/components/limitUp/`

Questions to answer:

- Is this a persisted database change or only a display adapter change?
- Does the date format remain `YYYYMMDD` at the UI/RPC boundary?
- Do SQL query defaults still avoid nullable frontend surprises?
- Does the zod validator match actual JSON from Go?

## RPC Contract Changes

For stock RPC changes, check all of these:

- `services/stock-rpc/proto/stock.proto`
- `services/stock-rpc/gen/stockv1/`
- `services/stock-rpc/internal/server/service.go`
- `services/stock-rpc/internal/runner/python.go`
- `front/src/main/stockRpc/client.ts`
- `front/src/shared/eventKey.ts`
- `front/env.d.ts`
- `front/src/preload/index.ts` if the bridge shape changes
- renderer page/component that invokes the event

Questions to answer:

- Is the new RPC immediate query behavior or async task behavior?
- If it is a task, what task type string does Go store and what Python command does it execute?
- How will the renderer poll status and refresh data?
- Does the Electron client need camelCase-to-snake_case mapping?

## Task Lifecycle Changes

The task path is:

`renderer -> window.api.stockRpc.invoke -> Electron IPC -> Go gRPC -> tasks.Store -> runner.PythonRunner -> agent/main.py`

When changing task behavior:

- keep submit RPCs fast
- store errors on the task, then surface through `GetTask`
- preserve `pending`, `running`, `succeeded`, `failed` statuses
- update both `MemoryStore` and `SQLStore` if task persistence changes
- update tests in `internal/server`, `internal/runner`, and `internal/tasks`

## AI Flow Changes

AI analysis is optional and may be unavailable. Before changing it, check:

- `agent/chain/stock/config.py`
- `agent/chain/stock/agents/ai_analyzer.py`
- `agent/chain/stock/agents/enhanced_risk_agent.py`
- `agent/tests/test_ai_flow.py`
- `risk_assessment` columns in `database.py` and migrations

Preserve rule-only fallback and cached AI reuse. New LLM output parsing should be testable without a live API call.

## Verification Selection

Choose verification by touched layer:

- Python logic: `cd agent && poetry run pytest`
- Go RPC/query/task changes: `cd services/stock-rpc && go test ./...`
- frontend types/UI bridge: `cd front && npm run typecheck`
- frontend lint/format-sensitive work: `cd front && npm run lint`
- proto changes: regenerate Go code and run Go plus frontend typecheck
