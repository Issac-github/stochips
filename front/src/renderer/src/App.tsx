import { RouterProvider } from 'react-router'
import { Toaster } from '@renderer/components/shared/Toast'
import router from './lib/router'

const App: React.FC = () => {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}

export default App
