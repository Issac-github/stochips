-- Persistent task store for stock_rpc.
-- Replaces in-memory store so task status survives container restarts.

CREATE TABLE IF NOT EXISTS rpc_tasks (
    id VARCHAR(64) NOT NULL PRIMARY KEY COMMENT '任务ID',
    type VARCHAR(32) NOT NULL COMMENT '任务类型',
    status VARCHAR(16) NOT NULL COMMENT 'pending|running|succeeded|failed',
    request_json TEXT DEFAULT NULL COMMENT '请求参数JSON',
    result MEDIUMTEXT DEFAULT NULL COMMENT '执行结果',
    error TEXT DEFAULT NULL COMMENT '错误信息',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    started_at DATETIME DEFAULT NULL COMMENT '开始时间',
    finished_at DATETIME DEFAULT NULL COMMENT '完成时间',
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='gRPC 任务状态表';
