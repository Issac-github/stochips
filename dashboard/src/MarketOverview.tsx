import { useMemo, useState } from 'react'
import { Card, Segmented, Statistic, Tag } from 'antd'
import { SafetyCertificateOutlined } from '@ant-design/icons'
import { barOption, Chart } from './Chart'
import type { Report } from './data'

export function MarketOverview({ report }: { report: Report }) {
  const [blockSource, setBlockSource] = useState('同花顺板块')
  const observedCount = (value: number, source: string) =>
    value > 0 ||
    report.fetch_logs.some(
      (log) => log.data_type === source && log.status === 'success',
    )
      ? value
      : null
  const continuous = Object.entries(report.continuous_distribution).sort(
    ([a], [b]) => Number(a) - Number(b),
  )
  const types = Object.entries(report.limit_up_type_distribution)
  const blocks =
    blockSource === '同花顺板块'
      ? report.top_blocks
      : report.eastmoney_industries
  const blockNames = blocks.map((item) =>
    String(item.block_name ?? item.industry_name ?? '未知'),
  )
  const blockCounts = blocks.map((item) => Number(item.stock_count ?? 0))
  const ladderOption = useMemo(
    () =>
      barOption(
        continuous.map(([name]) => `${name}板`),
        continuous.map(([, value]) => value),
      ),
    [continuous],
  )
  const typeOption = {
    color: ['#3867eb', '#55c3bf', '#8d9fec', '#edbd63', '#ef8790'],
    tooltip: { trigger: 'item', confine: true },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['50%', '44%'],
        itemStyle: { borderColor: '#fff', borderWidth: 4, borderRadius: 5 },
        label: { formatter: '{b}\n{c} 只', color: '#667085' },
        data: types.map(([name, value]) => ({ name, value })),
      },
    ],
  }
  return (
    <>
      <div className="stat-grid">
        {[
          [
            '同花顺涨停',
            observedCount(report.hr_limit_up_count, 'limit_up_pool'),
            '只',
            'red',
          ],
          [
            '东财涨停',
            observedCount(report.em_limit_up_count, 'eastmoney_zt_pool'),
            '只',
            'red',
          ],
          [
            '连板股票',
            observedCount(report.continuous_count, 'continuous_limit_up'),
            '只',
            'blue',
          ],
          [
            '最高连板',
            observedCount(report.max_continuous_days, 'continuous_limit_up'),
            '板',
            'blue',
          ],
          [
            '同花顺跌停',
            observedCount(report.lower_limit_count, 'lower_limit_pool'),
            '只',
            'green',
          ],
          [
            '热点板块',
            observedCount(report.block_count, 'block_top'),
            '个',
            'neutral',
          ],
        ].map(([title, value, suffix, color]) => (
          <Card key={String(title)} className={`stat-card ${color}`}>
            <Statistic
              title={title}
              value={Number(value)}
              suffix={value === null ? '未就绪' : suffix}
              formatter={value === null ? () => '—' : undefined}
            />
          </Card>
        ))}
      </div>
      <div className="chart-grid">
        <Card
          title="连板梯队"
          extra={<span className="muted">个股数量 / 连板高度</span>}
        >
          <Chart option={ladderOption} empty={!continuous.length} />
        </Card>
        <Card title="涨停结构" extra={<Tag bordered={false}>同花顺</Tag>}>
          <Chart option={typeOption} empty={!types.length} />
        </Card>
        <Card
          className="wide"
          title="市场热点"
          extra={
            <Segmented
              size="small"
              value={blockSource}
              onChange={setBlockSource}
              options={['同花顺板块', '东财行业']}
            />
          }
        >
          <Chart
            option={barOption(blockNames, blockCounts, true)}
            empty={!blocks.length}
          />
        </Card>
      </div>
      <div className="overview-note">
        <SafetyCertificateOutlined />
        <span>
          全部指标复用飞书播报统计口径。不同来源分别展示；图表未提供的细节可在「数据明细」查看。
        </span>
      </div>
    </>
  )
}
