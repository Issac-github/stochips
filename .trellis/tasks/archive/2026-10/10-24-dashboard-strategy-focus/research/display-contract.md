# Existing display contract

- `daily_market_review_agent.py` already requires five Markdown sections: 情绪定位、主线与梯队、龙头与助攻、风险与反证、次日验证清单。保留每节正文，避免将一句情绪判断脱离反证展示。
- Report has no historical volume, auction/opening gap or intraday first-tick data. Never infer 天量、弱转强、平台突破 from turnover, board counts or isolated breakout records.
- `leader_assists` includes non-one-word and first-board candidates, from same-reason/block + earlier first-limit time. It is retrospective and does not establish intraday validity or causality.
- `previous_high_feedback` distinguishes continued promotion, still-limit-up outside continuous pool and not in limit-up pool. The last does not imply 跌停/按钮.
- `top_stocks` ordered by backend; height is not equivalent to market leader classification. Render as observation records, not recommended targets.
- Keep Python as calculation owner; display the existing report and cached review. No new recommendation or methodology text exposed.
