import * as React from 'react'
import { cn } from '@renderer/lib/utils/cn'

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<'textarea'>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'focus-ring border-input bg-card text-foreground placeholder:text-muted-foreground/55 focus-visible:border-accent flex min-h-24 w-full rounded-xl border px-4 py-3 text-sm shadow-[var(--shadow-sm)] transition-all duration-200 outline-none disabled:cursor-not-allowed disabled:opacity-50',
      className
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'

export { Textarea }
