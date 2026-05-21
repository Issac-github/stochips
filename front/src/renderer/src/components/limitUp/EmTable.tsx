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

interface EmTableProps {
  data?: EMLimitUpData[]
  loading?: boolean
  pagination?: {
    current?: number
    pageSize?: number
    total?: number
  }
  onChange?: (pagination: unknown, filters: unknown, sorter: unknown) => void
}

const EmTable = ({ data = [], loading = false }: EmTableProps) => {
  const totalCount = data.length
  const avgAmount =
    data.length > 0
      ? (
          data.reduce((sum, item) => sum + item.amount, 0) /
          data.length /
          10000
        ).toFixed(0)
      : '0'
  const totalAmount = (
    data.reduce((sum, item) => sum + item.amount, 0) / 100000000
  ).toFixed(2)
  const highLbcCount = data.filter((item) => item.lbc >= 3).length
  const lowLbcCount = data.filter((item) => item.lbc <= 2).length
  const zeroZbcCount = data.filter((item) => (item.zbc || 0) === 0).length
  const hasZbcCount = data.filter((item) => (item.zbc || 0) > 0).length
  const highZbcCount = data.filter((item) => (item.zbc || 0) >= 3).length

  const industryMap = new Map<string, number>()
  data.forEach((item) => {
    const industry = item.hybk || '未分类'
    industryMap.set(industry, (industryMap.get(industry) || 0) + 1)
  })
  const topIndustries = Array.from(industryMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)

  const industryStats = data.reduce(
    (acc, item) => {
      const industry = item.hybk || '未分类'
      if (!acc[industry]) {
        acc[industry] = {
          count: 0,
          totalAmount: 0,
          highLbc: 0,
          zeroZbc: 0,
          hasZbc: 0,
          totalHs: 0
        }
      }
      acc[industry].count++
      acc[industry].totalAmount += item.amount
      acc[industry].totalHs += item.hs
      if (item.lbc >= 3) acc[industry].highLbc++
      if ((item.zbc || 0) === 0) acc[industry].zeroZbc++
      if ((item.zbc || 0) > 0) acc[industry].hasZbc++
      return acc
    },
    {} as Record<
      string,
      {
        count: number
        totalAmount: number
        highLbc: number
        zeroZbc: number
        hasZbc: number
        totalHs: number
      }
    >
  )

  const sortedIndustries = Object.entries(industryStats)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 10)
  const topIndustryNames = topIndustries
    .slice(0, 10)
    .map(([industry]) => industry)

  const formatZttj = (zttj: EMLimitUpData['zttj']) => {
    const value = Array.isArray(zttj) ? zttj[0] : zttj
    return value ? `${value.ct}/${value.days}` : '-'
  }

  const columns: DataColumn<EMLimitUpData>[] = [
    {
      title: '日期',
      key: 'qdate',
      width: 112,
      render: (record) =>
        dayjs(String(record.qdate), 'YYYYMMDD').format('YYYY-MM-DD')
    },
    { title: '代码', key: 'c', width: 95, render: (record) => record.c },
    { title: '名称', key: 'n', width: 110, render: (record) => record.n },
    {
      title: '最新价',
      key: 'p',
      width: 80,
      render: (record) => (record.p / 1000).toFixed(2)
    },
    {
      title: '换手率',
      key: 'hs',
      width: 90,
      render: (record) => `${record.hs.toFixed(2)}%`
    },
    { title: '连板', key: 'lbc', width: 80, render: (record) => record.lbc },
    {
      title: '行业板块',
      key: 'hybk',
      width: 120,
      render: (record) => (
        <span
          className={
            topIndustryNames.includes(record.hybk)
              ? 'font-semibold text-amber-600'
              : ''
          }
        >
          {record.hybk || '-'}
        </span>
      )
    },
    {
      title: '涨停统计',
      key: 'zttj',
      width: 100,
      render: (record) => formatZttj(record.zttj)
    },
    {
      title: '涨跌幅',
      key: 'zdp',
      width: 90,
      render: (record) => `${record.zdp.toFixed(2)}%`
    },
    {
      title: '炸板数',
      key: 'zbc',
      width: 90,
      render: (record) => (
        <span
          className={
            (record.zbc || 0) === 0
              ? 'text-emerald-600'
              : (record.zbc || 0) <= 2
                ? 'text-amber-600'
                : 'font-semibold text-red-600'
          }
        >
          {record.zbc || 0}
        </span>
      )
    },
    {
      title: '流通市值',
      key: 'ltsz',
      width: 100,
      render: (record) => `${(record.ltsz / 100000 / 1000).toFixed(2)}亿`
    },
    {
      title: '总市值',
      key: 'tshare',
      width: 100,
      render: (record) => `${(record.tshare / 100000 / 1000).toFixed(2)}亿`
    },
    {
      title: '交易额',
      key: 'amount',
      width: 100,
      render: (record) => `${(record.amount / 10000).toFixed(0)}万`
    },
    {
      title: '首封时间',
      key: 'fbt',
      width: 90,
      render: (record) =>
        dayjs(String(record.fbt).padStart(6, '0'), 'Hmmss').format('HH:mm:ss')
    },
    {
      title: '尾封时间',
      key: 'lbt',
      width: 90,
      render: (record) =>
        dayjs(String(record.lbt).padStart(6, '0'), 'Hmmss').format('HH:mm:ss')
    },
    {
      title: '资金',
      key: 'fund',
      width: 100,
      render: (record) => `${(record.fund / 10000).toFixed(0)}万`
    }
  ]

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        <StatTile label="总数量" value={totalCount} tone="blue" />
        <StatTile label="平均金额" value={avgAmount} suffix="万" tone="green" />
        <StatTile
          label="总金额"
          value={totalAmount}
          suffix="亿"
          tone="purple"
        />
        <StatTile label="高连板" value={highLbcCount} tone="red" />
        <StatTile label="低连板" value={lowLbcCount} tone="orange" />
        <StatTile label="无炸板" value={zeroZbcCount} tone="green" />
        <StatTile label="高炸板" value={highZbcCount} tone="red" />
        <StatTile
          label="炸板率"
          value={
            totalCount > 0 ? ((hasZbcCount / totalCount) * 100).toFixed(1) : '0'
          }
          suffix="%"
          tone="pink"
        />
      </div>

      {topIndustries.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>行业板块涨停数量统计</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {topIndustries.map(([industry, count], index) => (
              <Badge
                key={industry}
                variant={
                  index < 3
                    ? 'destructive'
                    : index < 8
                      ? 'warning'
                      : index < 15
                        ? 'info'
                        : 'outline'
                }
              >
                <span className="font-semibold">{industry}</span>
                <span className="ml-1 opacity-70">({count})</span>
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {sortedIndustries.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>行业板块统计</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 lg:grid-cols-5">
            {sortedIndustries.map(([industry, stats]) => (
              <div key={industry} className="rounded-md border p-2 text-xs">
                <div className="mb-2 font-semibold">{industry}</div>
                <div className="text-muted-foreground grid grid-cols-2 gap-1">
                  <span>数量 {stats.count}</span>
                  <span>
                    均额 {(stats.totalAmount / stats.count / 10000).toFixed(0)}
                    万
                  </span>
                  <span>高连 {stats.highLbc}</span>
                  <span>无炸 {stats.zeroZbc}</span>
                  <span>均手 {(stats.totalHs / stats.count).toFixed(1)}%</span>
                  <span>
                    炸板{' '}
                    {stats.count > 0
                      ? ((stats.hasZbc / stats.count) * 100).toFixed(1)
                      : '0'}
                    %
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="min-h-0 flex-1">
        <DataTable
          data={data}
          columns={columns}
          loading={loading}
          rowKey={(record, index) =>
            String(record.id ?? `${record.c}-${index}`)
          }
        />
      </div>
    </div>
  )
}

export default EmTable
