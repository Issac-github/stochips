/// <reference types="vite/client" />

interface ImportMetaEnv {}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface PortMapType {
  socket: number | null
  http: number | null
  gpt: number | null
}

interface EMLimitUpData<T = { days: number; ct: number }[]> {
  id: number
  c: string
  qdate: number
  m: number
  n: string
  p: number
  zdp: number
  amount: number
  ltsz: number
  tshare: number
  hs: number
  lbc: number
  fbt: number
  lbt: number
  fund: number
  zbc: number
  hybk: string
  zttj: T
  created_at: string
  updated_at: string
}
interface HRLimitUpData<T = number[]> {
  id: number
  date: string
  open_num: number
  first_limit_up_time: string
  last_limit_up_time: string
  code: string
  limit_up_type: string
  order_volume: number
  is_new: number
  limit_up_suc_rate: number
  currency_value: number
  market_id: number
  is_again_limit: number
  change_rate: number
  turnover_rate: number
  reason_type: string
  order_amount: number
  high_days: string
  name: string
  high_days_value: number
  change_tag: string
  market_type: string
  latest: number
  time_preview: T
}

interface EMLimitUpJSONData {
  qdate: number
  pool: EMLimitUpData[]
}
interface HRLimitUpJSONData {
  date: string
  info: HRLimitUpData[]
}

type ListenerEventArgs<T = string, V = object | object[]> = {
  event: T
} & V

type DatabaseListenerEventArgs =
  | ListenerEventArgs<
      import('@shared/eventKey').DatabaseEventKey.ReadEmLimitUpData,
      {
        payload?: {
          startDate: string
          endDate: string
        }
        data?: EMLimitUpData[]
        error?: Record<string, unknown>
      }
    >
  | ListenerEventArgs<
      import('@shared/eventKey').DatabaseEventKey.ReadHrLimitUpData,
      {
        payload?: {
          startDate: string
          endDate: string
        }
        data?: HRLimitUpData[]
        error?: Record<string, unknown>
      }
    >
  | ListenerEventArgs<
      import('@shared/eventKey').DatabaseEventKey.WriteEmLimitUpData,
      {
        payload?: never
        data: EMLimitUpJSONData | EMLimitUpJSONData[]
        error?: Record<string, unknown>
      }
    >
  | ListenerEventArgs<
      import('@shared/eventKey').DatabaseEventKey.WriteHrLimitUpData,
      {
        payload?: never
        data: HRLimitUpJSONData | HRLimitUpJSONData[]
        error?: Record<string, unknown>
      }
    >
