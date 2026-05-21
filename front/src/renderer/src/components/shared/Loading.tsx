import React from 'react'

const Loading: React.FC = () => {
  return (
    <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm">
      <div className="flex flex-col items-center space-y-6">
        <div className="relative h-20 w-20">
          <div className="border-accent/15 absolute inset-0 animate-spin rounded-full border-4">
            <div className="bg-accent absolute top-0 left-1/2 -mt-1 -ml-1 h-2 w-2 rounded-full" />
          </div>
          <div className="absolute inset-2 -scale-x-100 animate-spin rounded-full border-2 border-slate-200">
            <div className="absolute bottom-0 left-1/2 -mb-0.5 -ml-0.5 h-1.5 w-1.5 rounded-full bg-[var(--accent-secondary)]" />
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="accent-gradient h-3 w-3 animate-pulse rounded-full" />
          </div>
        </div>
        <div className="space-y-2 text-center">
          <div className="flex space-x-1">
            <div className="bg-accent h-2 w-2 animate-bounce rounded-full" />
            <div
              className="h-2 w-2 animate-bounce rounded-full bg-[var(--accent-secondary)]"
              style={{ animationDelay: '0.15s' }}
            />
            <div
              className="h-2 w-2 animate-bounce rounded-full bg-slate-400"
              style={{ animationDelay: '0.3s' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Loading
