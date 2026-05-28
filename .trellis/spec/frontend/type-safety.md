# Frontend Type Safety

## Global Contracts

`front/env.d.ts` currently holds app-wide renderer-visible data contracts:

- `PortMapType`
- `EMLimitUpData`
- `HRLimitUpData`
- `BrokenBoardRecord`
- `StockRpcTaskStatus`
- `StockRpcResponse`
- `StockRpcRequestArgs`

`front/global.d.ts` augments `Window` with the preload bridge:

- `window.api.mcpPort`
- `window.api.stockRpc.invoke`

When changing bridge or stock RPC shapes, update both files if the renderer-visible contract changes.

## Stock RPC Contract

The canonical backend contract is `services/stock-rpc/proto/stock.proto`. The Electron main-process client mirrors that proto as an inline string in `front/src/main/stockRpc/client.ts`.

If the proto changes, update these together:

- `services/stock-rpc/proto/stock.proto`
- generated Go code in `services/stock-rpc/gen/stockv1/`
- Go server implementation in `services/stock-rpc/internal/server/service.go`
- Electron gRPC method map and inline proto in `front/src/main/stockRpc/client.ts`
- `StockRpcEventKey` in `front/src/shared/eventKey.ts`
- `StockRpcRequestArgs` and `StockRpcResponse` in `front/env.d.ts`

The client currently maps camelCase renderer payload keys to snake_case proto fields for `startDate`, `endDate`, and `taskId`; preserve this adapter when adding similar fields.

## Runtime Validation

`front/src/shared/lib/validate.ts` defines zod validators for EM and HR data. Use these validators or extend them when JSON from `QueryEmLimitUp` or `QueryHrLimitUp` changes.

Keep validators aligned with:

- `services/stock-rpc/internal/query/repository.go`
- `front/env.d.ts`
- table renderers in `front/src/renderer/src/components/limitUp/`

Do not rely only on TypeScript interfaces for data coming from MySQL via Go JSON strings.

## Component Generics

`DataTable` uses a generic `DataColumn<T>` and a `rowKey` callback. Follow this pattern for typed tables:

- columns should be `DataColumn<DomainRecord>[]`
- render functions should receive the record type directly
- avoid `any` in table renderers
- keep formatting logic local to the domain table

For JSON parsing, `LimitUpData.tsx` uses `parseJsonReply<T>()`. If parsing becomes more complex, combine it with zod validation rather than loosening types.

## TypeScript Style

Formatting and linting are configured by:

- `front/.prettierrc.yaml`
- `front/eslint.config.mjs`
- `front/tsconfig.node.json`
- `front/tsconfig.web.json`

Prefer explicit exported types at module boundaries, but local component state can infer obvious types unless the inferred type loses important domain information.
