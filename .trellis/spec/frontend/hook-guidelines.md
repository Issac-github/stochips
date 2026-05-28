# Frontend Hook Guidelines

## Hook Scope

Renderer hooks live in `front/src/renderer/src/lib/hooks/`. Use hooks for reusable client-side behavior that is not tied to one presentational component.

Current examples:

- `useGPTChat` discovers the GPT server port through `window.api.mcpPort`, sends streaming chat requests, handles SSE-style `data:` chunks, and aborts previous streams.
- `useHttpMcpClient` and `useSocketMcpClient` own MCP client transport interactions.

Do not put Electron `ipcRenderer`, gRPC, or Node APIs inside renderer hooks. Hooks should call preload APIs exposed on `window.api`.

## Port Discovery

For local LLM/MCP services, follow `useGPTChat`:

- request ports through `window.api.mcpPort.request()`
- subscribe with `window.api.mcpPort.response(callback)`
- return the unsubscribe function from `useEffect`
- treat a missing port as a recoverable error

Main-process port state lives in `front/src/main/lib/ipc.ts` as `portMap`. Renderer hooks consume that state but do not mutate it.

## Streaming Requests

When handling stream responses:

- keep an `AbortController` in a `useRef`
- abort an existing stream before starting a new one
- handle `AbortError` quietly
- check `response.ok` and `response.body`
- decode chunks with `TextDecoder`
- parse only lines with the expected `data: ` prefix
- surface errors through callback options instead of throwing into React render

This mirrors `useGPTChat` and keeps chat components simple.

## Data Fetching Hooks

Stock RPC data fetching currently lives in `LimitUpData.tsx` because the behavior is page-specific. Extract a hook only when another screen needs the same request/polling pattern.

If extracting stock hooks, keep the same contracts:

- call `window.api.stockRpc.invoke`
- accept date strings in `YYYYMMDD`
- parse `{ json }` replies with explicit generic types
- preserve backend `{ error }` handling
- do not directly import `front/src/main/stockRpc/client.ts` into renderer code
