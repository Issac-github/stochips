# Frontend State Management

## Default Pattern

Use local React state for screen-level behavior. The current app does not use Redux, Zustand, React Query, or another global state library.

Reference: `front/src/renderer/src/pages/LimitUpData.tsx` keeps local state for:

- loading flags for HR, EM, and broken-board data
- active stock task ID/status/result/error
- HR/EM/broken-board dataset arrays
- selected date range

Do not add a global state library for a single page or a single request flow.

## IPC And Main Process State

Main-process state stays in the main process:

- `front/src/main/lib/ipc.ts` stores MCP/GPT ports in `portMap`
- `front/src/main/stockRpc/client.ts` caches the gRPC client by target

Renderer code accesses this state only through `window.api`. Do not mirror long-lived connection objects in React state.

## Stock Task State

Stock tasks are asynchronous:

1. renderer submits `SubmitFetch`, `SubmitAssess`, `SubmitAssessAi`, or `RunAgent`
2. Electron main calls Go gRPC
3. Go creates a task and runs Python in the background
4. renderer polls `GetTask`

Follow `LimitUpData.tsx` when adding task actions:

- set `activeTask` to pending before submit
- disable stock action buttons while a task is pending/running
- accept both `taskId` and `task_id` because gRPC/protobuf conversion may expose either shape
- poll every 1500 ms while pending/running
- refresh current data after success
- show task failures through toast and inline task status

## Dataset State

For stock data queries, keep each dataset independent:

- separate loading flags let HR, EM, and broken-board tabs render accurate loading states
- request range payload uses `startDate` and `endDate`
- the main-process gRPC client maps camelCase to proto snake_case

When adding a new dataset tab, add a distinct query method, loading flag, state array, table component, and parser branch. Do not overload HR/EM arrays with mixed record shapes.
