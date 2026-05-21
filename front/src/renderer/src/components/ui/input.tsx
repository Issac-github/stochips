import * as React from 'react'
import { cn } from '@renderer/lib/utils/cn'

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        'focus-ring border-input bg-card text-foreground placeholder:text-muted-foreground/55 focus-visible:border-accent flex h-12 w-full rounded-xl border px-4 py-2 text-sm shadow-[var(--shadow-sm)] transition-all duration-200 outline-none disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'

export { Input }
