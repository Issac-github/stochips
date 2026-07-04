-- 股票选股及风控Agent系统 - 数据库初始化脚本
-- 用于Docker Compose自动初始化

USE stock_analysis;

-- 迁移记录表
-- Docker 初始化脚本已经包含部分历史迁移的最终表结构，因此需要同步记录，
-- 避免 stock_agent/stock_rpc 启动时 migrations/runner.py 重复执行这些迁移。
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) NOT NULL PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 连板天梯表
CREATE TABLE IF NOT EXISTS continuous_limit_up (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    continuous_days INT NOT NULL COMMENT '连板天数',
    latest_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '最新涨停时间',
    limit_up_open_count INT DEFAULT 0 COMMENT '涨停打开次数',
    limit_up_price DECIMAL(10,2) DEFAULT NULL COMMENT '涨停价',
    change_percent DECIMAL(10,2) DEFAULT NULL COMMENT '涨跌幅%',
    volume BIGINT DEFAULT NULL COMMENT '成交量',
    turnover DECIMAL(20,2) DEFAULT NULL COMMENT '成交额',
    market_value DECIMAL(20,2) DEFAULT NULL COMMENT '总市值',
    concept TEXT DEFAULT NULL COMMENT '所属概念',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_date_continuous (date, continuous_days),
    UNIQUE INDEX idx_date_code (date, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='连板天梯数据';

-- 最强风口表
CREATE TABLE IF NOT EXISTS block_top (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    block_code VARCHAR(20) NOT NULL COMMENT '板块代码',
    block_name VARCHAR(100) NOT NULL COMMENT '板块名称',
    stock_count INT DEFAULT 0 COMMENT '涨停家数',
    prev_stock_count INT DEFAULT 0 COMMENT '上一日涨停家数',
    change_percent DECIMAL(10,2) DEFAULT NULL COMMENT '板块涨跌幅%',
    leading_stock VARCHAR(20) DEFAULT NULL COMMENT '龙头股代码',
    leading_stock_name VARCHAR(100) DEFAULT NULL COMMENT '龙头股名称',
    continuous_days INT DEFAULT 1 COMMENT '持续天数',
    avg_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '平均涨停时间',
    block_type VARCHAR(50) DEFAULT NULL COMMENT '板块类型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_date_block (date, block_code),
    INDEX idx_date_count (date, stock_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='最强风口数据';

-- 涨停强度表
CREATE TABLE IF NOT EXISTS limit_up_pool (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    latest_price DECIMAL(10,2) DEFAULT NULL COMMENT '最新价',
    limit_up_price DECIMAL(10,2) DEFAULT NULL COMMENT '涨停价',
    change_percent DECIMAL(10,2) DEFAULT NULL COMMENT '涨跌幅%',
    limit_up_type VARCHAR(20) DEFAULT NULL COMMENT '涨停类型(首板/连板)',
    limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '涨停时间',
    open_count INT DEFAULT 0 COMMENT '打开次数',
    last_time VARCHAR(100) DEFAULT NULL COMMENT '最后封板时间',
    strength DECIMAL(10,4) DEFAULT NULL COMMENT '封单强度',
    board_amount DECIMAL(20,2) DEFAULT NULL COMMENT '封单金额',
    volume_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '量比',
    turnover_rate DECIMAL(10,2) DEFAULT NULL COMMENT '换手率%',
    market_value DECIMAL(20,2) DEFAULT NULL COMMENT '流通市值',
    total_value DECIMAL(20,2) DEFAULT NULL COMMENT '总市值',
    pe_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '市盈率',
    pb_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '市净率',
    concept TEXT DEFAULT NULL COMMENT '所属概念',
    block_name VARCHAR(100) DEFAULT NULL COMMENT '所属板块',
    reason TEXT DEFAULT NULL COMMENT '涨停原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_date_code_pool (date, code),
    INDEX idx_date_type (date, limit_up_type),
    INDEX idx_date_strength (date, strength)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='涨停强度数据';

-- 风险评估表
CREATE TABLE IF NOT EXISTS risk_assessment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    risk_level VARCHAR(20) NOT NULL COMMENT '风险等级(高/中/低)',
    risk_score DECIMAL(5,2) DEFAULT NULL COMMENT '风险分数(0-100)',
    continuous_days INT DEFAULT 0 COMMENT '连板天数',
    risk_factors TEXT DEFAULT NULL COMMENT '风险因子JSON',
    rule_score DECIMAL(5,2) DEFAULT NULL COMMENT '规则引擎风险分数',
    ai_score DECIMAL(5,2) DEFAULT NULL COMMENT 'AI风险分数',
    ai_confidence DECIMAL(5,4) DEFAULT NULL COMMENT 'AI分析置信度',
    score_calculation TEXT DEFAULT NULL COMMENT '综合分数计算说明',
    ai_factors TEXT DEFAULT NULL COMMENT 'AI关键因子JSON',
    ai_analysis_report TEXT DEFAULT NULL COMMENT 'AI分析报告',
    is_ai_analyzed TINYINT DEFAULT 0 COMMENT '是否完成AI分析',
    suggestion VARCHAR(50) DEFAULT NULL COMMENT '建议(观望/谨慎/规避)',
    assessment_reason TEXT DEFAULT NULL COMMENT '评估理由',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_date_code_risk (date, code),
    INDEX idx_date_level (date, risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风险评估结果';

-- 数据抓取日志表
CREATE TABLE IF NOT EXISTS data_fetch_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    data_type VARCHAR(50) NOT NULL COMMENT '数据类型',
    status VARCHAR(20) NOT NULL COMMENT '状态(success/failed)',
    record_count INT DEFAULT 0 COMMENT '记录数',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    UNIQUE INDEX idx_date_type (date, data_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据抓取日志';

-- 东方财富涨停池表
CREATE TABLE IF NOT EXISTS eastmoney_zt_pool (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '数据日期',
    code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    latest_price DECIMAL(10,2) DEFAULT NULL COMMENT '最新价',
    change_percent DECIMAL(10,2) DEFAULT NULL COMMENT '涨跌幅%',
    first_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '首次涨停时间',
    last_limit_up_time VARCHAR(20) DEFAULT NULL COMMENT '最后涨停时间',
    limit_up_type VARCHAR(20) DEFAULT NULL COMMENT '涨停类型(首板/连板)',
    board_amount DECIMAL(20,2) DEFAULT NULL COMMENT '封单金额(万元)',
    block_name VARCHAR(100) DEFAULT NULL COMMENT '所属板块/行业',
    reason TEXT DEFAULT NULL COMMENT '涨停原因/特征',
    volume BIGINT DEFAULT NULL COMMENT '成交量',
    turnover BIGINT DEFAULT NULL COMMENT '成交额',
    market_value DECIMAL(20,2) DEFAULT NULL COMMENT '总市值(亿元)',
    circulating_value DECIMAL(20,2) DEFAULT NULL COMMENT '流通市值(亿元)',
    turnover_rate DECIMAL(10,2) DEFAULT NULL COMMENT '换手率%',
    pe_ratio DECIMAL(10,2) DEFAULT NULL COMMENT '市盈率',
    amplitude DECIMAL(10,2) DEFAULT NULL COMMENT '振幅%',
    pre_3_day_change DECIMAL(10,2) DEFAULT NULL COMMENT '前3日涨幅%',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX idx_date_code_em (date, code),
    INDEX idx_date_block_em (date, block_name),
    INDEX idx_date_first_time (date, first_limit_up_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='东方财富涨停池数据';

-- risk_assessment 已内置 AI 风控字段，对应迁移不需要再执行。
INSERT IGNORE INTO schema_migrations (filename)
VALUES ('20260506_add_risk_assessment_ai_fields.sql');
