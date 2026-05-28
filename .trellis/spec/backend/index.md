# Backend Specs

These specs describe the current backend shape of StoChips:

- `agent/` is the Python stock analysis backend. It owns stock fetching, MySQL persistence, rule risk assessment, Moonshot/Kimi AI analysis, wiki/RAG commands, scheduling, and the CLI in `agent/main.py`.
- `services/stock-rpc/` is the Go gRPC gateway. It owns the external RPC API, task status tracking, query JSON adapters, and dispatching existing Python commands. It must not reimplement stock business logic already owned by Python.

Read these guides before changing backend behavior:

| Guide | Use For |
| --- | --- |
| [Directory Structure](./directory-structure.md) | Package ownership, Python vs Go boundaries, generated code locations |
| [Database Guidelines](./database-guidelines.md) | MySQL schema, SQLAlchemy models, migrations, query adapters, task persistence |
| [Error Handling](./error-handling.md) | CLI exits, fetch/storage failures, gRPC status mapping, task errors |
| [Logging Guidelines](./logging-guidelines.md) | Python and Go logging conventions |
| [Quality Guidelines](./quality-guidelines.md) | Tests, command contracts, generated files, config, and forbidden patterns |

Primary references:

- `agent/README.md`
- `agent/main.py`
- `agent/chain/stock/`
- `services/stock-rpc/README.md`
- `services/stock-rpc/proto/stock.proto`
- `services/stock-rpc/internal/`
