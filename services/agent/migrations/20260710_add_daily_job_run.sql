CREATE TABLE IF NOT EXISTS daily_job_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    date DATE NOT NULL COMMENT '交易日期',
    stage VARCHAR(20) NOT NULL COMMENT '当前阶段(fetch/review/notify)',
    status VARCHAR(20) NOT NULL COMMENT '状态(running/retrying/completed/skipped/failed)',
    attempt INT NOT NULL DEFAULT 0 COMMENT '当前阶段失败次数',
    retry_at DATETIME DEFAULT NULL COMMENT '下一次重试时间',
    last_error TEXT DEFAULT NULL COMMENT '最近失败原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE INDEX idx_daily_job_run_date (date),
    INDEX idx_daily_job_run_recovery (status, retry_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日抓取、Codex复盘与飞书播报状态';
