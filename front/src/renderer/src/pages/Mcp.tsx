import { Filter, MessageCircle, Workflow } from 'lucide-react'
import McpChat from '@renderer/components/mcp/McpChat'
import McpFilter from '@renderer/components/mcp/McpFilter'
import StreamChat from '@renderer/components/mcp/StreamChat'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '@renderer/components/ui/tabs'

const tabsItems = [
  {
    label: 'Standard Chat (WS)',
    value: 'standard',
    icon: MessageCircle,
    children: <McpChat />
  },
  {
    label: 'Streaming Chat (HTTP)',
    value: 'stream',
    icon: Workflow,
    children: <StreamChat />
  },
  {
    label: 'JSON Filter (HTTP)',
    value: 'filter',
    icon: Filter,
    children: <McpFilter />
  }
]

const Mcp = () => {
  return (
    <Tabs defaultValue="stream" className="flex h-full flex-col gap-1">
      <div className="border-border bg-card flex items-center justify-between rounded-2xl border p-5 shadow-[var(--shadow-md)]">
        <div>
          <div className="border-accent/30 bg-accent/5 mb-2 inline-flex items-center gap-2 rounded-full border px-3 py-1">
            <span className="bg-accent h-2 w-2 animate-[pulse-dot_2s_infinite] rounded-full" />
            <span className="text-accent font-mono text-[10px] tracking-[0.15em] uppercase">
              Companion
            </span>
          </div>
          <h1 className="font-display text-2xl tracking-tight">
            MCP <span className="gradient-text">Chat</span>
          </h1>
          <p className="text-muted-foreground mt-1 text-sm font-medium">
            Socket, HTTP streaming and JSON filtering tools
          </p>
        </div>
        <TabsList>
          {tabsItems.map((item) => {
            const Icon = item.icon
            return (
              <TabsTrigger key={item.value} value={item.value}>
                <Icon className="h-4 w-4" />
                {item.label}
              </TabsTrigger>
            )
          })}
        </TabsList>
      </div>
      {tabsItems.map((item) => (
        <TabsContent
          key={item.value}
          value={item.value}
          className="min-h-0 flex-1"
        >
          {item.children}
        </TabsContent>
      ))}
    </Tabs>
  )
}

export default Mcp
