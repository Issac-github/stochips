import type React from 'react'
import dayjs from 'dayjs'
import DataTable, {
  type DataColumn
} from '@renderer/components/shared/DataTable'
import StatTile from '@renderer/components/shared/StatTile'
import { Badge } from '@renderer/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@renderer/components/ui/card'

interface HrTableProps {
  data?: HRLimitUpData[]
  loading?: boolean
  pagination?: {
    current: number
    pageSize: number
    total: number
  }
  onChange?: (pagination: unknown, filters: unknown, sorter: unknown) => void
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

const reasonKeywords = (data: HRLimitUpData[], marketFilter?: string) => {
  const reasonMap = new Map<string, number>()
  data
    .filter((item) => !marketFilter || item.market_type === marketFilter)
    .forEach((item) => {
      item.reason_type
        ?.split(/[+、,，；;|&\s]+/)
        .filter((keyword) => keyword.trim().length > 1)
        .forEach((keyword) => {
          const trimmed = keyword.trim()
          reasonMap.set(trimmed, (reasonMap.get(trimmed) || 0) + 1)
        })
    })

  return Array.from(reasonMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
}

const keywordBadges = (items: [string, number][]) => (
  <div className="flex flex-wrap gap-2">
    {items.map(([keyword, count], index) => (
      <Badge
        key={keyword}
        variant={
          index < 3
            ? 'destructive'
            : index < 8
              ? 'warning'
              : index < 15
                ? 'info'
                : 'outline'
        }
        className="gap-1"
      >
        <span className="font-semibold">{keyword}</span>
        <span className="opacity-70">({count})</span>
      </Badge>
    ))}
  </div>
)

const HrTable: React.FC<HrTableProps> = ({ data = [], loading = false }) => {
  const totalCount = data.length
  const hsCount = data.filter((item) => item.market_type === 'HS').length
  const starCount = data.filter((item) => item.market_type === 'STAR').length
  const gemCount = data.filter((item) => item.market_type === 'GEM').length
  const newStockCount = data.filter((item) => item.is_new === 1).length
  const againLimitCount = data.filter(
    (item) => item.is_again_limit === 1
  ).length
  const stStockCount = data.filter(
    (item) =>
      item.name && (item.name.includes('ST') || item.name.includes('*ST'))
  ).length

  const topReasons = reasonKeywords(data)
  const starReasons = reasonKeywords(data, 'STAR')
  const gemReasons = reasonKeywords(data, 'GEM')

  const columns: DataColumn<HRLimitUpData>[] = [
    {
      title: '日期',
      key: 'date',
      width: 112,
      render: (record) => dayjs(record.date, 'YYYYMMDD').format('YYYY-MM-DD')
    },
    { title: '代码', key: 'code', width: 90, render: (record) => record.code },
    { title: '名称', key: 'name', width: 110, render: (record) => record.name },
    {
      title: '市场',
      key: 'market_type',
      width: 90,
      render: (record) => marketBadge(record.market_type)
    },
    {
      title: '涨停原因',
      key: 'reason_type',
      width: 180,
      render: (record) => (
        <span className="line-clamp-2">{record.reason_type || '-'}</span>
      )
    },
    {
      title: '涨停统计',
      key: 'high_days',
      width: 100,
      render: (record) => record.high_days
    },
    {
      title: '换手率',
      key: 'turnover_rate',
      width: 90,
      render: (record) => `${record.turnover_rate.toFixed(2)}%`
    },
    {
      title: '涨幅',
      key: 'change_rate',
      width: 80,
      render: (record) => (
        <span
          className={
            record.change_rate > 0
              ? 'text-red-600'
              : record.change_rate < 0
                ? 'text-emerald-600'
                : ''
          }
        >
          {record.change_rate.toFixed(2)}%
        </span>
      )
    },
    {
      title: '流通市值',
      key: 'currency_value',
      width: 110,
      render: (record) => `${(record.currency_value / 100000000).toFixed(2)}亿`
    },
    {
      title: '价格',
      key: 'latest',
      width: 80,
      render: (record) => record.latest.toFixed(2)
    },
    {
      title: '类型',
      key: 'limit_up_type',
      width: 100,
      render: (record) => record.limit_up_type
    },
    {
      title: '开板数',
      key: 'open_num',
      width: 90,
      render: (record) => record.open_num
    },
    {
      title: '首次涨停',
      key: 'first_limit_up_time',
      width: 112,
      render: (record) =>
        dayjs(Number(record.first_limit_up_time) * 1000).format('HH:mm:ss')
    },
    {
      title: '最后涨停',
      key: 'last_limit_up_time',
      width: 112,
      render: (record) =>
        dayjs(Number(record.last_limit_up_time) * 1000).format('HH:mm:ss')
    },
    {
      title: '封板率',
      key: 'limit_up_suc_rate',
      width: 100,
      render: (record) => `${(record.limit_up_suc_rate * 100).toFixed(2)}%`
    },
    {
      title: '封单量',
      key: 'order_amount',
      width: 100,
      render: (record) => `${(record.order_amount / 10000).toFixed(2)}万`
    },
    {
      title: '封单额',
      key: 'order_volume',
      width: 100,
      render: (record) =>
        `${(record.order_volume / 100 / 10000).toFixed(2)}万手`
    },
    {
      title: '新股',
      key: 'is_new',
      width: 80,
      render: (record) => (
        <Badge variant={record.is_new ? 'info' : 'outline'}>
          {record.is_new ? '新股' : '正常'}
        </Badge>
      )
    },
    {
      title: '再次涨停',
      key: 'is_again_limit',
      width: 100,
      render: (record) => (
        <Badge variant={record.is_again_limit ? 'destructive' : 'success'}>
          {record.is_again_limit ? '是' : '否'}
        </Badge>
      )
    }
  ]

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        <StatTile label="涨停数" value={totalCount} tone="blue" />
        <StatTile label="主板" value={hsCount} tone="green" />
        <StatTile label="科创板" value={starCount} tone="purple" />
        <StatTile label="创业板" value={gemCount} tone="orange" />
        <StatTile label="新股" value={newStockCount} tone="cyan" />
        <StatTile label="ST股" value={stStockCount} tone="pink" />
        <StatTile label="再次涨停" value={againLimitCount} tone="red" />
      </div>
      {(topReasons.length > 0 ||
        starReasons.length > 0 ||
        gemReasons.length > 0) && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>涨停原因高频词统计</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {topReasons.length > 0 && (
              <section>
                <div className="text-muted-foreground mb-2 text-xs">
                  全部市场
                </div>
                {keywordBadges(topReasons)}
              </section>
            )}
            {starReasons.length > 0 && (
              <section>
                <div className="text-muted-foreground mb-2 text-xs">科创板</div>
                {keywordBadges(starReasons)}
              </section>
            )}
            {gemReasons.length > 0 && (
              <section>
                <div className="text-muted-foreground mb-2 text-xs">创业板</div>
                {keywordBadges(gemReasons)}
              </section>
            )}
          </CardContent>
        </Card>
      )}
      <div className="min-h-0 flex-1">
        <DataTable
          data={data}
          columns={columns}
          loading={loading}
          rowKey={(record, index) =>
            String(record.id ?? `${record.code}-${index}`)
          }
        />
      </div>
    </div>
  )
}

export default HrTable
