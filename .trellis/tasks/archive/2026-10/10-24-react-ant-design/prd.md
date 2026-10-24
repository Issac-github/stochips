# 飞书播报数据与分析看板

## Goal
在仓库新建独立 React + Ant Design 浏览器应用，展示飞书播报的每一项数据与已有市场分析结果，优先图表，同时保留可搜索明细。

## Known facts
- 现有 front 是 Electron 应用；新应用不依赖 Electron。
- `FeishuStockNotifier.build_report(date)` 是事实数据统一入口，返回 `FeishuStockReport` dataclass。
- 已有报告包括概览、两种分布、板块和行业、核心连板、早盘强势、一字板、龙头助攻、昨日高标反馈、弱板、跌停、突破、板块交集、原因池、涨停池指标、抓取日志和数据警告。
- `daily_review` 提供 content/provider/model；读取不得触发 Codex 或发送飞书。
- notifier 默认 init_database 会建表；只读接口应注入现有 sessionmaker，避免 DDL。
- 仓库已有用户修改（包含 feishu_notifier.py），本任务不覆盖或回退。

## Assumptions
- 新目录命名 dashboard，Vite + TypeScript + Ant Design + ECharts。
- 建议复用 Python 播报逻辑提供只读 HTTP 数据入口；按交易日查看。

## Decision
- 用户已确认直接接真实数据库，新增只读 HTTP 接口。
- 独立 dashboard 目录，React + TypeScript + Ant Design + ECharts；Python 标准库 HTTP 适配器复用现有报告逻辑。
- 默认接口仅监听 localhost；开发通过 Vite 代理，构建后 Python 可同源提供静态页面。

## Requirements
- 日期选择、刷新、明确加载/失败/无数据状态。
- 概览指标与分布/板块/行业图表；所有其余字段有明细入口，字段不可遗漏。
- 分析结果以安全 Markdown 展示，保留模型和服务商信息；无结果明确提示。
- 保留原始 JSON/素材用于核对数据口径。
- 只读，不触发抓取、AI 或播报，不改变现有 Electron。

## Acceptance criteria
- [x] 独立目录可安装启动并构建。
- [x] FeishuStockReport 所有字段可查看，嵌套明细可展开。
- [x] 图表、日期切换、搜索、空态、错误重试可用。
- [x] 数据接口复用 build_report，测试不依赖真实数据库/AI/飞书。
- [x] 文档给出本地/服务器数据连接方式与运行命令。

## Validation
- npm install completed with Node 22.17.1; npm run lint, npm run build (including strict typecheck) passed.
- Black check passed; git diff --check passed.
- Feishu notifier + dashboard suite: 48 passed. Existing SQLAlchemy declarative_base deprecation warning remains.
- Chrome desktop and 390px mobile: charts, nested record modal, search empty state, saved Markdown/provider/model, date switch, missing-review and no-data errors verified using isolated SQLite fixtures.
- Counter zeros without a successful source log are displayed as 未就绪; raw report remains available unchanged.
- Current .env points to Docker-internal mysql. Local live DB connection could not be established; no production data modified. README documents DATABASE_URL and SSH tunnel setup. Browser QA used explicitly isolated test data, no fixtures ship in the runtime UI.
- Build emits normal bundle-size warning (~631 KB gzip) and third-party zod annotation warnings; no build errors.

## Definition of done
- Typecheck/build/lint 通过，接口关键错误路径有测试，完成浏览器检查。

## Out of scope
- 自动生成分析、发送播报、写数据库、重做 Electron、公开部署和账号系统。
