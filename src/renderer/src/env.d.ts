/// <reference types="vite/client" />

interface Window {
  api: {
    handleMcpPort: {
      requestMcpPort: () => void
      responseMcpPort: (callback: (portMap: PortMapType) => void) => () => void
    }
  }
}
