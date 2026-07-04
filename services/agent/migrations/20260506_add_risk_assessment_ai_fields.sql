-- Add structured AI assessment fields for existing MySQL databases.
-- Keep each column idempotent so partially migrated databases can still start.

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN rule_score DECIMAL(5,2) DEFAULT NULL COMMENT ''规则引擎风险分数'' AFTER risk_factors',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'rule_score'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN ai_score DECIMAL(5,2) DEFAULT NULL COMMENT ''AI风险分数'' AFTER rule_score',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'ai_score'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN ai_confidence DECIMAL(5,4) DEFAULT NULL COMMENT ''AI分析置信度'' AFTER ai_score',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'ai_confidence'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN score_calculation TEXT DEFAULT NULL COMMENT ''综合分数计算说明'' AFTER ai_confidence',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'score_calculation'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN ai_factors TEXT DEFAULT NULL COMMENT ''AI关键因子JSON'' AFTER score_calculation',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'ai_factors'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN ai_analysis_report TEXT DEFAULT NULL COMMENT ''AI分析报告'' AFTER ai_factors',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'ai_analysis_report'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE risk_assessment ADD COLUMN is_ai_analyzed TINYINT DEFAULT 0 COMMENT ''是否完成AI分析'' AFTER ai_analysis_report',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'risk_assessment'
      AND column_name = 'is_ai_analyzed'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;
