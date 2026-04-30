import React, { useEffect, useState } from 'react'
import { DatePicker, Tabs, message } from 'antd'
import dayjs from 'dayjs'
import BrokenBoardAnalysis from '@renderer/components/limitUp/BrokenBoardAnalysis'
import EmTable from '@renderer/components/limitUp/EmTable'
import HrTable from '@renderer/components/limitUp/HrTable'
import { DatabaseEventKey } from '@shared/eventKey'
import { debugLog } from '@shared/logger'

const LimitUpData: React.FC = () => {
  const [isLoadingHr, setIsLoadingHr] = useState(true)
  const [isLoadingEm, setIsLoadingEm] = useState(true)
  const [isLoadingBroken, setIsLoadingBroken] = useState(true)
  const [hrLimitUpData, setHrLimitUpData] = useState<HRLimitUpData[]>([])
  const [emLimitUpData, setEmLimitUpData] = useState<EMLimitUpData[]>([])
  const [brokenBoardData, setBrokenBoardData] = useState<BrokenBoardRecord[]>(
    []
  )
  const [messageApi, contextHolder] = message.useMessage()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(
    null
  )

  useEffect(() => {
    setIsLoadingEm(true)
    setIsLoadingHr(true)
    setIsLoadingBroken(true)
    window.api.database.request({
      event: DatabaseEventKey.ReadEmLimitUpData,
      payload: {
        startDate: dayjs().format('YYYYMMDD'),
        endDate: dayjs().format('YYYYMMDD')
      }
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadHrLimitUpData,
      payload: {
        startDate: dayjs().format('YYYYMMDD'),
        endDate: dayjs().format('YYYYMMDD')
      }
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadBrokenBoardData,
      payload: {
        startDate: dayjs().subtract(5, 'day').format('YYYYMMDD'),
        endDate: dayjs().format('YYYYMMDD')
      }
    })
    const unsubscribe = window.api.database.response((event) => {
      debugLog('Database response received in LimitUpDataEditor:', event)
      switch (event.event) {
        case DatabaseEventKey.ReadEmLimitUpData:
          setEmLimitUpData(event.data || [])
          if (event.error) {
            messageApi.error(`Error loading EM limit up data: ${event.error}`)
          }
          setIsLoadingEm(false)
          break
        case DatabaseEventKey.ReadHrLimitUpData:
          setHrLimitUpData(event.data || [])
          if (event.error) {
            messageApi.error(`Error loading HR limit up data: ${event.error}`)
          }
          setIsLoadingHr(false)
          break
        case DatabaseEventKey.ReadBrokenBoardData:
          setBrokenBoardData(event.data || [])
          if (event.error) {
            messageApi.error(`Error loading broken board data: ${event.error}`)
          }
          setIsLoadingBroken(false)
          break
        default:
          break
      }
    })
    return () => {
      unsubscribe()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const tabs = [
    {
      key: 'HR',
      label: 'HR',
      children: <HrTable data={hrLimitUpData} loading={isLoadingHr} />
    },
    {
      key: 'EM',
      label: 'EM',
      children: <EmTable data={emLimitUpData} loading={isLoadingEm} />
    },
    {
      key: 'BrokenBoard',
      // label: '断板再涨停分析',
      label: 'UP2REUP',
      children: (
        <BrokenBoardAnalysis data={brokenBoardData} loading={isLoadingBroken} />
      )
    }
  ]

  const handleDateRangeChange = (dates: null | (dayjs.Dayjs | null)[]) => {
    if (dates?.[0] && dates?.[1]) {
      const startDate = dates[0].format('YYYYMMDD')
      const endDate = dates[1].format('YYYYMMDD')
      setDateRange([dates[0], dates[1]])
      setIsLoadingEm(true)
      setIsLoadingHr(true)
      setIsLoadingBroken(true)
      window.api.database.request({
        event: DatabaseEventKey.ReadEmLimitUpData,
        payload: { startDate, endDate }
      })
      window.api.database.request({
        event: DatabaseEventKey.ReadHrLimitUpData,
        payload: { startDate, endDate }
      })
      window.api.database.request({
        event: DatabaseEventKey.ReadBrokenBoardData,
        payload: { startDate, endDate }
      })
    } else {
      setDateRange(null)
      setIsLoadingEm(true)
      setIsLoadingHr(true)
      setIsLoadingBroken(true)
      window.api.database.request({ event: DatabaseEventKey.ReadEmLimitUpData })
      window.api.database.request({ event: DatabaseEventKey.ReadHrLimitUpData })
      window.api.database.request({
        event: DatabaseEventKey.ReadBrokenBoardData
      })
    }
  }

  return (
    <div className="flex h-full w-full flex-col">
      <div>
        <DatePicker.RangePicker
          value={
            dateRange
              ? [
                  dayjs(dateRange[0], 'YYYYMMDD'),
                  dayjs(dateRange[1], 'YYYYMMDD')
                ]
              : null
          }
          format="YYYYMMDD"
          placeholder={['开始日期', '结束日期']}
          onChange={handleDateRangeChange}
        />
      </div>
      <Tabs
        defaultActiveKey="2"
        items={tabs}
        className="limit-up-data h-full overflow-auto"
      />
      {contextHolder}
      <style>{`
        .limit-up-data .ant-tabs-content-holder {
          height: 100%;
          overflow: auto;
        }
      `}</style>
    </div>
  )
}

export default LimitUpData
