import { RouterProvider } from 'react-router'
import { ConfigProvider } from 'antd'
import { StyleProvider } from '@ant-design/cssinjs'
import router from './lib/router'

const App: React.FC = () => {
  return (
    <StyleProvider layer>
      <ConfigProvider>
        <RouterProvider router={router} />
      </ConfigProvider>
    </StyleProvider>
  )
}

export default App
