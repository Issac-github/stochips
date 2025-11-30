import { createHashRouter } from 'react-router'
import MainLayout from '@renderer/components/layout/MainLayout'
import RootBoundary from '@renderer/components/layout/RootBoundary'
import Introduction from '@renderer/pages/Introduction'
import LimitUpData from '@renderer/pages/LimitUpData'
import LimitUpDataEditor from '@renderer/pages/LimitUpDataEditor'
import Mcp from '@renderer/pages/Mcp'

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
        path: '/limit-up-data-editor',
        element: <LimitUpDataEditor />
      },
      {
        path: '/limit-up-data',
        element: <LimitUpData />
      },
      {
        path: '/mcp-chat',
        element: <Mcp />
      }
    ]
  }
])

export default router
