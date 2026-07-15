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

- Python: `DATABASE_URL`, `STOCK_COOKIE`, `AI_PROVIDER`, `CODEX_MODEL`, `LOG_LEVEL`, `TZ`, and fetch tuning variables in `agent/chain/stock/config.py`.
- Go: `STOCK_RPC_ADDR`, `STOCK_RPC_AGENT_DIR`, `PYTHON_BIN`, and `DATABASE_URL`.
- Docker Compose in `agent/docker-compose.yml` wires MySQL, `stock_agent`, optional `rag_agent`, and `stock_rpc`.

Do not introduce untracked configuration keys without updating `.env.example`, README guidance, and any Docker Compose usage that needs the variable.

## Scenario: Docker Build And Runtime Proxy Wiring

### 1. Scope / Trigger
- Trigger: Docker build networking or runtime outbound networking for `stock_agent`, `stock_rpc`, or `rag_agent`.

### 2. Signatures
- Compose build args must remain `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` because Docker, pip, apt, and Go tooling recognize those names inside build containers.
- Project-facing env keys must be `BUILD_HTTP_PROXY`, `BUILD_HTTPS_PROXY`, and `BUILD_NO_PROXY`.
- Codex runtime proxy env keys must be `CODEX_HTTP_PROXY`, `CODEX_HTTPS_PROXY`, `CODEX_ALL_PROXY`, and `CODEX_NO_PROXY`; Compose passes them through unchanged and Python maps them to standard proxy variables only while calling the Codex SDK.
- Host-loopback proxies for long-lived Codex reviews use the optional `codex_proxy_bridge` service. It runs with host networking, connects to `CODEX_HOST_PROXY_HOST:CODEX_HOST_PROXY_PORT`, and exposes `CODEX_PROXY_BRIDGE_BIND:CODEX_PROXY_BRIDGE_PORT` for bridge-network containers.
- Temporary SSH-tunnel builds and runtime checks use `./scripts/stochips-with-proxy.sh`; `PROXY_URL` defaults to `http://127.0.0.1:7892`. Its actions are `--build-only`, `--login`, `--assess-ai [date]`, `--ai-analyze [date]`, and `--notify-feishu [date]`. `docker-build-with-proxy.sh` is a compatibility wrapper only.

### 3. Contracts
- `BUILD_HTTP_PROXY`: optional HTTP proxy URL for image builds.
- `BUILD_HTTPS_PROXY`: optional HTTPS proxy URL for image builds.
- `BUILD_NO_PROXY`: optional no-proxy host list; defaults include local services.
- `CODEX_HTTP_PROXY`: optional HTTP proxy URL for Codex SDK calls.
- `CODEX_HTTPS_PROXY`: optional HTTPS proxy URL for Codex SDK calls.
- `CODEX_ALL_PROXY`: optional all-protocol proxy URL for Codex SDK calls.
- When `CODEX_HTTPS_PROXY` or `CODEX_HTTP_PROXY` is set, the Codex client uses that
  protocol proxy as its effective `ALL_PROXY` value. This prevents a stale
  `CODEX_ALL_PROXY=http://127.0.0.1:...` from redirecting container traffic away
  from the configured host bridge.
- Create the Codex app-server inside that scoped proxy environment. Applying proxy
  variables only around `thread.run()` is too late because its child process may
  capture the environment during `Codex()` construction.
- `CODEX_NO_PROXY`: optional no-proxy host list for Codex SDK calls; defaults include `host.docker.internal`, MySQL, and local service names.
- `CODEX_HOST_PROXY_HOST`: host-side proxy address for `codex_proxy_bridge`; defaults to `127.0.0.1`.
- `CODEX_HOST_PROXY_PORT`: host-side proxy port for `codex_proxy_bridge`; defaults to `7890`.
- `CODEX_PROXY_BRIDGE_BIND`: bind address exposed by `codex_proxy_bridge`; defaults to `0.0.0.0`.
- `CODEX_PROXY_BRIDGE_PORT`: bridge port exposed by `codex_proxy_bridge`; defaults to `7891`.
- Build definitions should map `BUILD_*` keys to the standard proxy build args and include `host.docker.internal:host-gateway` when host proxy access is supported.
- Runtime definitions for `stock_agent` and `stock_rpc` should pass `CODEX_*_PROXY` keys through unchanged and include runtime `extra_hosts: host.docker.internal:host-gateway`. Do not map these keys to process-wide `HTTP_PROXY` / `HTTPS_PROXY`, because Feishu, Moonshot, and fetch requests would inherit a proxy intended only for Codex.
- `stock_agent` and `stock_rpc` must remain on the Compose bridge network so `mysql:3306` stays valid. Do not switch these services to `network_mode: host` for proxy access; use `codex_proxy_bridge` instead.
- `stock_agent` and `stock_rpc` Compose builds should use the root multi-target `Dockerfile` and share the `python-runtime-base` stage so Poetry dependencies install once per dependency-lock change.
- Python dependency install steps should use BuildKit cache mounts for pip/Poetry caches while preserving `POETRY_REQUESTS_TIMEOUT`, `PIP_DEFAULT_TIMEOUT`, `PIP_RETRIES`, and `poetry config installer.max-workers 1`.
- The temporary proxy script must use an automatically removed Compose override with `build.network: host`; it must not write the proxy into `.env` or persistent Docker daemon configuration.
- `.env` remains Git-ignored, but `scripts/rsync-to-server.sh` deploys it with the repository so server runtime configuration tracks the local deployment configuration.
- Codex login from the temporary script must reuse the existing `stock_agent` image and `/root/.codex` volume, use host networking, and remove its one-off container after login.
- Runtime AI/report commands from the temporary script must reuse the existing `stock_agent` image and `/root/.codex` volume, use host networking for a loopback SSH tunnel, and override `DATABASE_URL` to the MySQL host-published port so commands do not depend on the Compose-only `mysql` DNS name.
- Runtime AI commands from the temporary script must pass through explicitly set `AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `CODEX_MODEL`, and `CODEX_WORKING_DIRECTORY` so one-off validation can override stale server `.env` values.
- `--rebuild` is valid only with `--login` or one runtime action. It rebuilds only `stock_agent`, recreates its Compose container with `--no-deps --force-recreate`, then runs the requested one-off command. Runtime actions without `--rebuild` intentionally reuse the current image.

### 4. Validation & Error Matrix
- Host shell has `HTTP_PROXY=http://127.0.0.1:7890`, but `.env` has no `BUILD_*` proxy -> Compose must render blank build proxy args.
- `.env` sets `BUILD_HTTP_PROXY=http://host.docker.internal:7890` while host proxy is reachable -> pip/go/apt may use the proxy.
- `.env` sets `BUILD_HTTP_PROXY=http://127.0.0.1:7890` -> build containers connect to themselves and usually fail with connection refused.
- `.env` sets `CODEX_HTTP_PROXY=http://host.docker.internal:7890` while host proxy is reachable -> scheduled Codex review in `stock_agent` and Python commands triggered through `stock_rpc` may use the proxy.
- `.env` sets `CODEX_HTTP_PROXY=http://127.0.0.1:7890` for bridged long-lived services -> Codex calls connect to the container itself and usually time out or refuse connections.
- Host proxy listens only on `127.0.0.1:7890` and `.env` sets `CODEX_HTTP_PROXY=http://host.docker.internal:7890` -> bridge containers usually get connection refused; set `CODEX_HTTP_PROXY=http://host.docker.internal:7891` and start `codex_proxy_bridge`.
- `.env` maps Codex proxy config into global `HTTP_PROXY` / `HTTPS_PROXY` -> Feishu webhooks and Moonshot fallback may fail through a proxy that was only meant for ChatGPT/Codex.
- Poetry fails after reaching package installation with `Cannot install <package>` and a Requests traceback -> treat as transient package download failure; use longer request timeouts and single-worker installs in Dockerfiles.
- Temporary proxy connectivity check fails -> exit before starting a Docker build.
- Build fails at `load metadata` or base-image pull -> report as Docker daemon traffic; the temporary build script only covers Dockerfile `RUN` downloads.
- One-off AI command uses `docker run --network host` but keeps `DATABASE_URL=@mysql:3306` -> PyMySQL fails with `Name or service not known`; the script must rewrite `DATABASE_URL` to `127.0.0.1:<published-mysql-port>`.
- Server `.env` still has `AI_PROVIDER=moonshot` -> daily review exits clearly unless the operator prefixes the command with `AI_PROVIDER=codex`.
- Source files were synchronized after the last image build -> `--assess-ai --force-ai` still runs old Python code unless the operator first builds, or adds `--rebuild`.
- `--rebuild` is passed without `--login` or a runtime action -> exit with a clear argument error instead of rebuilding an unused image.

### 5. Good/Base/Bad Cases
- Good: `BUILD_HTTP_PROXY=http://host.docker.internal:7890` for a proxy listening on the Docker host.
- Good: `CODEX_HTTP_PROXY=http://host.docker.internal:7891` plus `codex_proxy_bridge` forwarding to host `127.0.0.1:7890` for scheduled Codex review from long-lived Compose containers.
- Good: SSH reverse tunnel listens on server `127.0.0.1:7892`, then `./scripts/stochips-with-proxy.sh` builds through host networking and removes its override.
- Good: after Codex login, `./scripts/stochips-with-proxy.sh --assess-ai 20260710` runs AI analysis through the same loopback tunnel while connecting to MySQL through the host-published port.
- Good: `AI_PROVIDER=codex AI_FALLBACK_PROVIDER=none ./scripts/stochips-with-proxy.sh --rebuild --assess-ai 20260710 --force-ai` rebuilds the agent, validates Codex with fresh calls, and surfaces provider errors.
- Base: leave `BUILD_HTTP_PROXY` and `BUILD_HTTPS_PROXY` unset; builds use configured mirrors directly.
- Bad: mapping Compose args from `${HTTP_PROXY}` or `${HTTPS_PROXY}`, which silently imports the operator shell environment.
- Bad: manually running `docker run --network host --env-file .env ... python main.py assess-ai` without overriding `DATABASE_URL`, because `mysql` only resolves inside the Compose bridge network.

### 6. Tests Required
- Run `docker compose config --quiet` after changing build proxy wiring.
- After changing runtime proxy wiring, run `docker compose config --quiet` and inspect that `stock_agent`/`stock_rpc` include the expected `CODEX_*_PROXY` keys without global `HTTP_PROXY` / `HTTPS_PROXY` runtime variables.
- For host-loopback proxy bridging, run `docker compose config --quiet` and verify `codex_proxy_bridge` renders with `network_mode: host` and the expected listen/connect ports.
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

Correct runtime mapping:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  CODEX_HTTP_PROXY: ${CODEX_HTTP_PROXY:-}
  CODEX_NO_PROXY: ${CODEX_NO_PROXY:-localhost,127.0.0.1,host.docker.internal,mysql,stock_agent,stock_rpc,rag_agent}
```

Correct loopback bridge:

```yaml
codex_proxy_bridge:
  image: alpine/socat:latest
  network_mode: host
  command:
    - TCP-LISTEN:${CODEX_PROXY_BRIDGE_PORT:-7891},fork,reuseaddr,bind=${CODEX_PROXY_BRIDGE_BIND:-0.0.0.0}
    - TCP:${CODEX_HOST_PROXY_HOST:-127.0.0.1}:${CODEX_HOST_PROXY_PORT:-7890}
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
- daily qualitative review in `agent/chain/stock/agents/daily_market_review_agent.py`
- shared factual Feishu/Codex material in `agent/chain/stock/agents/feishu_notifier.py`
- legacy scorer modules are historical compatibility code, not active daily-flow owners
- RPC dispatch and task state in Go
- frontend JSON shape adaptation in Go query repository only when needed for display compatibility

Avoid copying scoring rules into frontend components or Go RPC handlers.
