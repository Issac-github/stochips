# 📈 股票智能选股与风控系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于Python的A股涨停股票智能分析系统，支持多源数据抓取、AI智能分析和风险评估。

## ✨ 核心特性

### 🔄 数据抓取
- **同花顺数据源**：连板天梯、最强风口、涨停强度
- **东方财富数据源**：涨停池（两步智能拉取）
- **完全保留请求头**：100%还原浏览器请求参数
- **异步高性能**：aiohttp异步并发抓取

### 🤖 AI智能分析
- **Moonshot/Kimi LLM**：深度分析涨停原因
- **多维度评估**：概念热度、市场情绪、基本面、技术面
- **混合评估模型**：规则引擎(60%) + AI分析(40%)
- **自动生成报告**：专业的投资分析报告

### 🛡️ 风险控制
- **规则引擎**：4维度风险评估（连板、封单、换手、开板）
- **AI增强分析**：LLM辅助判断市场情绪
- **历史模式匹配**：相似走势案例参考
- **智能建议生成**：观望/谨慎/规避/机会

### 🐳 容器化部署
- **Docker Compose**：一键启动MySQL + Agent服务
- **自动定时任务**：每日16:00自动抓取，16:30自动分析
- **数据持久化**：MySQL存储，支持历史回溯
- **日志监控**：完整日志记录和状态监控

## 🚀 快速开始

### 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd agent

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
DATABASE_URL=mysql+pymysql://stock:your_password@mysql:3306/stock_analysis

# 同花顺Cookie（数据抓取必需）
STOCK_COOKIE=your_ths_cookie
```

**可选配置**（AI分析功能）：
```bash
# Moonshot API Key（AI分析必需）
MOONSHOT_API_KEY=your_api_key
```

**获取Cookie方法**：
1. 访问 https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html
2. F12打开开发者工具 → Network标签
3. 刷新页面，找到XHR请求
4. 复制请求中的Cookie字段（主要是`v=`后面的值）

### Docker部署（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f stock_agent

# 进入MySQL查看数据
docker-compose exec mysql mysql -ustock -p stock_analysis
```

### 本地开发

```bash
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

以下命令默认在 `agent/` 目录下执行。推荐使用 `poetry run python -m ...`，这样会固定使用 Poetry 管理的虚拟环境，并按模块路径运行入口。

```bash
# 数据抓取
poetry run python -m main fetch [YYYYMMDD]           # 抓取所有数据源
poetry run python -m main fetch-ths [YYYYMMDD]       # 仅同花顺数据
poetry run python -m main fetch-em [YYYYMMDD]        # 仅东方财富数据

# 风险评估
poetry run python -m main assess [YYYYMMDD]          # 规则引擎评估
poetry run python -m main ai-analyze [YYYYMMDD]      # AI智能分析
poetry run python -m main assess-ai [YYYYMMDD]       # 混合评估（推荐）

# 完整流程
poetry run python -m main run [YYYYMMDD]             # 抓取+评估

# 定时任务
poetry run python -m main schedule                   # 启动定时调度器

# 状态查询
poetry run python -m main status [YYYYMMDD]          # 查看数据状态
poetry run python -m main report [YYYYMMDD]          # 生成分析报告

# Wiki 知识库
poetry run python -m main wiki query "什么是龙头"
poetry run python -m main wiki build

# RAG 检索
poetry run python -m chain.rag.main search "天量"
poetry run python -m chain.rag.main chat "天量代表什么"
```

### Python API

```python
from chain.stock.data import create_fetcher, create_storage
from chain.stock.agents import create_enhanced_risk_agent
from datetime import date

# 数据抓取
fetcher = create_fetcher()
data = fetcher.fetch_all_data('20260412')

# 数据存储
storage = create_storage('mysql+pymysql://user:pass@localhost/stock_analysis')
results = storage.save_all_data(data, date(2026, 4, 12))

# 风险评估
agent = create_enhanced_risk_agent()
result = agent.run_daily_assessment_enhanced(date(2026, 4, 12), use_ai=True)
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
│   │   ├── ai_analyzer.py          # AI分析器
│   │   ├── risk_agent.py           # 规则引擎
│   │   └── enhanced_risk_agent.py  # 混合评估
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

| 表名 | 说明 | 核心字段 |
|------|------|----------|
| `continuous_limit_up` | 连板天梯 | 连板天数、涨停时间、涨停原因 |
| `block_top` | 最强风口 | 板块热度、龙头股、涨停家数 |
| `limit_up_pool` | 涨停强度 | 封单强度、换手率、量比 |

### 东方财富数据源

| 表名 | 说明 | 核心字段 |
|------|------|----------|
| `eastmoney_zt_pool` | 涨停池 | 封单金额、涨停类型、3日涨幅 |

### 分析结果

| 表名 | 说明 | 核心字段 |
|------|------|----------|
| `risk_assessment` | 风险评估 | 风险分数、等级、建议 |
| `data_fetch_log` | 操作日志 | 抓取状态、记录数、错误信息 |

## 🧠 AI分析模型

### 评估维度

1. **涨停原因分析**
   - 利好消息真实性和持续性
   - 政策/业绩/概念驱动判断

2. **概念热度评估**
   - 板块涨停家数统计
   - 龙头股表现分析
   - 市场关注度判断

3. **市场情绪分析**
   - 大盘情绪判断
   - 板块情绪氛围
   - 个股资金博弈

4. **基本面评估**
   - PE/PB估值分析
   - 市值和流通性
   - 业绩预期

5. **技术面分析**
   - 封单强度解读
   - 换手率和量比
   - 连板节奏判断

### 评分算法

```
综合风险分 = 规则引擎(60%) + AI分析(40%)

AI权重调整：
- 高置信度(>0.8): AI权重40%
- 中置信度(0.5-0.8): AI权重30%
- 低置信度(<0.5): AI权重20%
```

### 风险等级

| 等级 | 分数 | 建议 | 策略 |
|------|------|------|------|
| 极高 | ≥80 | 规避 | 坚决不参与 |
| 高 | 60-79 | 谨慎 | 逢高减仓 |
| 中 | 40-59 | 观望 | 等待时机 |
| 低 | <40 | 机会 | 适量参与 |

## ⏰ 定时任务

默认调度策略：

```
16:00 - 抓取同花顺数据
16:05 - 抓取东方财富数据
16:30 - 运行规则引擎评估
16:35 - 运行AI分析（如配置API Key）
17:00 - 生成分析报告
```

自定义调度：

```python
from chain.stock.scheduler import create_scheduler

scheduler = create_scheduler()
scheduler.schedule_data_fetch(hour=16, minute=0)
scheduler.schedule_risk_assessment(hour=16, minute=30)
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

### 风险评估查询

```sql
-- 高风险股票列表
SELECT code, name, risk_score, risk_level, suggestion
FROM risk_assessment
WHERE date = CURDATE() AND risk_level = '高'
ORDER BY risk_score DESC;
```

## 🔧 高级配置

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `DATABASE_URL` | ✅ | MySQL连接URL |
| `STOCK_COOKIE` | ✅ | 同花顺Cookie |
| `MOONSHOT_API_KEY` | ❌ | Moonshot API Key |
| `LOG_LEVEL` | ❌ | 日志级别(DEBUG/INFO/WARNING) |
| `TZ` | ❌ | 时区(默认Asia/Shanghai) |

### 数据抓取配置

```python
# fetcher配置
fetcher = create_fetcher(
    cookie="your_cookie",  # 自定义cookie
    timeout=30,            # 超时时间
    max_retry=3           # 最大重试次数
)
```

### AI分析配置

```python
# AI分析器配置
analyzer = create_ai_analyzer(
    model="moonshot-v1-8k",  # 模型选择
    temperature=0.3,          # 温度参数
    max_tokens=2000          # 最大token数
)
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
- **AI分析**：单只股票分析~2-3秒（含API调用）
- **批量评估**：50只股票约5-8分钟（含AI）
- **数据库**：支持百万级数据量查询

## 📝 更新日志

### v1.1.0 (2026-04-12)
- ✅ 新增东方财富涨停池数据源
- ✅ AI智能分析功能（Moonshot/Kimi）
- ✅ 混合评估模型（规则+AI）
- ✅ 增强版风险评估Agent

### v1.0.0 (2026-04-10)
- ✅ 基础数据抓取（同花顺）
- ✅ 规则引擎风险评估
- ✅ MySQL数据存储
- ✅ Docker容器化部署
- ✅ 定时任务调度

## ⚠️ 免责声明

1. **数据准确性**：数据来源于第三方平台，仅供参考
2. **投资风险**：AI分析和风险评估不构成投资建议
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
