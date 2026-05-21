import dayjs from 'dayjs'
import { CalendarDays } from 'lucide-react'
import { Input } from '@renderer/components/ui/input'

interface DateRangePickerProps {
  value: [dayjs.Dayjs, dayjs.Dayjs] | null
  onChange: (dates: null | (dayjs.Dayjs | null)[]) => void
}

const formatInput = (value: dayjs.Dayjs) => value.format('YYYY-MM-DD')

const DateRangePicker = ({ value, onChange }: DateRangePickerProps) => {
  const start = value?.[0] ?? null
  const end = value?.[1] ?? null

  return (
    <div className="border-border bg-card inline-flex items-center gap-3 rounded-xl border px-2.5 py-2 shadow-[var(--shadow-sm)]">
      <div className="accent-gradient flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white shadow-[var(--shadow-accent)]">
        <CalendarDays className="h-4 w-4" />
      </div>
      <Input
        type="date"
        className="bg-muted focus-visible:bg-card h-10 w-40 rounded-lg border-0 px-3 text-sm shadow-none"
        value={start ? formatInput(start) : ''}
        onChange={(event) => {
          const nextStart = event.target.value
            ? dayjs(event.target.value)
            : null
          onChange(nextStart && end ? [nextStart, end] : null)
        }}
      />
      <span className="text-muted-foreground inline-flex w-6 justify-center font-mono text-[10px] tracking-[0.12em] uppercase">
        to
      </span>
      <Input
        type="date"
        className="bg-muted focus-visible:bg-card h-10 w-40 rounded-lg border-0 px-3 text-sm shadow-none"
        value={end ? formatInput(end) : ''}
        onChange={(event) => {
          const nextEnd = event.target.value ? dayjs(event.target.value) : null
          onChange(start && nextEnd ? [start, nextEnd] : null)
        }}
      />
    </div>
  )
}

export default DateRangePicker
