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
    # Daily market review uses the ChatGPT-authenticated Codex subscription.
    provider: str = field(default_factory=lambda: os.getenv('AI_PROVIDER', 'codex').strip().lower())

    # Codex调用失败时使用的备用服务商；设为 none 可关闭自动回退。
    fallback_provider: str = field(
        default_factory=lambda: os.getenv('AI_FALLBACK_PROVIDER', 'none').strip().lower()
    )

    # Moonshot API Key
    api_key: str = field(default_factory=lambda: os.getenv('MOONSHOT_API_KEY', ''))

    # 模型名称
    model: str = field(default_factory=lambda: os.getenv('MOONSHOT_MODEL', 'moonshot-v1-8k'))

    # API基础URL
    base_url: str = field(default_factory=lambda: os.getenv('MOONSHOT_BASE_URL', 'https://api.moonshot.cn/v1'))

    # 温度参数
    temperature: float = field(default_factory=lambda: float(os.getenv('MOONSHOT_TEMPERATURE', '0.3')))

    # 最大token数
    max_tokens: int = field(default_factory=lambda: int(os.getenv('MOONSHOT_MAX_TOKENS', '2000')))

    # 请求超时时间（秒）
    timeout: int = field(default_factory=lambda: int(os.getenv('MOONSHOT_TIMEOUT', '60')))

    # 最大重试次数
    max_retries: int = field(default_factory=lambda: int(os.getenv('MOONSHOT_MAX_RETRIES', '2')))

    # 仅供未导出的旧版逐股评分模块兼容，Codex每日复盘不读取此项。
    max_daily_calls: int = field(default_factory=lambda: int(os.getenv('AI_MAX_DAILY_CALLS', '20')))

    # Codex SDK uses the local app-server and owns ChatGPT OAuth tokens.
    codex_model: str = field(default_factory=lambda: os.getenv('CODEX_MODEL', ''))
    codex_working_directory: str = field(
        default_factory=lambda: os.getenv('CODEX_WORKING_DIRECTORY', '/app')
    )

    @property
    def is_configured(self) -> bool:
        """检查AI是否已配置"""
        if self.provider == 'codex':
            return True
        if self.provider == 'moonshot':
            return bool(self.api_key)
        return False

    def output_metadata(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """生成用户可见的AI执行来源信息。"""
        actual_provider = provider or self.provider
        if actual_provider == 'codex':
            provider_name = 'openai-codex'
            model_name = model or self.codex_model or 'default'
        else:
            provider_name = 'moonshot'
            model_name = model or self.model
        return f"Agent: main | Model: {model_name} | Provider: {provider_name}"


@dataclass
class SchedulerConfig:
    """定时任务配置"""
    # 数据抓取时间
    fetch_hour: int = field(default_factory=lambda: int(os.getenv('FETCH_HOUR', '16')))
    fetch_minute: int = field(default_factory=lambda: int(os.getenv('FETCH_MINUTE', '0')))

    # 兼容旧配置名；当前含义为每日Codex复盘时间。
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
                'message': '✅ 已配置' if self.ai.is_configured else '⚠️ 未配置AI Provider（AI分析不可用）'
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
