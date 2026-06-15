"""
股票选股及风控Agent系统

包含以下核心模块：
- data: 数据抓取模块
- models: 数据库模型
- agents: 风险评估Agent
- scheduler: 定时任务调度器
- wiki: 交易知识库查询与维护
"""

from .agents import (
    create_ai_analyzer,
    create_enhanced_risk_agent,
    create_risk_agent,
    create_stock_agent,
    create_wiki_agent,
)
from .data import create_fetcher, create_storage

__version__ = "1.0.0"
__author__ = "Stock Analysis Team"

__all__ = [
    "create_fetcher",
    "create_storage",
    "create_risk_agent",
    "create_enhanced_risk_agent",
    "create_ai_analyzer",
    "create_stock_agent",
    "create_wiki_agent",
]
