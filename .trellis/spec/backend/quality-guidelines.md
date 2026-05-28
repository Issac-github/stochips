# Backend Quality Guidelines

## Verification Commands

Use package-local commands:

- Python agent tests: `cd agent && poetry run pytest`
- Go gateway tests: `cd services/stock-rpc && go test ./...`
- Go protobuf generation after proto changes:

```bash
cd services/stock-rpc
protoc -I proto \
  --go_out=. --go_opt=module=stochips/stock_rpc \
  --go-grpc_out=. --go-grpc_opt=module=stochips/stock_rpc \
  proto/stock.proto
```

Do not regenerate protobuf output unless `proto/stock.proto` changes.

## Test Patterns

Use the current tests as examples:

- `agent/tests/test_ai_flow.py` tests LLM JSON parsing, normalization, and cached AI reuse without live LLM calls.
- `services/stock-rpc/internal/runner/python_test.go` tests task-to-command mapping.
- `services/stock-rpc/internal/server/service_test.go` tests async task submission through a fake executor.
- `services/stock-rpc/internal/tasks/store_test.go` tests task lifecycle transitions.
- `services/stock-rpc/internal/query/date_test.go` covers date normalization helpers.

Prefer narrow tests around command mapping, parsing, status transitions, and cache behavior. Avoid tests that need real upstream stock APIs or live Moonshot calls unless explicitly marked/integrated.

## Configuration

Backend behavior is environment-driven:

- Python: `DATABASE_URL`, `STOCK_COOKIE`, `MOONSHOT_API_KEY`, `AI_MAX_DAILY_CALLS`, `LOG_LEVEL`, `TZ`, and fetch/LLM tuning variables in `agent/chain/stock/config.py`.
- Go: `STOCK_RPC_ADDR`, `STOCK_RPC_AGENT_DIR`, `PYTHON_BIN`, and `DATABASE_URL`.
- Docker Compose in `agent/docker-compose.yml` wires MySQL, `stock_agent`, optional `rag_agent`, and `stock_rpc`.

Do not introduce untracked configuration keys without updating `.env.example`, README guidance, and any Docker Compose usage that needs the variable.

## Generated And Runtime Files

Do not treat these as source patterns:

- `agent/.venv/`
- `agent/__pycache__/`
- `agent/.pytest_cache/`
- `agent/stock_agent.log`
- `front/node_modules/`
- `front/.eslintcache`
- generated Go files in `services/stock-rpc/gen/stockv1/` except when regenerated from proto

When scanning or documenting code, filter these directories out.

## Business Logic Placement

Keep business logic in the owner package:

- stock fetch source rules in `agent/chain/stock/data/fetcher.py`
- field normalization and persistence in `agent/chain/stock/data/storage.py`
- rule scoring in `agent/chain/stock/agents/risk_agent.py`
- AI prompt/parsing in `agent/chain/stock/agents/ai_analyzer.py`
- combined scoring and AI cache reuse in `agent/chain/stock/agents/enhanced_risk_agent.py`
- RPC dispatch and task state in Go
- frontend JSON shape adaptation in Go query repository only when needed for display compatibility

Avoid copying scoring rules into frontend components or Go RPC handlers.
