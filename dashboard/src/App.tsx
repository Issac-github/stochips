import { lazy, Suspense, useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Collapse,
  DatePicker,
  Empty,
  Skeleton,
  Space,
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
import { Markdown } from './Markdown'
import { StrategyOverview } from './StrategyOverview'
import { Details } from './Details'
import { Watchlist } from './Watchlist'
import { StrategyCategories } from './StrategyCategories'
import { downloadJson, fetchJson, payloadSchema } from './data'
import type { DatasetKey, Payload } from './data'
import type { AuthState } from './AuthGate'

const dateListSchema = z.object({ dates: z.array(z.iso.date()) })
const MarketOverview = lazy(() =>
  import('./MarketOverview').then((module) => ({
    default: module.MarketOverview,
  })),
)

export default function App({
  auth,
  onAuthChange,
}: {
  auth: AuthState
  onAuthChange: () => void
}) {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [revision, setRevision] = useState(0)
  const [payload, setPayload] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateError, setDateError] = useState('')
  const [reportError, setReportError] = useState('')
  const [activeTab, setActiveTab] = useState('strategy')
  const [detailDataset, setDetailDataset] = useState<DatasetKey>('top_stocks')
  const [watchlistConcept, setWatchlistConcept] = useState('all')
  const [watchlistEntry, setWatchlistEntry] = useState(0)

  const openWatchlist = (concept = 'all') => {
    setWatchlistConcept(concept)
    setWatchlistEntry((value) => value + 1)
    setActiveTab('watchlist')
  }

  const openDataset = (key: DatasetKey) => {
    setDetailDataset(key)
    setActiveTab('details')
  }

  const logout = async () => {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'X-CSRF-Token': auth.csrf_token || '' },
    })
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
          <span className="brand-subtitle">策略复盘</span>
        </a>
        <Tag bordered={false} icon={<SafetyCertificateOutlined />}>
          行情只读 · 观察可记录
        </Tag>
        <Space className="account-bar">
          <span>{auth.user?.name || '飞书用户'}</span>
          <Button size="small" onClick={() => void logout()}>
            退出登录
          </Button>
        </Space>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">DAILY STRATEGY REVIEW</div>
            <Typography.Title level={2}>连板策略复盘</Typography.Title>
            <p>情绪与主线 · 高标与助攻 · 风险与次日验证</p>
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
                key: 'strategy',
                label: '策略复盘',
                children: (
                  <StrategyOverview
                    report={report}
                    onDataset={openDataset}
                    onReview={() => setActiveTab('review')}
                    onMarket={() => setActiveTab('overview')}
                  />
                ),
              },
              {
                key: 'categories',
                label: '策略分类',
                children: (
                  <StrategyCategories
                    report={report}
                    onWatchlist={openWatchlist}
                    onReview={() => setActiveTab('review')}
                  />
                ),
              },
              {
                key: 'watchlist',
                label: '次日观察池',
                children: (
                  <Watchlist
                    key={`${report.target_date}-${revision}-${watchlistConcept}-${watchlistEntry}`}
                    initialConcept={watchlistConcept}
                    date={report.target_date}
                    csrfToken={auth.csrf_token || ''}
                    onDataset={openDataset}
                    onReview={() => setActiveTab('review')}
                  />
                ),
              },
              {
                key: 'overview',
                label: '市场数据',
                children: (
                  <Suspense
                    fallback={<Skeleton active paragraph={{ rows: 9 }} />}
                  >
                    <MarketOverview report={report} />
                  </Suspense>
                ),
              },
              {
                key: 'details',
                label: '数据明细',
                children: (
                  <Card className="detail-card">
                    <Details
                      key={`${report.target_date}-${detailDataset}`}
                      report={report}
                      active={detailDataset}
                      onDatasetChange={setDetailDataset}
                    />
                  </Card>
                ),
              },
              {
                key: 'review',
                label: '完整复盘',
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
        ) : selectedDate && !dateError ? (
          <Watchlist
            key={`${selectedDate}-${revision}`}
            date={selectedDate}
            reportAvailable={false}
            csrfToken={auth.csrf_token || ''}
            onDataset={openDataset}
            onReview={() => setActiveTab('review')}
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
