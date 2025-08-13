import { FC, ReactNode, useState } from 'react'
import { Modal, ModalProps } from 'antd'

interface Props extends ModalProps {
  open: boolean
  title: ReactNode
  modalContent: ReactNode
  onConfirm?: () => void
}

export const StoModal: FC<Omit<Props, 'onConfirm'>> = ({
  open,
  title,
  onOk,
  onCancel,
  modalContent,
  confirmLoading = false,
  okText = 'OK',
  okType = 'primary',
  centered = true,
  footer,
  width = 520,
  closeIcon = true,
  maskClosable = true
}) => {
  return (
    <Modal
      title={title}
      open={open}
      onOk={onOk}
      onCancel={onCancel}
      centered={centered}
      destroyOnHidden
      confirmLoading={confirmLoading}
      okText={okText}
      okType={okType}
      footer={footer}
      width={width}
      maskClosable={maskClosable}
      closeIcon={closeIcon}
    >
      {modalContent}
    </Modal>
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
        props.onConfirm?.()
        setOpen(false)
      }}
      onCancel={() => {
        setOpen(false)
      }}
    />
  )

  return {
    modal,
    closeModal: () => {
      setOpen(false)
    },
    openModal: () => {
      setOpen(true)
    }
  }
}

// eslint-disable-next-line react-refresh/only-export-components
export default useModal
