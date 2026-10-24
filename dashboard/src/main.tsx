import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import 'antd/dist/reset.css'
import App from './App'
import { AuthGate } from './AuthGate'
import './style.css'

dayjs.locale('zh-cn')
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#3867eb',
          borderRadius: 10,
          fontFamily:
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif',
          colorText: '#202939',
          colorTextSecondary: '#667085',
          colorBorderSecondary: '#edf0f5',
        },
      }}
    >
      <AuthGate>{(auth, refresh) => <App auth={auth} onAuthChange={refresh} />}</AuthGate>
    </ConfigProvider>
  </React.StrictMode>,
)
