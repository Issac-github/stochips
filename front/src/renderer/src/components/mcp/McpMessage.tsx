import React, { useEffect, useRef } from 'react'
import { RobotOutlined, UserOutlined } from '@ant-design/icons'
import { Bubble } from '@ant-design/x'
import { XMarkdown } from '@ant-design/x-markdown'
import { ANTD_MAP_TOKEN, ANTD_SEED_TOKEN } from '../../assets/style/color'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  error?: boolean
}

interface Props {
  messageList: ChatMessage[]
}

const McpMessage: React.FC<Props> = ({ messageList }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getAvatarConfig = (type: ChatMessage['type']) => {
    switch (type) {
      case 'user':
        return {
          avatar: <UserOutlined style={{ fontSize: '18px' }} />,
          placement: 'end' as const
        }
      case 'assistant':
        return {
          avatar: <RobotOutlined style={{ fontSize: '18px' }} />,
          placement: 'start' as const
        }
      case 'system':
        return {
          avatar: <span style={{ fontSize: '12px' }}>●</span>,
          placement: 'start' as const
        }
      default:
        return {
          placement: 'start' as const
        }
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messageList])

  if (!messageList.length) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center text-center"
        style={{
          color: ANTD_MAP_TOKEN.colorTextSecondary,
          padding: '40px 20px'
        }}
      >
        <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
        <div>Start a conversation with the MCP server</div>
      </div>
    )
  }

  return (
    <div
      className="mb-4 flex-1 overflow-auto rounded-lg p-4"
      style={{ border: `1px solid ${ANTD_MAP_TOKEN.colorBorderSecondary}` }}
    >
      {messageList.map((message) => {
        const config = getAvatarConfig(message.type)
        return (
          <div key={message.id} style={{ marginBottom: '16px' }}>
            <Bubble
              avatar={config.avatar}
              header={formatTime(message.timestamp)}
              placement={config.placement}
              content={<XMarkdown>{message.content}</XMarkdown>}
              style={{
                borderColor: message.error
                  ? ANTD_SEED_TOKEN.colorError
                  : undefined
              }}
            />
          </div>
        )
      })}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default McpMessage
