# Add DEPLOY.md and one-click deploy script

## Goal
Give the repo a single source of truth for backend deployment after the
agent → services/agent relocation: a `DEPLOY.md` guide and a `deploy.sh`
one-click script, both at the repo root (where docker-compose.yml now lives).

## Context
Backend = mysql + stock_agent (Python) + stock_rpc (Go), orchestrated by
the root `docker-compose.yml`. `.env` + `.env.example` are at repo root.
MySQL data persists in the `mysql_data` named volume. User does NOT need
the old data — a fresh deploy is acceptable.

## Deliverables
### 1. `DEPLOY.md` (repo root)
- Prerequisites (Docker + compose plugin)
- Clone + `.env` setup with required vars table (MYSQL_*, STOCK_COOKIE,
  MOONSHOT_API_KEY optional)
- `docker compose up -d --build`, what auto-runs (migrations, scheduler)
- Ports (gRPC 50051, MySQL 3306), data persistence note (mysql_data volume,
  `down -v` wipes), smoke-test commands, ops commands, RAG optional.

### 2. `deploy.sh` (repo root, executable, bash)
- `set -euo pipefail`; run from repo root regardless of CWD.
- Preflight: docker daemon reachable + `docker compose version`.
- `.env`: if missing, copy from `.env.example`, then STOP and tell the user
  to fill secrets (don't deploy with placeholder STOCK_COOKIE / passwords).
- Validate required vars are non-placeholder before deploying.
- Flags: `--fresh` (docker compose down -v first), `--no-build`.
- `docker compose up -d --build`, wait for mysql + stock_rpc healthy
  (poll `docker compose ps`), then print final status; non-zero exit on
  health timeout.

## Acceptance
- `bash -n deploy.sh` parses; shellcheck-clean if available.
- DEPLOY.md commands all run from repo root and match current compose paths.
- No secrets committed; deploy.sh refuses to run with placeholder .env.

## Not in scope
- CI/CD, systemd units, TLS/reverse proxy, multi-host.
