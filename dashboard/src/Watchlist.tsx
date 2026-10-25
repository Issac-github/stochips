import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Drawer,
  Empty,
  Input,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { z } from 'zod'
import { fetchJson } from './data'
import type { DatasetKey } from './data'
import {
  annotationSchema,
  feedbackText,
  outcomeLabels,
  statusLabels,
  watchlistSchema,
} from './watchlistData'
import type { Annotation, Observation, WatchlistPayload } from './watchlistData'

function errorText(error: unknown) {
  return error instanceof z.ZodError
    ? '观察池格式不匹配，请检查接口版本'
    : error instanceof Error
      ? error.message
      : '观察记录暂不可用'
}

export function Watchlist({
  date,
  csrfToken,
  onDataset,
  onReview,
  reportAvailable = true,
}: {
  date: string
  csrfToken: string
  onDataset: (key: DatasetKey) => void
  onReview: () => void
  reportAvailable?: boolean
}) {
  const [payload, setPayload] = useState<WatchlistPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('active')
  const [role, setRole] = useState('all')
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [draft, setDraft] = useState<Annotation | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [savedMessage, setSavedMessage] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    fetchJson(
      `/api/watchlist?date=${encodeURIComponent(date)}`,
      controller.signal,
    )
      .then((body) => {
        const result = watchlistSchema.parse(body)
        if (result.date !== date) throw new Error('观察池日期不匹配，请重试')
        setPayload(result)
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(errorText(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [date, revision])

  const items = payload?.items ?? []
  const selected = items.find((item) => item.code === selectedCode)
  const visible = items.filter((item) => {
    const state = item.annotation.status
    if (
      status === 'active'
        ? state === 'excluded'
        : status !== 'all' && state !== status
    )
      return false
    if (role !== 'all' && !item.roles.includes(role)) return false
    return `${item.code} ${item.name} ${item.evidence.map((entry) => entry.detail).join(' ')} ${item.annotation.note}`
      .toLowerCase()
      .includes(search.toLowerCase().trim())
  })

  function open(item: Observation) {
    setSelectedCode(item.code)
    setDraft({ ...item.annotation })
    setSaveError('')
    setSavedMessage('')
  }

  async function save() {
    if (!selected || !draft || loading || error) return
    setSaving(true)
    setSaveError('')
    setSavedMessage('')
    try {
      const result = z.object({ annotation: annotationSchema }).parse(
        await fetchJson('/api/watchlist', undefined, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
          },
          body: JSON.stringify({
            date,
            code: selected.code,
            status: draft.status,
            outcome: draft.outcome,
            note: draft.note,
            revision: selected.annotation.revision,
          }),
        }),
      )
      setPayload((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) =>
                item.code === selected.code
                  ? { ...item, saved: true, annotation: result.annotation }
                  : item,
              ),
            }
          : current,
      )
      setDraft(result.annotation)
      setSavedMessage('已保存到当前飞书账号')
    } catch (reason: unknown) {
      setSaveError(errorText(reason))
    } finally {
      setSaving(false)
    }
  }

  function exportPool() {
    if (!payload) return
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json',
      }),
    )
    const link = document.createElement('a')
    link.href = url
    link.download = `stochips-watchlist-${date}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const columns: ColumnsType<Observation> = [
    {
      title: '观察个股',
      key: 'stock',
      width: 145,
      render: (_, item) => (
        <div className="stock-identity">
          <strong>{item.name}</strong>
          <span>{item.code}</span>
          {item.source_missing && <Tag color="orange">仅保存快照</Tag>}
        </div>
      ),
    },
    {
      title: '观察角色',
      key: 'roles',
      width: 125,
      render: (_, item) => (
        <Space direction="vertical" size={4}>
          {item.roles.map((value) => (
            <Tag key={value}>{value}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '入池依据',
      key: 'evidence',
      width: 310,
      render: (_, item) => (
        <ul className="observation-list">
          {item.evidence.map((entry, index) => (
            <li key={index}>{entry.detail}</li>
          ))}
        </ul>
      ),
    },
    {
      title: '观察记录',
      key: 'status',
      width: 130,
      render: (_, item) => (
        <Space direction="vertical" size={4}>
          <Tag
            color={item.annotation.status === 'watching' ? 'blue' : undefined}
          >
            {statusLabels[item.annotation.status]}
          </Tag>
          <span className="muted">
            人工：{outcomeLabels[item.annotation.outcome]}
          </span>
        </Space>
      ),
    },
    {
      title: '后续行情事实',
      key: 'feedback',
      width: 245,
      render: (_, item) => (
        <span>{payload && feedbackText(payload.feedback, item.code)}</span>
      ),
    },
    {
      title: '核对与记录',
      key: 'actions',
      width: 120,
      render: (_, item) => (
        <Button type="link" onClick={() => open(item)}>
          查看 / 编辑
        </Button>
      ),
    },
  ]

  return (
    <section className="watchlist-page">
      <div className="section-heading">
        <div>
          <Typography.Title level={3}>次日观察池</Typography.Title>
          <p>
            基于 {date}{' '}
            收盘记录汇总，按股票去重；入池表示需要核对，条件仍待验证。
          </p>
        </div>
        <Space wrap>
          <Button onClick={onReview} disabled={!reportAvailable}>
            对照完整复盘
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => setRevision((value) => value + 1)}
            disabled={saving}
          >
            重新读取
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={exportPool}
            disabled={!payload || loading || !!error}
          >
            导出观察池
          </Button>
        </Space>
      </div>
      <div className="watchlist-summary">
        <Card size="small">
          <span>来源候选</span>
          <strong>{items.length}</strong>
        </Card>
        <Card size="small">
          <span>已关注</span>
          <strong>
            {
              items.filter((item) => item.annotation.status === 'watching')
                .length
            }
          </strong>
        </Card>
        <Card size="small">
          <span>已剔除</span>
          <strong>
            {
              items.filter((item) => item.annotation.status === 'excluded')
                .length
            }
          </strong>
        </Card>
        <Card size="small">
          <span>已人工复核</span>
          <strong>
            {
              items.filter((item) => item.annotation.outcome !== 'pending')
                .length
            }
          </strong>
        </Card>
      </div>
      <Alert
        type="info"
        showIcon
        message="行情事实与人工验证分开记录"
        description={`关注、剔除和备注按飞书账号与报告日期保存。${payload?.feedback.date ? `后续首个可用行情日：${payload.feedback.date}，不保证是紧邻下一交易日。` : '尚无后续行情时保持待验证。'} 涨停与否不会自动判定策略条件满足。`}
      />
      {payload?.warnings.length ? (
        <Alert
          className="watchlist-alert"
          type="warning"
          showIcon
          message="来源数据不完整，请结合复盘核对"
          description={
            <ul>
              {payload.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
        />
      ) : null}
      {error && (
        <Alert
          className="watchlist-alert"
          type="error"
          showIcon
          message={error}
          action={
            <Button onClick={() => setRevision((value) => value + 1)}>
              重试
            </Button>
          }
        />
      )}
      <Card className="watchlist-table-card">
        <div className="watchlist-filters">
          <Input.Search
            aria-label="搜索观察个股"
            placeholder="搜索代码、名称、依据或备注"
            allowClear
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Select
            aria-label="筛选观察状态"
            value={status}
            onChange={setStatus}
            options={[
              { value: 'active', label: '待观察与关注' },
              { value: 'watching', label: '仅已关注' },
              { value: 'excluded', label: '仅已剔除' },
              { value: 'all', label: '全部状态' },
            ]}
          />
          <Select
            aria-label="筛选观察角色"
            value={role}
            onChange={setRole}
            options={[
              'all',
              ...new Set(items.flatMap((item) => item.roles)),
            ].map((value) => ({
              value,
              label: value === 'all' ? '全部角色' : value,
            }))}
          />
          <span className="muted">
            显示 {visible.length} / {items.length} 只
          </span>
        </div>
        <Table<Observation>
          rowKey="code"
          loading={loading}
          columns={columns}
          dataSource={error ? [] : visible}
          scroll={{ x: 1080 }}
          pagination={{ defaultPageSize: 10, showSizeChanger: true }}
          locale={{
            emptyText: (
              <Empty
                description={
                  error
                    ? '读取失败，请重试'
                    : items.length
                      ? '没有符合筛选条件的观察记录'
                      : '该日期暂无核心连板、助攻或前高观察来源'
                }
              />
            ),
          }}
        />
      </Card>
      <Drawer
        title={selected ? `${selected.name} · ${selected.code}` : '观察记录'}
        open={!!selected}
        width={640}
        onClose={() => {
          if (!saving) {
            setSelectedCode(null)
            setDraft(null)
          }
        }}
        maskClosable={!saving}
        closable={!saving}
        extra={saving ? <Spin size="small" /> : null}
      >
        {selected && draft && (
          <div className="observation-editor">
            <Tag>
              {date} 收盘观察 · {selected.saved ? '已保存来源快照' : '待保存'}
            </Tag>
            {selected.source_missing && (
              <Alert
                type="warning"
                message="当前来源已无此股，以下为此前保存的依据快照"
              />
            )}
            <Typography.Title level={5}>入池依据与原始来源</Typography.Title>
            {selected.evidence.map((entry, index) => (
              <Card key={index} size="small">
                <p>{entry.detail}</p>
                <Button
                  size="small"
                  disabled={selected.source_missing || !reportAvailable}
                  onClick={() => {
                    setSelectedCode(null)
                    onDataset(entry.source)
                  }}
                >
                  查看当前来源明细
                </Button>
                <details>
                  <summary>保存依据的完整字段</summary>
                  <pre className="raw-json">
                    {JSON.stringify(entry.fact, null, 2)}
                  </pre>
                </details>
              </Card>
            ))}
            <Typography.Title level={5}>风险与反证边界</Typography.Title>
            <ul className="observation-list">
              {selected.risks.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
            <Typography.Title level={5}>待验证条件</Typography.Title>
            <ul className="observation-list">
              {selected.checks.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
            <Typography.Title level={5}>后续行情事实</Typography.Title>
            <p>
              {payload?.feedback.date ?? '暂无可用日期'} ·{' '}
              {payload && feedbackText(payload.feedback, selected.code)}
            </p>
            <Typography.Title level={5}>我的观察记录</Typography.Title>
            <label>
              观察状态
              <Select
                value={draft.status}
                disabled={saving}
                onChange={(value) => setDraft({ ...draft, status: value })}
                options={Object.entries(statusLabels).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
            </label>
            <label>
              人工验证结果
              <Select
                value={draft.outcome}
                disabled={saving}
                onChange={(value) => setDraft({ ...draft, outcome: value })}
                options={Object.entries(outcomeLabels).map(
                  ([value, label]) => ({ value, label }),
                )}
              />
            </label>
            <label>
              验证依据 / 剔除原因 / 后续计划
              <Input.TextArea
                value={draft.note}
                disabled={saving}
                onChange={(event) =>
                  setDraft({ ...draft, note: event.target.value })
                }
                maxLength={2000}
                showCount
                autoSize={{ minRows: 4, maxRows: 10 }}
                placeholder="填写实际观察日期、证据、未满足的条件或继续观察的理由"
              />
            </label>
            <p className="muted">
              保存后才会保留，切换日期或关闭前请保存。剔除后可在“全部状态”中恢复。
              {selected.annotation.updated_at &&
                ` 上次保存：${new Date(selected.annotation.updated_at).toLocaleString()}`}
            </p>
            {saveError && (
              <Alert
                type="error"
                showIcon
                message={saveError}
                description="编辑内容已保留。若有版本冲突，请先重新读取，对比下方已保存备注，再保存你的修改。"
                action={
                  <Button
                    disabled={saving || loading}
                    onClick={() => setRevision((value) => value + 1)}
                  >
                    重新读取
                  </Button>
                }
              />
            )}
            {saveError && selected.saved && (
              <div className="saved-note">
                当前已保存备注：{selected.annotation.note || '无'}
              </div>
            )}
            {savedMessage && (
              <Alert type="success" showIcon message={savedMessage} />
            )}
            <Button
              type="primary"
              loading={saving}
              disabled={loading || !!error}
              onClick={() => void save()}
            >
              保存观察记录
            </Button>
          </div>
        )}
      </Drawer>
    </section>
  )
}
