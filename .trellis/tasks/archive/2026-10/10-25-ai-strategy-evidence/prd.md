# AI 辅助解释策略概念证据

## Goal

让每日 AI 复盘主动解释已有数据与策略概念的关系，给出候选结论、证据、反证、置信度和缺失项；把人工确认留给定义边界模糊或材料冲突的情况，减少看板把整理任务转交给用户。

## What I already know

- 用户希望由 AI 处理策略概念的综合判断，而不是要求用户逐项人工核对。
- 看板已有只读 `/api/strategy-evidence`、16 个概念目录和证据覆盖统计，但没有完整模式分类器。
- 每日 Codex 复盘已将分析保存在 `daily_market_review`，包含情绪、主线与梯队、龙头与助攻、风险与反证、次日验证五节。
- 现有策略复盘由 `DailyMarketReviewAgent` 调用模型；看板 API 当前不触发模型，也不生成分析。
- 可用事实是已保存复盘和报告已有行情记录；连续日线、竞价、分钟数据在看板尚未接入。

## Requirements

- 在现有每日复盘的一次模型调用中，同时生成现有 Markdown 复盘和 16 个概念的结构化证据判断；记录同日保存，打开看板只读取已有结果。
- AI 结论是带来源的研究判断，不等同于确定事实或自动交易信号。
- 每个概念输出结论类别（事实/候选/证据不足/证据冲突/不适用）、简洁解释、所引用的当日事实、反证/不确定性、缺失数据，以及定性置信度；不得为填满概念而编造结论。
- 只引用当日模型输入中真实存在的来源和字段；事实、推断与缺失信息必须分开表达。
- 后端校验结构化输出；无效、缺项或来源无法追溯时，不覆盖已有有效结论，保留旧版 Markdown 复盘行为并报告生成失败。
- 旧日期无结构化结果时显示“尚未生成”，不触发模型调用；仅通过既有每日任务或明确强制重跑更新。
- 更新复盘正文和结构化结果须按同一日期原子保存；失败不留下正文/判断不一致的半成品。

## Decision (ADR-lite)

**Context**: 看板目前只显示简短每日复盘和事实覆盖，所有16个策略概念都没有 AI 结构化解释。每次访问看板调用模型会增加延迟/调用量，并可能对同一日期产生不一致结果。

**Decision**: 将结构化概念证据加入现有每日复盘的同一次模型调用并与 Markdown 复盘一并保存；看板只读持久化结果。用户已选择“每日复盘生成并保存”。

**Consequences**: 复用现有分析流程且每日结果稳定，但旧复盘不会自动补跑；需处理结构化持久化兼容、模型输出校验和旧日期未生成状态。

## Acceptance Criteria

- [x] 正常每日调用可为目录中的16个概念返回结构化判断，不产生额外模型调用。
- [x] 每个判断至少含结论类别、解释、来源引用、反证/不确定点、缺失数据和定性置信度；可以明确为证据不足或不适用。
- [x] AI 判断可追溯到所选日期的真实输入材料；没有行情事实支撑的判断不得显示为已确认。
- [x] 缺失行情、无观测、模型错误、格式错误、有效的负向证据和证据冲突彼此区分。
- [x] 无效模型结果不覆盖已有有效结果；失败不破坏旧版 Markdown 复盘。
- [x] 页面清楚标记尚未生成、读取失败和已生成结果；看板读取不触发模型。
- [x] 原有报告和飞书复盘显示兼容，历史记录可读且数据库升级有迁移路径。

## Definition of Done (team quality bar)

- 对模型输出校验和回归测试覆盖缺失、冲突、无效 JSON、超时等情况。
- lint、类型检查、相关测试和看板浏览器检查通过。
- 文档说明 AI 推断、来源引用及无法判断的边界。

## Out of Scope (explicit)

- 自动交易、收益预测或把 AI 标签当作买卖指令。
- 在尚未接入时声称使用了完整 OHLCV、竞价、分钟/逐笔数据。
- 把详细私有策略原文复制到看板或公开提交。

## Technical Approach

- 扩展现有 `DailyMarketReviewAgent` 的 prompt，让单次结果返回 Markdown 正文与独立结构化概念结论。
- 为 `daily_market_review` 增加可空结构化 JSON/TEXT 字段及向前兼容迁移；旧行字段为空代表尚未生成。
- 在 `_save` 之前完整校验概念 key 集合、状态、必需字段和引用来源；同一数据库事务更新正文与结论。
- `FeishuStockNotifier` 的旧 `content` Markdown 不包含机器 JSON；报告 API 增加独立结构化字段，前端根据日期展示。
- 概念关联仍由现有目录元信息约束，不把内部策略文档逐字输出或复制到 UI。
- 结构化结果保存模型/provider、源材料 digest 和 schema 版本（若可复用现有列则不重复保存），保证可追溯及以后重跑识别。

## Out of Scope

- 自动交易、收益预测或把 AI 标签当作买卖指令。
- 额外的看板按需模型调用或历史数据批量重跑。
- 声称使用未接入的完整 OHLCV、竞价、分钟/逐笔数据。
- 把详细私有策略原文复制到看板或公开提交。

## Technical Notes

- `services/agent/chain/stock/agents/daily_market_review_agent.py` owns current daily Codex review generation.
- `dashboard/strategy_evidence.py` builds bounded factual coverage and must remain a read-only adapter.
- `dashboard/src/StrategyCategories.tsx` presents existing facts and status labels.
- `services/agent/chain/stock/agents/daily_market_review_agent.py` currently requires a private strategy file and daily facts, reuses a saved result by default, and replaces it only on force rerun.
- `DailyMarketReview` keeps the existing Markdown, provider/model, strategy path and source digest; new nullable JSON text is added by `20261025_add_daily_strategy_evidence.sql` and auto-applied by the existing migration runner.
- The main `FeishuStockReport` contract currently serializes `DailyReviewSummary` with `content/provider/model`; keep Markdown `content` compatible.

## Verification

- Backend unit/HTTP regression: **100 passed**, including single-call/cache behavior, full 16-concept schema, citation membership and exact field-value checks, invalid output preserving the last saved review, Feishu Markdown compatibility, read-only API serialization, auth, and existing evidence/watchlist behavior.
- Dashboard: `npm run lint`, `npm run build`, and `npm test` passed (**12 frontend tests**). Production build reports existing large-chunk and Zod comment warnings.
- `docker compose -f docker-compose.yml -f docker-compose.dashboard.yml config --quiet` and `git diff --check` passed.
- No live model invocation, production database write, migration execution, or deployment performed.
