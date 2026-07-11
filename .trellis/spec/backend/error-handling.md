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

## Codex Daily Review Failures

`DailyMarketReviewAgent.run` either returns a complete saved review or raises. It must not
fall back to legacy programmatic scores or Moonshot factor output. When
`AI_FALLBACK_PROVIDER=moonshot`, it may retry the same complete market-review prompt through
Moonshot after a Codex runtime failure.

- Reuse an existing target-date row unless `force=True`.
- Missing strategy file fails before any provider call. Unavailable Codex login uses Moonshot
  only when the explicit fallback is configured and `MOONSHOT_API_KEY` is present; otherwise it fails.
- Empty Codex output fails without committing. Moonshot validates its conservative prompt budget before the HTTP call and reports context exhaustion explicitly instead of truncating facts.
- Feishu remains usable without a review and renders the factual material plus a clear
  "尚未生成当日市场复盘" marker.
- Tests use fake Codex and Moonshot clients; assert the fallback receives exactly the same prompt
  and do not consume a real subscription during unit tests.

## Scenario: Feishu Webhook Rate Limit Retry

### 1. Scope / Trigger
- Trigger: Python agent sends Feishu custom-bot webhook payloads from `FeishuStockNotifier.send_report`.

### 2. Signatures
- `send_report(target_date: date) -> Dict[str, Any]`
- Internal post helper accepts the Feishu interactive-card payload and returns the decoded Feishu JSON response.

### 3. Contracts
- Required env: `FEISHU_WEBHOOK_URL`.
- Optional env: `FEISHU_WEBHOOK_SECRET`; when configured, include `timestamp` and `sign`.
- Feishu success response: `{"code": 0, ...}`.
- Feishu platform rate limit response: `{"code": 11232, "msg": "frequency limited ..."}`.
- The scheduled Feishu report has no independent cron trigger. `DailyJobScheduler.run_daily_job()` sends it only after complete data fetch and a successful Codex review.

### 4. Validation & Error Matrix
- Missing `FEISHU_WEBHOOK_URL` -> raise `ValueError("未设置 FEISHU_WEBHOOK_URL，无法发送飞书播报")`.
- Non-JSON Feishu response -> raise `RuntimeError("飞书返回非JSON响应: ...")`.
- Feishu `code=11232` -> retry with bounded backoff, then return final response if still limited.
- Feishu non-zero code other than `11232` -> do not retry; raise `RuntimeError("飞书发送失败: ...")` at the command boundary.
- Scheduled fetch errors, incomplete data, Codex failures, and formal Feishu failures -> persist `daily_job_run` before sending a red failure status card. Each failed stage retries twice after 5 and 15 minutes; startup restores today's `running`/`retrying` row from its saved stage. After the final failure, the status card uses the next weekday 16:03 as the next automatic task time.
- Failure cards prefer `FEISHU_ALERT_WEBHOOK_URL`; when it is absent they fall back to `FEISHU_WEBHOOK_URL`. A webhook/network outage can still prevent both cards, so logs remain the last-resort signal.
- Codex succeeds during an even minute or exactly at `:00` -> wait until an odd-minute send window with a small random offset before calling `send_feishu_report`.

### 5. Good/Base/Bad Cases
- Good: 11232, 11232, then code 0 -> logs warnings, sleeps between attempts, and reports success.
- Base: code 0 first try -> no warning and no sleep.
- Bad: bad signature or invalid webhook code -> fail fast instead of burning retries.
- Bad: scheduling the daily webhook independently, because it can race the fetch or Codex review and send an incomplete card.

### 6. Tests Required
- Unit test that monkeypatches `requests.post` and `time.sleep` to prove 11232 retries without real delay.
- Unit test that a non-11232 Feishu error returns after one post attempt.
- Unit test that the ordered daily job reaches Feishu only after fetch and Codex review, and stops before review when data is incomplete.

### 7. Wrong vs Correct

Wrong:

```python
if result.get("code", 0) != 0:
    raise RuntimeError(f"飞书发送失败: {result}")
```

Correct:

```python
result = post_with_retry(payload)
if result.get("code", 0) != 0:
    raise RuntimeError(f"飞书发送失败: {result}")
```

## Go gRPC Errors

`services/stock-rpc/internal/server/service.go` maps service errors to gRPC status codes:

- missing task: `codes.NotFound`
- query repository not configured: `codes.FailedPrecondition`
- query execution errors: `codes.Internal`

Task submission returns quickly and executes Python in a goroutine. Execution failures should be stored on the task through `MarkFailed`, then surfaced by `GetTask`; do not block submit RPCs until Python commands complete.

## Runner Errors

`services/stock-rpc/internal/runner/python.go` is the only place that maps task types to Python command lines. It must reject unsupported task types and require `goal` for `agent_run`. Preserve test coverage like `internal/runner/python_test.go` whenever adding a task type.
