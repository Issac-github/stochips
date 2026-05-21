import { useEffect, useRef } from 'react'
import { Bot, Circle, User } from 'lucide-react'
import Markdown from './Markdown'

export interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  error?: boolean
}

interface ChatMessagesProps {
  messages: ChatMessage[]
  emptyText: string
}

const formatTime = (date: Date) =>
  date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

const ChatMessages = ({ messages, emptyText }: ChatMessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!messages.length) {
    return (
      <div className="border-border bg-card text-muted-foreground mb-4 flex flex-1 flex-col items-center justify-center rounded-2xl border p-10 text-center shadow-[var(--shadow-lg)]">
        <div className="accent-gradient mb-4 flex h-16 w-16 items-center justify-center rounded-xl text-white shadow-[var(--shadow-accent)]">
          <Bot className="h-8 w-8" />
        </div>
        <div className="font-bold">{emptyText}</div>
      </div>
    )
  }

  return (
    <div className="border-border bg-card mb-4 flex-1 overflow-auto rounded-2xl border p-5 shadow-[var(--shadow-lg)]">
      {messages.map((message) => {
        const isUser = message.type === 'user'
        const Icon = isUser ? User : message.type === 'assistant' ? Bot : Circle
        return (
          <div
            key={message.id}
            className={`mb-4 flex gap-3 ${isUser ? 'justify-end' : ''}`}
          >
            {!isUser && (
              <div className="border-accent/20 bg-accent/5 text-accent flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border">
                <Icon className="h-4 w-4" />
              </div>
            )}
            <div
              className={`max-w-[78%] rounded-xl px-4 py-3 ${
                isUser
                  ? 'accent-gradient text-white shadow-[var(--shadow-accent)]'
                  : message.error
                    ? 'border border-red-200 bg-red-50 text-red-950 shadow-[var(--shadow-sm)]'
                    : 'border-border bg-card border shadow-[var(--shadow-sm)]'
              }`}
            >
              <div className="mb-1 text-[11px] opacity-70">
                {formatTime(message.timestamp)}
              </div>
              <Markdown>{message.content}</Markdown>
            </div>
            {isUser && (
              <div className="accent-gradient flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white shadow-[var(--shadow-accent)]">
                <Icon className="h-4 w-4" />
              </div>
            )}
          </div>
        )
      })}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default ChatMessages
