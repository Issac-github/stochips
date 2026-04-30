import type React from 'react'
import { Card, Col, Row, Statistic, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Text } = Typography

interface BrokenBoardRecord {
  code: string
  name: string
  firstLimitUpDate: string
  brokenDate: string
  secondLimitUpDate: string
  firstLimitUpData: HRLimitUpData
  secondLimitUpData: HRLimitUpData
  daysBetween: number
}

interface BrokenBoardAnalysisProps {
  data?: BrokenBoardRecord[]
  loading?: boolean
}

const BrokenBoardAnalysis: React.FC<BrokenBoardAnalysisProps> = ({
  data = [],
  loading = false
}) => {
  // 统计数据
  const totalCount = data.length
  // 按市场类型统计
  const hsCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'HS'
  ).length
  const starCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'STAR'
  ).length
  const gemCount = data.filter(
    (item) => item.secondLimitUpData.market_type === 'GEM'
  ).length

  // 按间隔天数统计
  const days3Count = data.filter((item) => item.daysBetween <= 3).length
  const days46Count = data.filter(
    (item) => item.daysBetween >= 4 && item.daysBetween <= 6
  ).length
  const days7Count = data.filter((item) => item.daysBetween >= 7).length

  const columns: ColumnsType<BrokenBoardRecord> = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 80,
      align: 'center' as const,
      fixed: 'left' as const,
      sorter: (a, b) => a.code.localeCompare(b.code)
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      align: 'center' as const,
      fixed: 'left' as const
    },
    {
      title: '市场',
      key: 'market_type',
      width: 100,
      align: 'center' as const,
      render: (_, record) => {
        const marketType = record.secondLimitUpData.market_type
        const marketInfo = [
          { text: '主板', value: 'HS', color: 'green' },
          { text: '科创', value: 'STAR', color: 'purple' },
          { text: '创业板', value: 'GEM', color: 'cyan' }
        ].find((item) => item.value === marketType)
        return (
          <Tag color={marketInfo?.color || 'default'}>
            {marketInfo?.text || marketType}
          </Tag>
        )
      },
      filters: [
        { text: '主板', value: 'HS' },
        { text: '科创', value: 'STAR' },
        { text: '创业板', value: 'GEM' }
      ],
      onFilter: (value, record) =>
        record.secondLimitUpData.market_type === value,
      sorter: (a, b) => {
        const order = { STAR: 1, GEM: 2, HS: 3 }
        return (
          (order[a.secondLimitUpData.market_type] || 999) -
          (order[b.secondLimitUpData.market_type] || 999)
        )
      },
      defaultSortOrder: 'ascend' as const
    },
    {
      title: '首次涨停日期',
      dataIndex: 'firstLimitUpDate',
      key: 'firstLimitUpDate',
      width: 130,
      align: 'center' as const,
      render: (date: string) => dayjs(date, 'YYYYMMDD').format('MM-DD'),
      sorter: (a, b) => Number(a.firstLimitUpDate) - Number(b.firstLimitUpDate)
    },
    {
      title: '断板日期',
      dataIndex: 'brokenDate',
      key: 'brokenDate',
      width: 120,
      align: 'center' as const,
      render: (date: string) => (
        <Text type="warning">{dayjs(date, 'YYYYMMDD').format('MM-DD')}</Text>
      )
    },
    {
      title: '再次涨停日期',
      dataIndex: 'secondLimitUpDate',
      key: 'secondLimitUpDate',
      width: 130,
      align: 'center' as const,
      render: (date: string) => (
        <Text type="success">{dayjs(date, 'YYYYMMDD').format('MM-DD')}</Text>
      ),
      sorter: (a, b) =>
        Number(a.secondLimitUpDate) - Number(b.secondLimitUpDate)
    },
    {
      title: '间隔天数',
      dataIndex: 'daysBetween',
      key: 'daysBetween',
      width: 120,
      align: 'center' as const,
      render: (days: number) => (
        <Tag color={days <= 3 ? 'red' : days === 4 ? 'orange' : 'blue'}>
          {days}天
        </Tag>
      ),
      sorter: (a, b) => a.daysBetween - b.daysBetween,
      filters: [
        { text: '2天', value: 2 },
        { text: '3天', value: 3 },
        { text: '4天', value: 4 },
        { text: '5天', value: 5 }
      ],
      onFilter: (value, record) => record.daysBetween === value
    },
    {
      title: '首次涨停原因',
      key: 'firstReason',
      width: 150,
      align: 'center' as const,
      ellipsis: true,
      render: (_, record) => record.firstLimitUpData.reason_type || '-'
    },
    {
      title: '再次涨停原因',
      key: 'secondReason',
      width: 150,
      align: 'center' as const,
      ellipsis: true,
      render: (_, record) => record.secondLimitUpData.reason_type || '-'
    },
    {
      title: '首次开板数',
      key: 'firstOpenNum',
      width: 100,
      align: 'center' as const,
      render: (_, record) => record.firstLimitUpData.open_num
    },
    {
      title: '再次开板数',
      key: 'secondOpenNum',
      width: 120,
      align: 'center' as const,
      render: (_, record) => record.secondLimitUpData.open_num,
      sorter: (a, b) =>
        a.secondLimitUpData.open_num - b.secondLimitUpData.open_num
    },
    {
      title: '首次换手率',
      key: 'firstTurnover',
      width: 110,
      align: 'center' as const,
      render: (_, record) =>
        `${record.firstLimitUpData.turnover_rate.toFixed(2)}%`
    },
    {
      title: '再次换手率',
      key: 'secondTurnover',
      width: 120,
      align: 'center' as const,
      render: (_, record) =>
        `${record.secondLimitUpData.turnover_rate.toFixed(2)}%`,
      sorter: (a, b) =>
        a.secondLimitUpData.turnover_rate - b.secondLimitUpData.turnover_rate
    },
    {
      title: '首次涨停时间',
      key: 'firstLimitUpTime',
      width: 120,
      align: 'center' as const,
      render: (_, record) =>
        dayjs(
          Number(record.firstLimitUpData.first_limit_up_time) * 1000
        ).format('HH:mm:ss')
    },
    {
      title: '再次涨停时间',
      key: 'secondLimitUpTime',
      width: 120,
      align: 'center' as const,
      render: (_, record) =>
        dayjs(
          Number(record.secondLimitUpData.first_limit_up_time) * 1000
        ).format('HH:mm:ss')
    },
    {
      title: '流通市值',
      key: 'currencyValue',
      width: 120,
      align: 'center' as const,
      render: (_, record) =>
        `${(record.secondLimitUpData.currency_value / 100000000).toFixed(2)}亿`
    }
  ]

  return (
    <div className="flex h-full flex-col">
      <Card className="mb-3 text-center" size="small">
        <Row gutter={24}>
          <Col span={3}>
            <Statistic
              title="符合条件个股"
              value={totalCount}
              valueStyle={{ color: '#1890ff', fontSize: '18px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="主板"
              value={hsCount}
              valueStyle={{ color: '#52c41a', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="科创板"
              value={starCount}
              valueStyle={{ color: '#722ed1', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="创业板"
              value={gemCount}
              valueStyle={{ color: '#fa541c', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="3天间隔"
              value={days3Count}
              valueStyle={{ color: '#fa8c16', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="4~6天间隔"
              value={days46Count}
              valueStyle={{ color: '#faad14', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="7天间隔"
              value={days7Count}
              valueStyle={{ color: '#f4a6f4', fontSize: '16px' }}
            />
          </Col>
        </Row>
      </Card>

      <Card
        className="mb-3"
        size="small"
        title={
          <Text strong>
            说明：统计前5天内有涨停，后某交易日断板，此后又涨停的个股
          </Text>
        }
      >
        <Text type="secondary">
          模式：涨停 → 断板(未涨停) →
          再次涨停。此类个股可能显示出较强的市场韧性和资金关注度。
        </Text>
      </Card>

      <div className="flex-1 overflow-hidden">
        <Table<BrokenBoardRecord>
          className="h-full"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={false}
          rowKey={(record) =>
            `${record.code}-${record.firstLimitUpDate}-${record.secondLimitUpDate}`
          }
          scroll={{ x: 'max-content' }}
          bordered
        />
      </div>
      <style>
        {`
        .ant-spin-nested-loading, .ant-spin-container, .ant-table {
          height: 100%;
        }
         .ant-spin-container {
          display: flex;
          flex-direction: column;
        }
      `}
      </style>
    </div>
  )
}

export default BrokenBoardAnalysis
