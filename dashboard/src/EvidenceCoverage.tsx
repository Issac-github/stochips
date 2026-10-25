import { Card, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { EvidencePayload } from './strategyEvidenceData'

type Coverage = EvidencePayload['coverage'][number]
const columns: ColumnsType<Coverage> = [
  { title: '来源', dataIndex: 'label', width: 130 },
  { title: '池内记录', dataIndex: 'rows', width: 95 },
  { title: '观测日数', dataIndex: 'dates', width: 95 },
  { title: '涉及个股', dataIndex: 'stocks', width: 95 },
  {
    title: '覆盖日期',
    key: 'period',
    width: 200,
    render: (_, row) =>
      row.first_date ? `${row.first_date} 至 ${row.last_date}` : '暂无记录',
  },
  { title: '正价格记录', dataIndex: 'positive_price_rows', width: 115 },
  {
    title: '正成交量记录',
    dataIndex: 'positive_volume_rows',
    width: 155,
    render: (value: number | null) =>
      value === null ? (
        <span className="muted">此表不采集</span>
      ) : (
        <Tag color={value ? 'blue' : 'orange'}>{value}</Tag>
      ),
  },
]
export function EvidenceCoverage({ evidence }: { evidence: EvidencePayload }) {
  return (
    <Card
      size="small"
      className="evidence-coverage"
      title="数据库证据覆盖"
      extra={<Tag color="blue">查询成功 · 截至 {evidence.date}</Tag>}
    >
      <p className="category-count-note">
        以下为所选日期及之前的池内观测，未使用未来数据。观测日数不等于每股连续交易日；来源之间可能重叠。正值记录仅表示字段有大于0的值，不证明历史天量或平台成立。
      </p>
      <Table<Coverage>
        rowKey="source"
        columns={columns}
        dataSource={evidence.coverage}
        pagination={false}
        size="small"
        scroll={{ x: 885 }}
      />
    </Card>
  )
}
