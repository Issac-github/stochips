-- Add analysis-friendly THS block_top and stock_list fields.

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top ADD COLUMN continuous_plate_num INT DEFAULT NULL COMMENT ''连续上榜板块数'' AFTER change_percent',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top'
      AND column_name = 'continuous_plate_num'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top ADD COLUMN high_text VARCHAR(50) DEFAULT NULL COMMENT ''板块高度'' AFTER continuous_plate_num',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top'
      AND column_name = 'high_text'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top ADD COLUMN high_num INT DEFAULT NULL COMMENT ''板块高度编码'' AFTER high_text',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top'
      AND column_name = 'high_num'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN limit_up_type VARCHAR(50) DEFAULT NULL COMMENT ''涨停高度'' AFTER continuous_days',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'limit_up_type'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN high_days INT DEFAULT NULL COMMENT ''同花顺高度编码'' AFTER limit_up_type',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'high_days'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN last_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT ''最后涨停时间'' AFTER first_limit_up_time',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'last_limit_up_time'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN change_percent DECIMAL(10,4) DEFAULT NULL COMMENT ''涨跌幅%'' AFTER last_limit_up_time',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'change_percent'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN latest_price DECIMAL(10,2) DEFAULT NULL COMMENT ''最新价'' AFTER change_percent',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'latest_price'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN reason_type VARCHAR(255) DEFAULT NULL COMMENT ''涨停原因标签'' AFTER latest_price',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'reason_type'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN reason_info TEXT DEFAULT NULL COMMENT ''涨停原因详情'' AFTER reason_type',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'reason_info'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN concept TEXT DEFAULT NULL COMMENT ''概念'' AFTER reason_info',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'concept'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN market_id INT DEFAULT NULL COMMENT ''市场ID'' AFTER concept',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'market_id'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN market_type VARCHAR(20) DEFAULT NULL COMMENT ''市场类型'' AFTER market_id',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'market_type'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN is_new TINYINT DEFAULT NULL COMMENT ''是否新标记'' AFTER market_type',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'is_new'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN is_st TINYINT DEFAULT NULL COMMENT ''是否ST'' AFTER is_new',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'is_st'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN change_tag VARCHAR(50) DEFAULT NULL COMMENT ''涨停状态标签'' AFTER is_st',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'change_tag'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;

SET @stochips_add_column = (
    SELECT IF(COUNT(*) = 0,
        'ALTER TABLE block_top_stock ADD COLUMN raw_json TEXT DEFAULT NULL COMMENT ''原始JSON'' AFTER change_tag',
        'SELECT 1'
    )
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'block_top_stock'
      AND column_name = 'raw_json'
);
PREPARE stochips_stmt FROM @stochips_add_column;
EXECUTE stochips_stmt;
DEALLOCATE PREPARE stochips_stmt;
