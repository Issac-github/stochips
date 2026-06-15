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
| `MOONSHOT_API_KEY` | 否 | Moonshot AI 分析密钥；留空则只跑规则引擎，不做 AI 分析 |
| `STOCK_RPC_PORT` | 否 | gRPC 宿主机映射端口（默认 `50051`） |
| `LOG_LEVEL` | 否 | 日志级别 `DEBUG/INFO/WARNING/ERROR`（默认 `INFO`） |
| `TZ` | 否 | 时区（默认 `Asia/Shanghai`） |

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

# 重启单个服务
docker compose restart stock_rpc

# 重新构建并更新（保留数据）
docker compose up -d --build

# 停止（保留数据卷）
docker compose down

# 停止并删除数据卷（清空数据库，谨慎）
docker compose down -v
```

---

## 7. 可选：RAG / Wiki 服务

`rag_agent` 默认不启动，位于 `rag` profile 下，仅在需要时按需运行：

```bash
docker compose --profile rag up -d --build rag_agent
```

---

## 8. 故障排查

- **数据抓取返回 403**：`STOCK_COOKIE` 未配置或已失效，重新从浏览器复制最新 Cookie 填入 `.env`，然后 `docker compose up -d`。
- **无法连接 MySQL**：确认 `mysql` 容器 `healthy`（`docker compose ps`）；检查 `.env` 中 `MYSQL_USER` / `MYSQL_PASSWORD` 与首次初始化时一致——若曾改过密码但卷已存在，旧密码仍然生效，需 `down -v` 重建（会清数据）。
- **AI 分析未生效**：`MOONSHOT_API_KEY` 为空或仍是占位值时只运行规则引擎，填入有效密钥后重启服务。
