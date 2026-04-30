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

/**
 * 查找前5天内有涨停，后某交易日断板，此后又涨停的个股
 * 逻辑：
 * 1. 找出所有涨停记录
 * 2. 对每个股票代码，按日期排序
 * 3. 查找模式：涨停 → (1-5天前有涨停) → 断板(当天未涨停) → 再次涨停
 */
export const findBrokenBoardStocks = (
  payload: DatabaseListenerEventArgs['payload']
) => {
  try {
    const { startDate, endDate } = payload || {}

    // 获取日期范围内所有的涨停数据和交易日期
    const query = `
      SELECT DISTINCT date
      FROM hr_limit_up
      WHERE date BETWEEN ? AND ?
      ORDER BY date ASC
    `
    const dates = db.prepare(query).all(startDate, endDate) as {
      date: string
    }[]

    if (dates.length === 0) {
      return []
    }

    // 获取所有股票代码
    const codesQuery = `
      SELECT DISTINCT code, name
      FROM hr_limit_up
      WHERE date BETWEEN ? AND ?
    `
    const stocks = db.prepare(codesQuery).all(startDate, endDate) as {
      code: string
      name: string
    }[]

    const results: Array<{
      code: string
      name: string
      firstLimitUpDate: string
      brokenDate: string
      secondLimitUpDate: string
      firstLimitUpData: HRLimitUpData<string>
      secondLimitUpData: HRLimitUpData<string>
      daysBetween: number
    }> = []

    // 对每个股票进行分析
    for (const stock of stocks) {
      // 获取该股票的所有交易记录（包括涨停和非涨停）
      const stockQuery = `
        SELECT * FROM hr_limit_up
        WHERE code = ? AND date BETWEEN ? AND ?
        ORDER BY date ASC
      `
      const stockData = db
        .prepare(stockQuery)
        .all(stock.code, startDate, endDate) as HRLimitUpData<string>[]

      // 将数据按日期组织成Map
      const stockDataMap = new Map<string, HRLimitUpData<string>>()
      stockData.forEach((item) => {
        stockDataMap.set(item.date, item)
      })

      // 遍历每个交易日，寻找符合条件的模式
      for (let i = 0; i < dates.length; i++) {
        const currentDate = dates[i].date
        const currentData = stockDataMap.get(currentDate)

        // 如果当天有涨停记录，检查是否为"再次涨停"的情况
        if (currentData) {
          // 向前查找5天，看是否有涨停
          let foundFirstLimitUp = false
          let firstLimitUpDate = ''
          let firstLimitUpData: HRLimitUpData<string> | null = null

          for (let j = i - 1; j >= Math.max(0, i - 5) && j >= 0; j--) {
            const checkDate = dates[j].date
            const checkData = stockDataMap.get(checkDate)

            if (checkData) {
              foundFirstLimitUp = true
              firstLimitUpDate = checkDate
              firstLimitUpData = checkData
              break
            }
          }

          // 如果找到了前面的涨停，检查中间是否有断板
          if (foundFirstLimitUp && firstLimitUpData) {
            const firstIndex = dates.findIndex(
              (d) => d.date === firstLimitUpDate
            )

            // 检查中间的交易日是否存在断板（即该股票在某些交易日没有涨停记录）
            let foundBroken = false
            let brokenDate = ''

            for (let k = firstIndex + 1; k < i; k++) {
              const middleDate = dates[k].date
              const middleData = stockDataMap.get(middleDate)

              // 如果这个交易日没有该股票的涨停记录，说明断板了
              if (!middleData) {
                foundBroken = true
                brokenDate = middleDate
                break
              }
            }

            // 如果找到了断板，且当前是再次涨停，记录这个模式
            if (foundBroken) {
              const daysBetween = i - firstIndex

              results.push({
                code: stock.code,
                name: stock.name,
                firstLimitUpDate,
                brokenDate,
                secondLimitUpDate: currentDate,
                firstLimitUpData,
                secondLimitUpData: currentData,
                daysBetween
              })
            }
          }
        }
      }
    }

    // 解析 time_preview 字段
    return results.map((item) => ({
      ...item,
      firstLimitUpData: {
        ...item.firstLimitUpData,
        time_preview: JSON.parse(item.firstLimitUpData.time_preview)
      },
      secondLimitUpData: {
        ...item.secondLimitUpData,
        time_preview: JSON.parse(item.secondLimitUpData.time_preview)
      }
    }))
  } catch (err) {
    errorLog(err)
    throw err
  }
}
