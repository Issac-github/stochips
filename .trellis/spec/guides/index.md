# Project Thinking Guides

Use these guides when a change crosses package or runtime boundaries in StoChips.

| Guide | Use For |
| --- | --- |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Changes that touch Python agent, Go RPC, Electron main/preload, renderer types, or database schema |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Finding existing factories, adapters, validators, UI primitives, query helpers, and task abstractions before adding new code |

High-risk boundaries in this project:

- stock data schema: Python models, migrations, Go query JSON, frontend global types, table components
- RPC contract: Go proto/server, Go runner, Electron gRPC client, shared event keys, preload bridge
- task lifecycle: Go task store, Python command execution, renderer polling
- AI flow: Codex strategy-file access, date-keyed review cache, shared Feishu material, and user-visible report metadata
- frontend data display: Go JSON adapters, zod validators, `DataTable`, HR/EM/BrokenBoard tables

Before changing a value or shape that appears in more than one layer, search the repository first with `rg`.
