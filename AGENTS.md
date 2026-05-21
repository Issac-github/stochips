# Stochips — Agent Instructions

A-share (Chinese stock market) intelligent analysis system. Two independent parts:

- **`agent/`** — Python backend: data scraping, AI risk agents, wiki knowledge base
- **`front/`** — Electron + React + TypeScript desktop UI

---

## Architecture

```
agent/
  main.py                  # CLI entry point — all backend commands go through here
  chain/stock/             # Core stock pipeline (fetch → assess → AI analyze)
  chain/rag/               # ChromaDB RAG over local .md documents
  chain/wiki/              # LLM-curated structured wiki (raw/ → wiki/ → ChromaDB)
  graph/                   # LangGraph workflow examples (standalone, not in main.py)
  migrations/              # MySQL schema migration SQL files

front/
  src/main/                # Electron main process (IPC, LLM servers, DB worker)
  src/renderer/src/        # React UI
  src/preload/             # Electron preload bridge
  src/shared/              # Shared types (eventKey.ts, logger.ts)
  storage/                 # Local SQLite DB (storage/sqlite.db)
```

See [agent/README.md](agent/README.md) for backend details and Docker setup.

---

## Backend Commands

Run from `agent/` directory:

```bash
# Data pipeline
python main.py fetch [YYYYMMDD]       # scrape THS + EastMoney → MySQL
python main.py assess [date]           # rule-engine risk scoring
python main.py ai-analyze [date]       # Moonshot AI analysis
python main.py assess-ai [date]        # combined rule + AI (rule 60% + AI 40%)
python main.py run [date]              # fetch → assess pipeline

# Goal-driven agent (LLM plans tool calls)
python main.py agent "分析今日涨停"

# Scheduler daemon (daily 16:00 fetch, 16:30 assess)
python main.py schedule

# Wiki / knowledge base
python main.py wiki ingest raw/001-xxx.md   # ingest raw doc via LLM
python main.py wiki query "什么是龙头"       # vector search + LLM answer
python main.py wiki build                    # rebuild ChromaDB from wiki/
python main.py wiki lint                     # check broken [[wikilinks]]

# Status
python main.py status [date]
```

### Install (Poetry)

```bash
cd agent
poetry install                  # core deps
poetry install --extras rag     # adds HuggingFace + ChromaDB (heavy, ~1.5 GB model)
```

### Docker

```bash
cd agent
docker compose up -d --build        # MySQL + stock_agent
docker compose up rag_agent         # optional RAG service (CPU-only torch)
```

---

## Frontend Commands

```bash
cd front
npm install
npm run dev           # Electron dev with HMR
npm run build:mac     # production build for macOS
```

---

## Required Environment Variables

File: `agent/.env` (copy from `agent/.env.example`)

| Variable           | Required | Purpose                                                                |
| ------------------ | -------- | ---------------------------------------------------------------------- |
| `DATABASE_URL`     | ✓        | `mysql+pymysql://stock:pass@mysql:3306/stock_analysis?charset=utf8mb4` |
| `STOCK_COOKIE`     | ✓        | 同花顺 (THS) session cookie (`v=...`); get from browser DevTools       |
| `MOONSHOT_API_KEY` | optional | Enables all AI analysis features (model: `moonshot-v1-8k`)             |
| `LOG_LEVEL`        | optional | Default: `INFO`                                                        |

Config is centralized in [`agent/chain/stock/config.py`](agent/chain/stock/config.py) as a singleton `config` object.

---

## Key Conventions

### Python Backend

- **Async-first**: All network operations use `aiohttp`. Use `@async_retry()` from `chain/stock/utils/decorators.py` for retries with exponential backoff.
- **Config access**: Always use `from chain.stock.config import config` — never read env vars directly.
- **Database**: MySQL via SQLAlchemy for stock data; SQLite (`storage/sqlite.db`) for the frontend (Electron).
- **Stock data tables**: `hr_limit_up`, `em_limit_up`, `article` in MySQL — always query these instead of re-fetching.
- **AI model**: Moonshot is accessed via the OpenAI-compatible API at `https://api.moonshot.cn/v1`. Use `langchain-openai` with a custom `base_url`.
- **Embeddings**: `BAAI/bge-small-zh-v1.5` via `HuggingFaceEmbeddings`. Cached in Docker volume. Only loaded when RAG extras are installed.

### LangGraph (graph/)

- `StateGraph` with `TypedDict` state. Prefer `add_messages` reducer for message lists.
- Tools defined with `@tool` decorator, bound to LLM via `llm.bind_tools(tools)`.
- `graph/` examples are standalone — to integrate into main pipeline, wire through `main.py`.

### Frontend

- **IPC communication**: Use `EventKey` enum from `src/shared/eventKey.ts` for all IPC channel names.
- **Database access**: Renderer never accesses SQLite directly. Always use `window.api.database.request()` → main process DB worker.
- **LLM ports**: Three dynamically-assigned ports (starting at 3336) for WebSocket MCP, HTTP MCP, and GPT proxy. Retrieved via `EventKey.McpPort`.
- **UI**: Local shadcn-style primitives with the Minimalist Modern design system in [`front/DESIGN_SYSTEM.md`](front/DESIGN_SYSTEM.md). Tokens and utilities live in `front/src/renderer/src/assets/style/global.css`. Do not reintroduce Ant Design or the old gold theme.
- **Protobuf**: `src/main/protobuf/data.proto` — regenerate with `build_js.sh` if schema changes.

### Wiki Structure

```
chain/wiki/raw/       ← immutable source documents (drop .md files here)
chain/wiki/wiki/      ← LLM-curated pages (do not edit manually)
chain/wiki/WIKI.md    ← schema contract for wiki pages
chain/wiki/chroma_wiki_db/  ← auto-generated, do not commit
```

Wiki pages use `[[PageName]]` wikilink syntax. Run `python main.py wiki lint` to find broken links.

---

## Common Pitfalls

- **RAG imports on non-RAG install**: `chain/rag/` and `chain/wiki/` import HuggingFace/ChromaDB — these fail with `ImportError` if `poetry install --extras rag` wasn't run. The `stock_agent` Docker service intentionally excludes these.
- **THS Cookie expiry**: `STOCK_COOKIE` expires frequently. If fetch returns empty data, refresh the cookie from browser DevTools on `data.10jqka.com.cn`.
- **`graph/` not wired to `main.py`**: The LangGraph examples in `graph/` are demos. They are not invoked by any production command.
- **MySQL charset**: Always include `?charset=utf8mb4` in `DATABASE_URL` for Chinese character support.
- **Migrations**: Schema changes need a SQL file in `migrations/` and manual application — there is no auto-migration runner.
