import { z } from 'zod'

export type JsonValue =
  string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
const jsonValue: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.null(),
    z.array(jsonValue),
    z.record(z.string(), jsonValue),
  ]),
)
export const rowSchema = z.record(z.string(), jsonValue)
export type Row = z.infer<typeof rowSchema>
const rows = z.array(rowSchema)
export const strategyEvidenceSchema = z.object({
  version: z.number(),
  concepts: z.array(z.object({
    key: z.string(),
    status: z.enum([
      'confirmed',
      'candidate',
      'insufficient_evidence',
      'conflicting_evidence',
      'not_applicable',
    ]),
    summary: z.string(),
    evidence: z.array(z.object({
      source: z.string(),
      reference: z.string(),
      field: z.string(),
      value: z.string(),
    })),
    counter_evidence: z.array(z.string()),
    missing_data: z.array(z.string()),
    confidence: z.enum(['high', 'medium', 'low', 'unavailable']),
  })),
})

export const reportSchema = z.object({
  target_date: z.iso.date(),
  is_complete: z.boolean(),
  continuous_count: z.number(),
  block_count: z.number(),
  hr_limit_up_count: z.number(),
  em_limit_up_count: z.number(),
  lower_limit_count: z.number(),
  max_continuous_days: z.number(),
  continuous_distribution: z.record(z.string(), z.number()),
  limit_up_type_distribution: z.record(z.string(), z.number()),
  data_warnings: z.array(z.string()),
  fetch_logs: rows,
  top_blocks: rows,
  eastmoney_industries: rows,
  top_stocks: rows,
  early_stocks: rows,
  weak_boards: rows,
  breakout_stocks: rows,
  lower_limit_stocks: rows,
  one_word_stocks: rows,
  leader_assists: rows,
  previous_high_feedback: rows,
  pool_stock_reasons: rows,
  limit_up_pool_metrics: rows,
  board_overlaps: rows,
  daily_review: z
    .object({
      content: z.string(),
      provider: z.string(),
      model: z.string(),
      strategy_evidence: strategyEvidenceSchema.nullable().optional(),
    })
    .nullable(),
})
export const payloadSchema = z.object({
  report: reportSchema,
  material: z.string(),
  previous_day_material: z.string(),
  reason_material: z.string(),
})
export type Report = z.infer<typeof reportSchema>
export type Payload = z.infer<typeof payloadSchema>

export const datasets = [
  ['top_blocks', '同花顺板块', '板块热度、龙头与完整涨停原因'],
  ['eastmoney_industries', '东财行业', '行业涨停数量与领涨股'],
  ['top_stocks', '核心连板', '连板高度、封板时间与换手'],
  ['leader_assists', '龙头助攻', '同属性或同板块、封板更早且板数更低的候选'],
  ['previous_high_feedback', '昨日高标', '昨日高标的今日收盘涨停反馈'],
  ['one_word_stocks', '一字板', '一字板个股及涨停原因'],
  ['early_stocks', '早盘强势', '同花顺首次涨停时间口径'],
  ['weak_boards', '分歧弱板', '开板、换手与回封样本'],
  ['lower_limit_stocks', '跌停池', '跌幅、首次及末次跌停时间'],
  ['breakout_stocks', '前高突破', '前高、突破价、间隔交易日与首破标识'],
  ['board_overlaps', '板块交集', '同花顺成员去重后的重叠情况'],
  ['pool_stock_reasons', '涨停原因', '个股原因分类与完整描述'],
  ['limit_up_pool_metrics', '涨停池指标', '涨幅、板型、开板次数与换手'],
  ['fetch_logs', '抓取日志', '各来源状态、记录数与错误信息'],
] as const
export type DatasetKey = (typeof datasets)[number][0]

export const labels: Record<string, string> = {
  code: '股票代码',
  name: '股票名称',
  block_name: '所属板块',
  block_code: '板块代码',
  block_count: '板块数量',
  block_name_label: '板块名称',
  stock_count: '股票数',
  leading_stock_name: '领涨股',
  change_percent: '涨跌幅 (%)',
  source: '来源',
  stocks: '成员股票',
  stock_reasons: '成员涨停原因',
  leading_turnover_rate: '领涨股换手 (%)',
  industry_name: '行业名称',
  leaders: '领涨股',
  leader_turnover_rates: '领涨股换手 (%)',
  continuous_days: '连板数',
  limit_up_time: '封板时间',
  reason: '涨停原因',
  turnover_rate: '换手率 (%)',
  reason_type: '原因分类',
  reason_info: '原因详情',
  leader: '龙头',
  stock: '助攻候选',
  shared_reason_tags: '相同属性',
  shared_blocks: '相同板块',
  leader_first_limit_up_time: '龙头首次封板',
  board_type: '板型',
  first_limit_up_time: '首次封板',
  last_limit_up_time: '末次封板',
  open_count: '开板次数',
  first_limit_down_time: '首次跌停',
  last_limit_down_time: '末次跌停',
  is_again_limit: '再次跌停',
  limit_up_type: '涨停类型',
  previous_continuous_days: '昨日连板数',
  feedback: '今日反馈',
  first_block_name: '板块一',
  second_block_name: '板块二',
  shared_stock_count: '交集股票数',
  first_stock_count: '板块一股票数',
  second_stock_count: '板块二股票数',
  breakout_price: '突破价',
  previous_high_price: '前高价',
  breakout_ratio: '突破比例',
  previous_max_days: '前期最高板数',
  gap_trading_days: '间隔交易日',
  is_first_breakout: '首次突破',
  data_type: '数据类型',
  status: '状态',
  record_count: '记录数',
  error_message: '错误信息',
}

export async function fetchJson(
  path: string,
  signal?: AbortSignal,
  options?: RequestInit,
): Promise<unknown> {
  const response = await fetch(path, { ...options, signal })
  const body: unknown = await response.json()
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('auth-expired'))
    const error = z.object({ error: z.string() }).safeParse(body)
    throw new Error(
      error.success ? error.data.error : `请求失败 (${response.status})`,
    )
  }
  return body
}

export function downloadJson(payload: Payload) {
  const link = document.createElement('a')
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }),
  )
  link.href = url
  link.download = `stochips-${payload.report.target_date}.json`
  link.click()
  URL.revokeObjectURL(url)
}
