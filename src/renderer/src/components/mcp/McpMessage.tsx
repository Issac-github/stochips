import React, { useEffect, useRef } from 'react'
import { Divider, Space, Typography } from 'antd'
import { marked } from 'marked'
import { RobotOutlined, UserOutlined } from '@ant-design/icons'
import { ANTD_MAP_TOKEN, ANTD_SEED_TOKEN } from '../../assets/style/color'

const { Text } = Typography
const customRenderer = new marked.Renderer()
customRenderer.link = ({ href, title, text }) => {
  return `<a href="${href}" target="_blank" rel="noopener noreferrer" title="${
    title || ''
  }">${text}</a>`
}
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

const getMessageStyle = (
  type: ChatMessage['type']
): {
  icon?: React.ReactNode
  textColor?: string
  bgColor?: string
  name?: string
} => {
  switch (type) {
    case 'user':
      return {
        icon: <UserOutlined style={{ color: ANTD_SEED_TOKEN.colorPrimary }} />,
        textColor: ANTD_SEED_TOKEN.colorPrimary,
        bgColor: ANTD_MAP_TOKEN.colorPrimaryBg,
        name: 'You'
      }
    case 'assistant':
      return {
        icon: <RobotOutlined style={{ color: ANTD_SEED_TOKEN.colorSuccess }} />,
        textColor: ANTD_SEED_TOKEN.colorSuccess,
        bgColor: ANTD_MAP_TOKEN.colorSuccessBg,
        name: 'Assistant'
      }
    case 'system':
      return {
        icon: <Text type="secondary">●</Text>,
        textColor: ANTD_MAP_TOKEN.colorTextSecondary,
        bgColor: ANTD_MAP_TOKEN.colorBgLayout,
        name: 'System'
      }
    default:
      return {}
  }
}

const Mcp: React.FC<Props> = ({ messageList }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messageList])

  return (
    <div
      className="mb-4 flex-1 overflow-auto rounded-lg p-4"
      style={{ border: `1px solid ${ANTD_MAP_TOKEN.colorBorderSecondary}` }}
    >
      {!messageList.length ? (
        <div
          className="flex h-full flex-col items-center justify-center text-center"
          style={{ color: ANTD_MAP_TOKEN.colorTextSecondary }}
        >
          <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
          <div>Start a conversation with the MCP server</div>
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {messageList.map((message) => (
            <div key={message.id}>
              <Space align="start" style={{ width: '100%' }}>
                {getMessageStyle(message.type).icon}
                <div className="max-w-4/5">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <Text
                      strong
                      style={{
                        color: getMessageStyle(message.type).textColor
                      }}
                      className="whitespace-nowrap"
                    >
                      {getMessageStyle(message.type).name}
                    </Text>
                    <Text
                      type="secondary"
                      className="text-xs whitespace-nowrap"
                    >
                      {formatTime(message.timestamp)}
                    </Text>
                  </div>
                  <div
                    className="rounded-md px-3 py-2 shadow-sm"
                    style={{
                      backgroundColor: getMessageStyle(message.type).bgColor,
                      border: message.error
                        ? `1px solid ${ANTD_SEED_TOKEN.colorError}`
                        : 'none'
                    }}
                  >
                    <div
                      className="whitespace-pre-wrap"
                      style={{
                        color: message.error
                          ? ANTD_SEED_TOKEN.colorError
                          : undefined
                      }}
                      dangerouslySetInnerHTML={{
                        __html: marked.parse(message.content || '', {
                          renderer: customRenderer,
                          gfm: true,
                          breaks: true,
                          async: false
                        })
                      }}
                    />
                  </div>
                </div>
              </Space>
              <Divider style={{ margin: '16px 0' }} />
            </div>
          ))}
        </Space>
      )}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default Mcp
