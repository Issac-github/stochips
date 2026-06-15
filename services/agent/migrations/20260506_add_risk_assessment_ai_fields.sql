-- Add structured AI assessment fields for existing MySQL databases.
-- Safe to run once after pulling the schema/model changes.

ALTER TABLE risk_assessment
    ADD COLUMN rule_score DECIMAL(5,2) DEFAULT NULL COMMENT '规则引擎风险分数' AFTER risk_factors,
    ADD COLUMN ai_score DECIMAL(5,2) DEFAULT NULL COMMENT 'AI风险分数' AFTER rule_score,
    ADD COLUMN ai_confidence DECIMAL(5,4) DEFAULT NULL COMMENT 'AI分析置信度' AFTER ai_score,
    ADD COLUMN score_calculation TEXT DEFAULT NULL COMMENT '综合分数计算说明' AFTER ai_confidence,
    ADD COLUMN ai_factors TEXT DEFAULT NULL COMMENT 'AI关键因子JSON' AFTER score_calculation,
    ADD COLUMN ai_analysis_report TEXT DEFAULT NULL COMMENT 'AI分析报告' AFTER ai_factors,
    ADD COLUMN is_ai_analyzed TINYINT DEFAULT 0 COMMENT '是否完成AI分析' AFTER ai_analysis_report;
