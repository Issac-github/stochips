# Backend Logging Guidelines

## Python Logging

`agent/main.py:setup_logging` configures Python logging from `LOG_LEVEL` and writes to both stdout and `stock_agent.log`.

Follow this pattern in backend Python modules:

- create module loggers with `logging.getLogger(__name__)`
- use `logger.info` for successful lifecycle events
- use `logger.warning` for recoverable missing data or retry attempts
- use `logger.error` for failed external calls, row save failures, and job failures
- use `logging.exception` only at command boundaries where traceback context is useful

Reference files:

- `agent/main.py`
- `agent/chain/stock/data/fetcher.py`
- `agent/chain/stock/data/storage.py`
- `agent/chain/stock/scheduler/daily_job.py`
- `agent/chain/stock/agents/enhanced_risk_agent.py`

## Do Not Log Secrets

Never log raw values for:

- `STOCK_COOKIE`
- `MOONSHOT_API_KEY`
- database passwords embedded in `DATABASE_URL`

When logging configuration state, log whether a feature is configured, not the secret value. `agent/chain/stock/config.py` already uses configured/not-configured messages.

## Go Logging

`services/stock-rpc/cmd/stock-rpc/main.go` uses the standard `log` package for service startup and fatal initialization failures.

Keep this style:

- `log.Fatalf` for failures that prevent the gateway from serving
- `log.Printf("WARN: ...")` for degraded mode, such as SQL task store fallback
- include address, agent directory, and store mode in startup logs

Do not print Python command stdout/stderr directly in the Go server logs by default. The runner returns stdout as task result and stderr as error context so the caller can inspect task status.

## Frontend-Visible Errors

Errors crossing from Go to Electron should become either:

- gRPC errors caught in `front/src/main/lib/ipc.ts` and returned as `{ error }`
- task failure strings stored by the Go task store and retrieved with `GetTask`

Keep error messages concise because `LimitUpData.tsx` displays them in toasts and a compact active-task panel.
