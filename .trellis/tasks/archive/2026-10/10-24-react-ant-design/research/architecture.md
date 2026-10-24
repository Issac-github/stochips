# Dashboard architecture research

## Repository sources
- `services/agent/chain/stock/agents/feishu_notifier.py`: `FeishuStockReport` has 29 fields; `build_report` reads database and cached DailyMarketReview; material builders add factual narrative.
- `services/agent/chain/stock/models/database.py`: avoid `init_database` in dashboard because it creates tables. Use create_engine + sessionmaker and inject notifier.Session.
- `front/package.json`: existing Electron renderer uses React 19, TS 5.8, Vite 6; new dashboard must not depend on window.api.

## Feasible approaches
1. Recommended: independent dashboard Vite frontend, small Python read-only HTTP adapter reusing notifier; no duplicated SQL/business rules, real dates and cached analysis. Stdlib HTTP is sufficient for a local/private read-only tool and adds no runtime dependency.
2. JSON import only: no backend but needs export and manual refresh; not sufficient for live browsing.
3. Extend Go gRPC + browser adapter: unnecessary proto/client changes; risks duplicating Python report rules.

## UI references
- https://ant.design/components/table/ : typed columns, pagination, expandable rows for full nested detail.
- https://ant.design/components/config-provider : locale and consistent theme.
- https://echarts.apache.org/handbook/en/concepts/chart-size/ : explicit container size, ResizeObserver, dispose on unmount.
- https://vite.dev/config/server-options : dev proxy forwards /api to Python, no browser database credentials.

## Scope and edge cases
- MVP reads full report per date, cached analysis, all fields and textual material; adds raw JSON export for audit.
- No historic trend invented from one date; charts only show available distribution/stock metrics.
- Empty days/partial sources, unavailable DB, no cached review, request races and narrow screens need explicit UI treatment.
- Runtime data must be validated; Decimal/date serialization must be explicit; errors must not expose database credentials.
- Browser uses frontend only; server binds localhost by default, static paths must not escape dist.
