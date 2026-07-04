# 后端部署指南

本文档说明如何在一台服务器上部署 stochips 后端。后端由根目录的
`docker-compose.yml` 编排，包含三个服务：

- **mysql**（MySQL 8.0，容器名 `stock_mysql`）—— 数据持久化在命名卷 `mysql_data`。
- **stock_agent**（Python）—— 容器启动时自动执行数据库迁移，然后运行每日调度任务。
- **stock_rpc**（Go gRPC 网关）—— 对外暴露 gRPC 端口 `50051`，启动时同样自动迁移。

> 所有命令都在**仓库根目录**执行（即 `docker-compose.yml` 与 `.env` 所在目录）。

---

## 1. 前置条件

- Docker Engine（24+ 建议）
- Docker Compose 插件（即可用 `docker compose version`，注意不是老的 `docker-compose`）

验证：

```bash
docker version
docker compose version
```

---

## 2. 克隆与配置 `.env`

```bash
git clone <your-repo-url> stochips
cd stochips
cp .env.example .env
```

然后编辑 `.env`，至少填写下列变量：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `MYSQL_ROOT_PASSWORD` | 是 | MySQL root 密码，生产请改掉默认值 `stock123` |
| `MYSQL_USER` | 是 | 应用数据库用户（默认 `stock`） |
| `MYSQL_PASSWORD` | 是 | 应用数据库密码，会被拼进 `DATABASE_URL`，生产请改掉默认值 |
| `MYSQL_PORT` | 是 | 宿主机映射端口（默认 `3306`） |
| `STOCK_COOKIE` | 是 | 数据抓取所需 Cookie，从浏览器开发者工具复制；不填会被目标站点返回 403 |
| `MOONSHOT_API_KEY` | 否 | Moonshot AI 分析密钥；配置后定时任务会在 16:20 跑 AI 增强评估 |
| `FEISHU_WEBHOOK_URL` | 否 | 飞书自定义机器人 Webhook；配置后定时任务会在 16:30 发送播报卡片 |
| `FEISHU_WEBHOOK_SECRET` | 否 | 飞书机器人签名密钥；仅机器人启用签名校验时填写 |
| `STOCK_RPC_PORT` | 否 | gRPC 宿主机映射端口（默认 `50051`） |
| `LOG_LEVEL` | 否 | 日志级别 `DEBUG/INFO/WARNING/ERROR`（默认 `INFO`） |
| `TZ` | 否 | 时区（默认 `Asia/Shanghai`） |

Docker 构建 Python 依赖默认使用 `.env` 中的 `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple`，该配置会同时作用于 `pip install poetry` 和 `poetry install`。如需切换镜像源，可改成腾讯云、清华源等兼容 PyPI simple API 的地址。

Docker 构建 Go 依赖默认使用 `.env` 中的 `GOPROXY=https://goproxy.cn,direct`，避免 `stock_rpc` 构建阶段访问 `https://proxy.golang.org` 超时。

> 注意：`.env.example` 中的占位值 `STOCK_COOKIE=your_cookie_here`、
> `MOONSHOT_API_KEY=your_moonshot_api_key_here` 以及默认密码 `stock123`
> 都需要按需替换。`deploy.sh` 会拒绝在 `STOCK_COOKIE` 仍是占位值时部署。

---

## 3. 一键部署

推荐使用脚本（含预检与健康等待）：

```bash
./deploy.sh
```

或手动执行：

```bash
docker compose up -d --build
```

启动后容器内会**自动**完成：

- `mysql` 初始化并通过健康检查；
- `stock_agent` 执行 `python migrations/runner.py` 完成数据库迁移，随后运行每日调度；
- `stock_rpc` 同样先迁移，再启动 gRPC 服务。

默认工作日调度（周一到周五执行，周六日不执行）：

| 时间 | 任务 | 条件 |
| --- | --- | --- |
| 16:00 | 抓取同花顺/东方财富股票数据 | 总是启用 |
| 16:10 | 规则风险评估 | 总是启用 |
| 16:20 | AI 增强风险评估 | 仅配置 `MOONSHOT_API_KEY` 时启用 |
| 16:30 | 飞书涨停播报 | 仅配置 `FEISHU_WEBHOOK_URL` 时启用 |

抓取阶段会校验目标日期是否可用：周末直接跳过；如果上游返回的同花顺时间戳不是请求日期，或同花顺为空但东财有数据导致无法确认交易日，会把当天写入 `data_fetch_log.status='skipped'`。后续 16:10/16:20/16:30 的规则评估、AI 评估和飞书播报会读取这个标记并直接退出，避免节假日旧数据继续流转。

> 迁移在容器内自动执行，全新部署无需手动跑迁移。

---

## 4. 端口与数据持久化

- **gRPC**：`${STOCK_RPC_PORT:-50051}` → 容器 `50051`
- **MySQL**：`${MYSQL_PORT:-3306}` → 容器 `3306`

MySQL 数据存放在命名卷 `mysql_data`（默认项目名下即 `stochips_mysql_data`）。

- `docker compose restart` / `down` / `up -d --build` **不会**清空数据。
- 只有 `docker compose down -v`（或手动 `docker volume rm stochips_mysql_data`）
  会**删除数据库数据**，请谨慎使用。

---

## 5. 冒烟测试

```bash
# 查看服务状态（mysql、stock_rpc 应为 healthy）
docker compose ps

# 手动抓取当日数据
docker compose exec stock_agent python main.py fetch

# 对某交易日做 AI 评估（日期格式 YYYYMMDD）
docker compose exec stock_agent python main.py assess-ai 20260615

# 查看某交易日处理状态
docker compose exec stock_agent python main.py status 20260615
```

---

## 6. 常用运维命令

```bash
# 查看日志
docker compose logs -f stock_agent
docker compose logs -f stock_rpc

# 使用 mycli 从宿主机直连 Docker MySQL（默认 .env 用户/端口）
mycli mysql://stock:stock123@127.0.0.1:3306/stock_analysis

# 使用自定义密码或端口时替换占位符；避免把真实密码提交到代码仓库
mycli mysql://stock:<MYSQL_PASSWORD>@127.0.0.1:<MYSQL_PORT>/stock_analysis

# 重启单个服务
docker compose restart stock_rpc

# 重新构建并更新（保留数据）
docker compose up -d --build

# 停止（保留数据卷）
docker compose down

# 停止并删除数据卷（清空数据库，谨慎）
docker compose down -v
```

## 7. 同步代码并重建服务

如果本地改完代码后需要同步到服务器，可以使用本地 rsync 脚本：

```bash
./scripts/rsync-to-server.sh root@8.163.22.74:/root/stochips/
```

然后登录服务器重建并重启后端服务：

```bash
ssh root@8.163.22.74
cd /root/stochips

# 首次启用飞书播报时，确认服务器 .env 已配置：
grep FEISHU .env

# 如果没有飞书配置，追加到服务器 .env
cat >> .env <<'EOF'

# 飞书自定义机器人播报
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id
FEISHU_WEBHOOK_SECRET=
EOF

# 代码有变化时需要重新构建镜像
docker compose up -d --build stock_agent stock_rpc

# 确认服务健康
docker ps -a
docker logs --tail=80 stock_agent
docker logs --tail=80 stock_rpc

# 如果本次改动涉及抓取/落库/播报逻辑，需要重抓目标日期以更新旧数据（upsert 保留数据卷）
docker compose exec stock_agent python main.py fetch 20260703
docker compose exec stock_agent python main.py notify-feishu 20260703
```

如果 `fetch` 输出“数据抓取跳过”，说明该日期被判断为周末、节假日或上游旧数据，后续不需要再手动执行 `assess-ai` / `notify-feishu`。

如果只改了服务器 `.env`，没有同步新代码，可以不加 `--build`：

```bash
docker compose up -d stock_agent stock_rpc
```

飞书播报冒烟测试：

```bash
docker compose exec stock_agent python main.py notify-feishu 20260704
```

---

## 8. 可选：RAG / Wiki 服务

`rag_agent` 默认不启动，位于 `rag` profile 下，仅在需要时按需运行：

```bash
docker compose --profile rag up -d --build rag_agent
```

---

## 9. 故障排查

- **数据抓取返回 403**：`STOCK_COOKIE` 未配置或已失效，重新从浏览器复制最新 Cookie 填入 `.env`，然后 `docker compose up -d`。
- **无法连接 MySQL**：确认 `mysql` 容器 `healthy`（`docker compose ps`）；检查 `.env` 中 `MYSQL_USER` / `MYSQL_PASSWORD` 与首次初始化时一致——若曾改过密码但卷已存在，旧密码仍然生效，需 `down -v` 重建（会清数据）。
- **AI 分析未生效**：`MOONSHOT_API_KEY` 为空或仍是占位值时只运行规则引擎，填入有效密钥后重启服务。
- **构建时 pip/go 连接到失效代理**：Compose 只读取 `.env` 中的 `BUILD_HTTP_PROXY` / `BUILD_HTTPS_PROXY` 作为构建代理。若不需要代理，保持这两个变量为空；若 7890 代理在服务器宿主机上，不要写 `127.0.0.1`，写 `http://host.docker.internal:7890`。
- **构建 `stock_rpc` 时 `go mod download` 访问 `proxy.golang.org` 超时**：默认 `.env` 使用 `GOPROXY=https://goproxy.cn,direct`，Compose 会透传到 Go builder。若仍超时，确认服务器 `.env` 没覆盖成空值，或改用其他可访问的 Go 模块代理。
- **构建时 `Cannot install langchain`**：通常是 Poetry 下载依赖时网络中断。Dockerfile 已提高 pip/Poetry 超时并改为单线程安装；如果服务器 7890 代理可用，可在 `.env` 设置 `BUILD_HTTP_PROXY=http://host.docker.internal:7890` 和 `BUILD_HTTPS_PROXY=http://host.docker.internal:7890` 后重新构建。
