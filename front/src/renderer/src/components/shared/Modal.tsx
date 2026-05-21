import { FC, ReactNode, useState } from 'react'
import { Button } from '@renderer/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@renderer/components/ui/dialog'

interface Props {
  open: boolean
  title: ReactNode
  modalContent: ReactNode
  onConfirm?: () => void
  onOk?: () => void
  onCancel?: () => void
  okText?: string
  footer?: ReactNode
}

export const StoModal: FC<Omit<Props, 'onConfirm'>> = ({
  open,
  title,
  onOk,
  onCancel,
  modalContent,
  okText = 'OK',
  footer
}) => {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel?.()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {modalContent}
        {footer ?? (
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={onOk}>{okText}</Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

const useModal = (props: Props) => {
  const [open, setOpen] = useState(false)
  const { onConfirm, ...restProps } = props

  const modal = (
    <StoModal
      {...restProps}
      open={open}
      onOk={() => {
        onConfirm?.()
        setOpen(false)
      }}
      onCancel={() => setOpen(false)}
    />
  )

  return {
    modal,
    closeModal: () => setOpen(false),
    openModal: () => setOpen(true)
  }
}

export default useModal
