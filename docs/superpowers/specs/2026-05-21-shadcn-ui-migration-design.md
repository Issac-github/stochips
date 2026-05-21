# shadcn/ui Migration Design

## Goal

Replace the `front/` renderer's Ant Design UI stack with shadcn/ui-style React components, remove `antd` and all `@ant-design/*` dependencies, and preserve the existing Electron, router, IPC, database, and LLM behavior.

## Chosen Direction

Use the Operational Redesign direction approved on 2026-05-21. The app remains a dense desktop stock-analysis tool: fixed dark sidebar, compact content area, tight metric strips, explicit tabbed workflows, and high-density data tables.

## Architecture

The migration will add local UI primitives under `front/src/renderer/src/components/ui/` and app-specific shared components under `front/src/renderer/src/components/shared/`. Business pages continue to own data fetching and transformation. The AntD provider will be removed from `App.tsx`; global styling will provide shadcn-compatible CSS variables and Tailwind 4 theme tokens.

## Component Strategy

- Use shadcn/ui primitives for buttons, cards, tabs, badges, dialogs, sheets, popovers, calendar, scroll areas, separators, textareas, tables, and toast notifications.
- Use `lucide-react` for icons.
- Replace `@ant-design/x` chat widgets with local `ChatMessages` and `ChatComposer` components.
- Replace `@ant-design/x-markdown` with the existing `marked` package and a small local Markdown renderer.
- Replace AntD `DatePicker.RangePicker` with a popover calendar range picker built from `react-day-picker`.
- Replace AntD table/statistic/tag usage with compact local compositions on top of shadcn `Table`, `Card`, and `Badge`.

## Data Flow

No backend, IPC, SQLite, or LLM protocol changes are in scope. `LimitUpData` and `LimitUpDataEditor` keep their current database requests. MCP chat components keep the current hook APIs and only replace rendering/input components.

## Testing And Verification

The primary verification is `npm run typecheck` and `npm run build` from `front/`. The final dependency check is `rg "antd|@ant-design" front/src front/package.json`, which must return no matches.

## Non-Goals

This migration does not change stock data schemas, backend commands, database migrations, MCP server behavior, route names, or the set of user-facing pages.
