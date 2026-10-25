# 飞书播报看板

## ECS Docker deployment

The root `docker-compose.dashboard.yml` overlay adds a `dashboard` container to the existing Compose project and MySQL network. Keep the ECS `.env` in place; the general synchronization script includes `.env` and must not be used for this deployment.

After transferring the dashboard source and Compose overlay to `/root/stochips`, run from that directory:

```sh
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml up -d --build dashboard
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml ps dashboard
curl -fsS http://127.0.0.1:8787/ >/dev/null
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8787/api/dates
```

The last command should print `401` while Feishu credentials and HTTPS callback configuration are absent. Inbound TCP 8787 must also be allowed in the ECS security group. This temporary HTTP deployment only verifies reachability; do not enable Feishu OAuth over public HTTP.

To roll back only the dashboard service:

```sh
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml stop dashboard
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml rm -f dashboard
```

This leaves the MySQL volume and all other containers untouched.

独立 React + Ant Design + ECharts 网页，直接复用 Python 的 `FeishuStockNotifier.build_report()`。原有 Electron 前端不受影响。

## 功能

- 默认“策略复盘”先展示已保存的情绪定位、主线与梯队、龙头与助攻；风险与反证、次日验证在桌面并排显示，手机端优先呈现风险。
- 仅完整识别已有五节格式时分卡展示，历史或非标准格式完整保留原文；没有分析时明确显示空态。
- 策略页可核对核心连板、昨日高标反馈和助攻候选，并跳转全部字段。历史量能、竞价与分时不足的条件单独标明待验证，不由换手率或收盘候选推导交易结论。
- “策略分类”按情绪与空间、主线与梯队、龙头与助攻、量能与弱转强、平台与反包、竞价与分时、风控与跟踪七类展示16个核对概念；每类关联原始数据和已保存复盘，保留风险反证。
- 平台类分别展示小平台、大龙头天量平台、小龙头天量平台、趋势龙头平台突破，并列出待补证据。来源条数仅是数据记录数，不是模式匹配或选股信号数。
- “次日观察池”合并核心连板、助攻及前高观察，同股保留多来源依据；支持关注、剔除、恢复、角色/状态筛选、搜索和独立 JSON 导出。
- 观察状态、人工验证结果和备注按飞书账号与报告日期保存在服务器，保存时保留依据快照；来源消失仍可查看。后续行情展示首个可用日期的事实，不自动判定条件满足。
- 日期选择、刷新、完整 JSON 导出；日历蓝点代表数据库有记录。
- “市场数据”保留同花顺/东财涨停、连板、最高板、跌停、板块数量，以及连板梯队、涨停结构、板块/行业图表；图表代码按需加载。
- 全部 14 类明细：板块、行业、核心连板、龙头助攻、昨日高标、一字板、早盘强势、弱板、跌停、突破、板块交集、原因池、涨停池指标、抓取日志。
- 明细支持搜索、排序、分页；嵌套记录点击“查看明细”展开，保留全部字段。
- 已保存的每日分析结果，包含 provider/model；飞书事实素材、前日对照、原因素材和原始 JSON 均可查看。
- 数据不完整、缺失分析、空日期和连接失败均明确提示。市场概览仅展示当日数据，不推算跨日走势。

## 环境

- Node.js >= 20.19，建议 Node.js 22。
- Python >= 3.10，使用 `services/agent` 的现有 Python 环境和依赖（SQLAlchemy、PyMySQL、python-dotenv 等）。
- 已迁移的 MySQL 数据库。行情数据库保持只读；看板不会迁移行情、抓取、调用 Codex 或发送飞书。个人观察记录写入独立 SQLite。
- 飞书开放平台中独立创建的 StoChips 企业自建应用，开启网页应用能力并配置回调地址。

## 飞书登录配置

看板所有日期与报表接口均要求飞书登录。请在服务器进程环境或根目录 `.env` 设置：

```dotenv
FEISHU_APP_ID=cli_...
FEISHU_APP_SECRET=...
DASHBOARD_PUBLIC_URL=https://dashboard.example.com
# 可选：限制到指定企业 tenant_key 或用户 open_id，逗号分隔
FEISHU_ALLOWED_TENANT_KEYS=
FEISHU_ALLOWED_OPEN_IDS=
```

开放平台新建独立的 StoChips 应用后，在应用能力中启用网页应用/网页登录；把 `https://dashboard.example.com/api/auth/feishu/callback` 配置为 OAuth 重定向地址，并把应用发布到允许使用者可见的范围。实际公开域名必须与 `DASHBOARD_PUBLIC_URL` 一致。仅申请登录所需的基础身份信息，不申请通讯录、消息或邮箱权限。不要把 App Secret 提交到 Git。

本机开发时，StoChips 应用 ID 为 `cli_aa56fa290af85cb7`。在根目录未跟踪的 `.env` 设置 `FEISHU_APP_ID=cli_aa56fa290af85cb7`、从开放平台“凭证与基础信息”复制 `FEISHU_APP_SECRET`、以及 `DASHBOARD_PUBLIC_URL=http://127.0.0.1:5174`。开发回调 `http://127.0.0.1:5174/api/auth/feishu/callback` 已登记；Vite 会代理授权回调到 Python 服务。运行前端时用 `npm run dev`，Python 服务仍需在另一个终端运行。服务器生产环境必须使用 HTTPS。可选的用户/企业白名单默认不启用；应用自身的可用范围仍由飞书管理。

登录采用一次性 state、PKCE 和 HttpOnly 会话 cookie；会话在服务端内存中保存，最长一小时，应用进程重启后需重新登录。生产部署保持单进程，或在反向代理后固定路由到同一进程。

## 个人观察记录

进入“次日观察池”，点击股票的“查看 / 编辑”核对来源、风险和待验证条件，再保存关注状态、人工结果与备注。剔除记录可通过“全部状态”或“仅已剔除”恢复。关闭详情、刷新或切换日期前请保存编辑内容。

详情中的“人工模式分类”可多选，例如“小平台突破”和“趋势龙头平台突破”。保存后可按模式或“未分类”筛选，并随观察池 JSON 导出；这些标记只记录观察方向，是否满足条件仍由人工验证结果单独记录。从策略概念卡可直接查看对应模式的已标记股票，空分类可点击“显示全部股票并添加分类”。

模式目录统一在 `dashboard/strategy-concepts.json`，由 Python 与 React 共用。启动时自动创建独立 `observation_concepts` 表，原有观察记录与版本号保留。旧客户端省略 `concepts` 时保留已有分类，传空数组可清空；原 `observations` 表仍为九列，兼容旧版保存逻辑。

默认写入 `dashboard/data/watchlist.sqlite3`；可用 `DASHBOARD_WATCHLIST_DB` 指定绝对路径，进程须有目录写权限。Docker overlay 自动挂载独立 `dashboard_data` 卷，重建容器不丢记录。SQLite 文件包含个人备注，已从 Git、镜像构建和同步脚本排除。备份时停止看板后复制此文件，或使用 SQLite backup API；不要删除该持久卷。

记录按飞书 `tenant_key + open_id` 隔离，其他账号不可见。保存版本冲突时保留编辑内容，重新读取并对比已保存备注后再保存。保存快照保留首次记录的依据，当前来源明细用于对照，二者可能因行情修正不同。

“后续首个可用行情日”可能跨过缺失日期，不保证紧邻下一交易日。只有抓取成功的完整来源才能把缺席显示为“未见记录”；缺少来源显示数据不足。人工结果与后续涨跌停事实各自保留。

## 开发运行

在仓库根目录启动只读接口，默认读取根目录 `.env` 中的 `DATABASE_URL`（外部环境变量优先）：

```bash
services/agent/.venv/bin/python dashboard/server.py
```

若未安装 Agent 环境：

```bash
cd services/agent
poetry install
poetry run python ../../dashboard/server.py
```

在另一个终端启动前端：

```bash
cd dashboard
npm ci
npm run dev
```

访问 **http://127.0.0.1:5174**。Vite 将 `/api` 代理到 `127.0.0.1:8787`。

宿主机启动接口时，连接串里的数据库主机应为宿主机可访问的地址；Docker Compose 的服务名 `mysql` 只在容器网络内可用。连接串使用现有 `DATABASE_URL` 格式：

```text
mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/stock_analysis?charset=utf8mb4
```

密码中的特殊字符需要 URL 编码。可使用只有 SELECT 权限的数据库账号。

## 读取服务器数据库

在本地建立 SSH 隧道，并保持终端打开：

```bash
ssh -N -L 13306:127.0.0.1:3306 root@192.0.2.10
```

为看板进程单独设置 `DATABASE_URL`，主机使用 `127.0.0.1`，端口使用 `13306`，账号与密码使用服务器数据库凭据。然后按上面的命令启动接口和网页。服务器的数据库映射端口如非 3306，需相应修改隧道目标端口。

该方式只读取服务器数据，不需要同步 Docker 数据卷或 Codex 登录信息。

## 构建后单进程运行

```bash
cd dashboard
npm ci
npm run build
cd ..
services/agent/.venv/bin/python dashboard/server.py
```

访问 **http://127.0.0.1:8787**，同一进程提供 `dist/` 静态页面和只读 API。默认仅监听本机；如需团队访问，可使用私有网络的反向代理。独立参数：`--host`、`--port`，不改动原有 Docker 服务。

## 接口

- `GET /api/auth/session` → 登录配置状态和当前用户（只返回 open_id、姓名、tenant_key）；
- `GET /api/auth/feishu/login` 与 `/api/auth/feishu/callback` → 飞书 OAuth；
- `POST /api/auth/logout` → 带 Origin 与 CSRF 校验的退出；
- `GET /api/dates` → `{ "dates": ["2026-10-23", ...] }`，日期降序，覆盖行情、日志、已有复盘及当前账号已保存观察日期。
- `GET /api/report?date=YYYY-MM-DD` → `{ report, material, previous_day_material, reason_material }`。
- report 原样序列化 `FeishuStockReport`；日期为 ISO 字符串、Decimal 转为数字，未知字段类型报错。
- 非法日期返回 400、无数据返回 404、数据库或表结构异常返回 503。
- 未登录的报表请求返回 401；无效退出请求返回 403。
- 每次请求重新查询数据库；分析内容来自已保存的 `daily_market_review`。缺失分析时不会自动生成。
- `GET /api/watchlist?date=YYYY-MM-DD` → `{date, items, warnings, feedback}`，候选来源与个人记录、后续行情事实。
- `POST /api/watchlist` → `{annotation}`；请求 `{date, code, status, outcome, note, revision, concepts?}`，`concepts` 为目录中模式 key 的去重数组，可省略。需要已登录会话、同源 Origin 和 `X-CSRF-Token`。仅保存自己的观察记录，备注最多2000字，旧版本返回409；不接受客户端指定账号或候选快照。

## 验证

```bash
cd dashboard
npm run lint
npm run build
npm test
cd ..
services/agent/.venv/bin/python -m pytest dashboard/test_server.py dashboard/test_auth.py dashboard/test_watchlist.py -q
```

前端测试覆盖五节 Markdown 的完整保留和非标准格式回退。接口测试使用隔离 SQLite 和本地 HTTP 服务，不连接生产数据库，不消耗 AI 额度。
