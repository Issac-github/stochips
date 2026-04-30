import { Tabs } from 'antd'
import {
  FilterOutlined,
  MessageOutlined,
  NodeIndexOutlined
} from '@ant-design/icons'
import McpChat from '@renderer/components/mcp/McpChat'
import McpFilter from '@renderer/components/mcp/McpFilter'
import StreamChat from '@renderer/components/mcp/StreamChat'

const tabsItems = [
  {
    label: 'Standard Chat (WS)',
    children: McpChat,
    icon: MessageOutlined
  },
  {
    label: 'Streaming Chat (HTTP)',
    children: StreamChat,
    icon: NodeIndexOutlined
  },
  {
    label: 'JSON Filter (HTTP)',
    children: McpFilter,
    icon: FilterOutlined
  }
]

const Mcp = () => {
  return (
    <>
      <Tabs
        className="mcp h-full"
        defaultActiveKey="2"
        items={tabsItems.map((item, index) => {
          const id = String(index + 1)
          return {
            label: item.label,
            key: id,
            children: <item.children />,
            icon: <item.icon />
          }
        })}
      />
      <style>{`
        .mcp .ant-tabs-content, .mcp .ant-tabs-tabpane {
          height: 100%;
        }
      `}</style>
    </>
  )
}

export default Mcp
