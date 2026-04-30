import type React from 'react'
import {
  Card,
  Col,
  Collapse,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Text } = Typography

interface HrTableProps {
  data?: HRLimitUpData[]
  loading?: boolean
  pagination?: {
    current: number
    pageSize: number
    total: number
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChange?: (pagination: any, filters: any, sorter: any) => void
}

const HrTable: React.FC<HrTableProps> = ({
  data = [],
  loading = false,
  onChange
}) => {
  // 计算统计数据
  const totalCount = data.length
  const hsCount = data.filter((item) => item.market_type === 'HS').length
  const starCount = data.filter((item) => item.market_type === 'STAR').length
  const gemCount = data.filter((item) => item.market_type === 'GEM').length
  const newStockCount = data.filter((item) => item.is_new === 1).length
  const againLimitCount = data.filter(
    (item) => item.is_again_limit === 1
  ).length
  // 统计ST股数量（股票名称包含ST或*ST的股票）
  const stStockCount = data.filter(
    (item) =>
      item.name && (item.name.includes('ST') || item.name.includes('*ST'))
  ).length

  // 统计涨停原因高频词（全部）
  const getReasonKeywords = (marketFilter?: string) => {
    const reasonMap = new Map<string, number>()
    data
      .filter((item) => !marketFilter || item.market_type === marketFilter)
      .forEach((item) => {
        if (item.reason_type) {
          // 使用多种分隔符分割涨停原因
          const keywords = item.reason_type
            .split(/[+、,，；;|&\s]+/)
            .filter((keyword) => keyword.trim().length > 0)
            .map((keyword) => keyword.trim())

          keywords.forEach((keyword) => {
            if (keyword.length >= 2) {
              // 过滤掉单字符
              reasonMap.set(keyword, (reasonMap.get(keyword) || 0) + 1)
            }
          })
        }
      })
    // 转换为数组并按频次排序
    return Array.from(reasonMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20) // 显示前20个高频词
  }

  const topReasons = getReasonKeywords()
  const starReasons = getReasonKeywords('STAR') // 科创板高频词
  const gemReasons = getReasonKeywords('GEM') // 创业板高频词

  const columns: ColumnsType<HRLimitUpData> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      align: 'center' as const,
      render: (date: string) => dayjs(date, 'YYYYMMDD').format('YYYY-MM-DD'),
      sorter: (a, b) => Number(a.date) - Number(b.date)
    },
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 90,
      align: 'center' as const,
      sorter: (a, b) => a.code.localeCompare(b.code)
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
      align: 'center' as const,
      ellipsis: true
    },
    {
      title: '市场类型',
      dataIndex: 'market_type',
      key: 'market_type',
      width: 120,
      align: 'center' as const,
      filters: [
        { text: '主板', value: 'HS' },
        { text: '科创', value: 'STAR' },
        { text: '创业板', value: 'GEM' }
      ],
      onFilter: (value, record) => record.market_type === value,
      render: (text) => {
        const marketInfo = [
          { text: '主板', value: 'HS', color: 'green' },
          { text: '科创', value: 'STAR', color: 'purple' },
          { text: '创业板', value: 'GEM', color: 'cyan' }
        ].find((item) => item.value === text)
        return (
          <Tag color={marketInfo?.color || 'default'}>
            {marketInfo?.text || text}
          </Tag>
        )
      },
      sorter: (a, b) => {
        const order = { STAR: 1, GEM: 2, HS: 3 }
        return (order[a.market_type] || 999) - (order[b.market_type] || 999)
      },
      defaultSortOrder: 'ascend' as const
    },
    {
      title: '涨停原因',
      dataIndex: 'reason_type',
      key: 'reason_type',
      width: 150,
      align: 'center' as const,
      ellipsis: {
        showTitle: false
      },
      render: (text: string, record: HRLimitUpData) => {
        if (!text) return '-'

        // 根据市场类型获取对应的高频词列表
        let relevantKeywords: string[] = []
        let highlightColor = '#f5222d'
        let backgroundColor = '#fff1f0'

        if (record.market_type === 'STAR') {
          relevantKeywords = starReasons
            .slice(0, 10)
            .map(([keyword]) => keyword)
          highlightColor = '#722ed1'
          backgroundColor = '#f9f0ff'
        } else if (record.market_type === 'GEM') {
          relevantKeywords = gemReasons.slice(0, 10).map(([keyword]) => keyword)
          highlightColor = '#13c2c2'
          backgroundColor = '#e6fffb'
        } else {
          relevantKeywords = topReasons.slice(0, 10).map(([keyword]) => keyword)
        }

        // 对涨停原因进行高亮处理
        let highlightedText = text
        relevantKeywords.forEach((keyword) => {
          if (text.includes(keyword)) {
            const regex = new RegExp(`(${keyword})`, 'g')
            highlightedText = highlightedText.replace(
              regex,
              `<span style="background-color: ${backgroundColor}; color: ${highlightColor}; font-weight: bold; padding: 0 2px; border-radius: 2px;">$1</span>`
            )
          }
        })

        return <div dangerouslySetInnerHTML={{ __html: highlightedText }} />
      }
    },
    {
      title: '涨停统计',
      dataIndex: 'high_days',
      key: 'high_days',
      width: 100,
      align: 'center' as const,
      ellipsis: true
    },
    {
      title: '换手率',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      width: 90,
      align: 'center' as const,
      render: (text: number) => `${text.toFixed(2)}%`,
      sorter: (a, b) => a.turnover_rate - b.turnover_rate
    },
    {
      title: '涨幅',
      dataIndex: 'change_rate',
      key: 'change_rate',
      width: 80,
      align: 'center' as const,
      render: (text: number) => (
        <span
          style={{
            color: text > 0 ? '#f5222d' : text < 0 ? '#52c41a' : '#000'
          }}
        >
          {text.toFixed(2)}%
        </span>
      ),
      sorter: (a, b) => a.change_rate - b.change_rate
    },
    {
      title: '流通市值',
      dataIndex: 'currency_value',
      key: 'currency_value',
      width: 120,
      align: 'center' as const,
      render: (text: number) => `${(text / 100000000).toFixed(2)}亿`
    },
    {
      title: '价格',
      dataIndex: 'latest',
      key: 'latest',
      width: 80,
      align: 'center' as const,
      render: (text: number) => text.toFixed(2)
    },
    {
      title: '涨停类型',
      dataIndex: 'limit_up_type',
      key: 'limit_up_type',
      width: 100,
      align: 'center' as const
    },
    {
      title: '开板数',
      dataIndex: 'open_num',
      key: 'open_num',
      width: 100,
      align: 'center' as const,
      sorter: (a, b) => a.open_num - b.open_num
    },
    {
      title: '首次涨停',
      dataIndex: 'first_limit_up_time',
      key: 'first_limit_up_time',
      width: 120,
      align: 'center' as const,
      render: (text: string) => dayjs(Number(text) * 1000).format('HH:mm:ss')
    },
    {
      title: '最后涨停',
      dataIndex: 'last_limit_up_time',
      key: 'last_limit_up_time',
      width: 120,
      align: 'center' as const,
      render: (text: string) => dayjs(Number(text) * 1000).format('HH:mm:ss')
    },
    {
      title: '近一年涨停封板率',
      dataIndex: 'limit_up_suc_rate',
      key: 'limit_up_suc_rate',
      width: 150,
      align: 'center' as const,
      render: (text: number) => `${(text * 100).toFixed(2)}%`
    },
    {
      title: '封单量',
      dataIndex: 'order_amount',
      key: 'order_amount',
      width: 120,
      align: 'center' as const,
      render: (text: number) => (text / 10000).toFixed(2) + '万'
    },
    {
      title: '封单额',
      dataIndex: 'order_volume',
      key: 'order_volume',
      width: 100,
      align: 'center' as const,
      render: (text: number) => (text / 100 / 10000).toFixed(2) + '万手'
    },
    {
      title: '是否新股',
      dataIndex: 'is_new',
      key: 'is_new',
      width: 100,
      align: 'center' as const,
      render: (text: number) =>
        text ? <Tag color="blue">新股</Tag> : <Tag>正常</Tag>
    },
    {
      title: '再次涨停',
      dataIndex: 'is_again_limit',
      key: 'is_again_limit',
      width: 100,
      align: 'center' as const,
      render: (text: number) =>
        text ? <Tag color="red">是</Tag> : <Tag color="green">否</Tag>
    }
  ]

  return (
    <div className="flex h-full flex-col">
      <Card className="mb-3 text-center" size="small">
        <Row gutter={16}>
          <Col span={3}>
            <Statistic
              title="涨停数"
              value={totalCount}
              styles={{
                content: {
                  color: '#1890ff',
                  fontSize: '18px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="主板"
              value={hsCount}
              styles={{
                content: {
                  color: '#52c41a',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="科创板"
              value={starCount}
              styles={{
                content: {
                  color: '#722ed1',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="创业板"
              value={gemCount}
              styles={{
                content: {
                  color: '#fa541c',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="新股"
              value={newStockCount}
              styles={{
                content: {
                  color: '#13c2c2',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="ST股"
              value={stStockCount}
              styles={{
                content: {
                  color: '#eb2f96',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="再次涨停"
              value={againLimitCount}
              styles={{
                content: {
                  color: '#f5222d',
                  fontSize: '16px'
                }
              }}
            />
          </Col>
        </Row>
      </Card>

      {/* 涨停原因高频词统计 */}
      {(topReasons.length > 0 ||
        starReasons.length > 0 ||
        gemReasons.length > 0) && (
        <Card className="mb-3" size="small" title="涨停原因高频词统计">
          <Collapse
            ghost
            defaultActiveKey={['all', 'star', 'gem']}
            items={[
              // 全部市场
              ...(topReasons.length > 0
                ? [
                    {
                      key: 'all',
                      label: `全部市场 (${totalCount}支)`,
                      children: (
                        <Space wrap>
                          {topReasons.map(([keyword, count], index) => (
                            <Tag
                              key={keyword}
                              color={
                                index < 3
                                  ? 'red'
                                  : index < 8
                                    ? 'orange'
                                    : index < 15
                                      ? 'blue'
                                      : 'default'
                              }
                              style={{
                                fontSize: Math.max(
                                  12,
                                  16 - Math.floor(index / 3)
                                ),
                                padding: '2px 8px',
                                margin: '2px'
                              }}
                            >
                              <Text strong>{keyword}</Text>
                              <Text type="secondary" style={{ marginLeft: 4 }}>
                                ({count})
                              </Text>
                            </Tag>
                          ))}
                        </Space>
                      )
                    }
                  ]
                : []),
              // 科创板
              ...(starReasons.length > 0
                ? [
                    {
                      key: 'star',
                      label: `科创板 (${starCount}支)`,
                      children: (
                        <Space wrap>
                          {starReasons.map(([keyword, count], index) => (
                            <Tag
                              key={keyword}
                              color={
                                index < 3
                                  ? 'purple'
                                  : index < 8
                                    ? 'magenta'
                                    : index < 15
                                      ? 'volcano'
                                      : 'default'
                              }
                              style={{
                                fontSize: Math.max(
                                  12,
                                  16 - Math.floor(index / 3)
                                ),
                                padding: '2px 8px',
                                margin: '2px'
                              }}
                            >
                              <Text strong>{keyword}</Text>
                              <Text type="secondary" style={{ marginLeft: 4 }}>
                                ({count})
                              </Text>
                            </Tag>
                          ))}
                        </Space>
                      )
                    }
                  ]
                : []),
              // 创业板
              ...(gemReasons.length > 0
                ? [
                    {
                      key: 'gem',
                      label: `创业板 (${gemCount}支)`,
                      children: (
                        <Space wrap>
                          {gemReasons.map(([keyword, count], index) => (
                            <Tag
                              key={keyword}
                              color={
                                index < 3
                                  ? 'geekblue'
                                  : index < 8
                                    ? 'cyan'
                                    : index < 15
                                      ? 'lime'
                                      : 'default'
                              }
                              style={{
                                fontSize: Math.max(
                                  12,
                                  16 - Math.floor(index / 3)
                                ),
                                padding: '2px 8px',
                                margin: '2px'
                              }}
                            >
                              <Text strong>{keyword}</Text>
                              <Text type="secondary" style={{ marginLeft: 4 }}>
                                ({count})
                              </Text>
                            </Tag>
                          ))}
                        </Space>
                      )
                    }
                  ]
                : [])
            ]}
          />
        </Card>
      )}
      <div className="flex-1 overflow-hidden">
        <Table<HRLimitUpData>
          className="h-full"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={false}
          onChange={onChange}
          rowKey="id"
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
        .rc-virtual-list-holder::-webkit-scrollbar {
          width: 0.25rem !important;
          height: 0.25rem !important;
        }
        .rc-virtual-list-holder::-webkit-scrollbar-thumb {
          background-color: var(--color-gray-300) !important;
          border-radius: 0.125rem !important;
        }
        .ant-pagination {
          margin-bottom: 0;
        }
      `}
      </style>
    </div>
  )
}

export default HrTable
