import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Collapse,
  Skeleton,
  Space,
  Tag,
  Typography,
} from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import type { DatasetKey, Report } from './data'
import { datasets, fetchJson, labels } from './data'
import { Details } from './Details'
import { Markdown } from './Markdown'
import { reviewSections, splitReview } from './review'
import { strategyCatalog } from './strategyCatalog'
import type { StrategyGroup } from './strategyCatalog'
import { EvidenceCoverage } from './EvidenceCoverage'
import {
  capabilityLabels,
  evidenceSchema,
  statusLabels,
} from './strategyEvidenceData'
import type { EvidencePayload } from './strategyEvidenceData'

const aiStatusLabels = {
  confirmed: 'AI 判断：证据支持',
  candidate: 'AI 判断：候选',
  insufficient_evidence: 'AI 判断：证据不足',
  conflicting_evidence: 'AI 判断：证据有冲突',
  not_applicable: 'AI 判断：当日不适用',
} as const

const confidenceLabels = {
  high: '较高',
  medium: '中等',
  low: '较低',
  unavailable: '无法评估',
} as const

function CategoryContent({
  group,
  report,
  onWatchlist,
  onReview,
  evidence,
  loading,
}: {
  group: StrategyGroup
  report: Report
  onWatchlist: (concept?: string) => void
  onReview: () => void
  evidence: EvidencePayload | null
  loading: boolean
}) {
  const [dataset, setDataset] = useState<DatasetKey>(group.datasets[0])
  const sections = report.daily_review
    ? splitReview(report.daily_review.content)
    : null
  const reviewKeys = group.reviewKeys.includes('risk')
    ? group.reviewKeys
    : [...group.reviewKeys, 'risk' as const]
  const concepts = strategyCatalog.concepts.filter(
    (concept) => concept.group === group.key,
  )
  return (
    <>
      <div className="category-title-row">
        <div>
          <Typography.Title level={3}>{group.title}</Typography.Title>
          <p>{group.description}</p>
        </div>
        <Button onClick={() => onWatchlist()}>
          到观察池添加人工分类 <ArrowRightOutlined />
        </Button>
      </div>
      {group.key === 'platform' && (
        <Alert
          type="info"
          showIcon
          message="平台形态单独核对"
          description="前高观察仅记录历史连板段价格比较，不等于平台形态匹配。以下状态分别说明已查到的关联观测、必需证据覆盖和完整模式识别进度。大/小龙头描述前期地位，大/小平台描述整理结构。"
        />
      )}
      <div className="concept-card-grid">
        {concepts.map((concept) => {
          const result = evidence?.concepts.find(
            (item) => item.key === concept.key,
          )
          const aiResult = report.daily_review?.strategy_evidence?.concepts.find(
            (item) => item.key === concept.key,
          )
          return (
            <Card key={concept.key} size="small" className="concept-card">
              <div className="concept-card-heading">
                <Typography.Title level={4}>{concept.label}</Typography.Title>
                <Tag
                  color={
                    result?.status === 'facts_available'
                      ? 'blue'
                      : result?.status === 'candidate'
                        ? 'cyan'
                        : result?.status === 'manual'
                          ? 'purple'
                          : 'orange'
                  }
                >
                  {result
                    ? statusLabels[result.status]
                    : loading
                      ? '正在查询'
                      : '状态未获取'}
                </Tag>
              </div>
              <p>{concept.focus}</p>
              {aiResult ? (
                <div className="concept-ai-result">
                  <Space wrap>
                    <Tag color={aiResult.status === 'confirmed' ? 'green' : 'blue'}>
                      {aiStatusLabels[aiResult.status]}
                    </Tag>
                    <Tag>置信度：{confidenceLabels[aiResult.confidence]}</Tag>
                  </Space>
                  <p>{aiResult.summary}</p>
                  {aiResult.evidence.length > 0 && (
                    <div>
                      <strong>引用事实</strong>
                      <ul>
                        {aiResult.evidence.map((item, index) => (
                          <li key={`${item.source}-${item.reference}-${index}`}>
                            {datasets.find(([key]) => key === item.source)?.[1] ?? item.source}
                            {item.reference !== 'aggregate' ? ` · ${item.reference}` : ''} ·{' '}
                            {labels[item.field] ?? item.field}={item.value}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {aiResult.counter_evidence.length > 0 && (
                    <div><strong>反证与限制</strong><ul>{aiResult.counter_evidence.map((item) => <li key={item}>{item}</li>)}</ul></div>
                  )}
                  {aiResult.missing_data.length > 0 && (
                    <div><strong>缺失数据</strong><ul>{aiResult.missing_data.map((item) => <li key={item}>{item}</li>)}</ul></div>
                  )}
                </div>
              ) : (
                <Alert
                  className="concept-ai-result"
                  type="info"
                  showIcon
                  message={report.daily_review ? '当日复盘未包含结构化概念判断' : '当日尚无 AI 复盘'}
                  description="不会在打开看板时额外调用模型。"
                />
              )}
              {result && (
                <>
                  <p className="concept-recognition">{result.explanation}</p>
                  <div className="concept-observations">
                    {result.source_counts.map((source) => (
                      <span key={source.dataset}>
                        {datasets.find(([key]) => key === source.dataset)?.[1]}{' '}
                        {source.rows} 条
                      </span>
                    ))}
                    {result.stock_count > 0 && (
                      <strong>
                        关联观测 {result.stock_count} 只
                        {result.kind === 'pattern' ? '（非模式匹配）' : ''}
                      </strong>
                    )}
                  </div>
                  <div className="concept-requirements">
                    {result.requirements.map((requirement) => (
                      <div key={requirement.key}>
                        <Space wrap>
                          <strong>{requirement.label}</strong>
                          <Tag
                            color={
                              requirement.state === 'available'
                                ? 'blue'
                                : 'orange'
                            }
                          >
                            {capabilityLabels[requirement.state]}
                          </Tag>
                        </Space>
                        <p>{requirement.detail}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
              <div className="concept-missing">
                <details>
                  <summary>概念核对清单</summary>
                  <ul>
                    {concept.checks.map((missing) => (
                      <li key={missing}>{missing}</li>
                    ))}
                  </ul>
                </details>
              </div>
              <Button type="link" onClick={() => onWatchlist(concept.key)}>
                查看此类人工标记 <ArrowRightOutlined />
              </Button>
            </Card>
          )
        })}
      </div>
      <div className="category-source-strip" aria-label="关联数据覆盖">
        {group.datasets.map((key) => (
          <button
            key={key}
            onClick={() => setDataset(key)}
            aria-pressed={dataset === key}
            className={dataset === key ? 'selected' : ''}
          >
            <span>{datasets.find(([value]) => value === key)?.[1]}</span>
            <strong>{report[key].length}</strong>
            <small>{report[key].length ? '条来源记录' : '当日无记录'}</small>
          </button>
        ))}
      </div>
      <p className="category-count-note">
        记录数仅表示关联来源的条数，各来源可能重叠；不代表此策略已匹配、独立个股数量或有效信号。
      </p>
      <Card
        className="detail-card category-evidence"
        title="关联事实 · 核对原始字段"
      >
        <Details
          key={`${report.target_date}-${dataset}`}
          report={report}
          active={dataset}
          onDatasetChange={setDataset}
          datasetKeys={group.datasets}
        />
      </Card>
      <Collapse
        className="category-review"
        items={[
          {
            key: 'review',
            label: '对照已保存复盘',
            children: report.daily_review ? (
              sections ? (
                <div className="category-review-sections">
                  {reviewKeys.map((key) => (
                    <section key={key}>
                      <Typography.Title level={4}>
                        {
                          reviewSections.find((section) => section.key === key)
                            ?.title
                        }
                      </Typography.Title>
                      <Markdown content={sections[key]} />
                    </section>
                  ))}
                  <Button onClick={onReview}>查看完整复盘与所有反证</Button>
                </div>
              ) : (
                <>
                  <Tag>非标准格式 · 保留完整原文</Tag>
                  <Markdown content={report.daily_review.content} />
                </>
              )
            ) : (
              <Alert
                type="info"
                message="尚未保存当日复盘，不能据此确认情绪、主线或模式。"
              />
            ),
          },
        ]}
      />
    </>
  )
}

export function StrategyCategories({
  report,
  onWatchlist,
  onReview,
}: {
  report: Report
  onWatchlist: (concept?: string) => void
  onReview: () => void
}) {
  const [active, setActive] = useState('platform')
  const [evidence, setEvidence] = useState<EvidencePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const date = report.target_date
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setEvidence(null)
    fetchJson(
      `/api/strategy-evidence?date=${encodeURIComponent(date)}`,
      controller.signal,
    )
      .then((body) => {
        const result = evidenceSchema.parse(body)
        if (result.date !== date) throw new Error('证据日期不匹配，请重试')
        setEvidence(result)
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(
            reason instanceof Error ? reason.message : '证据状态读取失败',
          )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [date, revision])
  const group =
    strategyCatalog.groups.find((item) => item.key === active) ??
    strategyCatalog.groups[0]
  return (
    <section className="strategy-categories">
      <div className="section-heading">
        <div>
          <Typography.Title level={3}>按策略概念复盘</Typography.Title>
          <p>选择类别，查看核对重点、现有证据和人工观察记录。</p>
        </div>
        <Tag bordered={false}>收盘事实 · 已保存分析 · 人工分类</Tag>
      </div>
      {loading ? (
        <Card size="small">
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>
      ) : error ? (
        <Alert
          type="error"
          showIcon
          message="证据状态读取失败"
          description="当前不显示模式判定；请确认后端接口版本与数据库连接后重试。"
          action={
            <Button onClick={() => setRevision((value) => value + 1)}>
              重试
            </Button>
          }
        />
      ) : (
        evidence?.date === date && <EvidenceCoverage evidence={evidence} />
      )}
      <nav className="category-navigation" aria-label="策略概念分类">
        {strategyCatalog.groups.map((item, index) => (
          <button
            key={item.key}
            aria-pressed={group.key === item.key}
            className={group.key === item.key ? 'selected' : ''}
            onClick={() => setActive(item.key)}
          >
            <span className="category-number">0{index + 1}</span>
            <strong>{item.title}</strong>
            <small>
              {
                strategyCatalog.concepts.filter(
                  (concept) => concept.group === item.key,
                ).length
              }{' '}
              个核对概念
            </small>
          </button>
        ))}
      </nav>
      <CategoryContent
        key={`${report.target_date}-${group.key}`}
        group={group}
        report={report}
        onWatchlist={onWatchlist}
        onReview={onReview}
        evidence={evidence?.date === date ? evidence : null}
        loading={loading}
      />
      <Card size="small" className="category-boundary">
        <Space wrap>
          <Tag color="blue">已有事实</Tag>
          <span>来源表中的记录</span>
          <Tag color="purple">人工分类</Tag>
          <span>记录你的观察方向</span>
          <Tag color="orange">数据有缺口</Tag>
          <span>字段无有效值或所需接口未接入；不等于数据库完全没有行情</span>
        </Space>
      </Card>
    </section>
  )
}
