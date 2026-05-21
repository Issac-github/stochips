import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      mcpPort: {
        request: () => void
        response: (callback: (port: PortMapType) => void) => () => void
      }
      stockRpc: {
        invoke: (args: StockRpcRequestArgs) => Promise<StockRpcResponse>
      }
    }
  }
}
