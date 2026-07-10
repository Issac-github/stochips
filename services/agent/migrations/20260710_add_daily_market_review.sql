CREATE TABLE IF NOT EXISTS daily_market_review (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '交易日期',
    content TEXT NOT NULL COMMENT 'Codex每日市场复盘',
    provider VARCHAR(50) NOT NULL COMMENT '实际AI服务商',
    model VARCHAR(100) DEFAULT NULL COMMENT '实际模型',
    strategy_path VARCHAR(255) NOT NULL COMMENT '交易体系文件路径',
    source_material_digest CHAR(64) NOT NULL COMMENT '输入行情材料SHA256',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_daily_market_review_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Codex每日市场复盘';
