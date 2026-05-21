/* eslint-disable react/prop-types */
import { useState } from 'react'
import { JsonData, JsonEditor } from 'json-edit-react'
import { Save, Trash2 } from 'lucide-react'
import { toast } from '@renderer/components/shared/Toast'
import { Button } from '@renderer/components/ui/button'

interface JSONEditorProps {
  onSave?: (data: JsonData) => void | Promise<void>
  loading?: boolean
}

const JSONEditor: React.FC<JSONEditorProps> = ({ onSave, loading = false }) => {
  const [data, setData] = useState<JsonData>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    if (!data) {
      toast.warning('No data to save')
      return
    }
    setIsSaving(true)
    try {
      if (onSave) {
        await onSave(data)
      }
      toast.success('Data saved successfully')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      toast.error('Failed to save data', errorMsg)
    } finally {
      setIsSaving(false)
    }
  }

  const handleClear = () => {
    if (!data) {
      toast.info('No data to clear')
      return
    }

    setData(null)
    toast.success('Data cleared')
  }

  return (
    <div className="flex h-full flex-col items-start gap-5">
      <div className="border-border bg-card flex gap-3 rounded-xl border p-3 shadow-[var(--shadow-md)]">
        <Button
          type="button"
          onClick={handleSave}
          disabled={!data || isSaving || loading}
        >
          <Save className="h-4 w-4" />
          Save
        </Button>
        <Button
          type="button"
          variant="destructive"
          onClick={handleClear}
          disabled={!data}
        >
          <Trash2 className="h-4 w-4" />
          Clear
        </Button>
      </div>
      <div className="border-border bg-card h-full w-full flex-1 overflow-auto rounded-2xl border p-4 shadow-[var(--shadow-lg)]">
        <JsonEditor
          data={data}
          setData={setData}
          className="h-full w-full max-w-full! overflow-auto"
        />
      </div>
    </div>
  )
}

export default JSONEditor
