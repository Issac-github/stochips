import * as React from 'react'
import { type VariantProps, cva } from 'class-variance-authority'
import { cn } from '@renderer/lib/utils/cn'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold transition-all duration-200',
  {
    variants: {
      variant: {
        default: 'accent-gradient text-white shadow-[var(--shadow-accent)]',
        secondary: 'border border-border bg-muted text-secondary-foreground',
        destructive:
          'bg-red-500 text-white shadow-[0_4px_14px_rgba(239,68,68,0.22)]',
        outline: 'border border-accent/30 bg-accent/5 text-accent',
        success:
          'bg-emerald-500 text-white shadow-[0_4px_14px_rgba(16,185,129,0.24)]',
        warning:
          'bg-amber-400 text-slate-950 shadow-[0_4px_14px_rgba(245,158,11,0.2)]',
        info: 'bg-sky-500 text-white shadow-[0_4px_14px_rgba(14,165,233,0.22)]',
        purple: 'accent-gradient text-white shadow-[var(--shadow-accent)]'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = ({ className, variant, ...props }: BadgeProps) => (
  <div className={cn(badgeVariants({ variant }), className)} {...props} />
)

export { Badge, badgeVariants }
