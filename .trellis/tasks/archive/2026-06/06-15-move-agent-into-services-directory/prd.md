# Move agent into services directory

## Goal
Relocate the Python `agent/` package to `services/agent/`, and hoist
`docker-compose.yml` to the repo root so it orchestrates both
`services/agent` and `services/stock-rpc` from one place.

## Decision
- Target: `agent/` → `services/agent/`
- Compose: `agent/docker-compose.yml` → `/docker-compose.yml` (repo root)

## Changes
1. `git mv agent services/agent`
2. `git mv services/agent/docker-compose.yml docker-compose.yml`, rewrite all
   relative paths (build context, volumes, init scripts) to `./services/agent/...`;
   `stock_rpc` build context becomes `.` (repo root).
3. `services/stock-rpc/Dockerfile`: `COPY agent/...` → `COPY services/agent/...`
4. `services/stock-rpc/cmd/stock-rpc/main.go`: default `STOCK_RPC_AGENT_DIR`
   `".."` → `"../agent"` (local dev from services/stock-rpc).
5. `services/stock-rpc/README.md`: update local-dev + compose commands.
6. `services/agent/README.md`: update compose commands (now run from repo root).

## Not affected
- `python_test.go` uses an abstract `/repo/agent` path — no change.
- Front-end talks to stock_rpc over gRPC port — no change.
- In-container runtime uses `STOCK_RPC_AGENT_DIR=/app` env — no change.

## Verification
- `cd services/stock-rpc && go build ./... && go test ./...`
- `docker compose config` resolves; `docker compose build` succeeds.
