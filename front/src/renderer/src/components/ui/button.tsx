import * as React from 'react'
import { type VariantProps, cva } from 'class-variance-authority'
import { Slot } from '@radix-ui/react-slot'
import { cn } from '@renderer/lib/utils/cn'

const buttonVariants = cva(
  'focus-ring group inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-200 ease-out disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default:
          'accent-gradient text-white shadow-[var(--shadow-sm)] hover:-translate-y-0.5 hover:brightness-110 hover:shadow-[var(--shadow-accent-lg)]',
        destructive:
          'bg-destructive text-destructive-foreground shadow-[var(--shadow-sm)] hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(220,38,38,0.25)]',
        outline:
          'border border-border bg-card text-foreground shadow-[var(--shadow-sm)] hover:-translate-y-0.5 hover:border-accent/30 hover:bg-muted/50 hover:shadow-[var(--shadow-md)]',
        secondary:
          'border border-border bg-muted text-foreground hover:-translate-y-0.5 hover:bg-card hover:shadow-[var(--shadow-md)]',
        ghost:
          'bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground',
        link: 'text-primary underline-offset-4 hover:underline'
      },
      size: {
        default: 'px-5 py-2.5',
        sm: 'min-h-10 rounded-xl px-3 text-xs',
        lg: 'min-h-12 rounded-xl px-8',
        icon: 'h-11 w-11 p-0'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
