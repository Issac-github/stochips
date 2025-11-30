import { FC } from 'react'
import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router'
import { Button, Flex, Layout, Menu, Space, theme } from 'antd'
import {
  ConsoleSqlOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ReadOutlined,
  ReconciliationOutlined,
  RobotOutlined
} from '@ant-design/icons'

const { Sider, Content } = Layout

const MainLayout: FC = () => {
  const [collapsed, setCollapsed] = useState(true)
  const navigate = useNavigate()
  const {
    token: { colorBgContainer, borderRadiusLG, colorBorderSecondary }
  } = theme.useToken()

  const handleMenuClick = (path: string) => {
    navigate(path)
  }

  return (
    <>
      <Layout className="h-screen">
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          className="flex h-screen flex-col justify-between"
          style={{ backgroundColor: colorBgContainer }}
        >
          <Flex className="h-screen" vertical>
            <Flex
              className="mx-auto w-full justify-center border-r-2 pt-8"
              style={{
                borderRightWidth: '1px',
                background: colorBgContainer,
                borderColor: colorBorderSecondary
              }}
            >
              <Space className="bg-gradient-to-r from-teal-400 to-blue-500 bg-clip-text text-lg text-transparent hover:from-pink-500 hover:to-orange-500">
                {!collapsed && <span className="font-bold">StoChips</span>}
                <Button
                  type="text"
                  icon={
                    collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />
                  }
                  onClick={() => setCollapsed(!collapsed)}
                  size="small"
                  className="h-10 w-10 text-base"
                  style={{
                    // @ts-ignore - WebkitAppRegion is a valid CSS property for Electron
                    WebkitAppRegion: 'drag'
                  }}
                />
              </Space>
            </Flex>
            <Menu
              mode="inline"
              className="h-full"
              defaultSelectedKeys={['1']}
              onClick={({ key }) => handleMenuClick(key)}
              items={[
                {
                  key: '/',
                  icon: <ReadOutlined />,
                  label: 'Home'
                },
                {
                  key: '/limit-up-data-editor',
                  icon: <ConsoleSqlOutlined />,
                  label: 'Limit Up Data Editor'
                },
                {
                  key: '/limit-up-data',
                  icon: <ReconciliationOutlined />,
                  label: 'Limit Up Data'
                },

                {
                  key: '/mcp-chat',
                  icon: <RobotOutlined />,
                  label: 'MCP Chat'
                }
              ]}
            />
          </Flex>
        </Sider>
        <Layout>
          <Content
            style={{
              margin: 6,
              padding: 16,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: borderRadiusLG
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </>
  )
}

export default MainLayout
