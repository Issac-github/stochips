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
- Temporary SSH-tunnel builds and runtime checks use `./scripts/stochips-with-proxy.sh`; `PROXY_URL` defaults to `http://127.0.0.1:7892`. Its actions are `--build-only`, `--login`, `--assess-ai [date]`, `--ai-analyze [date]`, and `--notify-feishu [date]`. `docker-build-with-proxy.sh` is a compatibility wrapper only.

### 3. Contracts
- `BUILD_HTTP_PROXY`: optional HTTP proxy URL for image builds.
- `BUILD_HTTPS_PROXY`: optional HTTPS proxy URL for image builds.
- `BUILD_NO_PROXY`: optional no-proxy host list; defaults include local services.
- Build definitions should map `BUILD_*` keys to the standard proxy build args and include `host.docker.internal:host-gateway` when host proxy access is supported.
- `stock_agent` and `stock_rpc` Compose builds should use the root multi-target `Dockerfile` and share the `python-runtime-base` stage so Poetry dependencies install once per dependency-lock change.
- Python dependency install steps should use BuildKit cache mounts for pip/Poetry caches while preserving `POETRY_REQUESTS_TIMEOUT`, `PIP_DEFAULT_TIMEOUT`, `PIP_RETRIES`, and `poetry config installer.max-workers 1`.
- The temporary proxy script must use an automatically removed Compose override with `build.network: host`; it must not write the proxy into `.env` or persistent Docker daemon configuration.
- Codex login from the temporary script must reuse the existing `stock_agent` image and `/root/.codex` volume, use host networking, and remove its one-off container after login.
- Runtime AI/report commands from the temporary script must reuse the existing `stock_agent` image and `/root/.codex` volume, use host networking for a loopback SSH tunnel, and override `DATABASE_URL` to the MySQL host-published port so commands do not depend on the Compose-only `mysql` DNS name.
- Runtime AI commands from the temporary script must pass through explicitly set `AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `CODEX_MODEL`, `CODEX_WORKING_DIRECTORY`, and `AI_MAX_DAILY_CALLS` so one-off validation can override stale server `.env` values.
- `--rebuild` is valid only with `--login` or one runtime action. It rebuilds only `stock_agent`, recreates its Compose container with `--no-deps --force-recreate`, then runs the requested one-off command. Runtime actions without `--rebuild` intentionally reuse the current image.

### 4. Validation & Error Matrix
- Host shell has `HTTP_PROXY=http://127.0.0.1:7890`, but `.env` has no `BUILD_*` proxy -> Compose must render blank build proxy args.
- `.env` sets `BUILD_HTTP_PROXY=http://host.docker.internal:7890` while host proxy is reachable -> pip/go/apt may use the proxy.
- `.env` sets `BUILD_HTTP_PROXY=http://127.0.0.1:7890` -> build containers connect to themselves and usually fail with connection refused.
- Poetry fails after reaching package installation with `Cannot install <package>` and a Requests traceback -> treat as transient package download failure; use longer request timeouts and single-worker installs in Dockerfiles.
- Temporary proxy connectivity check fails -> exit before starting a Docker build.
- Build fails at `load metadata` or base-image pull -> report as Docker daemon traffic; the temporary build script only covers Dockerfile `RUN` downloads.
- One-off AI command uses `docker run --network host` but keeps `DATABASE_URL=@mysql:3306` -> PyMySQL fails with `Name or service not known`; the script must rewrite `DATABASE_URL` to `127.0.0.1:<published-mysql-port>`.
- Server `.env` still has `AI_PROVIDER=moonshot` -> runtime script uses Moonshot unless the operator prefixes the command with `AI_PROVIDER=codex`.
- Source files were synchronized after the last image build -> `--assess-ai --force-ai` still runs old Python code unless the operator first builds, or adds `--rebuild`.
- `--rebuild` is passed without `--login` or a runtime action -> exit with a clear argument error instead of rebuilding an unused image.

### 5. Good/Base/Bad Cases
- Good: `BUILD_HTTP_PROXY=http://host.docker.internal:7890` for a proxy listening on the Docker host.
- Good: SSH reverse tunnel listens on server `127.0.0.1:7892`, then `./scripts/stochips-with-proxy.sh` builds through host networking and removes its override.
- Good: after Codex login, `./scripts/stochips-with-proxy.sh --assess-ai 20260710` runs AI analysis through the same loopback tunnel while connecting to MySQL through the host-published port.
- Good: `AI_PROVIDER=codex AI_FALLBACK_PROVIDER=none ./scripts/stochips-with-proxy.sh --rebuild --assess-ai 20260710 --force-ai` rebuilds the agent, validates Codex with fresh calls, and surfaces provider errors.
- Base: leave `BUILD_HTTP_PROXY` and `BUILD_HTTPS_PROXY` unset; builds use configured mirrors directly.
- Bad: mapping Compose args from `${HTTP_PROXY}` or `${HTTPS_PROXY}`, which silently imports the operator shell environment.
- Bad: manually running `docker run --network host --env-file .env ... python main.py assess-ai` without overriding `DATABASE_URL`, because `mysql` only resolves inside the Compose bridge network.

### 6. Tests Required
- Run `docker compose config --quiet` after changing build proxy wiring.
- Search `docker-compose.yml` for `${HTTP_PROXY}`, `${HTTPS_PROXY}`, or `${NO_PROXY}` build arg interpolation; there should be no implicit shell-proxy mapping.
- For proxy-related fixes, run or partially run `docker compose build stock_agent stock_rpc` far enough to verify `pip install poetry` does not retry a refused proxy.
- For Dockerfile Poetry install changes, keep `POETRY_REQUESTS_TIMEOUT`, `PIP_DEFAULT_TIMEOUT`, `PIP_RETRIES`, and `poetry config installer.max-workers 1` consistent across the shared root `Dockerfile` and `rag_agent`.
- For shared Python base changes, run `docker compose config --quiet` and verify both `stock_agent` and `stock_rpc` build entries point at `dockerfile: Dockerfile` with different `target` values.
- For the temporary proxy script, run `bash -n` for both the canonical script and compatibility wrapper, exercise `--help`, and validate its generated override with `docker compose config --quiet` without performing a live build.

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

For a loopback-only SSH tunnel, do not point a bridged build container at its own `127.0.0.1`.
Use the temporary script's `build.network: host` override instead:

```bash
./scripts/stochips-with-proxy.sh
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
