# Frontend Quality Guidelines

## Verification Commands

Use `front/package.json` scripts:

- install: `cd front && npm install`
- development: `cd front && npm run dev`
- lint: `cd front && npm run lint`
- typecheck: `cd front && npm run typecheck`
- build: `cd front && npm run build`

Platform builds are available through `build:win`, `build:mac`, and `build:linux`.

## Formatting And Imports

Prettier rules in `front/.prettierrc.yaml` are project conventions:

- 2 spaces
- single quotes
- no semicolons
- print width 80
- sorted imports through `@trivago/prettier-plugin-sort-imports`
- Tailwind class sorting through `prettier-plugin-tailwindcss`

Do not hand-format against these rules. Run the formatter for broad frontend changes.

## Lint Rules

ESLint is configured in `front/eslint.config.mjs` with Electron Toolkit TypeScript rules, React, hooks, React Refresh, and Prettier compatibility.

Important local rules:

- `no-console` is a warning
- `no-debugger` is a warning
- unused variables are errors unless prefixed with `_`
- React Hooks rules are enabled

Use `@shared/logger` instead of direct `console` in source code. `debugLog` only logs outside production and `errorLog` always reports errors.

## Electron Safety

Keep renderer code browser-like. Node, Electron, gRPC, filesystem, and process-level work belongs in main/preload.

Reference boundaries:

- `front/src/main/index.ts` creates windows and handles external links.
- `front/src/main/lib/ipc.ts` registers IPC handlers.
- `front/src/main/stockRpc/client.ts` owns `@grpc/grpc-js` and `protobufjs`.
- `front/src/preload/index.ts` exposes a small bridge.
- React pages call `window.api`, not `ipcRenderer` or gRPC directly.

## Assets And Dependencies

Do not edit or review generated/runtime dependency directories as source:

- `front/node_modules/`
- `front/out/`
- `front/dist/`
- `front/.eslintcache`
- generated icon font files under `assets/iconfont/` unless the source SVG generation flow is part of the change

When adding UI dependencies, prefer existing Radix primitives, local UI components, Tailwind utilities, `lucide-react`, `dayjs`, and existing MCP/gRPC packages before adding another library.

## Frontend Tests

The current frontend has lint and typecheck but no dedicated test runner configured. For risky UI behavior, at minimum run `npm run typecheck` and `npm run lint`; for Electron IPC or gRPC bridge changes, manually exercise the app through `npm run dev` against a running `stock_rpc` when feasible.
