# Frontend Component Guidelines

## Design System

Follow `front/DESIGN_SYSTEM.md` and `front/src/renderer/src/assets/style/global.css`.

Current visual language:

- minimalist modern, data-focused, professional
- Electric Blue accent through CSS variables and `.accent-gradient`
- display headings through `.font-display`
- technical labels through `.font-mono`
- reusable surface helpers such as `.surface-card`, `.surface-panel`, `.surface-chip`, and `.focus-ring`

Use existing tokens before adding new colors or shadows. Do not reintroduce Ant Design, the old gold theme, or one-off design systems.

## UI Primitives

Use `front/src/renderer/src/components/ui/*` for base UI elements. Pages should compose:

- `Button` for actions
- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` for tabbed datasets
- `Card`, `Badge`, `Table`, `Input`, `Toast`, and related primitives
- `lucide-react` icons for action buttons, as seen in `LimitUpData.tsx`

When a primitive needs a behavior or visual fix, improve the primitive first instead of patching each page.

## Shared Components

`components/shared/` holds app-level reusable components:

- `DataTable` owns loading, empty, sticky header, row striping, and scroll container behavior for tabular views.
- `DateRangePicker` owns the two-date input shape used by stock queries.
- `Toast` is the renderer notification surface.
- `ChatComposer`, `ChatMessages`, `Markdown`, and `Terminal` support MCP/chat workflows.

Keep generic behavior in shared components and domain calculations in domain components. For example, `DataTable` should not know EM/HR stock field names; `EmTable` and `HrTable` own those columns and statistics.

## Data-Heavy Components

Stock data screens are dense dashboards. Follow `front/src/renderer/src/pages/LimitUpData.tsx` and the `components/limitUp/*` tables:

- keep filters and stock task actions at the top of the page
- show task status separately from table data
- fetch HR, EM, and broken-board data together for a date range
- use `StatTile` for compact aggregate metrics
- keep table columns explicit and typed through `DataColumn<T>`
- display backend errors through toasts and compact inline status, not modal blocks

Avoid hiding the main data table behind marketing or instructional content.

## Component State

Prefer function components with local `useState`/`useEffect` state where the state belongs to a single screen. `LimitUpData.tsx` is the current reference for:

- separate loading flags per dataset
- an `activeTask` object for submitted stock tasks
- date range state using `dayjs`
- polling through `window.setTimeout`

When a state pattern repeats across screens, extract a renderer hook under `lib/hooks/`.

## Text And Language

The app currently mixes English product labels with Chinese operational labels. Preserve existing domain language where users already see it, such as stock task button labels and toast titles. Keep compact UI labels short because many controls live in dense dashboard headers.
