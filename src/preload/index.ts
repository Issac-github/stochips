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
    response: (callback: (port: number) => void): (() => void) => {
      const listener = (_event: Electron.IpcRendererEvent, port: number) => {
        callback(port)
      }
      ipcRenderer.on(EventKey.McpPort, listener)
      return () => ipcRenderer.removeListener(EventKey.McpPort, listener)
    }
  },
  database: {
    request: (args: DatabaseListenerEventArgs) => {
      ipcRenderer.send(EventKey.Database, args)
    },
    response: (callback: (...args: unknown[]) => void): (() => void) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        data: DatabaseListenerEventArgs
      ) => {
        callback(data)
      }
      ipcRenderer.on(EventKey.Database, listener)
      return () => ipcRenderer.removeListener(EventKey.Database, listener)
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
