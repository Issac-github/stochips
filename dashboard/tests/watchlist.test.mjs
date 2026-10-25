import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

// Run the browser-only schema/formatters in memory; no generated repo files.
async function moduleUrl(file, imports) {
  const source = await readFile(new URL(file, import.meta.url), 'utf8')
  const result = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  })
  const output = result.outputText.replace(
    /from '([^']+)'/g,
    (_match, name) => {
      assert.ok(imports[name], `Unexpected runtime import: ${name}`)
      return `from '${imports[name]}'`
    },
  )
  return `data:text/javascript;base64,${Buffer.from(output).toString('base64')}`
}
const zod = import.meta.resolve('zod')
const data = await moduleUrl('../src/data.ts', { zod })
const { strategyEvidenceSchema } = await import(data)
const rawCatalog = JSON.parse(
  await readFile(new URL('../strategy-concepts.json', import.meta.url), 'utf8'),
)
const catalogJson = `data:text/javascript;base64,${Buffer.from(`export default ${JSON.stringify(rawCatalog)}`).toString('base64')}`
const catalogModule = await moduleUrl('../src/strategyCatalog.ts', {
  zod,
  '../strategy-concepts.json': catalogJson,
  './data': data,
  './review': await moduleUrl('../src/review.ts', {}),
})
const { strategyCatalog, conceptKeys } = await import(catalogModule)
const { feedbackText, watchlistSchema } = await import(
  await moduleUrl('../src/watchlistData.ts', {
    zod,
    './data': data,
    './strategyCatalog': catalogModule,
  })
)

test('unknown follow-up membership remains unknown, confirmed absence stays explicit', () => {
  assert.equal(
    feedbackText({ date: null, stocks: {} }, '000001'),
    '尚无后续行情记录',
  )
  assert.equal(
    feedbackText({ date: '2026-10-26', stocks: {} }, '000001'),
    '该股后续记录不足',
  )
  const feedback = {
    date: '2026-10-26',
    stocks: {
      '000001': { limit_up: null, limit_down: false, continuous_days: null },
    },
  }
  assert.equal(feedbackText(feedback, '000001'), '涨停数据不足；未见跌停记录')
})

test('follow-up text reports facts without assigning a manual condition result', () => {
  const feedback = {
    date: '2026-10-26',
    stocks: {
      '000001': { limit_up: true, limit_down: false, continuous_days: 4 },
    },
  }
  assert.equal(
    feedbackText(feedback, '000001'),
    '有涨停记录；未见跌停记录；4连板',
  )
})

test('AI strategy evidence requires explicit status, sources and uncertainty arrays', () => {
  const concept = {
    key: 'small_platform',
    status: 'insufficient_evidence',
    summary: '缺少连续日线，无法确认平台结构',
    evidence: [],
    counter_evidence: ['只有前高观察记录'],
    missing_data: ['连续日线 OHLCV'],
    confidence: 'unavailable',
  }
  const result = { version: 1, concepts: [concept] }
  assert.equal(strategyEvidenceSchema.parse(result).concepts.length, 1)
  assert.equal(
    strategyEvidenceSchema.safeParse({
      version: 1,
      concepts: [{ ...concept, status: 'confirmed', evidence: [{ source: 'top_stocks' }] }],
    }).success,
    false,
  )
})

test('watchlist boundary validates dates, source snapshots and annotation versions', () => {
  const item = {
    code: '000001',
    name: '观察股',
    roles: ['核心连板'],
    evidence: [
      { source: 'top_stocks', detail: '换手0%', fact: { turnover_rate: 0 } },
    ],
    risks: [],
    checks: [],
    saved: false,
    source_missing: false,
    annotation: {
      status: 'candidate',
      outcome: 'pending',
      note: '',
      revision: 0,
      updated_at: null,
    },
  }
  const payload = {
    date: '2026-10-23',
    items: [item],
    warnings: [],
    feedback: { date: null, stocks: {} },
  }
  assert.equal(
    watchlistSchema.parse(payload).items[0].evidence[0].fact.turnover_rate,
    0,
  )
  assert.equal(
    watchlistSchema.safeParse({ ...payload, date: 'wrong' }).success,
    false,
  )
  assert.equal(
    watchlistSchema.safeParse({
      ...payload,
      items: [{ ...item, annotation: { ...item.annotation, outcome: 'buy' } }],
    }).success,
    false,
  )
  assert.equal(
    watchlistSchema.safeParse({
      ...payload,
      items: [{ ...item, annotation: { ...item.annotation, revision: -1 } }],
    }).success,
    false,
  )
})

test('catalog keeps every concept in one known category and separates four platform types', () => {
  assert.equal(new Set(conceptKeys).size, conceptKeys.length)
  const groups = new Set(strategyCatalog.groups.map((group) => group.key))
  assert.equal(groups.size, strategyCatalog.groups.length)
  for (const concept of strategyCatalog.concepts)
    assert.ok(groups.has(concept.group))
  for (const key of [
    'small_platform',
    'large_leader_platform',
    'small_leader_platform',
    'trend_platform',
  ]) {
    const concept = strategyCatalog.concepts.find((value) => value.key === key)
    assert.equal(concept.group, 'platform')
    assert.ok(concept.checks.length)
  }
})

test('legacy annotations default to unclassified; invalid manual labels are rejected', () => {
  const base = {
    date: '2026-10-23',
    items: [],
    warnings: [],
    feedback: { date: null, stocks: {} },
  }
  const item = {
    code: '000001',
    name: '观察股',
    roles: ['核心连板'],
    evidence: [],
    risks: [],
    checks: [],
    saved: true,
    source_missing: false,
    annotation: {
      status: 'watching',
      outcome: 'pending',
      note: '',
      revision: 1,
      updated_at: null,
    },
  }
  assert.deepEqual(
    watchlistSchema.parse({ ...base, items: [item] }).items[0].annotation
      .concepts,
    [],
  )
  assert.deepEqual(
    watchlistSchema.parse({
      ...base,
      items: [
        {
          ...item,
          annotation: { ...item.annotation, concepts: ['small_platform'] },
        },
      ],
    }).items[0].annotation.concepts,
    ['small_platform'],
  )
  assert.equal(
    watchlistSchema.safeParse({
      ...base,
      items: [
        { ...item, annotation: { ...item.annotation, concepts: ['unknown'] } },
      ],
    }).success,
    false,
  )
})

const { evidenceSchema } = await import(
  await moduleUrl('../src/strategyEvidenceData.ts', {
    zod,
    './data': data,
    './strategyCatalog': catalogModule,
  })
)
test('evidence boundary keeps zero distinct from uncollected and rejects invented statuses', () => {
  const coverage = {
    source: 'continuous_limit_up',
    label: '连板池',
    rows: 1,
    dates: 1,
    stocks: 1,
    first_date: '2026-10-23',
    last_date: '2026-10-23',
    positive_price_rows: 0,
    positive_volume_rows: 0,
  }
  const concept = {
    key: 'small_platform',
    kind: 'pattern',
    status: 'data_gap',
    explanation: '未接入连续日线',
    stock_count: 1,
    source_counts: [{ dataset: 'top_stocks', rows: 1 }],
    requirements: [
      {
        key: 'daily_bars',
        label: '连续日线',
        state: 'not_integrated',
        detail: '看板未接入',
      },
    ],
  }
  const payload = {
    date: '2026-10-23',
    coverage: [
      coverage,
      { ...coverage, source: 'limit_up_pool', positive_volume_rows: null },
    ],
    concepts: [concept],
  }
  const result = evidenceSchema.parse(payload)
  assert.equal(result.coverage[0].positive_volume_rows, 0)
  assert.equal(result.coverage[1].positive_volume_rows, null)
  assert.equal(
    evidenceSchema.safeParse({
      ...payload,
      concepts: [{ ...concept, status: 'confirmed_platform' }],
    }).success,
    false,
  )
  assert.equal(
    evidenceSchema.safeParse({ ...payload, date: 'wrong' }).success,
    false,
  )
})
