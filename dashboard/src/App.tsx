import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Collapse,
  DatePicker,
  Empty,
  Segmented,
  Skeleton,
  Space,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import {
  BarChartOutlined,
  DownloadOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { z } from 'zod'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { barOption, Chart } from './Chart'
import { Details } from './Details'
import { downloadJson, fetchJson, payloadSchema } from './data'
import type { Payload, Report } from './data'
import type { AuthState } from './AuthGate'

const dateListSchema = z.object({ dates: z.array(z.iso.date()) })
function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}

function Overview({ report }: { report: Report }) {
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

export default function App({ auth, onAuthChange }: { auth: AuthState; onAuthChange: () => void }) {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [revision, setRevision] = useState(0)
  const [payload, setPayload] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateError, setDateError] = useState('')
  const [reportError, setReportError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': auth.csrf_token || '' } })
    setPayload(null)
    onAuthChange()
  }

  useEffect(() => {
    const controller = new AbortController()
    setDateError('')
    fetchJson('/api/dates', controller.signal)
      .then((body) => {
        const list = dateListSchema.parse(body).dates
        setDates(list)
        setSelectedDate((current) => current || list[0] || '')
        if (!list.length) setLoading(false)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setDateError(
          error instanceof z.ZodError
            ? '日期接口返回格式不正确'
            : error instanceof Error
              ? error.message
              : '无法获取日期',
        )
        setLoading(false)
      })
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    if (!selectedDate) return
    const controller = new AbortController()
    setLoading(true)
    setReportError('')
    setPayload(null)
    fetchJson(
      `/api/report?date=${encodeURIComponent(selectedDate)}`,
      controller.signal,
    )
      .then((body) => {
        const result = payloadSchema.parse(body)
        if (result.report.target_date !== selectedDate)
          throw new Error('报告日期不匹配，请刷新重试')
        setPayload(result)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setReportError(
          error instanceof z.ZodError
            ? '报告格式不匹配，请检查接口版本'
            : error instanceof Error
              ? error.message
              : '无法读取报告',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [selectedDate, revision])

  const report = payload?.report
  const review = report?.daily_review
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="StoChips 首页">
          <span className="brand-icon">
            <BarChartOutlined />
          </span>
          StoChips
          <span className="brand-divider" />
          <span className="brand-subtitle">市场观察</span>
        </a>
        <Tag bordered={false} icon={<SafetyCertificateOutlined />}>
          只读看板
        </Tag>
        <Space className="account-bar">
          <span>{auth.user?.name || '飞书用户'}</span>
          <Button size="small" onClick={() => void logout()}>退出登录</Button>
        </Space>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">DAILY MARKET REVIEW</div>
            <Typography.Title level={2}>每日市场复盘</Typography.Title>
            <p>飞书播报数据与分析，一览全貌。</p>
          </div>
          <div className="page-actions">
            <DatePicker
              allowClear={false}
              value={selectedDate ? dayjs(selectedDate) : null}
              onChange={(value) =>
                value && setSelectedDate(value.format('YYYY-MM-DD'))
              }
              cellRender={(current, info) =>
                info.type === 'date' &&
                typeof current === 'object' &&
                dates.includes(current.format('YYYY-MM-DD')) ? (
                  <Badge dot color="#3867eb">
                    {info.originNode}
                  </Badge>
                ) : (
                  info.originNode
                )
              }
            />
            <Button
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={() => setRevision((value) => value + 1)}
            >
              刷新
            </Button>
            <Button
              icon={<DownloadOutlined />}
              disabled={!payload || loading}
              onClick={() => payload && downloadJson(payload)}
            >
              导出数据
            </Button>
          </div>
        </div>
        <div className="status-strip">
          <Space wrap>
            <Badge
              status={
                loading
                  ? 'processing'
                  : report?.is_complete
                    ? 'success'
                    : 'warning'
              }
              text={
                loading
                  ? '正在读取报告'
                  : report
                    ? report.is_complete
                      ? '基础数据完整'
                      : '基础数据不完整'
                    : '等待报告数据'
              }
            />
            {report && (
              <>
                <span className="status-divider" />
                <span>
                  交易日 <strong>{report.target_date}</strong>
                </span>
                <span className="status-divider" />
                <span>
                  {review ? `分析模型 ${review.model}` : '尚未生成当日市场复盘'}
                </span>
              </>
            )}
          </Space>
          <span className="muted">数据源 · 同花顺 / 东方财富</span>
        </div>
        {dateError && (
          <Alert
            className="notice"
            type="error"
            showIcon
            message="日期列表读取失败"
            description={dateError}
            action={
              <Button onClick={() => setRevision((value) => value + 1)}>
                重试
              </Button>
            }
          />
        )}
        {reportError && (
          <Alert
            className="notice"
            type="error"
            showIcon
            message="报告读取失败"
            description={reportError}
            action={
              <Button onClick={() => setRevision((value) => value + 1)}>
                重试
              </Button>
            }
          />
        )}
        {report && report.data_warnings.length > 0 && (
          <Alert
            className="notice"
            type="warning"
            showIcon
            message="部分分析字段缺失"
            description={
              <ul>
                {report.data_warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            }
          />
        )}
        {loading ? (
          <Card className="loading-card">
            <Skeleton active paragraph={{ rows: 9 }} />
          </Card>
        ) : payload && report ? (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'overview',
                label: '市场概览',
                children: <Overview report={report} />,
              },
              {
                key: 'details',
                label: '数据明细',
                children: (
                  <Card className="detail-card">
                    <Details key={report.target_date} report={report} />
                  </Card>
                ),
              },
              {
                key: 'review',
                label: '分析结果',
                children: (
                  <Card
                    title="当日市场复盘"
                    extra={
                      review && (
                        <Space>
                          <Tag color="blue">{review.provider}</Tag>
                          <Tag>{review.model}</Tag>
                        </Space>
                      )
                    }
                  >
                    {review ? (
                      <Markdown content={review.content} />
                    ) : (
                      <Empty description="尚未生成当日市场复盘。看板仅展示已保存的分析结果。" />
                    )}
                  </Card>
                ),
              },
              {
                key: 'source',
                label: '播报原文与数据',
                children: (
                  <Collapse
                    defaultActiveKey={['material']}
                    items={[
                      {
                        key: 'material',
                        label: '飞书播报事实素材',
                        children: <Markdown content={payload.material} />,
                      },
                      {
                        key: 'previous',
                        label: '前一交易日对照（分析输入）',
                        children: (
                          <Markdown content={payload.previous_day_material} />
                        ),
                      },
                      {
                        key: 'reasons',
                        label: '涨停原因素材（分析输入）',
                        children: (
                          <Markdown content={payload.reason_material} />
                        ),
                      },
                      {
                        key: 'json',
                        label: '完整原始数据 JSON',
                        children: (
                          <pre className="raw-json">
                            {JSON.stringify(payload.report, null, 2)}
                          </pre>
                        ),
                      },
                    ]}
                  />
                ),
              },
            ]}
          />
        ) : (
          !dateError &&
          !reportError && (
            <Card>
              <Empty description="数据库中暂无播报数据，请先完成数据抓取后刷新。" />
            </Card>
          )
        )}
        <footer>
          StoChips <span>·</span> 数据记录与市场复盘 <span>·</span>{' '}
          {selectedDate || '等待交易日'}
        </footer>
      </main>
    </div>
  )
}
