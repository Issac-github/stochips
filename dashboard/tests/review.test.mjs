import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

// The parser has no runtime imports. Compile it in memory so these tests also
// run on Node 20 without extra runners or generated files in the repository.
const source = await readFile(
  new URL('../src/review.ts', import.meta.url),
  'utf8',
)
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
})
const { splitReview, reviewSections } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
)
const bodies = [
  '昨日状态 -> 今日状态。\n\n- 空间事实\n- **关键反证**',
  '候选方向，不能确认主线。\n\n#### 成员交集\n保留子标题与原始表述。',
  '核心高标，助攻待验证。',
  '- 风险事实\n- 无法确认的条件',
  '1. 竞价待观察\n2. 盘中承接待观察',
]
const complete = (values = bodies) =>
  reviewSections
    .map(
      (section, index) =>
        `### ${index + 1}. ${section.title}\n${values[index]}`,
    )
    .join('\n\n')

test('complete reviews preserve every section, nested heading and counter-evidence', () => {
  const result = splitReview(complete())
  assert.deepEqual(Object.values(result), bodies)
})

test('CRLF, bold and closing heading markers retain the known five-section format', () => {
  const content = complete()
    .replace(/### (\d+)\. (.+)/g, '## **$1、$2** ##')
    .replace(/\n/g, '\r\n')
  assert.deepEqual(Object.values(splitReview(content)), bodies)
})

test('headings inside fenced blocks do not become review boundaries', () => {
  for (const marker of ['```', '~~~~']) {
    const values = [...bodies]
    values[2] += `\n\n${marker}\n### 4. 风险与反证\n保留代码块\n${marker}`
    assert.deepEqual(Object.values(splitReview(complete(values))), values)
  }
})

test('unknown, missing, duplicate, reordered and empty sections fall back to the full original', () => {
  for (const content of [
    '',
    '# 历史复盘\n任意格式',
    `结论摘要\n${complete()}`,
    complete().replace('### 4. 风险与反证', '### 4. 其他风险'),
    complete().replace('### 4. 风险与反证', '### 3. 龙头与助攻'),
    complete().replace(/### 5\. 次日验证清单[\s\S]*/, ''),
    complete().replace('### 1. 情绪定位', '### 2. 主线与梯队'),
    complete(bodies.map((body, index) => (index === 3 ? '  ' : body))),
    `${complete()}\n\n### 补充结论\n不能丢失`,
  ])
    assert.equal(splitReview(content), null)
})

test('unclosed fences fall back instead of hiding subsequent risk or validation sections', () => {
  const values = [...bodies]
  values[2] += '\n```\n示例未闭合'
  assert.equal(splitReview(complete(values)), null)
})
