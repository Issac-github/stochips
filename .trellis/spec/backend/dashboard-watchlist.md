# Personal dashboard observation pool

## 1. Scope / Trigger
`dashboard/` may write personal observation annotations to a separate SQLite file. Market MySQL remains read-only; this exception does not enable market writes, model generation, trading orders or automated trading scores.

## 2. Signatures
- `GET /api/watchlist?date=YYYY-MM-DD` -> `{date, items, warnings, feedback}`.
- `POST /api/watchlist`, JSON `{date, code, status, outcome, note, revision, concepts?}` -> `{annotation}`.
- `WatchlistService.read(target, user)`, `.save(payload, user)`, `.dates(user)`; owner derived exclusively from the Feishu session.
- `DASHBOARD_WATCHLIST_DB`: optional SQLite path, defaults to `dashboard/data/watchlist.sqlite3`. The Docker overlay fixes `/app/dashboard/data/watchlist.sqlite3` on named volume `dashboard_data`.
- SQLite `observations` key `(owner,date,code)`, fields `snapshot,status,outcome,note,revision,updated_at`. `owner` hashes JSON `[tenant_key,open_id]`. Bootstrap creates only this SQLite table, never market schema.

## 3. Contracts
- Python `build_candidates` merges `top_stocks`, `leader_assists.stock`, `breakout_stocks` by six-digit code in source order. Retain every distinct source observation and full raw fact, roles, risks and generic verification checks. Do not parse free-text AI into stock recommendations or rank candidates.
- Items contain `{code,name,roles,evidence:[{source,detail,fact}],risks,checks,saved,source_missing,annotation}`. Evidence source is a report dataset key.
- Status: `candidate|watching|excluded` (reversible); outcome: `pending|met|not_met|continue`, explicitly manual. Notes <=2000 Unicode characters. Reject missing/unknown fields and boolean/negative revisions.
- `annotation` contains `{status,outcome,note,revision,updated_at,concepts}`. Unsaved default revision0 and concepts[]; every successful save increments revision. `BEGIN IMMEDIATE` and revision comparison prevent lost updates across threads/browser sessions; mismatches409, draft retained in UI. Retrying after an ambiguous network failure requires reloading the current version.
- On first save, snapshot the server-derived observation; later saves preserve that premise. Missing current candidates stay visible from snapshot with `source_missing`; do not rewrite saved evidence when source data changes. Candidate fields/owner are never accepted from clients.
- `/api/dates` unions market dates with only this user's saved dates. If market report404 but saved observations remain, show the independent pool and disable unavailable report/source links. Report and observation queries have separate errors; a MySQL outage is not mistaken for a missing source.
- `feedback` is `{date: string|null, stocks: {[code]: {limit_up: boolean|null, limit_down: boolean|null, continuous_days: number|null}}}`. Choose the earliest later date with actual THS pool/continuous/lower-limit rows or successful relevant fetch logs. Label **后续首个可用行情日**, never claim it is necessarily the immediately next trading day. Membership true is a fact; absence false requires successful full-source log, otherwise null. No later data -> date null. Never infer manual outcome from these facts.
- All reads authenticate first; writes additionally require exact Origin and timing-safe CSRF match, JSON content type, fixed Content-Length1..16384 and no Transfer-Encoding. Responses no-store. Do not log body, personal notes or credentials.
- UI resets on report date change, aborts obsolete loads, disables save on loading/read failure, preserves draft after failure/conflict. Re-read on conflict updates server revision while preserving draft and showing current saved note. Default list hides exclusions; all/excluded filters permit restoring. Export includes the entire date pool, snapshots, annotations and feedback.
- Runtime `dashboard/data/` excluded from Git, Docker build context and rsync. Preserve Docker volume during rebuild/rollback; do not use `down -v`. An older dashboard can ignore the volume without altering market data.

## 4. Validation & Error Matrix
| Condition | HTTP / UI |
| --- | --- |
| No/expired session | 401 before DB access; return to login |
| Wrong Origin / CSRF | 403; no mutation |
| Wrong content type / unsupported framing | 415 / 400 |
| Empty or >16KiB body | 413 |
| Invalid date, code, status, result, note, revision or unknown fields | 400 |
| Stock absent from sources and owner's saved rows | 404 |
| Stale revision | 409, retain local draft; reload before resaving |
| Missing source after saved observation | 200 with saved snapshot and warning |
| SQLite/MySQL unavailable | 503 generic error, no optimistic success |

## 5. Good / Base / Bad Cases
- Good: one code has core/assist/breakout roles; show all evidence, save individual notes, revisit after restart under same identity.
- Base: empty sources render explicit empty table; missing later fetch remains unknown; successful zero-row source supports absence.
- Bad: store notes only in localStorage, write to market tables, trust a client owner/snapshot, drop saved excluded rows, equate missing pool membership with failed strategy conditions.

## 6. Tests Required
- `services/agent/.venv/bin/python -m pytest dashboard/test_server.py dashboard/test_auth.py dashboard/test_watchlist.py -q`: provenance/deduplication/zero values, persistence, user/tenant/date isolation, snapshots after source disappearance, revision conflict, restore, strict writes, real HTTP auth/CSRF/content limits, later-date and unknown feedback, all market statements SELECT-only.
- `cd dashboard && npm run lint && npm run build && npm test`: schemas reject invalid date/status/version, feedback preserves unknown vs confirmed absence; existing Markdown tests remain green.
- Browser: save and reload, exclude/filter/restore, search, date isolation, empty/errors, desktop/375px drawer and controls. Fixtures use only synthetic local identities and temporary annotation files.
- `docker compose -f docker-compose.yml -f docker-compose.dashboard.yml config --quiet` confirms the persistence mount.

## 7. Wrong vs Correct
Wrong: `outcome = 'met' if next_day_limit_up else 'not_met'`.

Correct: retain the manual `outcome` independently; display `limit_up is None` as unavailable evidence, and `limit_up is True` as a later recorded market fact only.

Wrong: accept `{owner, snapshot}` from browser and overwrite on each save.

Correct: derive owner from authenticated session, derive candidate snapshot from report or prior saved snapshot, and require matching revision in a transaction.

## Strategy categories and manual modes

- Canonical `dashboard/strategy-concepts.json` defines seven `groups` (key/title/description/reviewKeys/datasets) and sixteen `concepts` (key/label/group/focus/checks/kind/sources/requirements). Python derives its allowlist from this file; React `strategyCatalog.ts` validates metadata with zod. Evidence-backed display and the distinct meanings of manual review, data gaps, and unimplemented classifiers are specified in [Dashboard evidence](./dashboard-evidence.md). No automatic concept classification, numeric trading thresholds, private method prose or score weights.
- `StrategyCategories` starts with platform category, scopes reusable `Details` to the category's `datasetKeys`, and resets local search/modal on category/date/dataset changes. Source counts are record counts and may overlap, never matched-stock/signal counts. Always append the saved risk section to category-specific review sections; unknown formats render the whole original review.
- The four platform modes are `small_platform`, `large_leader_platform`, `small_leader_platform`, `trend_platform`. Existing `breakout_stocks` remain historical chain price observations, not proof of a platform. Evidence cards show actual coverage and distinguish related observations, missing data, integrations not connected to the dashboard, unimplemented recognition, and questions requiring human judgment. Do not label all cards as pending manual verification.
- `annotation.concepts` is a unique array of catalog keys, default[]. Reject non-arrays, unknown/non-string/duplicate keys and arrays longer than the catalog. POST omission preserves prior concepts for old clients; explicit[] clears. Manual concept tags remain separate from backend source roles and manual condition outcomes.
- SQLite startup transaction creates `observation_concepts(owner,date,code,concepts)` keyed by `(owner,date,code)`. LEFT JOIN with COALESCE[] supplies legacy defaults. Original `observations` stays nine columns so older binaries' positional writes remain compatible; store annotations and labels atomically in the same revision-checked transaction. Existing snapshots/status/notes/versions are not rewritten during bootstrap.
- Category-card navigation opens a fresh observation filter even when entering the same mode repeatedly. Empty manual filters offer reset-to-all for adding labels. Search also matches manual labels; export includes the concepts array. Conflict UI retains draft labels and shows current saved labels with the saved note.
- Tests: legacy nine-column DB initialization, label persistence/restart, old payload preservation/explicit clear, old binary positional updates preserving labels, invalid labels400, HTTP identity isolation. Frontend tests validate the shared catalog, four distinct platform modes, old-response defaults and unknown-label rejection. Browser checks category scoping/reset, manual multi-select/save/reload/filter and 375px layout.

Wrong: assign `small_platform` when `breakout_stocks` includes a code. Correct: keep its existing source role and let the user add a manual observation tag after checking the missing evidence.
