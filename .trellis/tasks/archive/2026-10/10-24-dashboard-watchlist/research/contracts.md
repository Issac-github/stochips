# Existing contracts and approach
- ReportService owns MySQL reads and FeishuStockNotifier reuse. App uses zod + local state and aborts date requests. FeishuAuth stores server-side identity and CSRF tokens. Reuse these patterns.
- Compare persistence choices: localStorage cannot share across browsers; MySQL annotation tables require changing read-only account/migrations; separate SQLite with Docker volume isolates personal writes and uses stdlib without dependencies. Choose separate SQLite.
- Existing top_stocks, leader_assists.stock and breakout_stocks are already report observations. Merge by six-digit code; retain each source fact and label retrospective assist/breakout limitations.
- Never derive investment outcomes from pool absence. Show later database facts separately from user-entered condition results. Label earliest available later date, not guaranteed next trading day.
- Save snapshot with annotation so refreshed source data cannot silently remove saved observations; optimistic revision detects competing browser edits.
- Future: real auction/volume feed can enrich conditions later. MVP handles user/date isolation, missing data, source disappearance, retries and persistence; no trading integration or method publication.
