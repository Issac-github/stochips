import React, { useEffect, useState } from 'react'
import dayjs from 'dayjs'
import { Bot, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'
import BrokenBoardAnalysis, {
  type BrokenBoardRecord
} from '@renderer/components/limitUp/BrokenBoardAnalysis'
import EmTable from '@renderer/components/limitUp/EmTable'
import HrTable from '@renderer/components/limitUp/HrTable'
import DateRangePicker from '@renderer/components/shared/DateRangePicker'
import { toast } from '@renderer/components/shared/Toast'
import { Button } from '@renderer/components/ui/button'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '@renderer/components/ui/tabs'
import { StockRpcEventKey } from '@shared/eventKey'
import { debugLog } from '@shared/logger'

type StockAction = {
  event:
    | StockRpcEventKey.SubmitFetch
    | StockRpcEventKey.SubmitAssess
    | StockRpcEventKey.SubmitAssessAi
    | StockRpcEventKey.RunAgent
  label: string
  runningLabel: string
  icon: React.ElementType
}

const stockActions: StockAction[] = [
  {
    event: StockRpcEventKey.SubmitFetch,
    label: '抓取',
    runningLabel: '抓取中',
    icon: RefreshCw
  },
  {
    event: StockRpcEventKey.SubmitAssess,
    label: '规则评估',
    runningLabel: '评估中',
    icon: ShieldCheck
  },
  {
    event: StockRpcEventKey.SubmitAssessAi,
    label: 'AI评估',
    runningLabel: 'AI评估中',
    icon: Sparkles
  },
  {
    event: StockRpcEventKey.RunAgent,
    label: 'Agent巡检',
    runningLabel: '巡检中',
    icon: Bot
  }
]

const LimitUpData: React.FC = () => {
  const [isLoadingHr, setIsLoadingHr] = useState(true)
  const [isLoadingEm, setIsLoadingEm] = useState(true)
  const [isLoadingBroken, setIsLoadingBroken] = useState(true)
  const [activeTask, setActiveTask] = useState<{
    id: string
    action: StockAction
    status: StockRpcTaskStatus
    result?: string
    error?: string
  } | null>(null)
  const [hrLimitUpData, setHrLimitUpData] = useState<HRLimitUpData[]>([])
  const [emLimitUpData, setEmLimitUpData] = useState<EMLimitUpData[]>([])
  const [brokenBoardData, setBrokenBoardData] = useState<BrokenBoardRecord[]>(
    []
  )
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(
    null
  )

  const parseJsonReply = <T,>(response: StockRpcResponse): T[] => {
    if (response.error) {
      throw new Error(response.error)
    }
    if (!response.json) {
      return []
    }
    return JSON.parse(response.json) as T[]
  }

  const requestRange = async (startDate?: string, endDate?: string) => {
    const today = dayjs().format('YYYYMMDD')
    const payload = {
      startDate: startDate || today,
      endDate: endDate || today
    }

    setIsLoadingEm(true)
    setIsLoadingHr(true)
    setIsLoadingBroken(true)

    try {
      const [emResponse, hrResponse, brokenResponse] = await Promise.all([
        window.api.stockRpc.invoke({
          event: StockRpcEventKey.QueryEmLimitUp,
          payload
        }),
        window.api.stockRpc.invoke({
          event: StockRpcEventKey.QueryHrLimitUp,
          payload
        }),
        window.api.stockRpc.invoke({
          event: StockRpcEventKey.QueryBrokenBoard,
          payload
        })
      ])

      setEmLimitUpData(parseJsonReply<EMLimitUpData>(emResponse))
      setHrLimitUpData(parseJsonReply<HRLimitUpData>(hrResponse))
      setBrokenBoardData(parseJsonReply<BrokenBoardRecord>(brokenResponse))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      toast.error('加载股票数据失败', message)
    } finally {
      setIsLoadingEm(false)
      setIsLoadingHr(false)
      setIsLoadingBroken(false)
    }
  }

  useEffect(() => {
    const today = dayjs().format('YYYYMMDD')
    requestRange(dayjs().subtract(5, 'day').format('YYYYMMDD'), today)
      .then(() => debugLog('Stock RPC data loaded'))
      .catch((error) => debugLog('Stock RPC data load failed:', error))
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

  const selectedTaskDate = () => (dateRange?.[1] || dayjs()).format('YYYYMMDD')

  const refreshCurrentDate = () => {
    if (dateRange?.[0] && dateRange?.[1]) {
      requestRange(
        dateRange[0].format('YYYYMMDD'),
        dateRange[1].format('YYYYMMDD')
      )
      return
    }
    const today = dayjs().format('YYYYMMDD')
    requestRange(dayjs().subtract(5, 'day').format('YYYYMMDD'), today)
  }

  const pollTask = async (taskId: string, action: StockAction) => {
    const response = await window.api.stockRpc.invoke({
      event: StockRpcEventKey.GetTask,
      payload: { taskId }
    })

    if (response.error && !response.status) {
      setActiveTask({
        id: taskId,
        action,
        status: 'failed',
        error: response.error
      })
      toast.error('任务查询失败', response.error)
      return
    }

    const status = response.status || 'pending'
    setActiveTask({
      id: taskId,
      action,
      status,
      result: response.result,
      error: response.error
    })

    if (status === 'succeeded') {
      toast.success(`${action.label}完成`)
      refreshCurrentDate()
      return
    }

    if (status === 'failed') {
      toast.error(
        `${action.label}失败`,
        response.error || 'stock_rpc returned failed'
      )
      return
    }

    window.setTimeout(() => {
      pollTask(taskId, action).catch((error) => {
        const message = error instanceof Error ? error.message : String(error)
        setActiveTask({ id: taskId, action, status: 'failed', error: message })
        toast.error('任务轮询失败', message)
      })
    }, 1500)
  }

  const submitStockTask = async (action: StockAction) => {
    const date = selectedTaskDate()
    const payload =
      action.event === StockRpcEventKey.RunAgent
        ? { date, goal: '更新数据并完成每日股票风险巡检' }
        : { date }

    setActiveTask({
      id: '',
      action,
      status: 'pending'
    })

    const response = await window.api.stockRpc.invoke({
      event: action.event,
      payload
    } as StockRpcRequestArgs)

    if (response.error) {
      setActiveTask({
        id: '',
        action,
        status: 'failed',
        error: response.error
      })
      toast.error(`${action.label}提交失败`, response.error)
      return
    }

    const taskId = response.taskId || response.task_id
    if (!taskId) {
      const error = 'stock_rpc did not return task id'
      setActiveTask({ id: '', action, status: 'failed', error })
      toast.error(`${action.label}提交失败`, error)
      return
    }

    setActiveTask({
      id: taskId,
      action,
      status: 'pending'
    })
    toast.info(`${action.label}已提交`, `任务 ${taskId}`)
    pollTask(taskId, action)
  }

  const isTaskRunning =
    activeTask?.status === 'pending' || activeTask?.status === 'running'

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
        <div className="flex flex-wrap items-center justify-end gap-3">
          <DateRangePicker value={dateRange} onChange={handleDateRangeChange} />
          <div className="flex flex-wrap items-center justify-end gap-2">
            {stockActions.map((action) => {
              const Icon = action.icon
              const isCurrent = activeTask?.action.event === action.event
              return (
                <Button
                  key={action.event}
                  variant={
                    action.event === StockRpcEventKey.RunAgent
                      ? 'default'
                      : 'outline'
                  }
                  size="sm"
                  disabled={isTaskRunning}
                  onClick={() => submitStockTask(action)}
                >
                  <Icon
                    className={
                      isCurrent && isTaskRunning
                        ? 'h-4 w-4 animate-spin'
                        : 'h-4 w-4'
                    }
                  />
                  {isCurrent && isTaskRunning
                    ? action.runningLabel
                    : action.label}
                </Button>
              )
            })}
          </div>
        </div>
      </div>
      {activeTask && (
        <div className="border-border bg-muted/40 flex items-start justify-between gap-4 rounded-xl border px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold">
              {activeTask.action.label} · {activeTask.status}
              {activeTask.id ? ` · #${activeTask.id}` : ''}
            </div>
            {(activeTask.error || activeTask.result) && (
              <div className="text-muted-foreground mt-1 line-clamp-2 font-mono text-xs">
                {activeTask.error || activeTask.result}
              </div>
            )}
          </div>
          {activeTask.status === 'succeeded' && (
            <Button variant="ghost" size="sm" onClick={refreshCurrentDate}>
              刷新表格
            </Button>
          )}
        </div>
      )}
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
