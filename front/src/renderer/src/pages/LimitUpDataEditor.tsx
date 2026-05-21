import React, { useEffect, useState } from 'react'
import { JsonData } from 'json-edit-react'
import JSONEditor from '@renderer/components/shared/JSONEditor'
import { toast } from '@renderer/components/shared/Toast'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '@renderer/components/ui/tabs'
import { DatabaseEventKey } from '@shared/eventKey'
import { debugLog } from '@shared/logger'

const LimitUpDataEditor: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('HR')

  useEffect(() => {
    const unsubscribe = window.api.database.response((event) => {
      debugLog('Database response received in LimitUpDataEditor:', event)
      if (event.error) {
        const message =
          event.error instanceof Error
            ? event.error.message
            : typeof event.error === 'string'
              ? event.error
              : JSON.stringify(event.error)
        toast.error('Database error', message)
      } else {
        toast.success('Database operation successful')
      }
    })
    return () => unsubscribe()
  }, [])

  const handleSave = async (data: JsonData) => {
    setLoading(true)
    try {
      if (activeTab === 'EM') {
        window.api.database.request({
          event: DatabaseEventKey.WriteEmLimitUpData,
          data: data as EMLimitUpJSONData | EMLimitUpJSONData[]
        })
      } else if (activeTab === 'HR') {
        window.api.database.request({
          event: DatabaseEventKey.WriteHrLimitUpData,
          data: data as HRLimitUpJSONData | HRLimitUpJSONData[]
        })
      }
      debugLog(`Data saved for ${activeTab}`)
    } catch (error) {
      debugLog('Error saving data:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="flex h-full flex-col gap-5"
    >
      <div className="border-border bg-card flex items-center justify-between rounded-2xl border p-5 shadow-[var(--shadow-md)]">
        <div>
          <div className="border-accent/30 bg-accent/5 mb-2 inline-flex items-center gap-2 rounded-full border px-3 py-1">
            <span className="bg-accent h-2 w-2 animate-[pulse-dot_2s_infinite] rounded-full" />
            <span className="text-accent font-mono text-[10px] tracking-[0.15em] uppercase">
              JSON Console
            </span>
          </div>
          <h1 className="font-display text-2xl tracking-tight">
            Data <span className="gradient-text">Editor</span>
          </h1>
        </div>
        <TabsList>
          <TabsTrigger value="HR">HR</TabsTrigger>
          <TabsTrigger value="EM">EM</TabsTrigger>
        </TabsList>
      </div>
      {['HR', 'EM'].map((value) => (
        <TabsContent key={value} value={value} className="min-h-0 flex-1">
          <JSONEditor onSave={handleSave} loading={loading} />
        </TabsContent>
      ))}
    </Tabs>
  )
}

export default LimitUpDataEditor
