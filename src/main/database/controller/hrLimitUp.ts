import { errorLog } from '@shared/logger'
import db from '../models'

export const readAllHrLimitUp = (
  payload: DatabaseListenerEventArgs['payload']
) => {
  try {
    const { startDate, endDate } = payload || {}
    const query = `SELECT * FROM hr_limit_up WHERE date BETWEEN ? AND ?`
    const readQuery = db.prepare(query)
    let rowList = readQuery.all(startDate, endDate) as HRLimitUpData<string>[]
    let currentStartDate = startDate
    let currentEndDate = endDate
    let maxRetries = 20

    while (!rowList.length && maxRetries) {
      currentStartDate = String(Number(currentStartDate) - 1)
      currentEndDate = String(Number(currentEndDate) - 1)
      rowList = readQuery.all(
        currentStartDate,
        currentEndDate
      ) as HRLimitUpData<string>[]
      maxRetries--
    }

    return rowList.map((item) => ({
      ...item,
      time_preview: JSON.parse(
        item.time_preview
      ) as HRLimitUpData['time_preview']
    }))
  } catch (err) {
    errorLog(err)
    throw err
  }
}

export const insertHrLimitUp = (data: (HRLimitUpData & { date: string })[]) => {
  try {
    const insertQuery = db.prepare(
      `INSERT OR REPLACE INTO hr_limit_up
        (date, open_num, first_limit_up_time, last_limit_up_time, code, limit_up_type, order_volume, is_new, limit_up_suc_rate, currency_value, market_id, is_again_limit, change_rate, turnover_rate, reason_type, order_amount, high_days, name, high_days_value, change_tag, market_type, latest, time_preview)
        VALUES
        (@date, @open_num, @first_limit_up_time, @last_limit_up_time, @code, @limit_up_type, @order_volume, @is_new, @limit_up_suc_rate, @currency_value, @market_id, @is_again_limit, @change_rate, @turnover_rate, @reason_type, @order_amount, @high_days, @name, @high_days_value, @change_tag, @market_type, @latest, @time_preview)`
    )
    const insertMany = db.transaction((items) => {
      for (const item of items) {
        const newItem = {
          ...item,
          time_preview: JSON.stringify(item.time_preview)
        }
        insertQuery.run(newItem)
      }
    })
    insertMany(data)
  } catch (err) {
    errorLog(err)
    throw err
  }
}
