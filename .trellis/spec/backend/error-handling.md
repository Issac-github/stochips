# Backend Error Handling

## Python CLI Commands

`agent/main.py` is user-facing. Follow its current command pattern:

- validate required environment variables at the command boundary
- print clear command errors before exiting
- wrap command body in `try/except`
- log traceback details with `logging.exception`
- call `sys.exit(1)` for command failure

Examples:

- `cmd_fetch` requires `DATABASE_URL`, warns when partial upstream fetches fail, then saves successful data.
- `cmd_ai_analyze` requires both `DATABASE_URL` and `MOONSHOT_API_KEY`.
- `cmd_agent` requires a goal and `DATABASE_URL`.
- `parse_date` accepts two formats and exits with a user-facing message when parsing fails.

Do not let raw stack traces be the only CLI feedback. The CLI should print the short error and log the detailed exception.

## Fetching And Retries

`agent/chain/stock/data/fetcher.py` uses `async_retry` around upstream HTTP/JSON parsing errors. Preserve this behavior when adding sources:

- retry `aiohttp.ClientError`, `asyncio.TimeoutError`, and parse `ValueError`
- log each failed attempt with attempt number
- raise the final exception after retries
- keep upstream headers and JSON/JSONP parsing close to the source-specific fetch code

Never hardcode real cookies in source. `StockDataFetcher` reads `STOCK_COOKIE` or accepts a cookie argument and parses either full Cookie headers or a raw `v` cookie value.

## Storage Failures

`StockDataStorage` counts per-row failures but keeps processing other rows. Follow the existing pattern:

- skip malformed rows that lack required business keys
- log row-level failures with enough identifying data
- commit only after a batch finishes
- rollback and re-raise for batch-level failures
- close sessions in `finally`

Use `DataFetchLog` for successful batch counts. If adding failed fetch logging, keep it consistent with `data_fetch_log.status` and `error_message`.

## AI Analysis Failures

AI analysis is optional and budgeted. `EnhancedRiskAssessmentAgent.assess_stock_enhanced` already distinguishes:

- `cached`
- `fresh`
- `failed`
- `budget_limited`
- `unavailable`
- `disabled`

Preserve these states when changing enhanced assessment. A missing or failing LLM should not prevent rule-only risk assessment from completing.

`AIStockAnalyzer.parse_analysis_json` normalizes suggestions and clamps numeric fields. Tests in `agent/tests/test_ai_flow.py` cover invalid JSON and suggestion normalization; add similar tests for new LLM parsing rules.

## Go gRPC Errors

`services/stock-rpc/internal/server/service.go` maps service errors to gRPC status codes:

- missing task: `codes.NotFound`
- query repository not configured: `codes.FailedPrecondition`
- query execution errors: `codes.Internal`

Task submission returns quickly and executes Python in a goroutine. Execution failures should be stored on the task through `MarkFailed`, then surfaced by `GetTask`; do not block submit RPCs until Python commands complete.

## Runner Errors

`services/stock-rpc/internal/runner/python.go` is the only place that maps task types to Python command lines. It must reject unsupported task types and require `goal` for `agent_run`. Preserve test coverage like `internal/runner/python_test.go` whenever adding a task type.
