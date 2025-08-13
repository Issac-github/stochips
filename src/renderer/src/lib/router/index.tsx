import { createHashRouter } from 'react-router'
import MainLayout from '@renderer/components/layout/MainLayout'
import RootBoundary from '@renderer/components/layout/RootBoundary'
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
      }
    ]
  }
])

export default router
