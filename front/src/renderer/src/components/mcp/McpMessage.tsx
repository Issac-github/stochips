import ChatMessages, {
  type ChatMessage
} from '@renderer/components/shared/ChatMessages'

interface Props {
  messageList: ChatMessage[]
}

const McpMessage: React.FC<Props> = ({ messageList }) => (
  <ChatMessages
    messages={messageList}
    emptyText="Start a conversation with the MCP server"
  />
)

export default McpMessage
