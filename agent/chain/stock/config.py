"""
配置管理模块

集中管理所有配置参数，支持从环境变量读取
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = field(default_factory=lambda: os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://stock:stock123@localhost:3306/stock_analysis?charset=utf8mb4'
    ))

    @property
    def is_configured(self) -> bool:
        """检查数据库是否已配置"""
        return bool(self.url)


@dataclass
class FetcherConfig:
    """数据抓取配置"""
    # 同花顺Cookie
    ths_cookie: str = field(default_factory=lambda: os.getenv('STOCK_COOKIE', ''))

    # 请求超时时间（秒）
    timeout: int = 30

    # 最大重试次数
    max_retries: int = 3

    # 重试延迟（秒）
    retry_delay: float = 1.0

    @property
    def is_ths_configured(self) -> bool:
        """检查同花顺Cookie是否已配置"""
        return bool(self.ths_cookie)


@dataclass
class AIConfig:
    """AI分析配置"""
    # Moonshot API Key
    api_key: str = field(default_factory=lambda: os.getenv('MOONSHOT_API_KEY', ''))

    # 模型名称
    model: str = 'moonshot-v1-8k'

    # API基础URL
    base_url: str = 'https://api.moonshot.cn/v1'

    # 温度参数
    temperature: float = 0.3

    # 最大token数
    max_tokens: int = 2000

    @property
    def is_configured(self) -> bool:
        """检查AI是否已配置"""
        return bool(self.api_key)


@dataclass
class SchedulerConfig:
    """定时任务配置"""
    # 数据抓取时间
    fetch_hour: int = field(default_factory=lambda: int(os.getenv('FETCH_HOUR', '16')))
    fetch_minute: int = field(default_factory=lambda: int(os.getenv('FETCH_MINUTE', '0')))

    # 风险评估时间
    assess_hour: int = field(default_factory=lambda: int(os.getenv('ASSESS_HOUR', '16')))
    assess_minute: int = field(default_factory=lambda: int(os.getenv('ASSESS_MINUTE', '30')))

    # 时区
    timezone: str = field(default_factory=lambda: os.getenv('TZ', 'Asia/Shanghai'))


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file: str = 'stock_agent.log'


class Config:
    """
    全局配置类

    Usage:
        from chain.stock.config import config

        # 访问配置
        db_url = config.database.url
        ai_enabled = config.ai.is_configured
    """

    def __init__(self):
        self.database = DatabaseConfig()
        self.fetcher = FetcherConfig()
        self.ai = AIConfig()
        self.scheduler = SchedulerConfig()
        self.logging = LoggingConfig()

    def validate(self) -> dict:
        """
        验证配置完整性

        Returns:
            包含验证结果的字典
        """
        results = {
            'database': {
                'valid': self.database.is_configured,
                'message': '✅ 已配置' if self.database.is_configured else '❌ 未配置DATABASE_URL'
            },
            'fetcher_ths': {
                'valid': self.fetcher.is_ths_configured,
                'message': '✅ 已配置' if self.fetcher.is_ths_configured else '⚠️ 未配置STOCK_COOKIE（同花顺数据源不可用）'
            },
            'ai': {
                'valid': self.ai.is_configured,
                'message': '✅ 已配置' if self.ai.is_configured else '⚠️ 未配置MOONSHOT_API_KEY（AI分析不可用）'
            }
        }

        return results

    def print_status(self):
        """打印配置状态"""
        print("=" * 60)
        print("系统配置状态")
        print("=" * 60)

        results = self.validate()
        for component, result in results.items():
            status = "✓" if result['valid'] else "✗"
            print(f"{status} {component}: {result['message']}")

        print("=" * 60)


# 全局配置实例
config = Config()
