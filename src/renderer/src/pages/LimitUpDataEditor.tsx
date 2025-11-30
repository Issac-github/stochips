import React, { useEffect, useState } from 'react'
import { Tabs, message } from 'antd'
import { JsonData } from 'json-edit-react'
import JSONEditor from '@renderer/components/shared/JSONEditor'
import { DatabaseEventKey } from '@shared/eventKey'
import { debugLog } from '@shared/logger'

const LimitUpDataEditor: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('HR')
  const [messageApi, contextHolder] = message.useMessage()

  useEffect(() => {
    const unsubscribe = window.api.database.response((event) => {
      debugLog('Database response received in LimitUpDataEditor:', event)
      if (event.error) {
        messageApi.error(`Database error: ${event.error.message}`)
      } else {
        messageApi.success('Database operation successful')
      }
    })
    return () => {
      unsubscribe()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    <>
      <Tabs
        className="limit-up-data-editor h-full"
        defaultActiveKey="HR"
        activeKey={activeTab}
        onChange={setActiveTab}
        items={['HR', 'EM'].map((value) => {
          return {
            key: value,
            label: value,
            children: <JSONEditor onSave={handleSave} loading={loading} />
          }
        })}
      />
      {contextHolder}
      <style>{`
        .limit-up-data-editor .ant-tabs-content, .limit-up-data-editor .ant-tabs-tabpane {
          height: 100%;
        }
      `}</style>
    </>
  )
}

export default LimitUpDataEditor
