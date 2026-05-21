import React, { useEffect, useState } from 'react'
import dayjs from 'dayjs'
import BrokenBoardAnalysis, {
  type BrokenBoardRecord
} from '@renderer/components/limitUp/BrokenBoardAnalysis'
import EmTable from '@renderer/components/limitUp/EmTable'
import HrTable from '@renderer/components/limitUp/HrTable'
import DateRangePicker from '@renderer/components/shared/DateRangePicker'
import { toast } from '@renderer/components/shared/Toast'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '@renderer/components/ui/tabs'
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
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(
    null
  )

  const requestRange = (startDate?: string, endDate?: string) => {
    setIsLoadingEm(true)
    setIsLoadingHr(true)
    setIsLoadingBroken(true)
    window.api.database.request({
      event: DatabaseEventKey.ReadEmLimitUpData,
      payload: startDate && endDate ? { startDate, endDate } : undefined
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadHrLimitUpData,
      payload: startDate && endDate ? { startDate, endDate } : undefined
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadBrokenBoardData,
      payload: startDate && endDate ? { startDate, endDate } : undefined
    })
  }

  useEffect(() => {
    const today = dayjs().format('YYYYMMDD')
    setIsLoadingEm(true)
    setIsLoadingHr(true)
    setIsLoadingBroken(true)
    window.api.database.request({
      event: DatabaseEventKey.ReadEmLimitUpData,
      payload: { startDate: today, endDate: today }
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadHrLimitUpData,
      payload: { startDate: today, endDate: today }
    })
    window.api.database.request({
      event: DatabaseEventKey.ReadBrokenBoardData,
      payload: {
        startDate: dayjs().subtract(5, 'day').format('YYYYMMDD'),
        endDate: today
      }
    })
    const unsubscribe = window.api.database.response((event) => {
      debugLog('Database response received in LimitUpDataEditor:', event)
      switch (event.event) {
        case DatabaseEventKey.ReadEmLimitUpData:
          setEmLimitUpData(event.data || [])
          if (event.error)
            toast.error(`Error loading EM limit up data: ${event.error}`)
          setIsLoadingEm(false)
          break
        case DatabaseEventKey.ReadHrLimitUpData:
          setHrLimitUpData(event.data || [])
          if (event.error)
            toast.error(`Error loading HR limit up data: ${event.error}`)
          setIsLoadingHr(false)
          break
        case DatabaseEventKey.ReadBrokenBoardData:
          setBrokenBoardData(event.data || [])
          if (event.error)
            toast.error(`Error loading broken board data: ${event.error}`)
          setIsLoadingBroken(false)
          break
        default:
          break
      }
    })
    return () => unsubscribe()
  }, [])

  const handleDateRangeChange = (dates: null | (dayjs.Dayjs | null)[]) => {
    if (dates?.[0] && dates?.[1]) {
      setDateRange([dates[0], dates[1]])
      requestRange(dates[0].format('YYYYMMDD'), dates[1].format('YYYYMMDD'))
    } else {
      setDateRange(null)
      requestRange()
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-5">
      <div className="border-border bg-card flex items-center justify-between gap-4 rounded-2xl border p-5 shadow-[var(--shadow-md)]">
        <div>
          <div className="border-accent/30 bg-accent/5 mb-2 inline-flex items-center gap-2 rounded-full border px-3 py-1">
            <span className="bg-accent h-2 w-2 animate-[pulse-dot_2s_infinite] rounded-full" />
            <span className="text-accent font-mono text-[10px] tracking-[0.15em] uppercase">
              Live Dataset
            </span>
          </div>
          <h1 className="font-display text-2xl tracking-tight">
            Limit Up <span className="gradient-text">Data</span>
          </h1>
          <p className="text-muted-foreground mt-1 text-sm font-medium">
            HR, EM and re-up analysis
          </p>
        </div>
        <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
      </div>
      <Tabs defaultValue="HR" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="w-fit">
          <TabsTrigger value="HR">HR</TabsTrigger>
          <TabsTrigger value="EM">EM</TabsTrigger>
          <TabsTrigger value="BrokenBoard">UP2REUP</TabsTrigger>
        </TabsList>
        <TabsContent value="HR" className="min-h-0 flex-1">
          <HrTable data={hrLimitUpData} loading={isLoadingHr} />
        </TabsContent>
        <TabsContent value="EM" className="min-h-0 flex-1">
          <EmTable data={emLimitUpData} loading={isLoadingEm} />
        </TabsContent>
        <TabsContent value="BrokenBoard" className="min-h-0 flex-1">
          <BrokenBoardAnalysis
            data={brokenBoardData}
            loading={isLoadingBroken}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default LimitUpData
