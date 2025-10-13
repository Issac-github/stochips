import { createHashRouter } from 'react-router'
import MainLayout from '@renderer/components/layout/MainLayout'
import RootBoundary from '@renderer/components/layout/RootBoundary'
import McpChat from '@renderer/components/mcp/McpChat'
import StreamChat from '@renderer/components/mcp/StreamChat'
import Introduction from '@renderer/pages/Introduction'

const router = createHashRouter([
  {
    path: '/',
    element: <MainLayout />,
    errorElement: <RootBoundary />,
    children: [
      {
        path: '/',
        element: <Introduction />
      },
      {
        path: '/mcp-chat',
        element: <McpChat />
        // element: <StreamChat />
      }
    ]
  }
])

export default router
