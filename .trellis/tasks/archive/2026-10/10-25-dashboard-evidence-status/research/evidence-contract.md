# Findings
- Previous StrategyCategories fixed every card to 待人工核对 and used catalog.missing as actual missing-data claims, without querying capability coverage.
- Read-only remote audit through an existing authenticated terminal found historical pool/board/review tables, with about three months of pool observations; positive volume counts in the two modeled volume sources were zero. No modeled full daily OHLC series adapter exists. Do not hardcode observed server counts or infrastructure identifiers.
- Existing Feishu report remains owner of candidate/factual derivations. Add bounded aggregate coverage of modeled tables and status classification only; no new trading-pattern heuristics.
- Choose separate authenticated endpoint and distinct UI load/error state so report and observation workflows remain usable if coverage query fails. Pool samples never imply continuous history; missing modeled adapter differs from absent database rows.
- Shared catalog metadata maps concepts to existing sources and evidence requirements. Full semantic patterns stay explicitly unimplemented even if data becomes available.
