import { FC } from 'react'
import { useState } from 'react'
import { Outlet } from 'react-router'
// import chipsImage from '@renderer/assets/images/chips.svg'

import { Button, Flex, Layout, Menu, Space, theme } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ReadOutlined,
  UploadOutlined,
  VideoCameraOutlined
} from '@ant-design/icons'

const { Sider, Content } = Layout

const MainLayout: FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const {
    token: { colorBgContainer, borderRadiusLG, colorBorderSecondary }
  } = theme.useToken()

  return (
    <>
      <Layout className="h-screen">
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          className="flex h-screen flex-col justify-between"
          style={{ backgroundColor: colorBgContainer }}
          // style={
          //   {
          //     backgroundColor: colorBgContainer,
          //     WebkitAppRegion: 'drag'
          //   } as React.CSSProperties
          // }
        >
          <Flex className="h-screen" vertical>
            <Flex
              className="mx-auto w-full justify-center pt-8"
              style={{
                borderRightWidth: '1px',
                background: colorBgContainer,
                borderColor: colorBorderSecondary
              }}
            >
              <Space className="bg-gradient-to-r from-teal-400 to-blue-500 bg-clip-text text-lg text-transparent hover:from-pink-500 hover:to-orange-500">
                {/* <Image src={chipsImage} preview={false} className="w-8 h-8" /> */}
                {!collapsed && <span className="font-bold">StoChips</span>}
                <Button
                  type="text"
                  icon={
                    collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />
                  }
                  onClick={() => setCollapsed(!collapsed)}
                  size="small"
                  style={{
                    fontSize: '16px',
                    width: 40,
                    height: 40
                  }}
                />
              </Space>
            </Flex>
            <Menu
              mode="inline"
              className="h-full"
              defaultSelectedKeys={['1']}
              items={[
                {
                  key: '1',
                  icon: <ReadOutlined />,
                  label: 'Today'
                },
                {
                  key: '2',
                  icon: <VideoCameraOutlined />,
                  label: 'This Week'
                },
                {
                  key: '3',
                  icon: <UploadOutlined />,
                  label: 'This Month'
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
