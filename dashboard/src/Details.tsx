import { useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Input,
  Modal,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { datasets, labels } from './data'
import type { DatasetKey, JsonValue, Report, Row } from './data'

function Value({ value }: { value: JsonValue | undefined }) {
  if (value === null || value === undefined || value === '')
    return <span className="muted">—</span>
  if (typeof value === 'boolean')
    return <Tag color={value ? 'blue' : undefined}>{value ? '是' : '否'}</Tag>
  if (Array.isArray(value))
    return value.length ? (
      <div className="nested-list">
        {value.map((item, index) => (
          <Value key={index} value={item} />
        ))}
      </div>
    ) : (
      <span className="muted">暂无</span>
    )
  if (typeof value === 'object')
    return (
      <Descriptions
        column={1}
        size="small"
        items={Object.entries(value).map(([key, item]) => ({
          key,
          label: labels[key] ?? key,
          children: <Value value={item} />,
        }))}
      />
    )
  return <span className="cell-value">{String(value)}</span>
}

export function Details({ report }: { report: Report }) {
  const [active, setActive] = useState<DatasetKey>('top_blocks')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Row | null>(null)
  const rows = report[active]
  const current = datasets.find(([key]) => key === active)!
  const filtered = useMemo(
    () =>
      rows.filter((row) =>
        JSON.stringify(row).toLowerCase().includes(search.toLowerCase()),
      ),
    [rows, search],
  )
  const keys = useMemo(() => [...new Set(rows.flatMap(Object.keys))], [rows])
  const columns: ColumnsType<Row> = keys.map((key) => ({
    title: labels[key] ?? key,
    key,
    dataIndex: key,
    width: key.includes('reason') || key === 'error_message' ? 260 : 150,
    render: (value: JsonValue, row) =>
      value !== null && typeof value === 'object' ? (
        <Button type="link" size="small" onClick={() => setSelected(row)}>
          查看明细{Array.isArray(value) ? ` (${value.length})` : ''}
        </Button>
      ) : (
        <Value value={value} />
      ),
    sorter: (a, b) =>
      typeof a[key] === 'number' && typeof b[key] === 'number'
        ? Number(a[key]) - Number(b[key])
        : String(a[key] ?? '').localeCompare(String(b[key] ?? ''), 'zh-CN'),
  }))
  return (
    <div className="details-layout">
      <div className="dataset-menu" role="navigation" aria-label="播报数据分类">
        {datasets.map(([key, title]) => (
          <button
            key={key}
            className={active === key ? 'selected' : ''}
            onClick={() => {
              setActive(key)
              setSearch('')
            }}
          >
            <span>{title}</span>
            <span className="dataset-count">{report[key].length}</span>
          </button>
        ))}
      </div>
      <div className="dataset-content">
        <div className="table-toolbar">
          <div>
            <Typography.Title level={4}>{current[1]}</Typography.Title>
            <span className="muted">{current[2]}</span>
          </div>
          <Input.Search
            allowClear
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索代码、名称或原因"
            style={{ maxWidth: 300 }}
          />
        </div>
        {active === 'leader_assists' && (
          <Alert
            type="info"
            showIcon
            message="收盘池回溯：首次封板更早不代表龙头封板时仍有效，也不证明因果带动。"
          />
        )}
        <Table<Row>
          key={`${active}-${report.target_date}-${search}`}
          size="middle"
          columns={columns}
          dataSource={filtered}
          rowKey={(row) => String(rows.indexOf(row))}
          scroll={{ x: Math.max(650, columns.length * 155) }}
          locale={{
            emptyText: (
              <Empty
                description={search ? '未找到匹配记录' : '当日暂无此项数据'}
              />
            ),
          }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </div>
      <Modal
        open={selected !== null}
        onCancel={() => setSelected(null)}
        footer={null}
        title="完整记录"
        width={820}
      >
        {selected && <Value value={selected} />}
      </Modal>
    </div>
  )
}
