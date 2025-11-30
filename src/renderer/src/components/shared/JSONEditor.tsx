/* eslint-disable react/prop-types */
import { useState } from 'react'
import { Button, Space, message } from 'antd'
import { JsonData, JsonEditor } from 'json-edit-react'
import { DeleteOutlined, SaveOutlined } from '@ant-design/icons'

interface JSONEditorProps {
  onSave?: (data: JsonData) => void | Promise<void>
  loading?: boolean
}

const JSONEditor: React.FC<JSONEditorProps> = ({ onSave, loading = false }) => {
  const [data, setData] = useState<JsonData>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    if (!data) {
      message.warning('No data to save')
      return
    }
    setIsSaving(true)
    try {
      if (onSave) {
        await onSave(data)
      }
      message.success('Data saved successfully')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      message.error(`Failed to save data: ${errorMsg}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleClear = () => {
    if (!data) {
      message.info('No data to clear')
      return
    }

    setData(null)
    message.success('Data cleared')
  }

  return (
    <div className="flex h-full flex-col items-start gap-4">
      <Space>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={isSaving || loading}
          disabled={!data}
        >
          Save
        </Button>
        <Button
          danger
          icon={<DeleteOutlined />}
          onClick={handleClear}
          disabled={!data}
        >
          Clear
        </Button>
      </Space>
      <div className="h-full w-full flex-1 overflow-auto">
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
