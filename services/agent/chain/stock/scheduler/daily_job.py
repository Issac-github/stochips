"""
每日任务调度器

使用APScheduler实现定时任务：
1. 每天收盘后（16:00）抓取股票数据
2. 数据抓取完成后运行风险评估
3. 发送通知（可选）
"""

import asyncio
import logging
import os
from datetime import datetime, date
from typing import Optional, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from ..data import create_fetcher
from ..data.storage import StockDataStorage
from ..agents import (
    create_enhanced_risk_agent,
    create_feishu_notifier,
    create_risk_agent,
    create_stock_agent,
)

logger = logging.getLogger(__name__)


def _env_is_configured(key: str, placeholders: Optional[set[str]] = None) -> bool:
    value = os.getenv(key, "").strip()
    if not value:
        return False
    if placeholders and value in placeholders:
        return False
    return True


def _weekday_trigger(hour: int, minute: int) -> CronTrigger:
    return CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute)


class DailyJobScheduler:
    """
    每日任务调度器

    任务流程：
    1. 抓取三类股票数据（连板天梯、最强风口、涨停强度）
    2. 存储到MySQL
    3. 运行风险评估Agent
    4. 保存评估结果
    """

    def __init__(
        self,
        database_url: str,
        cookie: Optional[str] = None,
        notification_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化调度器

        Args:
            database_url: MySQL连接URL
            cookie: 数据抓取用的cookie
            notification_callback: 通知回调函数
        """
        self.database_url = database_url
        self.cookie = cookie
        self.notification_callback = notification_callback

        # 初始化组件
        self.fetcher = create_fetcher(cookie)
        self.storage = StockDataStorage(database_url)
        self.risk_agent = create_risk_agent(database_url)
        self.enhanced_risk_agent = None
        self.feishu_notifier = None
        self.stock_agent = create_stock_agent(
            database_url,
            cookie=cookie,
            notification_callback=notification_callback,
        )

        # 初始化调度器
        self.scheduler = AsyncIOScheduler()

        # 注册事件监听
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

    def _on_job_executed(self, event):
        """任务执行事件处理"""
        if event.exception:
            logger.error(f"任务执行失败: {event.job_id}, 错误: {event.exception}")
            if self.notification_callback:
                self.notification_callback(f"❌ 任务失败: {event.job_id}")
        else:
            logger.info(f"任务执行成功: {event.job_id}")

    def _skip_if_non_trading_day(self, target_date: date, job_name: str) -> Optional[dict]:
        if self.storage.is_fetch_skipped(target_date):
            reason = "当日抓取已标记为非交易日/上游旧数据，跳过后续流程"
            logger.info("%s: %s %s", job_name, target_date, reason)
            if self.notification_callback:
                self.notification_callback(f"⏭️ {job_name}跳过: {target_date}\n{reason}")
            return {
                "date": target_date.isoformat(),
                "skipped": True,
                "reason": reason,
            }
        return None

    async def fetch_and_store_data(self, target_date: Optional[date] = None):
        """
        抓取并存储数据

        Args:
            target_date: 目标日期，默认今天

        Returns:
            执行结果
        """
        if not target_date:
            target_date = date.today()

        date_str = target_date.strftime('%Y%m%d')
        logger.info(f"开始抓取数据: {date_str}")

        try:
            # 抓取数据（使用同步版本）
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.fetcher.fetch_all_data(date_str)
            )

            # 检查错误
            errors = data.get('errors', [])
            if errors:
                error_msg = "\n".join([f"{e['type']}: {e['error']}" for e in errors])
                logger.error(f"数据抓取部分失败:\n{error_msg}")

            # 存储数据
            results = self.storage.save_all_data(data, target_date)
            if data.get("skipped"):
                reason = data.get("skip_reason", "skipped")
                if self.notification_callback:
                    self.notification_callback(
                        f"⏭️ 数据抓取跳过: {date_str}\n{reason}"
                    )
                return {
                    'date': date_str,
                    'status': 'skipped',
                    'results': results,
                    'errors': errors,
                    'reason': reason,
                }

            # 发送通知
            if self.notification_callback:
                msg = f"✅ 数据抓取完成: {date_str}\n"
                for data_type, (success, failed) in results.items():
                    msg += f"- {data_type}: 成功{success}条"
                    if failed > 0:
                        msg += f", 失败{failed}条"
                    msg += "\n"
                self.notification_callback(msg)

            return {
                'date': date_str,
                'status': 'success',
                'results': results,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"数据抓取失败: {e}")
            if self.notification_callback:
                self.notification_callback(f"❌ 数据抓取失败: {date_str}, 错误: {e}")
            raise

    async def run_risk_assessment(self, target_date: Optional[date] = None):
        """
        运行风险评估

        Args:
            target_date: 目标日期，默认今天

        Returns:
            评估结果
        """
        if not target_date:
            target_date = date.today()

        logger.info(f"开始风险评估: {target_date}")
        skipped = self._skip_if_non_trading_day(target_date, "风险评估")
        if skipped:
            return skipped

        try:
            # 在异步环境中运行同步代码
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.risk_agent.run_daily_assessment(target_date)
            )

            # 发送通知
            if self.notification_callback:
                msg = f"📊 风险评估完成: {target_date}\n"
                msg += f"评估股票数: {result['total_assessed']}\n"
                msg += "风险分布:\n"
                for level, count in result['risk_distribution'].items():
                    msg += f"- {level}: {count}只\n"
                self.notification_callback(msg)

            return result

        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            if self.notification_callback:
                self.notification_callback(f"❌ 风险评估失败: {target_date}, 错误: {e}")
            raise

    async def run_enhanced_risk_assessment(self, target_date: Optional[date] = None):
        """
        运行 AI 增强风险评估。

        Args:
            target_date: 目标日期，默认今天

        Returns:
            增强评估结果
        """
        if not target_date:
            target_date = date.today()

        skipped = self._skip_if_non_trading_day(target_date, "AI增强风险评估")
        if skipped:
            return skipped

        if not _env_is_configured("MOONSHOT_API_KEY", {"your_moonshot_api_key_here"}):
            logger.warning("MOONSHOT_API_KEY 未配置，跳过 AI 增强风险评估")
            return {
                "total_assessed": 0,
                "skipped": True,
                "reason": "MOONSHOT_API_KEY not set",
            }

        logger.info(f"开始 AI 增强风险评估: {target_date}")

        try:
            if not self.enhanced_risk_agent:
                self.enhanced_risk_agent = create_enhanced_risk_agent(
                    self.database_url
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.enhanced_risk_agent.run_daily_assessment_enhanced(
                    target_date,
                    min_continuous_days=2,
                    use_ai=True,
                ),
            )

            if self.notification_callback:
                msg = f"🤖 AI增强风险评估完成: {target_date}\n"
                msg += f"评估股票数: {result['total_assessed']}\n"
                msg += (
                    f"AI分析成功: {result.get('ai_success_count', 0)}只，"
                    f"新发起AI调用: {result.get('fresh_ai_call_count', 0)}只\n"
                )
                self.notification_callback(msg)

            return result

        except Exception as e:
            logger.error(f"AI增强风险评估失败: {e}")
            if self.notification_callback:
                self.notification_callback(
                    f"❌ AI增强风险评估失败: {target_date}, 错误: {e}"
                )
            raise

    async def send_feishu_report(self, target_date: Optional[date] = None):
        """
        发送飞书涨停数据播报。

        Args:
            target_date: 目标日期，默认今天

        Returns:
            飞书发送结果
        """
        if not target_date:
            target_date = date.today()

        skipped = self._skip_if_non_trading_day(target_date, "飞书播报")
        if skipped:
            return skipped

        if not os.getenv("FEISHU_WEBHOOK_URL"):
            logger.warning("FEISHU_WEBHOOK_URL 未配置，跳过飞书播报")
            return {
                "date": target_date.isoformat(),
                "skipped": True,
                "reason": "FEISHU_WEBHOOK_URL not set",
            }

        logger.info(f"开始发送飞书播报: {target_date}")

        try:
            if not self.feishu_notifier:
                self.feishu_notifier = create_feishu_notifier(self.database_url)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.feishu_notifier.send_report(target_date),
            )

            if self.notification_callback:
                self.notification_callback(f"✅ 飞书播报完成: {target_date}")

            return result

        except Exception as e:
            logger.error(f"飞书播报失败: {e}")
            if self.notification_callback:
                self.notification_callback(f"❌ 飞书播报失败: {target_date}, 错误: {e}")
            raise

    async def run_daily_job(self, target_date: Optional[date] = None):
        """
        运行每日完整任务（目标驱动 StockAgent）

        Args:
            target_date: 目标日期，默认今天
        """
        if not target_date:
            target_date = date.today()

        logger.info(f"开始每日任务: {target_date}")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.stock_agent.run("更新数据并完成每日股票风险巡检", target_date)
        )

        logger.info(f"每日任务完成: {target_date}")
        return result.to_dict()

    def schedule_daily_job(self, hour: int = 16, minute: int = 0):
        """
        设置每日定时任务

        Args:
            hour: 小时（默认16，即下午4点）
            minute: 分钟（默认0）
        """
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.run_daily_job,
            trigger=trigger,
            id='daily_stock_job',
            name='每日股票数据抓取与风险评估',
            replace_existing=True
        )

        logger.info(f"已设置工作日每日定时任务: {hour:02d}:{minute:02d}")

    def schedule_data_fetch(self, hour: int = 16, minute: int = 0):
        """
        设置数据抓取定时任务

        Args:
            hour: 小时
            minute: 分钟
        """
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.fetch_and_store_data,
            trigger=trigger,
            id='daily_data_fetch',
            name='每日数据抓取',
            replace_existing=True
        )

        logger.info(f"已设置工作日数据抓取任务: {hour:02d}:{minute:02d}")

    def schedule_risk_assessment(self, hour: int = 16, minute: int = 30):
        """
        设置风险评估定时任务

        Args:
            hour: 小时
            minute: 分钟
        """
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.run_risk_assessment,
            trigger=trigger,
            id='daily_risk_assessment',
            name='每日风险评估',
            replace_existing=True
        )

        logger.info(f"已设置工作日风险评估任务: {hour:02d}:{minute:02d}")

    def schedule_enhanced_risk_assessment(self, hour: int = 16, minute: int = 45):
        """
        设置 AI 增强风险评估定时任务

        Args:
            hour: 小时
            minute: 分钟
        """
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.run_enhanced_risk_assessment,
            trigger=trigger,
            id='daily_enhanced_risk_assessment',
            name='每日AI增强风险评估',
            replace_existing=True
        )

        logger.info(f"已设置工作日AI增强风险评估任务: {hour:02d}:{minute:02d}")

    def schedule_feishu_report(self, hour: int = 17, minute: int = 0):
        """
        设置飞书播报定时任务

        Args:
            hour: 小时
            minute: 分钟
        """
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.send_feishu_report,
            trigger=trigger,
            id='daily_feishu_report',
            name='每日飞书涨停播报',
            replace_existing=True
        )

        logger.info(f"已设置工作日飞书播报任务: {hour:02d}:{minute:02d}")

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已关闭")

    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()


def create_scheduler(
    database_url: Optional[str] = None,
    cookie: Optional[str] = None,
    notification_callback: Optional[Callable[[str], None]] = None
) -> DailyJobScheduler:
    """
    工厂函数：创建调度器

    Args:
        database_url: MySQL连接URL，默认从环境变量读取
        cookie: 数据抓取用的cookie，默认从环境变量读取
        notification_callback: 通知回调函数

    Returns:
        DailyJobScheduler实例
    """
    if not database_url:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("请提供database_url或设置DATABASE_URL环境变量")

    if not cookie:
        cookie = os.getenv('STOCK_COOKIE')

    return DailyJobScheduler(database_url, cookie, notification_callback)
