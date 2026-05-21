import { useEffect, useState } from 'react'
import {
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from '@renderer/components/ui/toast'
import { cn } from '@renderer/lib/utils/cn'

type ToastKind = 'success' | 'error' | 'warning' | 'info'

interface ToastItem {
  id: number
  kind: ToastKind
  title: string
  description?: string
}

type Listener = (items: ToastItem[]) => void

let items: ToastItem[] = []
const listeners = new Set<Listener>()

const notify = (kind: ToastKind, title: string, description?: string) => {
  items = [
    ...items,
    { id: Date.now() + Math.random(), kind, title, description }
  ]
  listeners.forEach((listener) => listener(items))
}

export const toast = {
  success: (title: string, description?: string) =>
    notify('success', title, description),
  error: (title: string, description?: string) =>
    notify('error', title, description),
  warning: (title: string, description?: string) =>
    notify('warning', title, description),
  info: (title: string, description?: string) =>
    notify('info', title, description)
}

export const Toaster = () => {
  const [visibleItems, setVisibleItems] = useState(items)

  useEffect(() => {
    listeners.add(setVisibleItems)
    return () => {
      listeners.delete(setVisibleItems)
    }
  }, [])

  const remove = (id: number) => {
    items = items.filter((item) => item.id !== id)
    listeners.forEach((listener) => listener(items))
  }

  return (
    <ToastProvider>
      {visibleItems.map((item) => (
        <Toast
          key={item.id}
          open
          onOpenChange={(open) => {
            if (!open) remove(item.id)
          }}
          className={cn(
            item.kind === 'success' && 'border-emerald-200',
            item.kind === 'error' && 'border-red-200',
            item.kind === 'warning' && 'border-amber-200',
            item.kind === 'info' && 'border-sky-200'
          )}
        >
          <ToastTitle>{item.title}</ToastTitle>
          {item.description && (
            <ToastDescription>{item.description}</ToastDescription>
          )}
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  )
}
