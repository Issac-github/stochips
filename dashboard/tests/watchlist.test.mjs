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
const { feedbackText, watchlistSchema } = await import(
  await moduleUrl('../src/watchlistData.ts', { zod, './data': data })
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
