import type React from 'react'
import dayjs from 'dayjs'
import DataTable, {
  type DataColumn
} from '@renderer/components/shared/DataTable'
import StatTile from '@renderer/components/shared/StatTile'
import { Badge } from '@renderer/components/ui/badge'
import { Card, CardContent } from '@renderer/components/ui/card'

export interface BrokenBoardRecord {
  code: string
  name: string
  firstLimitUpDate: string
  brokenDate: string
  secondLimitUpDate: string
  firstLimitUpData: HRLimitUpData
  secondLimitUpData: HRLimitUpData
  daysBetween: number
}

interface BrokenBoardAnalysisProps {
  data?: BrokenBoardRecord[]
  loading?: boolean
}

const marketBadge = (marketType: string) => {
  const marketInfo = [
    { text: '主板', value: 'HS', variant: 'success' as const },
    { text: '科创', value: 'STAR', variant: 'purple' as const },
    { text: '创业板', value: 'GEM', variant: 'info' as const }
  ].find((item) => item.value === marketType)
  return (
    <Badge variant={marketInfo?.variant ?? 'outline'}>
      {marketInfo?.text || marketType}
    </Badge>
  )
}

const BrokenBoardAnalysis: React.FC<BrokenBoardAnalysisProps> = ({
  data = [],
  loading = false
}) => {
  const totalCount = data.length
  const hsCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'HS'
  ).length
  const starCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'STAR'
  ).length
  const gemCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'GEM'
  ).length
  const days3Count = data.filter((item) => item.daysBetween <= 3).length
  const days46Count = data.filter(
    (item) => item.daysBetween >= 4 && item.daysBetween <= 6
  ).length
  const days7Count = data.filter((item) => item.daysBetween >= 7).length

  const columns: DataColumn<BrokenBoardRecord>[] = [
    { title: '代码', key: 'code', width: 80, render: (record) => record.code },
    { title: '名称', key: 'name', width: 100, render: (record) => record.name },
    {
      title: '市场',
      key: 'market_type',
      width: 100,
      render: (record) => marketBadge(record.secondLimitUpData.market_type)
    },
    {
      title: '首次涨停',
      key: 'firstLimitUpDate',
      width: 110,
      render: (record) =>
        dayjs(record.firstLimitUpDate, 'YYYYMMDD').format('MM-DD')
    },
    {
      title: '断板',
      key: 'brokenDate',
      width: 90,
      render: (record) => (
        <span className="text-amber-600">
          {dayjs(record.brokenDate, 'YYYYMMDD').format('MM-DD')}
        </span>
      )
    },
    {
      title: '再次涨停',
      key: 'secondLimitUpDate',
      width: 110,
      render: (record) => (
        <span className="text-emerald-600">
          {dayjs(record.secondLimitUpDate, 'YYYYMMDD').format('MM-DD')}
        </span>
      )
    },
    {
      title: '间隔',
      key: 'daysBetween',
      width: 80,
      render: (record) => (
        <Badge
          variant={
            record.daysBetween <= 3
              ? 'destructive'
              : record.daysBetween === 4
                ? 'warning'
                : 'info'
          }
        >
          {record.daysBetween}天
        </Badge>
      )
    },
    {
      title: '首次原因',
      key: 'firstReason',
      width: 160,
      render: (record) => (
        <span className="line-clamp-2">
          {record.firstLimitUpData.reason_type || '-'}
        </span>
      )
    },
    {
      title: '再次原因',
      key: 'secondReason',
      width: 160,
      render: (record) => (
        <span className="line-clamp-2">
          {record.secondLimitUpData.reason_type || '-'}
        </span>
      )
    },
    {
      title: '首次开板',
      key: 'firstOpenNum',
      width: 90,
      render: (record) => record.firstLimitUpData.open_num
    },
    {
      title: '再次开板',
      key: 'secondOpenNum',
      width: 90,
      render: (record) => record.secondLimitUpData.open_num
    },
    {
      title: '首次换手',
      key: 'firstTurnover',
      width: 100,
      render: (record) => `${record.firstLimitUpData.turnover_rate.toFixed(2)}%`
    },
    {
      title: '再次换手',
      key: 'secondTurnover',
      width: 100,
      render: (record) =>
        `${record.secondLimitUpData.turnover_rate.toFixed(2)}%`
    },
    {
      title: '首次时间',
      key: 'firstLimitUpTime',
      width: 100,
      render: (record) =>
        dayjs(
          Number(record.firstLimitUpData.first_limit_up_time) * 1000
        ).format('HH:mm:ss')
    },
    {
      title: '再次时间',
      key: 'secondLimitUpTime',
      width: 100,
      render: (record) =>
        dayjs(
          Number(record.secondLimitUpData.first_limit_up_time) * 1000
        ).format('HH:mm:ss')
    },
    {
      title: '流通市值',
      key: 'currencyValue',
      width: 110,
      render: (record) =>
        `${(record.secondLimitUpData.currency_value / 100000000).toFixed(2)}亿`
    }
  ]

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        <StatTile label="符合条件个股" value={totalCount} tone="blue" />
        <StatTile label="主板" value={hsCount} tone="green" />
        <StatTile label="科创板" value={starCount} tone="purple" />
        <StatTile label="创业板" value={gemCount} tone="orange" />
        <StatTile label="3天间隔" value={days3Count} tone="orange" />
        <StatTile label="4~6天间隔" value={days46Count} tone="amber" />
        <StatTile label="7天间隔" value={days7Count} tone="pink" />
      </div>
      <Card>
        <CardContent className="text-muted-foreground p-3 text-sm">
          <span className="text-foreground font-medium">说明：</span>
          {
            '统计前5天内有涨停，后某交易日断板，此后又涨停的个股。模式：涨停 -> 断板(未涨停) -> 再次涨停。'
          }
        </CardContent>
      </Card>
      <div className="min-h-0 flex-1">
        <DataTable
          data={data}
          columns={columns}
          loading={loading}
          rowKey={(record) =>
            `${record.code}-${record.firstLimitUpDate}-${record.secondLimitUpDate}`
          }
        />
      </div>
    </div>
  )
}

export default BrokenBoardAnalysis
