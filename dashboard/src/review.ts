export const reviewSections = [
  { key: 'sentiment', title: '情绪定位' },
  { key: 'themes', title: '主线与梯队' },
  { key: 'leaders', title: '龙头与助攻' },
  { key: 'risk', title: '风险与反证' },
  { key: 'nextDay', title: '次日验证清单' },
] as const

export type ReviewSectionKey = (typeof reviewSections)[number]['key']
export type ReviewSections = Record<ReviewSectionKey, string>

// Only rearrange the complete, known review format. Never silently drop text
// from older reviews, unexpected sections, or fenced Markdown examples.
export function splitReview(content: string): ReviewSections | null {
  const bodies: string[][] = []
  let fence: { marker: string; length: number } | null = null
  for (const line of content.split(/\r?\n/)) {
    const fenceMatch = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line)
    if (fence) {
      if (
        fenceMatch &&
        fenceMatch[1][0] === fence.marker &&
        fenceMatch[1].length >= fence.length &&
        !fenceMatch[2].trim()
      )
        fence = null
    } else if (fenceMatch) {
      fence = { marker: fenceMatch[1][0], length: fenceMatch[1].length }
    } else {
      const heading = /^ {0,3}#{1,3}[ \t]+(.+?)[ \t]*#*[ \t]*$/.exec(line)
      if (heading) {
        const title = heading[1]
          .replace(/\*\*/g, '')
          .replace(/^\d+[.、．)]\s*/, '')
          .trim()
        if (title !== reviewSections[bodies.length]?.title) return null
        bodies.push([])
        continue
      }
    }
    if (bodies.length) bodies[bodies.length - 1].push(line)
    else if (line.trim()) return null
  }
  if (fence || bodies.length !== reviewSections.length) return null
  const values = bodies.map((lines) => lines.join('\n').trim())
  if (values.some((value) => !value)) return null
  return {
    sentiment: values[0],
    themes: values[1],
    leaders: values[2],
    risk: values[3],
    nextDay: values[4],
  }
}
