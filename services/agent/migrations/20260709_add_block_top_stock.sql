-- Persist full THS block_top.stock_list members for Feishu board rendering.

CREATE TABLE IF NOT EXISTS block_top_stock (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    block_code VARCHAR(20) NOT NULL COMMENT '板块代码',
    block_name VARCHAR(100) NOT NULL COMMENT '板块名称',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    continuous_days INT DEFAULT 1 COMMENT '连板天数',
    first_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '首次涨停时间',
    sort_order INT DEFAULT 0 COMMENT '接口返回顺序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_date_block_stock (date, block_code, code),
    INDEX idx_date_block_order (date, block_code, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='最强风口板块股票明细';
