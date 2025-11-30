import {
  Card,
  Col,
  Collapse,
  Row,
  Space,
  Statistic,
  Table,
  type TableColumnsType,
  Tag,
  Typography
} from 'antd'
import dayjs from 'dayjs'

const { Text } = Typography
const { Panel } = Collapse

interface EmTableProps {
  data?: EMLimitUpData[]
  loading?: boolean
  pagination?: {
    current?: number
    pageSize?: number
    total?: number
  }
  onChange?: (pagination: unknown, filters: unknown, sorter: unknown) => void
}

const EmTable = ({ data = [], loading = false, onChange }: EmTableProps) => {
  // 计算统计数据
  const totalCount = data.length
  const avgAmount =
    data.length > 0
      ? (
          data.reduce((sum, item) => sum + item.amount, 0) /
          data.length /
          10000
        ).toFixed(0)
      : '0'
  const totalAmount = (
    data.reduce((sum, item) => sum + item.amount, 0) / 100000000
  ).toFixed(2)
  const highLbcCount = data.filter((item) => item.lbc >= 3).length // 3连板以上
  const lowLbcCount = data.filter((item) => item.lbc <= 2).length // 2连板以下
  const zeroZbcCount = data.filter((item) => (item.zbc || 0) === 0).length // 无炸板
  const hasZbcCount = data.filter((item) => (item.zbc || 0) > 0).length // 有炸板
  const highZbcCount = data.filter((item) => (item.zbc || 0) >= 3).length // 3次以上炸板

  // 统计行业板块涨停数量（类似高频词统计）
  const getIndustryStats = () => {
    const industryMap = new Map<string, number>()

    data.forEach((item) => {
      const industry = item.hybk || '未分类'
      if (industry && industry.trim().length > 0) {
        industryMap.set(industry, (industryMap.get(industry) || 0) + 1)
      }
    })

    // 转换为数组并按涨停数量排序
    return Array.from(industryMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20) // 只显示前20个热门板块
  }

  const topIndustries = getIndustryStats()

  // 行业板块统计（保留原有详细统计用于折叠面板）
  const industryStats = data.reduce(
    (acc, item) => {
      const industry = item.hybk || '未分类'
      if (!acc[industry]) {
        acc[industry] = {
          count: 0,
          totalAmount: 0,
          highLbc: 0,
          zeroZbc: 0,
          hasZbc: 0,
          avgAmount: 0,
          avgHs: 0,
          avgLbc: 0,
          avgZbc: 0,
          totalHs: 0,
          totalLbc: 0,
          totalZbc: 0
        }
      }
      acc[industry].count++
      acc[industry].totalAmount += item.amount
      acc[industry].totalHs += item.hs
      acc[industry].totalLbc += item.lbc
      acc[industry].totalZbc += item.zbc || 0
      if (item.lbc >= 3) acc[industry].highLbc++
      if ((item.zbc || 0) === 0) acc[industry].zeroZbc++
      if ((item.zbc || 0) > 0) acc[industry].hasZbc++
      return acc
    },
    {} as Record<
      string,
      {
        count: number
        totalAmount: number
        highLbc: number
        zeroZbc: number
        hasZbc: number
        avgAmount: number
        avgHs: number
        avgLbc: number
        avgZbc: number
        totalHs: number
        totalLbc: number
        totalZbc: number
      }
    >
  )

  // 计算平均值
  Object.keys(industryStats).forEach((industry) => {
    const stats = industryStats[industry]
    stats.avgAmount = stats.totalAmount / stats.count / 10000
    stats.avgHs = stats.totalHs / stats.count
    stats.avgLbc = stats.totalLbc / stats.count
    stats.avgZbc = stats.totalZbc / stats.count
  })

  // 按数量排序的行业板块
  const sortedIndustries = Object.entries(industryStats)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 10) // 取前10个
  const columns: TableColumnsType<EMLimitUpData> = [
    {
      title: '日期',
      dataIndex: 'qdate',
      key: 'qdate',
      width: 120,
      align: 'center' as const,
      render: (qdate: number) =>
        dayjs(String(qdate), 'YYYYMMDD').format('YYYY-MM-DD'),
      sorter: (a, b) => a.qdate - b.qdate
    },
    {
      title: '代码',
      dataIndex: 'c',
      key: 'c',
      width: 100,
      align: 'center' as const
    },
    {
      title: '名称',
      dataIndex: 'n',
      key: 'n',
      width: 120,
      align: 'center' as const
    },
    {
      title: '最新价',
      dataIndex: 'p',
      key: 'p',
      width: 80,
      align: 'center' as const,
      render: (p: number) => (p / 1000).toFixed(2)
    },
    {
      title: '换手率',
      dataIndex: 'hs',
      key: 'hs',
      width: 100,
      align: 'center' as const,
      render: (hs: number) => `${hs.toFixed(2)}%`,
      sorter: (a, b) => a.hs - b.hs
    },
    {
      title: '连板次数',
      dataIndex: 'lbc',
      key: 'lbc',
      width: 110,
      align: 'center' as const,
      sorter: (a, b) => a.lbc - b.lbc
    },
    {
      title: '行业板块',
      dataIndex: 'hybk',
      key: 'hybk',
      width: 110,
      align: 'center' as const,
      ellipsis: {
        showTitle: false
      },
      render: (text: string) => {
        if (!text) {
          return '-'
        }
        // 获取高频板块列表用于高亮显示
        const topIndustryNames = topIndustries
          .slice(0, 10)
          .map(([industry]) => industry)
        // 检查是否为高频板块
        const isTopIndustry = topIndustryNames.includes(text)
        return (
          <div
            title={text}
            className={`text-center ${isTopIndustry ? 'text-amber-400' : ''}`}
          >
            {text}
          </div>
        )
      },
      sorter: (a, b) => {
        // 计算每个板块的涨停数量
        const aCount = data.filter((item) => item.hybk === a.hybk).length
        const bCount = data.filter((item) => item.hybk === b.hybk).length
        // 数量多的排前面（降序）
        return bCount - aCount
      },
      defaultSortOrder: 'ascend' as const
    },
    {
      title: '涨停统计',
      dataIndex: 'zttj',
      key: 'zttj',
      width: 100,
      align: 'center' as const,
      render: (zttj: { days: number; ct: number }) => (
        <div>{`${zttj.ct}/${zttj.days}`}</div>
      )
    },
    {
      title: '涨跌幅',
      dataIndex: 'zdp',
      key: 'zdp',
      width: 100,
      align: 'center' as const,
      render: (zdp: number) => `${zdp.toFixed(2)}%`,
      sorter: (a, b) => a.zdp - b.zdp
    },
    {
      title: '炸板数',
      dataIndex: 'zbc',
      key: 'zbc',
      width: 100,
      align: 'center' as const,
      sorter: (a, b) => (a.zbc || 0) - (b.zbc || 0),
      render: (zbc: number) => (
        <span
          style={{
            color: zbc === 0 ? '#52c41a' : zbc <= 2 ? '#fa8c16' : '#ff4d4f',
            fontWeight: zbc > 0 ? 'bold' : 'normal'
          }}
        >
          {zbc || 0}
        </span>
      )
    },
    {
      title: '流通市值',
      dataIndex: 'ltsz',
      key: 'ltsz',
      width: 100,
      align: 'center' as const,
      render: (ltsz: number) => `${(ltsz / 100000 / 1000).toFixed(2)}亿`
    },
    {
      title: '总市值',
      dataIndex: 'tshare',
      key: 'tshare',
      width: 100,
      align: 'center' as const,
      render: (tshare: number) => `${(tshare / 100000 / 1000).toFixed(2)}亿`
    },
    {
      title: '交易额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      align: 'center' as const,
      render: (amount: number) => `${(amount / 10000).toFixed(0)}万`
    },
    {
      title: '首封时间',
      dataIndex: 'fbt',
      key: 'fbt',
      width: 80,
      align: 'center' as const,
      render: (fbt: number) =>
        dayjs(String(fbt).padStart(6, '0'), 'Hmmss').format('HH:mm:ss')
    },
    {
      title: '尾封时间',
      dataIndex: 'lbt',
      key: 'lbt',
      width: 80,
      align: 'center' as const,
      render: (lbt: number) =>
        dayjs(String(lbt).padStart(6, '0'), 'Hmmss').format('HH:mm:ss')
    },
    {
      title: '资金',
      dataIndex: 'fund',
      key: 'fund',
      width: 100,
      align: 'center' as const,
      render: (fund: number) => `${(fund / 10000).toFixed(0)}万`
    }
  ]

  return (
    <div className="flex h-full flex-col">
      <Card className="mb-3 text-center" size="small">
        <Row gutter={16}>
          <Col span={3}>
            <Statistic
              title="总数量"
              value={totalCount}
              valueStyle={{ color: '#1890ff', fontSize: '16px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="平均金额"
              value={avgAmount}
              suffix="万"
              valueStyle={{ color: '#52c41a', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="总金额"
              value={totalAmount}
              suffix="亿"
              valueStyle={{ color: '#722ed1', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="高连板(≥3)"
              value={highLbcCount}
              valueStyle={{ color: '#f5222d', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="低连板(≤2)"
              value={lowLbcCount}
              valueStyle={{ color: '#fa541c', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="无炸板"
              value={zeroZbcCount}
              valueStyle={{ color: '#52c41a', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="高炸板(≥3次)"
              value={highZbcCount}
              valueStyle={{ color: '#ff4d4f', fontSize: '14px' }}
            />
          </Col>
          <Col span={3}>
            <Statistic
              title="炸板率"
              value={
                totalCount > 0
                  ? ((hasZbcCount / totalCount) * 100).toFixed(1)
                  : '0'
              }
              suffix="%"
              valueStyle={{ color: '#f759ab', fontSize: '14px' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 行业板块涨停数量统计 */}
      {topIndustries.length > 0 && (
        <Card className="mb-3" size="small" title="行业板块涨停数量统计">
          <Space wrap>
            {topIndustries.map(([industry, count], index) => (
              <Tag
                key={industry}
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
                  fontSize: Math.max(12, 16 - Math.floor(index / 3)),
                  padding: '2px 8px',
                  margin: '2px'
                }}
              >
                <Text strong>{industry}</Text>
                <Text type="secondary" style={{ marginLeft: 4 }}>
                  ({count})
                </Text>
              </Tag>
            ))}
          </Space>
        </Card>
      )}

      <Card className="mb-3" size="small">
        <Collapse ghost defaultActiveKey={['1']}>
          <Panel
            header={`行业板块统计 (共 ${Object.keys(industryStats).length} 个板块)`}
            key="1"
          >
            <Row gutter={[16, 16]}>
              {sortedIndustries.map(([industry, stats]) => (
                <Col span={6} key={industry}>
                  <Card size="small" className="text-center">
                    <div
                      style={{
                        fontSize: '12px',
                        fontWeight: 'bold',
                        marginBottom: '8px'
                      }}
                    >
                      {industry}
                    </div>
                    <Row gutter={8}>
                      <Col span={12}>
                        <Statistic
                          title="数量"
                          value={stats.count}
                          valueStyle={{ color: '#1890ff', fontSize: '12px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="平均金额"
                          value={stats.avgAmount.toFixed(0)}
                          suffix="万"
                          valueStyle={{ color: '#52c41a', fontSize: '12px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="高连板"
                          value={stats.highLbc}
                          valueStyle={{ color: '#f5222d', fontSize: '12px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="无炸板"
                          value={stats.zeroZbc}
                          valueStyle={{ color: '#52c41a', fontSize: '12px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="平均换手"
                          value={stats.avgHs.toFixed(1)}
                          suffix="%"
                          valueStyle={{ color: '#722ed1', fontSize: '12px' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="炸板率"
                          value={
                            stats.count > 0
                              ? ((stats.hasZbc / stats.count) * 100).toFixed(1)
                              : '0'
                          }
                          suffix="%"
                          valueStyle={{ color: '#f759ab', fontSize: '12px' }}
                        />
                      </Col>
                    </Row>
                  </Card>
                </Col>
              ))}
            </Row>
            {Object.keys(industryStats).length > 10 && (
              <div
                style={{
                  textAlign: 'center',
                  marginTop: '16px',
                  color: '#666',
                  fontSize: '12px'
                }}
              >
                {'显示前 10 个板块，总共 '}
                {Object.keys(industryStats).length} 个板块
              </div>
            )}
          </Panel>
        </Collapse>
      </Card>

      <div className="flex-1 overflow-hidden">
        <Table<EMLimitUpData>
          className="h-full"
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="id"
          pagination={false}
          onChange={onChange}
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
        .ant-table {
          overflow: auto;
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

export default EmTable
