# 📈 股票智能选股与风控系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于Python的A股涨停数据系统，使用Codex结合交易体系生成每日市场复盘并发送飞书。

## ✨ 核心特性

### 🔄 数据抓取

- **同花顺数据源**：连板天梯、最强风口、涨停强度
- **东方财富数据源**：涨停池（两步智能拉取）
- **完全保留请求头**：100%还原浏览器请求参数
- **异步高性能**：aiohttp异步并发抓取

### 🤖 AI智能分析

- **Codex每日复盘**：每天只调用一次，不再逐股打分
- **交易体系驱动**：Python读取 `chain/wiki/raw/001-连板龙头交易体系.md` 并完整传给 Codex
- **完整事实材料**：输入与飞书一致的板块热度、涨停结构、核心连板和异动数据
- **定性自主研判**：不使用程序预设分数、权重、风险因子或建议标签

### 🐳 容器化部署

- **Docker Compose**：一键启动MySQL + Agent服务
- **自动定时任务**：工作日16:03启动串行流程，抓取完成后复盘，复盘完成后播报
- **数据持久化**：MySQL存储，支持历史回溯
- **日志监控**：完整日志记录和状态监控

## 🚀 快速开始

### 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd stochips   # 仓库根目录，docker compose 与 .env 都在这里

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要参数
vim .env
```

### 配置说明

**必需配置**：

```bash
# MySQL配置
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_USER=stock
MYSQL_PASSWORD=your_password
DATABASE_URL=mysql+pymysql://stock:your_password@mysql:3306/stock_analysis?charset=utf8mb4

# 同花顺Cookie（数据抓取必需）
STOCK_COOKIE=your_ths_cookie
```

使用自己的 ChatGPT/Codex 订阅。设置以下配置后，Python 服务会直接通过官方
`openai-codex` SDK 调用本地 Codex app-server；OAuth 登录态只保存在容器的
`/root/.codex` volume，不会写入 `.env`：

```bash
AI_PROVIDER=codex
AI_FALLBACK_PROVIDER=moonshot  # 可选：Codex不可用时使用Kimi API
MOONSHOT_API_KEY=your_moonshot_api_key
MOONSHOT_MODEL=kimi-k2.5
MOONSHOT_CONTEXT_WINDOW=262144
```

**获取Cookie方法**：

1. 访问 https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html
2. F12打开开发者工具 → Network标签
3. 刷新页面，找到XHR请求
4. 复制请求中的Cookie字段（主要是`v=`后面的值）

### Docker 部署（推荐）

默认 Docker 部署包含 MySQL、Python Agent 与 Go RPC；RAG/wiki 按需启动：

| 服务            | 说明                                                  |
| --------------- | ----------------------------------------------------- |
| `mysql`       | MySQL 8.0 数据库，保存抓取数据、日志和Codex每日复盘   |
| `stock_agent` | Python Agent 服务，定时抓取数据并生成Codex每日复盘    |
| `stock_rpc`   | Go gRPC 网关，提交任务并调用现有 Python 股票命令执行  |
| `rag_agent`   | 可选服务，运行 wiki/RAG 向量检索，使用 CPU-only torch |

`stock_agent` 镜像默认只安装股票抓取、风控和 Moonshot AI 分析依赖，不安装 HuggingFace/Chroma/Torch，避免镜像过大。需要 wiki/RAG 时启动单独的 `rag_agent`，它会安装 CPU-only torch，并把模型缓存、Chroma 向量库挂到 Docker volume。

#### 基础启动

```bash
# 1. 准备环境变量
cp .env.example .env
vim .env

# 2. 构建并启动 MySQL + 股票 Agent
docker compose up -d --build

# 3. 查看服务状态
docker compose ps

# 4. 查看日志
docker compose logs -f stock_agent
docker compose logs -f mysql
```

#### 使用 ChatGPT/Codex 订阅

先在 `.env` 设置 `AI_PROVIDER=codex`。服务器能够直接访问 OpenAI 时，启动 Agent 后完成一次设备码登录：

```bash
docker compose up -d --build stock_agent stock_rpc
docker compose exec stock_agent python main.py codex-login
```

登录命令会显示 OpenAI 的授权地址和设备码；登录态写入 `codex_home` volume。每日复盘
使用只读、禁止命令审批的 Codex 线程。订阅额度耗尽或 Codex 不可用时，若设置
`AI_FALLBACK_PROVIDER=moonshot` 且配置 `MOONSHOT_API_KEY`，会把完全相同的复盘 prompt
交给 Kimi；否则本次复盘失败。无论哪种情况，都不会生成旧版评分结果。

##### 服务器临时使用本地代理

当服务器无法直接访问 OpenAI、但本地电脑可以访问时，可以通过 SSH 反向端口转发，
让服务器临时使用本地代理。以下示例假设本地代理监听 `127.0.0.1:7892`。

先在本地电脑执行，并保持这个终端连接：

```bash
ssh -NT \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -R 127.0.0.1:7892:127.0.0.1:7892 \
  root@8.163.22.74
```

另开一个服务器终端，确认 HTTP 代理可以访问 OpenAI：

```bash
curl -I -x http://127.0.0.1:7892 https://chatgpt.com
```

隧道只在 SSH 连接存活期间有效。不要在服务器全局设置 `HTTP_PROXY`；下面的脚本会把
代理只传给本次 Docker 构建、Codex 登录或 AI 命令。

##### 服务器临时代理操作

SSH 隧道已经映射到服务器 `127.0.0.1:7892` 后，按这个顺序操作：

```bash
# 1. 首次部署或同步代码后：构建并启动两个服务
./scripts/stochips-with-proxy.sh

# 2. 首次使用 Codex：设备码登录，授权信息保存在 codex_home volume
./scripts/stochips-with-proxy.sh --login

# 3. 验证最新代码确实走 Codex，并强制忽略旧 AI 缓存
AI_PROVIDER=codex AI_FALLBACK_PROVIDER=moonshot \
  ./scripts/stochips-with-proxy.sh --rebuild --assess-ai 20260710 --force-ai

# 4. 使用同一临时代理发送飞书报告
./scripts/stochips-with-proxy.sh --notify-feishu 20260710
```

`--rebuild` 会只重建 `stock_agent`，并重建它的服务容器后再执行指定动作。因此同步了
Python 代码、又要马上执行 `--assess-ai` 时应使用它；不带 `--rebuild` 的运行命令只复用
当前镜像，不会自动读取新同步的源文件。

常用补充命令：

```bash
# 只构建，不启动服务
./scripts/stochips-with-proxy.sh --build-only

# 指定不同的本地反向代理端口
PROXY_URL=http://127.0.0.1:7893 ./scripts/stochips-with-proxy.sh --login

# 只运行原始 AI 分析
AI_PROVIDER=codex ./scripts/stochips-with-proxy.sh --ai-analyze 20260710
```

脚本在运行时使用 host 网络访问反向隧道，并临时把数据库连接改到宿主机发布的 MySQL
端口，因此不会碰到 host 网络容器无法解析 Compose 服务名 `mysql` 的问题。所有临时容器
都会删除，代理和授权信息不会写入 `.env`；授权信息只保存在 `codex_home` volume。

##### 代理端口与生效周期

| 端口 | 所在位置 | 用途 | 何时可用 |
| --- | --- | --- | --- |
| `127.0.0.1:7892` | 服务器宿主机 | 本地电脑代理的 SSH 反向隧道 | 本地 `ssh -R` 连接保持期间 |
| `127.0.0.1:7890` | 服务器宿主机 | 服务器自身的 HTTP 代理 | 服务器代理服务运行期间 |

`stochips-with-proxy.sh` 当前一次只能使用一个代理：默认是 `7892`，也可以显式指定服务器
本地代理：

```bash
PROXY_URL=http://127.0.0.1:7890 ./scripts/stochips-with-proxy.sh --login
```

它会把选中的地址传给临时构建和一次性 `docker run --network host` 容器；因此 Docker 能访问
服务器宿主机的 `7892` 与 `7890`。普通 `docker compose exec stock_agent ...` 位于 Compose
网络中，`127.0.0.1` 指向容器自身，不能直接使用这两个宿主机端口。

代理只在脚本进程存活期间生效：构建结束会删除临时 Compose 覆盖文件，AI/登录/播报的一次性
容器退出后代理环境变量随即消失，`--rebuild` 创建的常驻 `stock_agent` 容器也不会继承代理。
Docker daemon 拉取基础镜像同样不使用这个临时代理。

当前脚本不会自动从 `7892` 切换到 `7890`。如果隧道断开，请显式传入上述 `PROXY_URL=...7890`；
自动探测并回退需要在脚本中额外实现，不能由 Docker 自身完成。

旧命令 `./scripts/docker-build-with-proxy.sh` 仍可使用，但只作为兼容入口；新操作统一使用
`./scripts/stochips-with-proxy.sh`。

该脚本只代理 Dockerfile 中的 `apt`、`pip`、`poetry` 等下载。若失败发生在
`load metadata` 或基础镜像 `pull` 阶段，则是 Docker daemon 拉取镜像，脚本无法代理
该阶段。

`.env` 中至少需要确认这些值：

```bash
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_USER=stock
MYSQL_PASSWORD=your_password
MYSQL_PORT=3306

STOCK_COOKIE=your_ths_cookie
STOCK_FETCH_START_JITTER_MIN=5
STOCK_FETCH_START_JITTER_MAX=45
STOCK_FETCH_SOURCE_DELAY_MIN=3
STOCK_FETCH_SOURCE_DELAY_MAX=8
STOCK_FETCH_PAGE_DELAY_MIN=0.8
STOCK_FETCH_PAGE_DELAY_MAX=2.0

# 启用Codex每日市场复盘
AI_PROVIDER=codex
AI_FALLBACK_PROVIDER=none

# 可选：启用定时飞书播报
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id
FEISHU_WEBHOOK_SECRET=
# 失败状态卡建议使用另一台机器人；留空时才复用正式播报机器人。
FEISHU_ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-alert-hook-id
FEISHU_ALERT_WEBHOOK_SECRET=

LOG_LEVEL=INFO
TZ=Asia/Shanghai
```

#### 股票任务命令

```bash
# 手动抓取今天数据
docker compose exec stock_agent python main.py fetch

# 手动抓取指定日期
docker compose exec stock_agent python main.py fetch 20260506

# 生成每日Codex复盘；加 --force-ai 可替换已保存的当日报告
docker compose exec stock_agent python main.py assess-ai 20260506 --force-ai

# 完整流程：抓取 + Codex每日复盘
docker compose exec stock_agent python main.py run 20260506

# 目标驱动 Agent：根据目标决定抓取、Codex复盘和报告
docker compose exec stock_agent python main.py agent "更新数据并完成每日市场复盘" 20260506

# 查看数据状态
docker compose exec stock_agent python main.py status 20260506

# 发送飞书涨停播报卡片
docker compose exec stock_agent python main.py notify-feishu 20260506
```

如果抓取目标日期是周末，或上游实际返回的同花顺交易日期不是请求日期，抓取命令会输出“数据抓取跳过”并写入 `data_fetch_log.status='skipped'`；后续 `assess-ai`、`notify-feishu` 会读取该标记并直接退出，避免节假日/旧数据继续复盘和播报。

飞书播报需要在 `.env` 中配置群自定义机器人 Webhook：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id

# 如果机器人启用了签名校验，再配置签名密钥
FEISHU_WEBHOOK_SECRET=your_secret

# 失败状态卡优先使用独立机器人；未配置时复用上面的正式机器人
FEISHU_ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-alert-hook-id
FEISHU_ALERT_WEBHOOK_SECRET=your_alert_secret
```

#### MySQL 命令

```bash
# 进入 MySQL
docker compose exec mysql mysql --default-character-set=utf8mb4 -ustock -p stock_analysis
```

如果想在宿主机使用 `mycli` 连接 Docker 里的 MySQL，先确认容器已启动，并使用映射到宿主机的端口连接：

```bash
# 启动 MySQL 容器
docker compose up -d mysql

# 使用 mycli 连接，默认密码见 .env 中的 MYSQL_PASSWORD
mycli mysql://stock:stock123@127.0.0.1:3306/stock_analysis

# 如果 .env 修改了 MYSQL_PASSWORD 或 MYSQL_PORT，对应替换密码和端口
mycli mysql://stock:<MYSQL_PASSWORD>@127.0.0.1:<MYSQL_PORT>/stock_analysis
```

注意：宿主机连接 Docker 暴露端口时使用 `127.0.0.1:<MYSQL_PORT>`；只有在 `stock_agent` 等 Compose 容器内部访问时才使用 `mysql:3306`。

```sql
-- 清理某天板块数据后重新抓取
DELETE FROM block_top WHERE date = '2026-05-06';

-- 查询当天各表数量
SELECT COUNT(*) FROM continuous_limit_up WHERE date = '2026-05-06';
SELECT COUNT(*) FROM block_top WHERE date = '2026-05-06';
SELECT COUNT(*) FROM limit_up_pool WHERE date = '2026-05-06';
SELECT COUNT(*) FROM lower_limit_pool WHERE date = '2026-05-06';
SELECT COUNT(*) FROM eastmoney_zt_pool WHERE date = '2026-05-06';
```

#### 运维命令

```bash
# 停止服务但保留 MySQL 数据卷
docker compose down

# 停止并删除 MySQL 数据卷（会清空数据）
docker compose down -v

# 只重建并重启股票 Agent
docker compose build --no-cache stock_agent
docker compose up -d stock_agent

# 构建并启动 Go gRPC 网关
docker compose up -d --build stock_rpc

# 清理无标签旧镜像
docker image prune -f

# 清理未使用的构建缓存
docker builder prune -f
```

#### Wiki/RAG 命令

```bash
# 构建 RAG/wiki 镜像（CPU-only torch）
docker compose --profile rag build rag_agent

# 列出 wiki 页面
docker compose --profile rag run --rm rag_agent python -m main wiki pages

# 构建/强制重建 wiki 向量库
docker compose --profile rag run --rm rag_agent python -m main wiki build

# 查询 wiki
docker compose --profile rag run --rm rag_agent python -m main wiki query "什么是龙头"

# RAG 检索/问答
docker compose --profile rag run --rm rag_agent python -m chain.rag.main build
docker compose --profile rag run --rm rag_agent python -m chain.rag.main rebuild
docker compose --profile rag run --rm rag_agent python -m chain.rag.main search "天量"
docker compose --profile rag run --rm rag_agent python -m chain.rag.main chat "天量代表什么"

# 删除 RAG/wiki 向量库 volume（会清空已构建索引，保留模型缓存）
docker compose down
docker volume rm agent_rag_chroma agent_wiki_chroma

# 如果连 HuggingFace 模型缓存也要清空，再执行这个
docker volume rm agent_hf_cache
```

`rag_agent` 使用 Docker volume 保存 Chroma 向量库和 HuggingFace 模型缓存。重建镜像不会删除向量库和模型缓存；删除 `agent_rag_chroma`、`agent_wiki_chroma` 会强制重新构建索引，删除 `agent_hf_cache` 会导致下次重新下载 embedding 模型。

国内服务器首次下载 embedding 模型时建议保留 `.env` 中的：

```bash
HF_ENDPOINT=https://hf-mirror.com
PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
TORCH_VERSION=2.7.1+cpu
```

已有数据库升级不需要手工执行SQL；`stock_agent` 和 `stock_rpc` 启动时会自动运行
`migrations/runner.py`，创建 `daily_market_review` 与 `daily_job_run` 表。

### 本地开发

```bash
# 进入 agent 目录（本地开发命令都在这里执行）
cd services/agent

# 安装依赖
pip install poetry
poetry install

# 查看 Poetry 当前使用的 Python
poetry run python --version

# 运行命令（推荐始终通过 poetry run 使用项目虚拟环境）
poetry run python -m main fetch 20260412
```

## 📖 使用指南

### CLI命令

以下命令默认在 `services/agent/` 目录下执行。推荐使用 `poetry run python -m ...`，这样会固定使用 Poetry 管理的虚拟环境，并按模块路径运行入口。

```bash
# 数据抓取
poetry run python -m main fetch [YYYYMMDD]           # 抓取同花顺 + 东方财富数据

# Codex每日市场复盘
poetry run python -m main assess-ai [YYYYMMDD] [--force-ai]
# assess / ai-analyze 保留为同一命令的兼容别名

# 完整流程
poetry run python -m main run [YYYYMMDD]             # 抓取+Codex复盘
poetry run python -m main agent "完成每日市场复盘" [YYYYMMDD]

# 定时任务
poetry run python -m main schedule                   # 启动定时调度器

# 状态查询
poetry run python -m main status [YYYYMMDD]          # 查看数据状态

# Wiki 知识库
poetry run python -m main wiki query "什么是龙头"
poetry run python -m main wiki build

# RAG 检索
poetry run python -m chain.rag.main search "天量"
poetry run python -m chain.rag.main chat "天量代表什么"

# 测试
poetry run python -m pytest
```

### Python API

```python
from chain.stock.data import create_fetcher, create_storage
from chain.stock.agents import create_daily_market_review_agent
from datetime import date

# 数据抓取
fetcher = create_fetcher()
data = fetcher.fetch_all_data('20260412')

# 数据存储
storage = create_storage('mysql+pymysql://user:pass@localhost/stock_analysis?charset=utf8mb4')
results = storage.save_all_data(data, date(2026, 4, 12))

# Codex每日市场复盘
agent = create_daily_market_review_agent(
    'mysql+pymysql://user:pass@localhost/stock_analysis?charset=utf8mb4'
)
result = agent.run(date(2026, 4, 12), force=True)
```

## 🏗️ 系统架构

```
agent/
├── 📁 chain/stock/                 # 核心业务代码
│   ├── 📁 data/
│   │   ├── fetcher.py              # 数据抓取（同花顺+东财）
│   │   └── storage.py              # MySQL存储
│   ├── 📁 models/
│   │   └── database.py             # 数据模型定义
│   ├── 📁 agents/
│   │   ├── codex_client.py         # Codex订阅客户端
│   │   ├── daily_market_review_agent.py # 每日市场复盘
│   │   └── feishu_notifier.py      # 事实汇总与飞书卡片
│   └── 📁 scheduler/
│       └── daily_job.py            # 定时任务
├── 📁 docker/mysql/init/           # MySQL初始化脚本
├── 📁 examples/                    # 示例报告
├── main.py                         # CLI入口
├── docker-compose.yml              # Docker编排
└── pyproject.toml                  # 依赖管理
```

## 🗄️ 数据库Schema

### 同花顺数据源

| 表名                    | 说明     | 核心字段                     |
| ----------------------- | -------- | ---------------------------- |
| `continuous_limit_up` | 连板天梯 | 连板天数、涨停时间、涨停原因 |
| `block_top`           | 最强风口 | 板块热度、龙头股、涨停家数   |
| `limit_up_pool`       | 涨停强度 | 封单强度、换手率、量比       |
| `lower_limit_pool`    | 跌停池   | 首次/最后跌停时间、跌幅、换手率、流通市值 |

### 东方财富数据源

| 表名                  | 说明   | 核心字段                    |
| --------------------- | ------ | --------------------------- |
| `eastmoney_zt_pool` | 涨停池 | 封单金额、涨停类型、3日涨幅 |

### 分析结果

| 表名                | 说明     | 核心字段                   |
| ------------------- | -------- | -------------------------- |
| `daily_market_review` | Codex每日复盘 | 日期、复盘正文、模型、材料摘要 |
| `daily_job_run` | 每日任务状态 | 阶段、状态、重试次数、下次重试时间 |
| `risk_assessment` | 历史兼容 | 旧版逐股评分，不再由日常流程写入 |
| `data_fetch_log`  | 操作日志 | 抓取状态、记录数、错误信息 |

## 🧠 Codex每日复盘

`assess-ai` 每个交易日最多生成一份定性复盘。Python会完整读取
`chain/wiki/raw/001-连板龙头交易体系.md` 并嵌入 Codex 提示词，再分析飞书卡片使用的事实材料，包括涨停概览、
板块热度、行业涨停、核心连板、早盘强势、分歧弱板、前高突破和抓取日志。Codex还会收到
同花顺板块成员与涨停池个股的 `reason_type` 简略原因、未经截断的 `reason_info` 详细原因，
以及同花顺首次/最后涨停时间；飞书板块列表仍保持紧凑。

为判断情绪和主线变化，Codex还会收到前一交易日的完整事实与原因材料，以及涨停概览、
结构、核心连板、全部热点板块及与当日共同热点的涨停家数变化。飞书不会重复展示前一日材料。

程序不再计算风险分数、权重或因子，也不要求Codex返回JSON。结果按日期写入
`daily_market_review`，普通执行复用当日报告；`--force-ai` 会发起一次新调用并覆盖当日报告。
飞书卡片保留事实材料，并在末尾追加保存的Codex复盘和实际模型来源。

## ⏰ 定时任务

默认调度策略（周一到周五执行，周六日不执行）：

```
16:03 - 启动每日串行流程（启动前随机等待 5-45 秒，数据源之间随机等待 3-8 秒）
抓取完成且数据完整 - 生成或复用Codex每日市场复盘
Codex复盘成功 - 等到非整分的奇数分钟后发送飞书涨停播报
```

抓取、Codex复盘和正式播报每个阶段都在首次、第二次失败后分别于 5 分钟、15 分钟后重试。每次失败先写入 `daily_job_run`，再发送红色状态卡并告知预计重试时间；容器重启后会从保存的失败阶段继续，不重复已完成的抓取或复盘。第三次失败才结束当天该阶段，并在状态卡中提示下一个工作日的自动任务时间。失败状态卡优先使用 `FEISHU_ALERT_WEBHOOK_URL`，未配置时才复用正式播报机器人。正式播报、状态卡和飞书限流重试都避开整分，优先使用奇数分钟。

自定义调度：

```python
from chain.stock.scheduler import create_scheduler

scheduler = create_scheduler()
scheduler.schedule_daily_job(hour=16, minute=3)
scheduler.start()
```

## 📊 数据分析示例

### 查看今日涨停概况

```sql
-- 同花顺连板统计
SELECT continuous_days, COUNT(*) as count
FROM continuous_limit_up
WHERE date = CURDATE()
GROUP BY continuous_days
ORDER BY continuous_days DESC;

-- 东方财富涨停池
SELECT block_name, COUNT(*) as count, AVG(change_percent) as avg_change
FROM eastmoney_zt_pool
WHERE date = CURDATE()
GROUP BY block_name
ORDER BY count DESC
LIMIT 10;
```

### Codex每日复盘查询

```sql
SELECT date, provider, model, content
FROM daily_market_review
WHERE date = CURDATE();
```

## 🔧 高级配置

### 环境变量

| 变量                 | 必需 | 说明                         |
| -------------------- | ---- | ---------------------------- |
| `DATABASE_URL`     | ✅   | MySQL连接URL                 |
| `STOCK_COOKIE`     | ✅   | 同花顺Cookie                 |
| `STOCK_FETCH_START_JITTER_MIN/MAX` | ❌   | 定时抓取启动前随机等待范围，默认 5-45 秒 |
| `STOCK_FETCH_SOURCE_DELAY_MIN/MAX` | ❌   | 数据源之间随机等待范围，默认 3-8 秒 |
| `STOCK_FETCH_PAGE_DELAY_MIN/MAX` | ❌   | 分页请求之间随机等待范围，默认 0.8-2 秒 |
| `AI_PROVIDER` | ✅ | 每日市场复盘主服务商，使用订阅时设为 `codex` |
| `AI_FALLBACK_PROVIDER` | ❌ | 设为 `moonshot` 时，Codex失败后用相同prompt调用Kimi；`none`关闭降级 |
| `MOONSHOT_MODEL` | ❌ | Kimi 回退模型，默认 `kimi-k2.5` |
| `MOONSHOT_CONTEXT_WINDOW` | ❌ | Kimi 输入和输出共享的上下文窗口，默认 `262144`；调用前会预留输出并检查预算 |
| `CODEX_MODEL` | ❌ | Codex 模型，留空使用账号默认模型 |
| `CODEX_WORKING_DIRECTORY` | ❌ | 旧版单股分析配置；每日复盘固定使用 Agent 根目录 |
| `LOG_LEVEL`        | ❌   | 日志级别(DEBUG/INFO/WARNING) |
| `TZ`               | ❌   | 时区(默认Asia/Shanghai)      |

### 数据抓取配置

```python
# fetcher配置
fetcher = create_fetcher(
    cookie="your_cookie",  # 自定义cookie
    timeout=30,            # 超时时间
    max_retries=3,         # 最大重试次数
    source_delay_range=(3, 8),
    page_delay_range=(0.8, 2.0),
)
```

### Codex复盘配置

```bash
AI_PROVIDER=codex
AI_FALLBACK_PROVIDER=moonshot
MOONSHOT_API_KEY=your_moonshot_api_key
MOONSHOT_MODEL=kimi-k2.5
MOONSHOT_CONTEXT_WINDOW=262144
CODEX_MODEL=
```

## 🛠️ 故障排查

### 常见问题

**Q: 数据抓取返回403错误**

- 检查Cookie是否过期，重新获取
- 检查IP是否被封，使用代理
- 降低请求频率

**Q: AI分析无法使用**

- 检查MOONSHOT_API_KEY是否正确
- 检查网络是否能访问api.moonshot.cn
- 查看日志中的详细错误信息

**Q: MySQL连接失败**

- 检查DATABASE_URL格式
- 确认MySQL服务已启动
- 检查用户权限

### 日志查看

```bash
# Docker日志
docker-compose logs -f stock_agent

# 本地日志
tail -f stock_agent.log
```

## 📈 性能指标

- **数据抓取**：异步并发，单次抓取<10秒
- **Codex复盘**：每个交易日一次模型调用
- **数据库**：支持百万级数据量查询

## 📝 更新日志

### v1.1.0 (2026-04-12)

- ✅ 新增东方财富涨停池数据源
- ✅ AI智能分析功能（Moonshot/Kimi）
- ✅ 混合评估模型（规则+AI）
- ✅ 增强版风险评估Agent

### 当前流程

- ✅ Codex读取连板龙头交易体系
- ✅ 每日事实材料一次性复盘
- ✅ 复盘按日期落库并追加到飞书
- ✅ 旧评分表仅保留历史兼容

### v1.0.0 (2026-04-10)

- ✅ 基础数据抓取（同花顺）
- ✅ 规则引擎风险评估
- ✅ MySQL数据存储
- ✅ Docker容器化部署
- ✅ 定时任务调度

## ⚠️ 免责声明

1. **数据准确性**：数据来源于第三方平台，仅供参考
2. **投资风险**：Codex复盘不构成投资建议
3. **合规使用**：请遵守相关法律法规，合法使用数据
4. **Cookie安全**：请勿泄露个人Cookie信息

## 🤝 贡献指南

欢迎提交Issue和PR：

1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**温馨提示**：股市有风险，投资需谨慎。本系统仅供参考，不构成任何投资建议。
