import { useEffect, useState, type ReactNode } from 'react'
import { Alert, Button, Card, Spin, Typography } from 'antd'
import { SafetyCertificateOutlined } from '@ant-design/icons'

export type Identity = { open_id: string; name: string; tenant_key: string }
export type AuthState = {
  configured: boolean
  authenticated: boolean
  user: Identity | null
  csrf_token: string | null
}

export async function readAuth(): Promise<AuthState> {
  const response = await fetch('/api/auth/session', { cache: 'no-store' })
  if (!response.ok) throw new Error('无法检查登录状态')
  return response.json() as Promise<AuthState>
}

export function AuthGate({ children }: { children: (auth: AuthState, refresh: () => void) => ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(null)
  const [error, setError] = useState(new URLSearchParams(location.search).get('login_error') || '')
  useEffect(() => {
    let active = true
    readAuth().then((result) => { if (active) setAuth(result) }).catch(() => { if (active) setError('无法连接看板服务') })
    return () => { active = false }
  }, [])
  useEffect(() => {
    const expire = () => setAuth((current) => current ? { ...current, authenticated: false, user: null, csrf_token: null } : current)
    window.addEventListener('auth-expired', expire)
    return () => window.removeEventListener('auth-expired', expire)
  }, [])
  const refresh = () => { setAuth(null); readAuth().then(setAuth).catch(() => setError('无法连接看板服务')) }
  if (!auth) return <main className="auth-shell"><Spin size="large" /></main>
  if (!auth.authenticated) return (
    <main className="auth-shell">
      <Card className="auth-card">
        <div className="auth-mark"><SafetyCertificateOutlined /></div>
        <Typography.Title level={2}>StoChips 市场观察</Typography.Title>
        <Typography.Paragraph type="secondary">使用 StoChips 飞书应用验证身份后查看播报数据。</Typography.Paragraph>
        {error && <Alert showIcon type="error" message={errorText(error)} className="auth-alert" />}
        {!auth.configured && <Alert showIcon type="warning" message="飞书登录尚未配置" description="在服务器环境中设置 FEISHU_APP_ID、FEISHU_APP_SECRET 和 DASHBOARD_PUBLIC_URL，再重启看板。" className="auth-alert" />}
        <Button type="primary" size="large" block disabled={!auth.configured} href="/api/auth/feishu/login">使用飞书登录</Button>
      </Card>
    </main>
  )
  return <>{children(auth, refresh)}</>
}

function errorText(code: string) {
  const labels: Record<string, string> = { access_denied: '你取消了飞书授权。', forbidden: '此飞书账号未获准访问看板。', invalid_state: '登录链接已失效，请重新开始。', invalid_code: '飞书没有返回有效授权，请重试。', upstream_error: '飞书身份验证失败，请稍后重试。', busy: '当前登录请求较多，请稍后重试。', not_configured: '飞书登录尚未配置。' }
  return labels[code] || '登录失败，请重试。'
}
