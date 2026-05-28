# Frontend Specs

The frontend is an Electron + React + TypeScript app in `front/`. It has three runtime layers:

- Electron main process under `front/src/main/`
- preload bridge under `front/src/preload/`
- React renderer under `front/src/renderer/src/`

Read these guides before frontend changes:

| Guide | Use For |
| --- | --- |
| [Directory Structure](./directory-structure.md) | Electron layer boundaries, aliases, route and component locations |
| [Component Guidelines](./component-guidelines.md) | UI composition, shared components, design system, table/dashboard patterns |
| [Hook Guidelines](./hook-guidelines.md) | Renderer hooks, streaming chat, IPC-backed data access |
| [State Management](./state-management.md) | Local state, task polling, RPC data loading, global bridge state |
| [Type Safety](./type-safety.md) | Global types, zod validators, proto/RPC shape changes |
| [Quality Guidelines](./quality-guidelines.md) | Lint, typecheck, formatting, generated assets, and runtime boundaries |

Primary references:

- `front/README.md`
- `front/DESIGN_SYSTEM.md`
- `front/package.json`
- `front/electron.vite.config.ts`
- `front/src/main/lib/ipc.ts`
- `front/src/main/stockRpc/client.ts`
- `front/src/preload/index.ts`
- `front/src/renderer/src/pages/LimitUpData.tsx`
