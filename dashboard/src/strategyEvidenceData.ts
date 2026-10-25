import { z } from 'zod'
import { datasets } from './data'
import { conceptKeys } from './strategyCatalog'

export const statusLabels = {
  facts_available: '已有事实',
  candidate: '候选待验证',
  data_gap: '数据有缺口',
  not_implemented: '自动规则尚未实现',
  manual: '人工记录',
  no_observations: '当日无关联观测',
} as const
export const capabilityLabels = {
  available: '已有记录',
  partial: '部分证据',
  missing: '缺有效记录',
  not_integrated: '未接入看板',
} as const
export const evidenceSchema = z.object({
  date: z.iso.date(),
  coverage: z.array(
    z.object({
      source: z.string(),
      label: z.string(),
      rows: z.number().int().nonnegative(),
      dates: z.number().int().nonnegative(),
      stocks: z.number().int().nonnegative(),
      first_date: z.iso.date().nullable(),
      last_date: z.iso.date().nullable(),
      positive_price_rows: z.number().int().nonnegative(),
      positive_volume_rows: z.number().int().nonnegative().nullable(),
    }),
  ),
  concepts: z.array(
    z.object({
      key: z.enum(conceptKeys),
      kind: z.enum(['fact', 'candidate', 'pattern', 'manual']),
      status: z.enum([
        'facts_available',
        'candidate',
        'data_gap',
        'not_implemented',
        'manual',
        'no_observations',
      ]),
      explanation: z.string(),
      stock_count: z.number().int().nonnegative(),
      source_counts: z.array(
        z.object({
          dataset: z.enum(datasets.map(([key]) => key)),
          rows: z.number().int().nonnegative(),
        }),
      ),
      requirements: z.array(
        z.object({
          key: z.string(),
          label: z.string(),
          state: z.enum(['available', 'partial', 'missing', 'not_integrated']),
          detail: z.string(),
        }),
      ),
    }),
  ),
})
export type EvidencePayload = z.infer<typeof evidenceSchema>
export type ConceptEvidence = EvidencePayload['concepts'][number]
