import { useState } from 'react'
import { Alert, Button, Card, Collapse, Space, Tag, Typography } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import type { DatasetKey, Report } from './data'
import { datasets } from './data'
import { Details } from './Details'
import { Markdown } from './Markdown'
import { reviewSections, splitReview } from './review'
import { strategyCatalog } from './strategyCatalog'
import type { StrategyGroup } from './strategyCatalog'

function CategoryContent({
  group,
  report,
  onWatchlist,
  onReview,
}: {
  group: StrategyGroup
  report: Report
  onWatchlist: (concept?: string) => void
  onReview: () => void
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
          description="当前前高观察仅记录历史连板段价格比较。连续日线、历史成交量和整理区间尚未接入，以下平台模式均待人工核对。大/小龙头描述前期地位，大/小平台描述整理结构。"
        />
      )}
      <div className="concept-card-grid">
        {concepts.map((concept) => (
          <Card key={concept.key} size="small" className="concept-card">
            <div className="concept-card-heading">
              <Typography.Title level={4}>{concept.label}</Typography.Title>
              <Tag color="orange">待人工核对</Tag>
            </div>
            <p>{concept.focus}</p>
            <div className="concept-missing">
              <span>需补充或人工核实</span>
              <ul>
                {concept.missing.map((missing) => (
                  <li key={missing}>{missing}</li>
                ))}
              </ul>
            </div>
            <Button type="link" onClick={() => onWatchlist(concept.key)}>
              查看此类人工标记 <ArrowRightOutlined />
            </Button>
          </Card>
        ))}
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
      />
      <Card size="small" className="category-boundary">
        <Space wrap>
          <Tag color="blue">已有事实</Tag>
          <span>来源表中的记录</span>
          <Tag color="purple">人工分类</Tag>
          <span>记录你的观察方向</span>
          <Tag color="orange">待验证</Tag>
          <span>仍需量价或盘中证据</span>
        </Space>
      </Card>
    </section>
  )
}
