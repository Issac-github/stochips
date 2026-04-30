import { ReactNode, useState } from 'react'
import { Drawer, DrawerProps } from 'antd'
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
    size = 960,
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

  const baseStyles = typeof styles === 'function' ? styles({ props }) : styles
  const {
    mask: maskStyle,
    section: sectionStyle,
    header: headerStyle,
    body: bodyStyle,
    footer: footerStyle,
    wrapper: wrapperStyle
  } = baseStyles || {}

  const drawerStyles: typeof baseStyles = {
    header: headerStyle,
    body: bodyStyle,
    section: { borderRadius: '5px', ...sectionStyle },
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
      size={size}
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
