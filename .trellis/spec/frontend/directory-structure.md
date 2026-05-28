# Frontend Directory Structure

## Runtime Layers

Keep Electron boundaries explicit:

- `front/src/main/`: Electron main process code. It creates windows, starts local LLM/MCP servers, registers IPC handlers, and owns Node-only integrations such as gRPC clients.
- `front/src/preload/`: safe bridge from main process to renderer. `index.ts` exposes `window.api.mcpPort` and `window.api.stockRpc`.
- `front/src/shared/`: constants, event keys, validation, and logging used by more than one layer.
- `front/src/renderer/src/`: React application, routes, pages, components, hooks, utilities, and styling.

Do not import Electron or Node-only libraries directly into renderer components. Route those calls through preload APIs or main-process services.

## Aliases

Use aliases configured in `front/electron.vite.config.ts` and TypeScript configs:

- main: `@main/*`, `@shared/*`
- preload: `@shared/*`
- renderer: `@renderer/*`, `@shared/*`

Avoid deep relative imports when an alias is available. Keep shared imports free of browser-only or Node-only assumptions unless the shared module is intentionally layer-specific.

## Renderer Layout

Renderer code follows this structure:

- `components/ui/`: local shadcn-style primitives such as `button`, `card`, `tabs`, `table`, `toast`, `dialog`, and inputs.
- `components/shared/`: app-level reusable components such as `DataTable`, `DateRangePicker`, `Toast`, `Markdown`, `Terminal`, and chat surfaces.
- `components/layout/`: shell and route error boundary.
- `components/limitUp/`: stock limit-up domain tables and analysis views.
- `components/mcp/`: MCP/chat UI.
- `pages/`: route-level screens.
- `lib/router/`: `createHashRouter` route tree.
- `lib/hooks/`: renderer hooks for GPT/MCP interactions.
- `lib/utils/`: small renderer utilities, currently including `cn`.
- `assets/style/global.css`: Tailwind 4 import, theme tokens, font utilities, and global surface helpers.

Add reusable primitives before duplicating page-local UI. Add domain-specific table logic under `components/limitUp/`, not in generic shared components.

## Routing

Routes are defined in `front/src/renderer/src/lib/router/index.tsx` with `createHashRouter`:

- `/` -> `Introduction`
- `/limit-up-data` -> `LimitUpData`
- `/mcp-chat` -> `Mcp`

New routes should live under `MainLayout` unless they intentionally replace the app shell. Provide an `errorElement` at the layout level through `RootBoundary`.

## Assets And Generated Files

SVG source icons live under `front/src/renderer/src/assets/icons/`. The `svg2font` script generates icon font assets under `assets/iconfont/`.

Do not edit generated icon font files by hand. Change source SVGs and rerun the asset generation script when needed.
