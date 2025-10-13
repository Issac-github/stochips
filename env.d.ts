/// <reference types="vite/client" />

interface ImportMetaEnv {}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface PortMapType {
  socket: number | null
  http: number | null
  gpt: number | null
}
