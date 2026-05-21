# shadcn/ui Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `front/` Ant Design UI stack with local shadcn/ui-style components and remove all AntD dependencies.

**Architecture:** Add local primitives under `front/src/renderer/src/components/ui/`, app-specific shared widgets under `front/src/renderer/src/components/shared/`, then migrate layout, stock data pages, editor wrappers, and MCP chat views. Keep Electron, IPC, router, data fetching, and LLM hooks unchanged.

**Tech Stack:** Electron Vite, React 19, TypeScript, Tailwind CSS 4, shadcn/ui patterns, Radix primitives, lucide-react, marked, dayjs.

---

## File Structure

- Create `front/src/renderer/src/lib/utils/cn.ts` for class name merging.
- Create `front/src/renderer/src/components/ui/*` for reusable shadcn-style primitives.
- Create `front/src/renderer/src/components/shared/Markdown.tsx`, `ChatComposer.tsx`, `ChatMessages.tsx`, `DateRangePicker.tsx`, `Toast.tsx`, and compact table/stat components.
- Modify `front/src/renderer/src/App.tsx` to remove AntD providers and mount toast state.
- Modify `front/src/renderer/src/assets/style/global.css` for shadcn tokens and remove the AntD layer.
- Modify `front/src/renderer/src/components/layout/MainLayout.tsx` for the operational sidebar shell.
- Modify `front/src/renderer/src/pages/Mcp.tsx`, `LimitUpData.tsx`, and `LimitUpDataEditor.tsx`.
- Modify `front/src/renderer/src/components/mcp/*` to remove AntD X.
- Modify `front/src/renderer/src/components/limitUp/*` to remove AntD cards/statistics/tags/tables.
- Modify or remove AntD wrapper files in `front/src/renderer/src/components/shared/`.
- Modify `front/package.json` and `front/package-lock.json` to remove AntD packages and add required shadcn peer packages.

### Task 1: Dependencies And Theme Foundation

**Files:**
- Modify: `front/package.json`
- Modify: `front/package-lock.json`
- Modify: `front/src/renderer/src/assets/style/global.css`
- Modify: `front/src/renderer/src/App.tsx`
- Create: `front/src/renderer/src/lib/utils/cn.ts`

- [ ] Install runtime packages: `class-variance-authority clsx tailwind-merge lucide-react @radix-ui/react-dialog @radix-ui/react-popover @radix-ui/react-scroll-area @radix-ui/react-separator @radix-ui/react-slot @radix-ui/react-tabs @radix-ui/react-toast @radix-ui/react-tooltip react-day-picker`.
- [ ] Remove runtime packages: `antd @ant-design/charts @ant-design/icons @ant-design/x @ant-design/x-markdown`.
- [ ] Add shadcn-compatible CSS variables to `global.css`, remove the `antd` Tailwind layer, and keep the app background restrained.
- [ ] Replace `App.tsx` with plain `RouterProvider` plus local toast viewport.
- [ ] Run `npm run typecheck` and expect failures only from remaining AntD imports.

### Task 2: UI Primitive Layer

**Files:**
- Create: `front/src/renderer/src/components/ui/button.tsx`
- Create: `front/src/renderer/src/components/ui/card.tsx`
- Create: `front/src/renderer/src/components/ui/tabs.tsx`
- Create: `front/src/renderer/src/components/ui/table.tsx`
- Create: `front/src/renderer/src/components/ui/badge.tsx`
- Create: `front/src/renderer/src/components/ui/input.tsx`
- Create: `front/src/renderer/src/components/ui/textarea.tsx`
- Create: `front/src/renderer/src/components/ui/dialog.tsx`
- Create: `front/src/renderer/src/components/ui/sheet.tsx`
- Create: `front/src/renderer/src/components/ui/popover.tsx`
- Create: `front/src/renderer/src/components/ui/calendar.tsx`
- Create: `front/src/renderer/src/components/ui/scroll-area.tsx`
- Create: `front/src/renderer/src/components/ui/separator.tsx`
- Create: `front/src/renderer/src/components/ui/toast.tsx`

- [ ] Add the primitives with `forwardRef`, variants where needed, and `cn()` composition.
- [ ] Keep all primitives ASCII-only and colocated under `components/ui`.
- [ ] Run `npm run typecheck` and expect remaining failures only from app files still importing AntD.

### Task 3: Shared App Widgets

**Files:**
- Create: `front/src/renderer/src/components/shared/Toast.tsx`
- Create: `front/src/renderer/src/components/shared/Markdown.tsx`
- Create: `front/src/renderer/src/components/shared/ChatComposer.tsx`
- Create: `front/src/renderer/src/components/shared/ChatMessages.tsx`
- Create: `front/src/renderer/src/components/shared/DateRangePicker.tsx`
- Modify: `front/src/renderer/src/components/shared/Drawer.tsx`
- Modify: `front/src/renderer/src/components/shared/Modal.tsx`
- Modify: `front/src/renderer/src/components/shared/InfiniteScroll.tsx`
- Modify: `front/src/renderer/src/components/shared/JSONEditor.tsx`

- [ ] Implement a tiny local toast store with success/error/warning/info helpers.
- [ ] Implement markdown rendering with `marked.parse`.
- [ ] Implement chat message bubbles and composer with Enter-to-send and Shift+Enter newline.
- [ ] Implement `DateRangePicker` returning Dayjs-compatible values to existing page code.
- [ ] Replace Drawer/Modal wrappers with Sheet/Dialog wrappers.
- [ ] Replace loading and JSON editor controls with local components.
- [ ] Run `npm run typecheck` and expect remaining failures only from layout/pages/limit-up/MCP files.

### Task 4: Layout And Navigation

**Files:**
- Modify: `front/src/renderer/src/components/layout/MainLayout.tsx`
- Modify: `front/src/renderer/src/components/layout/RootBoundary.tsx`
- Modify: `front/src/renderer/src/assets/style/color.ts`

- [ ] Replace AntD Layout/Menu/Flex/Button/theme with semantic div layout, lucide icons, and local Button.
- [ ] Keep collapsed navigation behavior and existing route keys.
- [ ] Replace color token exports with local constants or remove the file if no longer needed.
- [ ] Run `npm run typecheck` and expect remaining failures only from migrated pages/components not yet complete.

### Task 5: MCP Views

**Files:**
- Modify: `front/src/renderer/src/pages/Mcp.tsx`
- Modify: `front/src/renderer/src/components/mcp/McpChat.tsx`
- Modify: `front/src/renderer/src/components/mcp/McpFilter.tsx`
- Modify: `front/src/renderer/src/components/mcp/StreamChat.tsx`
- Modify: `front/src/renderer/src/components/mcp/McpMessage.tsx`

- [ ] Replace Tabs with local shadcn tabs.
- [ ] Replace cards, buttons, connection status text, chat bubbles, markdown, and sender controls.
- [ ] Preserve `useSocketMcpClient`, `useHttpMcpClient`, and `useGPTChat` behavior.
- [ ] Run `npm run typecheck` and expect remaining failures only from stock data pages/components.

### Task 6: Stock Data Views

**Files:**
- Modify: `front/src/renderer/src/pages/LimitUpData.tsx`
- Modify: `front/src/renderer/src/pages/LimitUpDataEditor.tsx`
- Modify: `front/src/renderer/src/components/limitUp/HrTable.tsx`
- Modify: `front/src/renderer/src/components/limitUp/EmTable.tsx`
- Modify: `front/src/renderer/src/components/limitUp/BrokenBoardAnalysis.tsx`

- [ ] Replace date range picker, tabs, message API, cards, statistics, tags, and tables.
- [ ] Keep all existing data calculations and row render logic.
- [ ] Use compact metric tiles and horizontally scrollable tables.
- [ ] Run `npm run typecheck` and expect no TypeScript errors from migrated UI.

### Task 7: Remove Leftover AntD Surface

**Files:**
- Modify or delete: `front/src/renderer/src/components/Introduction.tsx`
- Modify or delete: `front/src/renderer/src/components/shared/Table.tsx`
- Modify: any file returned by `rg "antd|@ant-design" front/src front/package.json`

- [ ] Remove or rewrite demo components that still import AntD.
- [ ] Run `rg "antd|@ant-design" front/src front/package.json`.
- [ ] Confirm the search returns no matches.

### Task 8: Final Verification

**Files:**
- Read: `front/package.json`
- Read: `front/package-lock.json`

- [ ] Run `npm run typecheck`.
- [ ] Run `npm run build`.
- [ ] Run `rg "antd|@ant-design" front/src front/package.json`.
- [ ] If the build needs native Electron dependencies and fails for environment reasons, record the exact failure and keep `typecheck` plus dependency search clean.

## Self-Review

- The plan covers dependency removal, UI primitives, shared replacements, layout, MCP chat, stock data tables, and final verification.
- The plan avoids backend, database, IPC, and route changes.
- No placeholders remain; each task names exact files and verification commands.
