# Read-only report dashboard

## 1. Scope / Trigger

`dashboard/` is an independent browser app requested with React + Ant Design + ECharts. These choices apply only to the dashboard; `front/` keeps its existing Electron and UI conventions. Python remains the owner of all report calculations.

## 2. Signatures

- `python dashboard/server.py [--host 127.0.0.1] [--port 8787]`
- `GET /api/dates` → `{dates: string[]}` descending ISO dates from行情、日志、已有复盘与当前用户已保存观察日期。
- `GET /api/report?date=YYYY-MM-DD` → `{report, material, previous_day_material, reason_material}`.
- `GET /api/strategy-evidence?date=YYYY-MM-DD` → `{date, coverage, concepts}`; authenticated, date-bounded read-only coverage and per-concept evidence states. See [Dashboard Evidence](./dashboard-evidence.md) for status and inference limits.
- `GET /api/auth/session`, `GET /api/auth/feishu/login`, `GET /api/auth/feishu/callback`, `POST /api/auth/logout` implement login state, OAuth and CSRF-protected logout.
- `ReportService.report(date)` calls `FeishuStockNotifier.build_report` and the three existing material builders. No new SQL business rules, schema or gRPC changes.

## 3. Contracts

- Read `DATABASE_URL` from process environment or repository `.env`, environment wins; do not expose it to browser/Vite.
- Browser schemas live in `dashboard/src/data.ts`; align all report fields with `FeishuStockReport`. Every array has a searchable table; nested values remain accessible via full-record modal. Keep provider/model and cached content intact.
- Dates serialize to ISO, Decimal to numeric; refuse NaN/non-JSON values.
- Market report APIs never create market tables, run migrations, fetch stocks, generate reviews or send Feishu. Use existing `create_engine` + `sessionmaker` injected into notifier. Optional SELECT-only DB account can enforce permissions. Personal observation writes use separate SQLite; see [Dashboard Watchlist](./dashboard-watchlist.md).
- Default HTTP listener is localhost; built assets only from dashboard/dist, no directory listing or files outside dist.
- All report API routes require a server-side Feishu session. OAuth uses one-use state bound to an HttpOnly short-lived cookie and PKCE; session cookie is HttpOnly/SameSite=Lax and Secure on HTTPS. Never log callback query strings or persist provider access tokens.
- Configure explicit `DASHBOARD_PUBLIC_URL`; allow plain HTTP only for loopback development. Production needs HTTPS. Sessions are process-local, expire no later than one hour/provider token expiry, and are invalidated on logout. Optional tenant/open_id allowlists restrict sign-in.
- Frontend fetches relative `/api`; Vite proxies during dev, Python serves same-origin built assets. No Electron `window.api` dependency.

## 4. Validation & Error Matrix

| Trigger | Behavior |
| --- | --- |
| Invalid/missing/duplicate date | 400 JSON error |
| Date with no行情、日志、复盘 | 404 JSON error |
| Partial data or missing review | 200 with warnings/null review; show explicitly |
| DB/table unavailable | 503 generic JSON error; detailed server log |
| Unknown API/static file | 404 |
| Rapid date changes | Abort previous request; validate returned report date |
| Failed refresh | Clear old report; retry action available |
| Missing auth or expired session | Return 401 before database access; frontend returns to login |

## 5. Good / Base / Bad Cases

- Good: latest date loads real report, visualizations reflect same fields as Feishu and JSON export.
- Base: empty dates show empty UI; no cached review shows a clear marker without invoking Codex.
- Bad: copying report rules into frontend/Go, auto-creating tables on a read, showing stale report under a new selected date, rendering raw HTML from analysis.

## 6. Tests Required

- `services/agent/.venv/bin/python -m pytest dashboard/test_server.py dashboard/test_auth.py dashboard/test_strategy_evidence.py -q`: isolated SQLite report/date/evidence queries, no-auth denial, OAuth/PKCE/state replay, session expiry, allowlists and CSRF logout; no credentials in API errors.
- `cd dashboard && npm run lint && npm run build && npm test`: strict TypeScript, runtime zod contracts, production build, conservative Markdown section parsing.
- Browser: charts, detail search/nested values, Markdown, date switching, retry/empty state, responsive layout.

## 7. Wrong vs Correct

Wrong: `notifier = FeishuStockNotifier(database_url); notifier.build_report(day)` in a read-only adapter: default lazy init calls `Base.metadata.create_all`.

Correct:

```python
notifier = FeishuStockNotifier(database_url="")
notifier.engine = engine
notifier.Session = sessionmaker(bind=engine)
report = notifier.build_report(day)
```

Use `CreateTable` without MySQL indexes in isolated SQLite tests: MySQL index names are table-scoped, SQLite index names are database-scoped; existing models reuse `idx_date_type`.

## 8. Feishu authentication

- Report APIs must authenticate before invoking `ReportService`. Public routes are limited to auth status, login start/callback, and built static assets.
- Bind one-use OAuth state to a short-lived HttpOnly cookie and use PKCE. Keep provider tokens server-side and discard after identity lookup. Do not log query strings on OAuth routes.
- Use an explicit HTTPS `DASHBOARD_PUBLIC_URL` in production; loopback HTTP is allowed for local development. Never derive the OAuth redirect from `Host` or accept a return URL parameter.
- Store only opaque random session ids in browser cookies and keep identity/session/CSRF material server-side. Set HttpOnly and SameSite, Secure on HTTPS, expire within one hour/token expiry, and invalidate on logout after exact Origin/CSRF checks.
- This single-process dashboard stores sessions in memory, so restart invalidates sessions and multi-process deployment requires sticky routing. Do not silently expose anonymous reports when login configuration is missing.

## 9. ECS Docker deployment

### 1. Scope / Trigger
- Trigger: deploy the browser dashboard beside the existing Compose services without replacing the server's environment file or database volume.

### 2. Signatures
- Build: `docker compose -f docker-compose.yml -f docker-compose.dashboard.yml build dashboard`.
- Start: `docker compose -f docker-compose.yml -f docker-compose.dashboard.yml up -d dashboard`.
- The overlay adds `dashboard` on `stock_network`, binds `${DASHBOARD_PORT:-8787}:8787`, and uses `mysql` as its database host.

### 3. Contracts
- Repository deployment examples and task notes use documentation IP `192.0.2.10`, instance `i-example`, and security group `sg-example`; replace these locally when deploying. Keep real infrastructure identifiers outside committed files.
- `dashboard/Dockerfile` builds `dashboard/dist` with Node 22 and uses the ECS host's existing `stochips-stock_agent:latest` image as its Python runtime; that image supplies the agent modules' installed dependencies.
- The server binds `0.0.0.0:8787` only inside the container; Compose publishes host port 8787 by default.
- Preserve the ECS `.env`; do not run `scripts/rsync-to-server.sh` for dashboard-only deployment because it syncs the workstation `.env`.
- `DASHBOARD_PUBLIC_URL` defaults to loopback. Missing Feishu credentials keep login unconfigured; all report APIs still require a session. Do not enable public HTTP OAuth.
- Inbound TCP 8787 is a cloud security-group rule separate from the Compose host-port mapping.

### 4. Validation & Error Matrix
| Condition | Behavior |
| --- | --- |
| Node build succeeds and Compose can merge both files | Image can be built and service can be started without changing existing services |
| Missing/invalid DB URL or database unavailable | Dashboard reports an unavailable-data error; it does not create tables |
| No Feishu credentials / no HTTPS domain | Login stays unconfigured and report APIs return 401 |
| TCP 8787 rule missing or host port occupied | Public connection fails even when the container itself is running |

### 5. Good / Base / Bad Cases
- Good: build and start only the dashboard service with the overlay; use an existing Compose network and preserve the server `.env` and volumes.
- Base: HTTP serves the login shell for reachability testing while authenticated data remains unavailable until HTTPS OAuth is configured.
- Bad: use the general rsync script, overwrite `.env`, recreate the database volume, expose the API without session checks, or assume an open security-group port starts the service.

### 6. Tests Required
- `docker compose -f docker-compose.yml -f docker-compose.dashboard.yml config --quiet` validates the merged service definition.
- Build the image and inspect container health / `GET /` after deployment.
- Assert unauthenticated `GET /api/dates` returns 401 and existing services/volume remain running.
- Local build verification requires Node >=20.19; runtime image pins Node 22 for the asset stage.

### 7. Wrong vs Correct
#### Wrong
```sh
rsync -avz ./ root@server:/root/stochips/
```
This can overwrite the server `.env` with workstation credentials.

#### Correct
```sh
rsync -avz --exclude='.env' --exclude='.git/' --exclude='node_modules/' ./ root@server:/root/stochips/
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml up -d --build dashboard
```
For a dashboard-only transfer, explicitly include the dashboard source, `services/agent/`, the root Compose file, and the overlay while preserving `.env`.

## 10. Strategy review presentation

- Default tab is `strategy`; `StrategyOverview` renders saved `daily_review.content`. `MarketOverview` retains existing charts and loads via `React.lazy`. Do not run analysis or introduce frontend trading scores.
- `splitReview(content): ReviewSections | null` in `dashboard/src/review.ts` accepts the complete ordered headings 情绪定位、主线与梯队、龙头与助攻、风险与反证、次日验证清单. Only strip presentation markers from headings; preserve section bodies. Fence contents are not headings.
- Unknown, missing, duplicate, reordered or empty sections, preamble text and unclosed fences return `null`: render the entire original Markdown rather than losing counter-evidence. A null review gets an explicit empty state. Keep the complete-review tab available.
- Keep risk next to analysis on desktop and immediately after sentiment on narrow screens. Keep next-day conditions explicitly pending.
- Evidence tables use `top_stocks`, `previous_high_feedback`, `leader_assists` in backend order. Preserve zero values and distinguish null from zero. `App` owns the `DatasetKey` so evidence links open the matching `Details` view; reset search/modal on date or dataset changes.
- Height does not confirm leadership; turnover does not prove historical volume extremes. “未进入涨停池” does not mean limit down. Assist records are retrospective candidates (including non-one-word/first-board), not verified intraday causal relationships. Historical volume, auction, opening gaps and intraday continuity require additional facts.
- Keep internal methodology source documents private. Public UI and committed documentation describe display contracts without copying private source material.
- Verify with `npm test`: all five bodies preserved, CRLF/heading markers, fenced headings, invalid-format fallback. Browser checks cover desktop/mobile, evidence navigation, missing review, legacy Markdown, date changes and failed requests clearing stale data.
