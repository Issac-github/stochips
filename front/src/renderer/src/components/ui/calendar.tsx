import { DayPicker, type DayPickerProps } from 'react-day-picker'
import { cn } from '@renderer/lib/utils/cn'

const Calendar = ({ className, classNames, ...props }: DayPickerProps) => (
  <DayPicker
    className={cn('p-3', className)}
    classNames={{
      root: 'text-sm',
      month_caption: 'mb-2 text-center font-medium',
      months: 'flex flex-col gap-4',
      month: 'space-y-2',
      weekdays: 'grid grid-cols-7 text-muted-foreground',
      weekday: 'text-center text-xs font-normal',
      week: 'grid grid-cols-7',
      day: 'h-8 w-8 rounded-md text-center hover:bg-accent',
      selected: 'bg-primary text-primary-foreground hover:bg-primary',
      today: 'border border-primary',
      outside: 'text-muted-foreground opacity-50',
      ...classNames
    }}
    {...props}
  />
)

export { Calendar }
