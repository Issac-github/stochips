import React, { useRef, useState } from 'react'
import { Trash2 } from 'lucide-react'
import ChatComposer from '@renderer/components/shared/ChatComposer'
import ChatMessages, {
  type ChatMessage
} from '@renderer/components/shared/ChatMessages'
import { Button } from '@renderer/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@renderer/components/ui/card'
import useStreamChat from '@renderer/lib/hooks/useGPTChat'

interface StreamMessage extends ChatMessage {
  type: 'user' | 'assistant'
  streaming?: boolean
}

const StreamChat: React.FC = () => {
  const currentMessageIdRef = useRef('')
  const [messageList, setMessageList] = useState<StreamMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { sendStreamMessage, stopStream, isPortReady } = useStreamChat()

  const addMessage = (message: Omit<StreamMessage, 'id' | 'timestamp'>) => {
    const newMessage: StreamMessage = {
      ...message,
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      timestamp: new Date()
    }
    setMessageList((prev) => [...prev, newMessage])
    return newMessage.id
  }

  const finishMessage = (id: string) => {
    setMessageList((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, streaming: false } : message
      )
    )
  }

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading || !isPortReady) return
    const userMessage = inputValue.trim()
    setInputValue('')
    setIsLoading(true)
    addMessage({ type: 'user', content: userMessage })
    const assistantMessageId = addMessage({
      type: 'assistant',
      content: '',
      streaming: true
    })
    currentMessageIdRef.current = assistantMessageId
    await sendStreamMessage(userMessage, {
      onChunk: (chunk) => {
        setMessageList((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: message.content + chunk }
              : message
          )
        )
      },
      onComplete: () => {
        finishMessage(assistantMessageId)
        setIsLoading(false)
      },
      onError: (error) => {
        setMessageList((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: `错误: ${error}`, error: true }
              : message
          )
        )
        finishMessage(assistantMessageId)
        setIsLoading(false)
      }
    })
  }

  const handleStop = () => {
    stopStream()
    if (currentMessageIdRef.current) finishMessage(currentMessageIdRef.current)
    setIsLoading(false)
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-3">
          <CardTitle>Streaming Chat (HTTP)</CardTitle>
          <span
            className={
              isPortReady
                ? 'rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-600'
                : 'border-border bg-muted text-muted-foreground rounded-full border px-3 py-1 text-xs font-bold'
            }
          >
            {isPortReady ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setMessageList([])}>
          <Trash2 className="h-4 w-4" />
          Clear
        </Button>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
        <ChatMessages
          messages={messageList}
          emptyText="Start chatting with the AI"
        />
        <ChatComposer
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSend}
          onStop={handleStop}
          placeholder="Send message... (Enter to send, Shift+Enter to newline)"
          loading={isLoading}
          disabled={!isPortReady || isLoading}
        />
      </CardContent>
    </Card>
  )
}

export default StreamChat
