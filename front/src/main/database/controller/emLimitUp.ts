import { errorLog } from '@shared/logger'
import db from '../models'

export const readAllEmLimitUp = (
  payload: DatabaseListenerEventArgs['payload']
) => {
  try {
    const { startDate, endDate } = payload || {}
    const query = `SELECT * FROM em_limit_up WHERE qdate BETWEEN ? AND ?`
    const readQuery = db.prepare(query)
    let rowList = readQuery.all(startDate, endDate) as EMLimitUpData<string>[]
    let currentStartDate = startDate
    let currentEndDate = endDate
    let maxRetries = 20

    while (!rowList.length && maxRetries) {
      currentStartDate = String(Number(currentStartDate) - 1)
      currentEndDate = String(Number(currentEndDate) - 1)
      rowList = readQuery.all(
        currentStartDate,
        currentEndDate
      ) as EMLimitUpData<string>[]
      maxRetries--
    }

    return rowList.map((item) => ({
      ...item,
      zttj: JSON.parse(item.zttj) as EMLimitUpData['zttj']
    }))
  } catch (err) {
    errorLog(err)
    throw err
  }
}

export const insertEmLimitUp = (
  data: (EMLimitUpData & { qdate: number })[]
) => {
  try {
    const insertQuery = db.prepare(
      `INSERT OR REPLACE INTO em_limit_up
        (c, qdate, m, n, p, zdp, amount, ltsz, tshare, hs, lbc, fbt, lbt, fund, zbc, hybk, zttj) VALUES
        (@c, @qdate, @m, @n, @p, @zdp, @amount, @ltsz, @tshare, @hs, @lbc, @fbt, @lbt, @fund, @zbc, @hybk, @zttj)
      `
    )
    const insertMany = db.transaction((items) => {
      for (const item of items) {
        const newItem = { ...item, zttj: JSON.stringify(item.zttj) }
        insertQuery.run(newItem)
      }
    })
    insertMany(data)
  } catch (err) {
    errorLog(err)
    throw err
  }
}
