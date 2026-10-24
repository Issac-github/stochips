import { Button, Card, Empty, Space, Table, Tabs, Tag, Typography } from 'antd'
import { ArrowRightOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { DatasetKey, JsonValue, Report, Row } from './data'
import { Markdown } from './Markdown'
import { splitReview } from './review'

function text(value: JsonValue | undefined) {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : '—'
}

function StockName({ value }: { value: JsonValue | undefined }) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return <>—</>
  return (
    <div className="stock-identity">
      <strong>{text(value.name)}</strong>
      <span>{text(value.code)}</span>
    </div>
  )
}

const stockColumns: ColumnsType<Row> = [
  {
    title: '观察个股',
    key: 'stock',
    width: 150,
    render: (_, row) => <StockName value={row} />,
  },
  {
    title: '连板高度',
    dataIndex: 'continuous_days',
    width: 95,
    render: (value: JsonValue) => <Tag color="blue">{text(value)} 板</Tag>,
  },
  { title: '所属板块', dataIndex: 'block_name', width: 150, render: text },
  { title: '封板时间', dataIndex: 'limit_up_time', width: 120, render: text },
  {
    title: '换手率',
    dataIndex: 'turnover_rate',
    width: 105,
    render: (value: JsonValue) =>
      typeof value === 'number' ? `${value}%` : '—',
  },
  {
    title: '涨停原因',
    key: 'reason',
    width: 240,
    render: (_, row) => text(row.reason_info || row.reason),
  },
]
const feedbackColumns: ColumnsType<Row> = [
  {
    title: '昨日高标',
    key: 'stock',
    width: 150,
    render: (_, row) => <StockName value={row} />,
  },
  {
    title: '昨日高度',
    dataIndex: 'previous_continuous_days',
    width: 110,
    render: (value: JsonValue) => `${text(value)} 板`,
  },
  { title: '今日收盘反馈', dataIndex: 'feedback', render: text },
]
const assistColumns: ColumnsType<Row> = [
  {
    title: '被观察高标',
    dataIndex: 'leader',
    width: 150,
    render: (value: JsonValue) => <StockName value={value} />,
  },
  {
    title: '助攻候选',
    dataIndex: 'stock',
    width: 150,
    render: (value: JsonValue) => <StockName value={value} />,
  },
  { title: '板型', dataIndex: 'board_type', width: 110, render: text },
  {
    title: '相同属性',
    dataIndex: 'shared_reason_tags',
    width: 180,
    render: (value: JsonValue) =>
      Array.isArray(value) ? value.map(text).join(' / ') || '—' : '—',
  },
  {
    title: '相同板块',
    dataIndex: 'shared_blocks',
    width: 180,
    render: (value: JsonValue) =>
      Array.isArray(value) ? value.map(text).join(' / ') || '—' : '—',
  },
  {
    title: '高标首次封板',
    dataIndex: 'leader_first_limit_up_time',
    width: 135,
    render: text,
  },
  {
    title: '候选末次封板',
    dataIndex: 'last_limit_up_time',
    width: 135,
    render: text,
  },
]

function Evidence({
  report,
  onDataset,
}: {
  report: Report
  onDataset: (key: DatasetKey) => void
}) {
  const groups: {
    key: DatasetKey
    title: string
    note: string
    rows: Row[]
    columns: ColumnsType<Row>
    width: number
  }[] = [
    {
      key: 'top_stocks',
      title: '核心连板',
      note: '高度是观察入口，不能单独确认龙头地位；换手率不等于历史天量。',
      rows: report.top_stocks,
      columns: stockColumns,
      width: 900,
    },
    {
      key: 'previous_high_feedback',
      title: '昨日高标反馈',
      note: '“未进入涨停池”仅描述收盘池记录，不等于跌停或严重负反馈。',
      rows: report.previous_high_feedback,
      columns: feedbackColumns,
      width: 520,
    },
    {
      key: 'leader_assists',
      title: '助攻候选',
      note: '收盘池回溯，含非一字及首板候选；封板更早不代表当时仍有效，也不证明因果带动。',
      rows: report.leader_assists,
      columns: assistColumns,
      width: 1050,
    },
  ]
  return (
    <section className="strategy-evidence" aria-labelledby="evidence-heading">
      <div className="section-heading">
        <div>
          <Typography.Title level={3} id="evidence-heading">
            核对关键证据
          </Typography.Title>
          <p>对照高标地位、昨日反馈与助攻记录，复核上方研判。</p>
        </div>
      </div>
      <Card className="evidence-card">
        <Tabs
          items={groups.map((group) => ({
            key: group.key,
            label: (
              <Space size={6}>
                {group.title}
                <Tag bordered={false}>{group.rows.length}</Tag>
              </Space>
            ),
            children: (
              <>
                <div className="evidence-toolbar">
                  <p>{group.note}</p>
                  <Button
                    type="link"
                    icon={<ArrowRightOutlined />}
                    onClick={() => onDataset(group.key)}
                  >
                    查看全部字段
                  </Button>
                </div>
                <Table<Row>
                  size="small"
                  columns={group.columns}
                  dataSource={group.rows}
                  rowKey={(row, index) => `${text(row.code)}-${index}`}
                  scroll={{ x: group.width }}
                  pagination={{
                    defaultPageSize: 6,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                  }}
                  locale={{
                    emptyText: (
                      <Empty description="当日暂无记录，不能据此认定相关条件已满足。" />
                    ),
                  }}
                />
              </>
            ),
          }))}
        />
      </Card>
    </section>
  )
}

function VerificationBoundary() {
  return (
    <Card
      className="verification-card"
      size="small"
      title={
        <Space>
          <ClockCircleOutlined />
          仍需核实的条件
        </Space>
      }
    >
      <dl>
        <div>
          <dt>天量 / 倍量</dt>
          <dd>需历史成交量对照；当前换手数据无法确认。</dd>
        </div>
        <div>
          <dt>竞价 / 开盘缺口</dt>
          <dd>待下一交易日观察，收盘报告不能提前确认。</dd>
        </div>
        <div>
          <dt>弱转强 / 助攻延续</dt>
          <dd>需竞价与盘中承接验证，候选记录不等于成立。</dd>
        </div>
      </dl>
    </Card>
  )
}

export function StrategyOverview({
  report,
  onDataset,
  onReview,
  onMarket,
}: {
  report: Report
  onDataset: (key: DatasetKey) => void
  onReview: () => void
  onMarket: () => void
}) {
  const review = report.daily_review
  const sections = review ? splitReview(review.content) : null
  return (
    <>
      <div className="section-heading strategy-heading">
        <div>
          <Typography.Title level={3}>今日研判</Typography.Title>
          <p>先看情绪与主线，再核对高标；用风险反证约束次日观察。</p>
        </div>
        {review && (
          <Space wrap>
            <Tag bordered={false}>已保存的收盘分析</Tag>
            <Button type="link" onClick={onReview}>
              完整复盘 <ArrowRightOutlined />
            </Button>
          </Space>
        )}
      </div>
      {sections ? (
        <div className="strategy-layout">
          <div className="strategy-main">
            <Card
              className="review-card sentiment-card"
              title={
                <Space>
                  <span className="section-index">01</span>情绪定位
                </Space>
              }
            >
              <Markdown content={sections.sentiment} />
            </Card>
            <Card
              className="review-card themes-card"
              title={
                <Space>
                  <span className="section-index">02</span>主线与梯队
                </Space>
              }
            >
              <Markdown content={sections.themes} />
            </Card>
            <Card
              className="review-card leaders-card"
              title={
                <Space>
                  <span className="section-index">03</span>龙头与助攻
                </Space>
              }
            >
              <Markdown content={sections.leaders} />
            </Card>
          </div>
          <aside className="strategy-aside" aria-label="风险与次日验证">
            <Card
              className="review-card risk-card"
              title={
                <Space>
                  <span className="section-index">04</span>风险与反证
                </Space>
              }
            >
              <Markdown content={sections.risk} />
            </Card>
            <Card
              className="review-card next-day-card"
              title={
                <Space>
                  <span className="section-index">05</span>次日验证清单
                </Space>
              }
            >
              <span className="pending-label">以下条件尚待下一交易日确认</span>
              <Markdown content={sections.nextDay} />
            </Card>
            <VerificationBoundary />
          </aside>
        </div>
      ) : (
        <div className="strategy-layout">
          <Card className="review-card">
            {review ? (
              <>
                <Tag className="review-format-note">历史格式 · 完整原文</Tag>
                <Markdown content={review.content} />
              </>
            ) : (
              <Empty description="尚未保存当日复盘。下方保留事实记录，暂不生成策略结论。">
                <Button onClick={onMarket}>先看市场数据</Button>
              </Empty>
            )}
          </Card>
          <aside>
            <VerificationBoundary />
          </aside>
        </div>
      )}
      <Evidence
        key={report.target_date}
        report={report}
        onDataset={onDataset}
      />
    </>
  )
}
