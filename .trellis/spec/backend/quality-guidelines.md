# Backend Quality Guidelines

## Verification Commands

Use package-local commands:

- Python agent tests: `cd services/agent && poetry run python -m pytest`
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

## Scenario: Docker Build Proxy Wiring

### 1. Scope / Trigger
- Trigger: Docker build networking for `stock_agent`, `stock_rpc`, or `rag_agent`.

### 2. Signatures
- Compose build args must remain `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` because Docker, pip, apt, and Go tooling recognize those names inside build containers.
- Project-facing env keys must be `BUILD_HTTP_PROXY`, `BUILD_HTTPS_PROXY`, and `BUILD_NO_PROXY`.

### 3. Contracts
- `BUILD_HTTP_PROXY`: optional HTTP proxy URL for image builds.
- `BUILD_HTTPS_PROXY`: optional HTTPS proxy URL for image builds.
- `BUILD_NO_PROXY`: optional no-proxy host list; defaults include local services.
- Build definitions should map `BUILD_*` keys to the standard proxy build args and include `host.docker.internal:host-gateway` when host proxy access is supported.
- `stock_agent` and `stock_rpc` Compose builds should use the root multi-target `Dockerfile` and share the `python-runtime-base` stage so Poetry dependencies install once per dependency-lock change.
- Python dependency install steps should use BuildKit cache mounts for pip/Poetry caches while preserving `POETRY_REQUESTS_TIMEOUT`, `PIP_DEFAULT_TIMEOUT`, `PIP_RETRIES`, and `poetry config installer.max-workers 1`.

### 4. Validation & Error Matrix
- Host shell has `HTTP_PROXY=http://127.0.0.1:7890`, but `.env` has no `BUILD_*` proxy -> Compose must render blank build proxy args.
- `.env` sets `BUILD_HTTP_PROXY=http://host.docker.internal:7890` while host proxy is reachable -> pip/go/apt may use the proxy.
- `.env` sets `BUILD_HTTP_PROXY=http://127.0.0.1:7890` -> build containers connect to themselves and usually fail with connection refused.
- Poetry fails after reaching package installation with `Cannot install <package>` and a Requests traceback -> treat as transient package download failure; use longer request timeouts and single-worker installs in Dockerfiles.

### 5. Good/Base/Bad Cases
- Good: `BUILD_HTTP_PROXY=http://host.docker.internal:7890` for a proxy listening on the Docker host.
- Base: leave `BUILD_HTTP_PROXY` and `BUILD_HTTPS_PROXY` unset; builds use configured mirrors directly.
- Bad: mapping Compose args from `${HTTP_PROXY}` or `${HTTPS_PROXY}`, which silently imports the operator shell environment.

### 6. Tests Required
- Run `docker compose config --quiet` after changing build proxy wiring.
- Search `docker-compose.yml` for `${HTTP_PROXY}`, `${HTTPS_PROXY}`, or `${NO_PROXY}` build arg interpolation; there should be no implicit shell-proxy mapping.
- For proxy-related fixes, run or partially run `docker compose build stock_agent stock_rpc` far enough to verify `pip install poetry` does not retry a refused proxy.
- For Dockerfile Poetry install changes, keep `POETRY_REQUESTS_TIMEOUT`, `PIP_DEFAULT_TIMEOUT`, `PIP_RETRIES`, and `poetry config installer.max-workers 1` consistent across the shared root `Dockerfile` and `rag_agent`.
- For shared Python base changes, run `docker compose config --quiet` and verify both `stock_agent` and `stock_rpc` build entries point at `dockerfile: Dockerfile` with different `target` values.

### 7. Wrong vs Correct

Wrong:

```yaml
args:
  HTTP_PROXY: ${HTTP_PROXY:-}
```

Correct:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
args:
  HTTP_PROXY: ${BUILD_HTTP_PROXY:-}
```

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
