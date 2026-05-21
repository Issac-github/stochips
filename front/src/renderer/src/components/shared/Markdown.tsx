import { useMemo } from 'react'
import { marked } from 'marked'

interface MarkdownProps {
  children: string
}

const Markdown = ({ children }: MarkdownProps) => {
  const html = useMemo(() => marked.parse(children || '') as string, [children])

  return (
    <div
      className="prose prose-sm [&_code]:bg-muted max-w-none text-sm leading-6 [&_code]:rounded [&_code]:px-1 [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:bg-slate-950 [&_pre]:p-3 [&_pre]:text-slate-50"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default Markdown
