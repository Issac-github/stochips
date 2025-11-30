import { BrowserWindow, IpcMainEvent, ipcMain } from 'electron'
import { Worker } from 'worker_threads'
import { EventKey } from '@shared/eventKey'
import { errorLog } from '@shared/logger'
import initLLMServer from '../llm'
import createDatabaseWorker from '../worker/database?nodeWorker'

export const portMap: PortMapType = {
  socket: null,
  http: null,
  gpt: null
}
initLLMServer().then(({ SOCKETPORT, HTTPPORT, GPTPORT }) => {
  // MCP WebSocket server port
  portMap.socket = SOCKETPORT
  // MCP HTTP server port
  portMap.http = HTTPPORT
  // GPT HTTP server port
  portMap.gpt = GPTPORT
})

let uniqueDatabaseWorker: Worker | null = null

const ensureDatabaseWorker = (mainWindow: BrowserWindow | null) => {
  if (uniqueDatabaseWorker) {
    return uniqueDatabaseWorker
  }
  try {
    uniqueDatabaseWorker = createDatabaseWorker({ workerData: 'worker' })
    uniqueDatabaseWorker.on('message', (args: DatabaseListenerEventArgs) => {
      const win = mainWindow || BrowserWindow.getAllWindows()[0]
      if (!win || win.webContents.isDestroyed()) {
        return
      }
      win.webContents.send(EventKey.Database, args)
    })
  } catch (e) {
    errorLog('createDatabaseWorker init error', e)
    uniqueDatabaseWorker = null
  }
  return uniqueDatabaseWorker
}

export class IPC {
  ipcOnMainWindow(mainWindow: BrowserWindow | null) {
    mainWindow?.on('closed', () => {
      ipcMain.removeAllListeners()
    })
    const databaseWorker = ensureDatabaseWorker(mainWindow)
    ipcMain.on(
      EventKey.Database,
      (_: IpcMainEvent, args: DatabaseListenerEventArgs) => {
        try {
          databaseWorker?.postMessage(args)
        } catch (error) {
          errorLog(error)
        }
      }
    )

    ipcMain.on(EventKey.McpPort, () => {
      mainWindow?.webContents.send(EventKey.McpPort, portMap)
    })
  }
}
