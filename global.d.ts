import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      mcpPort: {
        request: () => void
        response: (callback: (port: PortMapType) => void) => () => void
      }
      database: {
        request: (args: DatabaseListenerEventArgs) => void
        response: (
          callback: (args: DatabaseListenerEventArgs) => void
        ) => () => void
      }
    }
  }
}
