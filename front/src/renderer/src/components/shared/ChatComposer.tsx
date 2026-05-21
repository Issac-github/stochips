import { Send, Square } from 'lucide-react'
import { Button } from '@renderer/components/ui/button'
import { Textarea } from '@renderer/components/ui/textarea'

interface ChatComposerProps {
  value: string
  placeholder?: string
  loading?: boolean
  disabled?: boolean
  onChange: (value: string) => void
  onSubmit: () => void
  onStop?: () => void
}

const ChatComposer = ({
  value,
  placeholder,
  loading = false,
  disabled = false,
  onChange,
  onSubmit,
  onStop
}: ChatComposerProps) => {
  return (
    <div className="border-border bg-card flex items-end gap-3 rounded-2xl border p-3 shadow-[var(--shadow-md)]">
      <Textarea
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        rows={2}
        className="min-h-14 resize-none rounded-xl"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            onSubmit()
          }
        }}
      />
      {loading && onStop ? (
        <Button type="button" size="icon" variant="outline" onClick={onStop}>
          <Square className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          type="button"
          size="icon"
          disabled={disabled || loading}
          onClick={onSubmit}
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}

export default ChatComposer
