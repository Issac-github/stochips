import { BrowserWindow, ipcMain } from 'electron'
import { EventKey } from '@shared/eventKey'
import { errorLog } from '@shared/logger'
import initLLMServer from '../llm'
import { callStockRpc } from '../stockRpc/client'

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

export class IPC {
  ipcOnMainWindow(mainWindow: BrowserWindow | null) {
    mainWindow?.on('closed', () => {
      ipcMain.removeAllListeners()
    })

    ipcMain.on(EventKey.McpPort, () => {
      mainWindow?.webContents.send(EventKey.McpPort, portMap)
    })

    ipcMain.handle(EventKey.StockRpc, async (_, args: StockRpcRequestArgs) => {
      try {
        return await callStockRpc(args.event, args.payload || {})
      } catch (error) {
        errorLog('stock_rpc request failed', error)
        const message =
          error instanceof Error ? error.message : JSON.stringify(error)
        return { error: message }
      }
    })
  }
}
