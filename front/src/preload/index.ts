import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import { EventKey } from '@shared/eventKey'
import { errorLog } from '@shared/logger'

// Custom APIs for renderer
const api = {
  mcpPort: {
    request: () => {
      ipcRenderer.send(EventKey.McpPort)
    },
    response: (callback: (port: PortMapType) => void): (() => void) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        port: PortMapType
      ) => {
        callback(port)
      }
      ipcRenderer.on(EventKey.McpPort, listener)
      return () => ipcRenderer.removeListener(EventKey.McpPort, listener)
    }
  },
  stockRpc: {
    invoke: (args: StockRpcRequestArgs) => {
      return ipcRenderer.invoke(EventKey.StockRpc, args)
    }
  }
}

// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    errorLog(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
