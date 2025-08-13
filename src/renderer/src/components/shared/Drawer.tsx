import { ReactNode, useState } from 'react'
import { Drawer, DrawerProps } from 'antd'
import { DrawerStyles } from 'antd/es/drawer/DrawerPanel'
import { CloseOutlined } from '@ant-design/icons'
import { detectMacOs } from '@renderer/lib/utils/device'

interface Props extends DrawerProps {
  drawerContent: ReactNode
  drawerButton?: ReactNode
  hideDrawerHeader?: boolean
  afterClose?: () => void
}

export const useDrawer = (props: Omit<Props, 'drawerButton'>) => {
  const {
    title,
    drawerContent,
    styles,
    width = 960,
    placement = 'right',
    extra = <></>,
    destroyOnHidden = false,
    afterClose,
    forceRender = false,
    getContainer = document.querySelector('body') ?? false,
    mask = true,
    hideDrawerHeader = false
  } = props
  let wrapperPadding = '6px 6px 6px 0'
  switch (placement) {
    case 'right':
      wrapperPadding = '6px 6px 6px 0'
      break
    case 'left':
      wrapperPadding = '6px 0 6px 6px'
      break
    case 'top':
      wrapperPadding = '6px 6px 0 6px'
      break
    case 'bottom':
      wrapperPadding = '0 6px 6px 6px'
      break
    default:
      break
  }
  const {
    mask: maskStyle,
    content: contentStyle,
    header: headerStyle,
    body: bodyStyle,
    footer: footerStyle,
    wrapper: wrapperStyle
  } = styles || {}
  const drawerStyles: DrawerStyles = {
    header: headerStyle,
    body: bodyStyle,
    content: { borderRadius: '5px', ...contentStyle },
    wrapper: {
      borderRadius: '5px',
      padding: detectMacOs() ? wrapperPadding : 0,
      ...wrapperStyle
    },
    mask: maskStyle,
    footer: footerStyle
  }

  const [open, setOpen] = useState(false)
  const openDrawer = () => {
    setOpen(true)
  }
  const closeDrawer = () => {
    afterClose?.()
    setOpen(false)
  }

  const drawer = (
    <Drawer
      title={title}
      placement={placement}
      onClose={closeDrawer}
      open={open}
      width={width}
      styles={drawerStyles}
      extra={extra}
      destroyOnHidden={destroyOnHidden}
      forceRender={forceRender}
      getContainer={getContainer}
      mask={mask}
    >
      {drawerContent}
      {hideDrawerHeader && (
        <CloseOutlined
          onClick={closeDrawer}
          style={{
            position: 'absolute',
            right: '25px',
            top: '25px',
            fontSize: '16px',
            color: 'rgb(140, 140, 140)'
          }}
        />
      )}
    </Drawer>
  )
  return {
    open,
    drawer,
    openDrawer,
    closeDrawer
  }
}
