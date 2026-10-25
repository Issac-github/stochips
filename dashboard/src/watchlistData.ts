import { z } from 'zod'
import { rowSchema } from './data'

export const statusLabels = {
  candidate: '待观察',
  watching: '已关注',
  excluded: '已剔除',
} as const
export const outcomeLabels = {
  pending: '待验证',
  met: '条件满足',
  not_met: '条件未满足',
  continue: '继续观察',
} as const
export const annotationSchema = z.object({
  status: z.enum(['candidate', 'watching', 'excluded']),
  outcome: z.enum(['pending', 'met', 'not_met', 'continue']),
  note: z.string(),
  revision: z.number().int().nonnegative(),
  updated_at: z.string().nullable(),
})
export const observationSchema = z.object({
  code: z.string().regex(/^\d{6}$/),
  name: z.string(),
  roles: z.array(z.string()),
  evidence: z.array(
    z.object({
      source: z.enum(['top_stocks', 'leader_assists', 'breakout_stocks']),
      detail: z.string(),
      fact: rowSchema,
    }),
  ),
  risks: z.array(z.string()),
  checks: z.array(z.string()),
  saved: z.boolean(),
  source_missing: z.boolean(),
  annotation: annotationSchema,
})
export const watchlistSchema = z.object({
  date: z.iso.date(),
  items: z.array(observationSchema),
  warnings: z.array(z.string()),
  feedback: z.object({
    date: z.iso.date().nullable(),
    stocks: z.record(
      z.string(),
      z.object({
        limit_up: z.boolean().nullable(),
        limit_down: z.boolean().nullable(),
        continuous_days: z.number().nullable(),
      }),
    ),
  }),
})
export type Observation = z.infer<typeof observationSchema>
export type Annotation = z.infer<typeof annotationSchema>
export type WatchlistPayload = z.infer<typeof watchlistSchema>

export function feedbackText(
  feedback: WatchlistPayload['feedback'],
  code: string,
) {
  if (!feedback.date) return '尚无后续行情记录'
  const stock = feedback.stocks[code]
  if (!stock) return '该股后续记录不足'
  const facts = [
    stock.limit_up === null
      ? '涨停数据不足'
      : stock.limit_up
        ? '有涨停记录'
        : '未见涨停记录',
    stock.limit_down === null
      ? '跌停数据不足'
      : stock.limit_down
        ? '跌停池有记录'
        : '未见跌停记录',
  ]
  if (stock.continuous_days !== null) facts.push(`${stock.continuous_days}连板`)
  return facts.join('；')
}
