import * as z from 'zod'

export const EmLimitDataValidator = z.object({
  c: z.string(),
  qdate: z.number(),
  m: z.number(),
  n: z.string(),
  p: z.number(),
  zdp: z.number(),
  amount: z.number(),
  ltsz: z.number(),
  tshare: z.number(),
  hs: z.number(),
  lbc: z.number(),
  fbt: z.number(),
  lbt: z.number(),
  fund: z.number(),
  zbc: z.number(),
  hybk: z.string(),
  zttj: z.object({
    days: z.number(),
    ct: z.number()
  })
})

export const HrLimitDataValidator = z.object({
  date: z.string(),
  open_num: z.number().nullable(),
  first_limit_up_time: z.string(),
  last_limit_up_time: z.string(),
  code: z.string(),
  limit_up_type: z.string(),
  order_volume: z.number(),
  is_new: z.number(),
  limit_up_suc_rate: z.number().nullable(),
  currency_value: z.number(),
  market_id: z.number(),
  is_again_limit: z.number(),
  change_rate: z.number(),
  turnover_rate: z.number(),
  reason_type: z.string(),
  order_amount: z.number(),
  high_days: z.string(),
  name: z.string(),
  high_days_value: z.number(),
  change_tag: z.string(),
  market_type: z.string(),
  latest: z.number(),
  time_preview: z.array(z.number())
})

export const EmLimitDataListValidator = z.array(EmLimitDataValidator)
export const HrLimitDataListValidator = z.array(HrLimitDataValidator)
