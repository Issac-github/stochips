# Existing contracts and approach
- Details already renders all fields, nested modal, search, sort and pagination. Add optional dataset scope rather than a second table implementation.
- Saved daily review has conservative five-section parsing. Only show whole mapped sections if fully recognized; legacy review remains complete.
- Watchlist annotations already use SQLite + Feishu owner + revision. Add a separate observation_concepts table without changing the original observations column count, and use explicit SQL columns and preserve omitted values for old requests.
- Choices: UI-only concept list cannot classify saved observations; automatic classification lacks required OHLCV/auction facts; shared static catalog + manual labels meets the request using existing evidence.
- Existing report breakouts cover historical chain price comparison, not platform shape; no numeric score or implied pattern confirmation.
- Future real historical candles may enrich evidence later. Current labels are independent from source roles and manual validation result; date/user isolation and legacy compatibility are required.
