# 策略分类状态与数据库证据覆盖

## Goal
移除固定“待人工核对”和静态缺失断言，按选择日期读取数据库真实覆盖、现有事实与候选，并区分缺数据、未接入和模式识别未实现。

## Requirements
- 独立认证只读 GET /api/strategy-evidence?date=YYYY-MM-DD；汇总不晚于所选日期的观测记录、日期/股票数量、起止日期、有效价格和正成交量记录数。
- 只统计已支持的行情池表，明确池内样本不等于每只股票连续日线；不从池内最高量推断历史天量。
- 能力状态区分已有记录、部分数据、字段缺失、接口未接入。连续OHLCV、竞价、分时未接入不能表述为数据库必然没有这些数据。
- 概念按共享目录声明来源、必需证据、事实/候选/模式/人工类型。事实和现有候选显示真实条数与去重股票数；完整模式识别未实现必须明确。
- 取消所有卡片固定待核对；平台模式可以有前高关联候选，但不能据此宣称平台成立。缺失条件列出实际状态与解释。
- 页面展示实时覆盖表、状态/来源卡、已有分析与原始表；读取失败/日期变化不得遗留旧状态或退回固定结论。保留人工分类和所有原有流程。
- 仅本地实现、测试、一个提交，不抓取补数、不修改行情库、不部署。

## Acceptance Criteria
- [x] 覆盖统计真实、日期有界、0与NULL/未采集区分，无写入或敏感配置泄漏。
- [x] 全部16概念都有状态，已有事实/候选/数据缺口/识别未实现含义清晰。
- [x] 非连续池内数据不被当成完整K线或历史天量，竞价与分时缺口正确。
- [x] lint/build、前后端回归与HTTP认证/错误测试、浏览器动态状态与移动布局通过。

## Verification
- `dashboard/test_strategy_evidence.py` plus backend report/auth/watchlist regression suite: 42 passed. Includes date bounds, 0 vs uncollected fields, sparse-volume caveats, candidate deduplication, unimplemented-pattern status, authentication, invalid dates, no-store errors, and SELECT-only query assertions.
- `npm run lint`, `npm run build`, and `npm test`: passed; frontend tests 11 passed.
- Local browser fixture: dynamic evidence states and coverage, date-change/failure clearing, retry path, and 375px viewport without page overflow verified. The fixture uses synthetic data and a temporary local database.
- No production database writes, market-data collection, or deployment performed.

## Research References
- research/evidence-contract.md
