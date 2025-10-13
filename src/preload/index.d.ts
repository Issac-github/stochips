import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      handleMcpPort: {
        requestMcpPort: () => void
        responseMcpPort: (callback: (port: number) => void) => () => void
      }
    }
  }
}
