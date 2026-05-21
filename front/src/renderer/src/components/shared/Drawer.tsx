import { ReactNode, useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle
} from '@renderer/components/ui/sheet'

interface Props {
  title?: ReactNode
  drawerContent: ReactNode
  placement?: 'left' | 'right' | 'top' | 'bottom'
  afterClose?: () => void
  hideDrawerHeader?: boolean
}

export const useDrawer = (props: Props) => {
  const {
    title,
    drawerContent,
    placement = 'right',
    afterClose,
    hideDrawerHeader = false
  } = props
  const [open, setOpen] = useState(false)

  const closeDrawer = () => {
    afterClose?.()
    setOpen(false)
  }

  const drawer = (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => (nextOpen ? setOpen(true) : closeDrawer())}
    >
      <SheetContent side={placement}>
        {!hideDrawerHeader && (
          <SheetHeader>
            <SheetTitle>{title}</SheetTitle>
          </SheetHeader>
        )}
        {drawerContent}
      </SheetContent>
    </Sheet>
  )

  return {
    open,
    drawer,
    openDrawer: () => setOpen(true),
    closeDrawer
  }
}
