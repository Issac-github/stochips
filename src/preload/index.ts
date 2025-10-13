import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import { errorLog } from '@shared/logger'

// Custom APIs for renderer
const api = {
  handleMcpPort: {
    requestMcpPort: () => {
      ipcRenderer.send('mcp-port')
    },
    responseMcpPort: (callback: (port: number) => void): (() => void) => {
      const listener = (_event: Electron.IpcRendererEvent, port: number) => {
        callback(port)
      }
      ipcRenderer.on('mcp-port', listener)
      return () => ipcRenderer.removeListener('mcp-port', listener)
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
