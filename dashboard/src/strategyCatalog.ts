import { z } from 'zod'
import rawCatalog from '../strategy-concepts.json'
import { datasets } from './data'
import { reviewSections } from './review'

const catalogSchema = z.object({
  groups: z
    .array(
      z.object({
        key: z.string(),
        title: z.string(),
        description: z.string(),
        reviewKeys: z.array(
          z.enum(reviewSections.map((section) => section.key)),
        ),
        datasets: z.array(z.enum(datasets.map(([key]) => key))).min(1),
      }),
    )
    .min(1),
  concepts: z
    .array(
      z.object({
        key: z.string(),
        label: z.string(),
        group: z.string(),
        focus: z.string(),
        checks: z.array(z.string()),
        kind: z.enum(['fact', 'candidate', 'pattern', 'manual']),
        sources: z.array(z.enum(datasets.map(([key]) => key))),
        requirements: z.array(z.string()),
      }),
    )
    .min(1),
})
export const strategyCatalog = catalogSchema.parse(rawCatalog)
export const conceptKeys = strategyCatalog.concepts.map(
  (concept) => concept.key,
)
export const conceptLabels = Object.fromEntries(
  strategyCatalog.concepts.map((concept) => [concept.key, concept.label]),
)
export type StrategyGroup = (typeof strategyCatalog.groups)[number]
