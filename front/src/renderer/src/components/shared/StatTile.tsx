import { cn } from '@renderer/lib/utils/cn'

interface StatTileProps {
  label: string
  value: string | number
  suffix?: string
  tone?:
    | 'blue'
    | 'green'
    | 'purple'
    | 'orange'
    | 'red'
    | 'pink'
    | 'cyan'
    | 'amber'
}

const toneMap = {
  blue: 'text-sky-600',
  green: 'text-emerald-600',
  purple: 'text-violet-600',
  orange: 'text-orange-600',
  red: 'text-red-600',
  pink: 'text-pink-600',
  cyan: 'text-cyan-600',
  amber: 'text-amber-600'
}

const StatTile = ({ label, value, suffix, tone = 'blue' }: StatTileProps) => (
  <div className="group border-border bg-card relative overflow-hidden rounded-xl border px-4 py-3 text-center shadow-[var(--shadow-md)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow-xl)]">
    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[var(--accent-solid)] to-[var(--accent-secondary)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
    <div className="text-muted-foreground font-mono text-[10px] tracking-[0.12em] uppercase">
      {label}
    </div>
    <div
      className={cn(
        'mt-1 text-2xl font-bold tracking-tight tabular-nums',
        toneMap[tone]
      )}
    >
      {value}
      {suffix && <span className="ml-1 text-xs font-normal">{suffix}</span>}
    </div>
  </div>
)

export default StatTile
