import { FC, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Database,
  Home,
  LineChart,
  NotebookText
} from 'lucide-react'
import { Button } from '@renderer/components/ui/button'
import { cn } from '@renderer/lib/utils/cn'

const navItems = [
  { key: '/', label: 'Home', icon: Home },
  {
    key: '/limit-up-data-editor',
    label: 'Limit Up Data Editor',
    icon: Database
  },
  { key: '/limit-up-data', label: 'Limit Up Data', icon: LineChart },
  { key: '/mcp-chat', label: 'MCP Chat', icon: Bot }
]

const MainLayout: FC = () => {
  const [collapsed, setCollapsed] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="bg-background text-foreground flex h-screen overflow-hidden p-4">
      <aside
        className={cn(
          'dot-pattern bg-foreground relative mt-3 mb-2 flex h-[calc(100%-1.25rem)] shrink-0 flex-col overflow-hidden rounded-2xl p-3 text-white shadow-[var(--shadow-xl)] transition-all duration-300',
          collapsed ? 'w-[86px]' : 'w-[252px]'
        )}
      >
        <div className="pointer-events-none absolute -top-24 -right-20 h-56 w-56 rounded-full bg-[var(--accent-solid)]/20 blur-[90px]" />
        <div className="flex h-16 items-center justify-between px-1">
          <div
            className={cn(
              'relative z-10 flex items-center gap-3',
              collapsed && 'justify-center'
            )}
          >
            <div className="accent-gradient flex h-13 w-13 items-center justify-center rounded-xl text-white shadow-[var(--shadow-accent)]">
              <NotebookText className="h-6 w-6" />
            </div>
            {!collapsed && (
              <div>
                <span className="font-display text-lg tracking-tight text-white">
                  StoChips
                </span>
                <div className="font-mono text-[10px] tracking-[0.15em] text-white/55 uppercase">
                  Market Lab
                </div>
              </div>
            )}
          </div>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className={cn(
              'relative z-10 h-11 w-11 rounded-xl text-white/70 hover:bg-white/10 hover:text-white',
              collapsed && 'hidden'
            )}
            onClick={() => setCollapsed((value) => !value)}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
        <nav className="relative z-10 mt-5 flex flex-1 flex-col gap-3">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.key
            return (
              <button
                key={item.key}
                type="button"
                title={collapsed ? item.label : undefined}
                onClick={() => navigate(item.key)}
                className={cn(
                  'focus-ring flex min-h-12 items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold transition-all duration-200',
                  active
                    ? 'accent-gradient text-white shadow-[var(--shadow-accent)]'
                    : 'text-white/62 hover:-translate-y-0.5 hover:bg-white/10 hover:text-white',
                  collapsed && 'justify-center px-0'
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </button>
            )
          })}
        </nav>
        {collapsed && (
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="relative z-10 mx-auto mb-1 h-13 w-13 rounded-xl border-white/15 bg-white/10 text-white hover:bg-white/15"
            onClick={() => setCollapsed(false)}
          >
            <ChevronRight className="h-5 w-5" />
          </Button>
        )}
      </aside>
      <main className="min-w-0 flex-1 pl-5">
        <section className="border-border bg-card h-full overflow-hidden rounded-2xl border p-5 shadow-[var(--shadow-lg)]">
          <Outlet />
        </section>
      </main>
    </div>
  )
}

export default MainLayout
