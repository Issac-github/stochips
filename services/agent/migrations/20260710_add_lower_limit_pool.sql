-- Persist the complete THS lower-limit pool as independent market facts.

CREATE TABLE IF NOT EXISTS lower_limit_pool (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    latest_price DECIMAL(10,2) DEFAULT NULL COMMENT '最新价',
    change_percent DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅%',
    first_limit_down_time VARCHAR(20) DEFAULT NULL COMMENT '首次跌停时间',
    last_limit_down_time VARCHAR(20) DEFAULT NULL COMMENT '最后跌停时间',
    turnover_rate DECIMAL(10,4) DEFAULT NULL COMMENT '换手率%',
    market_value DECIMAL(20,2) DEFAULT NULL COMMENT '流通市值',
    market_id INT DEFAULT NULL COMMENT '市场ID',
    market_type VARCHAR(20) DEFAULT NULL COMMENT '市场类型',
    is_new INT DEFAULT NULL COMMENT '是否新标记',
    is_again_limit INT DEFAULT NULL COMMENT '是否再次跌停',
    change_tag VARCHAR(50) DEFAULT NULL COMMENT '跌停状态标签',
    time_preview TEXT DEFAULT NULL COMMENT '盘中涨跌幅预览JSON',
    raw_json TEXT DEFAULT NULL COMMENT '原始JSON',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_date_code_lower_pool (date, code),
    INDEX idx_date_first_down_time (date, first_limit_down_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同花顺跌停池数据';
