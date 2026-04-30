import { parentPort } from 'worker_threads'
import { DatabaseEventKey } from '@shared/eventKey'
import {
  EmLimitDataListValidator,
  HrLimitDataListValidator
} from '@shared/lib/validate'
import { debugLog, errorLog } from '@shared/logger'
import {
  insertEmLimitUp,
  readAllEmLimitUp
} from '../database/controller/emLimitUp'
import {
  findBrokenBoardStocks,
  insertHrLimitUp,
  readAllHrLimitUp
} from '../database/controller/hrLimitUp'

try {
  const port = parentPort
  if (!port) {
    throw new Error('Illegal worker thread: no parent port found')
  }
  port.on('message', (args: DatabaseListenerEventArgs) => {
    const { event, data, payload } = args || {}
    try {
      switch (event) {
        case DatabaseEventKey.WriteEmLimitUpData: {
          if (Array.isArray(data)) {
            data.forEach((item) => {
              const _ = item.pool.map((i) => ({ ...i, qdate: item.qdate }))
              EmLimitDataListValidator.parse(_)
              insertEmLimitUp(_)
            })
            port.postMessage({
              event
            })
            break
          }
          const _ = data.pool.map((i) => ({ ...i, qdate: data.qdate }))
          EmLimitDataListValidator.parse(_)
          insertEmLimitUp(_)
          port.postMessage({
            event
          })
          break
        }
        case DatabaseEventKey.WriteHrLimitUpData: {
          if (Array.isArray(data)) {
            data.forEach((item) => {
              const _ = item.info.map((i) => ({ ...i, date: item.date }))
              HrLimitDataListValidator.parse(_)
              insertHrLimitUp(_)
            })
            port.postMessage({
              event
            })
            break
          }
          const _ = data.info.map((i) => ({ ...i, date: data.date }))
          HrLimitDataListValidator.parse(_)
          insertHrLimitUp(_)
          port.postMessage({
            event
          })
          break
        }
        case DatabaseEventKey.ReadEmLimitUpData: {
          const data = readAllEmLimitUp(payload)
          debugLog('Read EM Limit Up data count: ' + data.length)
          port.postMessage({ event, data })
          break
        }
        case DatabaseEventKey.ReadHrLimitUpData: {
          const data = readAllHrLimitUp(payload)
          debugLog('Read HR Limit Up data count: ' + data.length)
          port.postMessage({ event, data })
          break
        }
        case DatabaseEventKey.ReadBrokenBoardData: {
          const data = findBrokenBoardStocks(payload)
          debugLog('Read Broken Board data count: ' + data.length)
          port.postMessage({ event, data })
          break
        }
        default:
          break
      }
    } catch (error) {
      errorLog('Database Worker Event Error:', error)
      port.postMessage({
        event,
        error: error instanceof Error ? { message: error.message } : error
      })
    }
  })
} catch (error) {
  errorLog(error)
  try {
    const errStr = JSON.stringify(error)
    errorLog('Database Worker Error: ' + errStr)
  } catch (err) {
    errorLog(err)
  }
}
