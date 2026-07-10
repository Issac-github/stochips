"""
每日任务调度器

使用APScheduler实现定时任务：
1. 每天收盘后避开整点抓取股票数据
2. 数据抓取完成后运行Codex每日市场复盘
3. 发送通知（可选）
"""

import asyncio
import logging
import os
import random
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from ..data import create_fetcher
from ..data.storage import StockDataStorage
from ..config import config
from ..agents import (
    create_daily_market_review_agent,
    create_feishu_notifier,
)
from ..models.database import DailyJobRun

logger = logging.getLogger(__name__)

DEFAULT_DATA_FETCH_HOUR = 16
DEFAULT_DATA_FETCH_MINUTE = 3
DEFAULT_FETCH_START_JITTER_MIN = 5.0
DEFAULT_FETCH_START_JITTER_MAX = 45.0
DAILY_JOB_RETRY_DELAYS = (300, 900)
# Kept as a compatibility name for callers that only tune Codex retries.
CODEX_RETRY_DELAYS = DAILY_JOB_RETRY_DELAYS

DAILY_JOB_STAGE_FETCH = "fetch"
DAILY_JOB_STAGE_REVIEW = "review"
DAILY_JOB_STAGE_NOTIFY = "notify"
DAILY_JOB_ACTIVE_STATUSES = ("running", "retrying")


def _next_scheduled_daily_job_at(
    now: Optional[datetime] = None,
    hour: int = DEFAULT_DATA_FETCH_HOUR,
    minute: int = DEFAULT_DATA_FETCH_MINUTE,
) -> datetime:
    """Return the next weekday daily workflow start time."""
    current = now or datetime.now()
    candidate = current.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate <= current:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def _weekday_trigger(hour: int, minute: int) -> CronTrigger:
    return CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute)


def _env_float(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def _fetch_start_jitter_range() -> tuple[float, float]:
    jitter_min = _env_float(
        "STOCK_FETCH_START_JITTER_MIN",
        DEFAULT_FETCH_START_JITTER_MIN,
    )
    jitter_max = _env_float(
        "STOCK_FETCH_START_JITTER_MAX",
        DEFAULT_FETCH_START_JITTER_MAX,
    )
    if jitter_min < 0 or jitter_max < 0:
        raise ValueError("STOCK_FETCH_START_JITTER_MIN/MAX 不能为负数")
    if jitter_min > jitter_max:
        raise ValueError(
            "STOCK_FETCH_START_JITTER_MIN 不能大于 "
            "STOCK_FETCH_START_JITTER_MAX"
        )
    return jitter_min, jitter_max


async def _sleep_fetch_start_jitter() -> None:
    jitter_min, jitter_max = _fetch_start_jitter_range()
    if jitter_max <= 0:
        return
    delay = random.uniform(jitter_min, jitter_max)
    if delay <= 0:
        return
    logger.info("数据抓取启动前随机等待 %.2f 秒", delay)
    await asyncio.sleep(delay)


class DailyJobScheduler:
    """
    每日任务调度器

    任务流程：
    1. 抓取三类股票数据（连板天梯、最强风口、涨停强度）
    2. 存储到MySQL
    3. 生成并保存Codex每日市场复盘
    4. 发送事实材料和Codex复盘到飞书
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
        self.daily_review_agent = None
        self.feishu_notifier = None
        self.alert_feishu_notifier = None
        self.scheduled_hour = DEFAULT_DATA_FETCH_HOUR
        self.scheduled_minute = DEFAULT_DATA_FETCH_MINUTE

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
        should_jitter = target_date is None
        if not target_date:
            target_date = date.today()

        date_str = target_date.strftime('%Y%m%d')
        logger.info(f"开始抓取数据: {date_str}")

        try:
            if should_jitter:
                await _sleep_fetch_start_jitter()

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

    async def run_daily_market_review(
        self,
        target_date: Optional[date] = None,
        *,
        force: bool = False,
    ):
        """Generate the persisted daily Codex market review."""
        if not target_date:
            target_date = date.today()

        skipped = self._skip_if_non_trading_day(target_date, "Codex每日市场复盘")
        if skipped:
            return skipped

        if config.ai.provider != "codex":
            logger.warning("AI_PROVIDER 不是 codex，跳过每日市场复盘")
            return {
                "skipped": True,
                "reason": "AI_PROVIDER is not codex",
            }

        logger.info("开始Codex每日市场复盘: %s", target_date)

        try:
            if not self.daily_review_agent:
                self.daily_review_agent = create_daily_market_review_agent(
                    self.database_url
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.daily_review_agent.run(
                    target_date,
                    force=force,
                ).to_dict(),
            )

            if self.notification_callback:
                state = "复用已有报告" if result.get("cached") else "新生成并保存"
                self.notification_callback(
                    f"🤖 Codex每日市场复盘完成: {target_date}\n{state}"
                )

            return result

        except Exception as e:
            logger.error("Codex每日市场复盘失败: %s", e)
            if self.notification_callback:
                self.notification_callback(
                    f"❌ Codex每日市场复盘失败: {target_date}, 错误: {e}"
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

    async def _send_failure_broadcast(
        self,
        target_date: date,
        stage: str,
        error: Exception | str,
        retry_at: Optional[datetime] = None,
    ) -> None:
        """Notify the Feishu group about a failed stage without blocking recovery."""
        alert_webhook_url = (
            os.getenv("FEISHU_ALERT_WEBHOOK_URL")
            or os.getenv("FEISHU_WEBHOOK_URL", "")
        ).strip()
        if not alert_webhook_url:
            logger.warning("无法发送失败通知，飞书告警Webhook未配置")
            return

        error_text = str(error)
        if len(error_text) > 500:
            error_text = error_text[:499] + "..."
        if retry_at:
            next_step = f"**预计重试时间**：{retry_at:%Y-%m-%d %H:%M:%S}"
        else:
            next_step = "**后续处理**：重试已耗尽，今日不发送正式涨停播报。"
        content = "\n".join(
            [
                f"**日期**：{target_date:%Y-%m-%d}",
                f"**失败阶段**：{stage}",
                f"**失败原因**：{error_text}",
                next_step,
            ]
        )

        try:
            if alert_webhook_url == os.getenv("FEISHU_WEBHOOK_URL", "").strip():
                if not self.feishu_notifier:
                    self.feishu_notifier = create_feishu_notifier(self.database_url)
                notifier = self.feishu_notifier
            else:
                if not self.alert_feishu_notifier:
                    self.alert_feishu_notifier = create_feishu_notifier(
                        self.database_url,
                        webhook_url=alert_webhook_url,
                        webhook_secret=os.getenv("FEISHU_ALERT_WEBHOOK_SECRET", ""),
                    )
                notifier = self.alert_feishu_notifier
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: notifier.send_status_notification(
                    target_date,
                    "StoChips 任务失败通知",
                    content,
                ),
            )
        except Exception:
            logger.exception("飞书失败通知发送失败")

    def _next_daily_retry_at(self) -> datetime:
        return _next_scheduled_daily_job_at(
            hour=getattr(self, "scheduled_hour", DEFAULT_DATA_FETCH_HOUR),
            minute=getattr(self, "scheduled_minute", DEFAULT_DATA_FETCH_MINUTE),
        )

    def _get_daily_job_run(self, target_date: date) -> Optional[DailyJobRun]:
        session_factory = getattr(getattr(self, "storage", None), "Session", None)
        if not session_factory:
            return None
        session = session_factory()
        try:
            return (
                session.query(DailyJobRun)
                .filter(DailyJobRun.date == target_date)
                .one_or_none()
            )
        finally:
            session.close()

    def _save_daily_job_run(
        self,
        target_date: date,
        *,
        stage: str,
        status: str,
        attempt: int,
        retry_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> None:
        session_factory = getattr(getattr(self, "storage", None), "Session", None)
        if not session_factory:
            return
        session = session_factory()
        try:
            run = (
                session.query(DailyJobRun)
                .filter(DailyJobRun.date == target_date)
                .one_or_none()
            )
            if run is None:
                run = DailyJobRun(date=target_date)
                session.add(run)
            run.stage = stage
            run.status = status
            run.attempt = attempt
            run.retry_at = retry_at
            run.last_error = last_error
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("保存每日任务状态失败: %s", target_date)
            raise
        finally:
            session.close()

    def _list_recoverable_job_runs(self) -> List[DailyJobRun]:
        session_factory = getattr(getattr(self, "storage", None), "Session", None)
        if not session_factory:
            return []
        session = session_factory()
        try:
            return (
                session.query(DailyJobRun)
                .filter(DailyJobRun.status.in_(DAILY_JOB_ACTIVE_STATUSES))
                .all()
            )
        finally:
            session.close()

    @staticmethod
    def _retry_job_id(target_date: date) -> str:
        return f"daily_stock_retry_{target_date:%Y%m%d}"

    def _schedule_retry(self, target_date: date, retry_at: datetime) -> None:
        run_at = max(retry_at, datetime.now() + timedelta(seconds=1))
        self.scheduler.add_job(
            self.resume_daily_job,
            trigger=DateTrigger(run_date=run_at),
            args=[target_date],
            id=self._retry_job_id(target_date),
            name=f"每日任务恢复 {target_date:%Y-%m-%d}",
            replace_existing=True,
            misfire_grace_time=None,
        )
        logger.info("已安排每日任务恢复: %s %s", target_date, run_at)

    def _recover_persisted_jobs(self) -> int:
        """Requeue today's interrupted workflow after a process restart."""
        recovered = 0
        today = date.today()
        for run in self._list_recoverable_job_runs():
            if run.date < today:
                self._save_daily_job_run(
                    run.date,
                    stage=run.stage,
                    status="failed",
                    attempt=run.attempt,
                    last_error="服务恢复时已跨交易日，不再补跑历史播报",
                )
                continue
            if run.date > today:
                continue
            self._schedule_retry(run.date, run.retry_at or datetime.now())
            recovered += 1
        return recovered

    def _mark_stage_running(
        self,
        target_date: date,
        stage: str,
        attempt: int = 0,
    ) -> None:
        self._save_daily_job_run(
            target_date,
            stage=stage,
            status="running",
            attempt=attempt,
        )

    async def _handle_stage_failure(
        self,
        target_date: date,
        stage: str,
        error: Exception | str,
    ) -> Dict[str, object]:
        run = self._get_daily_job_run(target_date)
        previous_attempt = run.attempt if run and run.stage == stage else 0
        attempt = previous_attempt + 1
        error_text = str(error)

        if attempt <= len(DAILY_JOB_RETRY_DELAYS):
            retry_at = datetime.now() + timedelta(
                seconds=DAILY_JOB_RETRY_DELAYS[attempt - 1]
            )
            self._save_daily_job_run(
                target_date,
                stage=stage,
                status="retrying",
                attempt=attempt,
                retry_at=retry_at,
                last_error=error_text,
            )
            self._schedule_retry(target_date, retry_at)
            logger.warning(
                "每日任务阶段失败，将在 %s 重试: date=%s stage=%s attempt=%s/%s error=%s",
                retry_at.strftime("%Y-%m-%d %H:%M:%S"),
                target_date,
                stage,
                attempt,
                len(DAILY_JOB_RETRY_DELAYS) + 1,
                error_text,
            )
            await self._send_failure_broadcast(
                target_date,
                self._stage_display_name(stage),
                error,
                retry_at,
            )
            return {
                "date": target_date.isoformat(),
                "status": "retrying",
                "stage": stage,
                "attempt": attempt,
                "retry_at": retry_at.isoformat(),
            }

        self._save_daily_job_run(
            target_date,
            stage=stage,
            status="failed",
            attempt=attempt,
            last_error=error_text,
        )
        await self._send_failure_broadcast(
            target_date,
            self._stage_display_name(stage),
            error,
            self._next_daily_retry_at(),
        )
        return {
            "date": target_date.isoformat(),
            "status": "failed",
            "stage": stage,
            "attempt": attempt,
            "retry_at": self._next_daily_retry_at().isoformat(),
        }

    @staticmethod
    def _stage_display_name(stage: str) -> str:
        return {
            DAILY_JOB_STAGE_FETCH: "数据抓取",
            DAILY_JOB_STAGE_REVIEW: "Codex每日复盘",
            DAILY_JOB_STAGE_NOTIFY: "飞书播报",
        }.get(stage, stage)

    async def _run_fetch_stage(
        self,
        target_date: date,
        *,
        scheduled_run: bool,
    ) -> Dict[str, object]:
        try:
            fetch_result = await self.fetch_and_store_data(
                None if scheduled_run else target_date
            )
        except Exception as exc:
            return await self._handle_stage_failure(
                target_date,
                DAILY_JOB_STAGE_FETCH,
                exc,
            )

        if fetch_result.get("status") == "skipped":
            self._save_daily_job_run(
                target_date,
                stage=DAILY_JOB_STAGE_FETCH,
                status="skipped",
                attempt=0,
            )
            return {
                "date": target_date.isoformat(),
                "status": "skipped",
                "fetch": fetch_result,
            }

        errors = fetch_result.get("errors") or []
        try:
            data_status = self.storage.get_data_status(target_date)
        except Exception as exc:
            return await self._handle_stage_failure(
                target_date,
                DAILY_JOB_STAGE_FETCH,
                exc,
            )
        if errors or not data_status["is_complete"]:
            return await self._handle_stage_failure(
                target_date,
                DAILY_JOB_STAGE_FETCH,
                RuntimeError(
                    "数据抓取不完整，取消Codex复盘和飞书播报: "
                    f"errors={len(errors)}, status={data_status}"
                ),
            )

        self._mark_stage_running(target_date, DAILY_JOB_STAGE_REVIEW)
        result = await self._run_review_stage(target_date, resumed=False)
        if result.get("status") == "success":
            result["fetch"] = fetch_result
        return result

    async def _run_review_stage(
        self,
        target_date: date,
        *,
        resumed: bool,
    ) -> Dict[str, object]:
        try:
            review_result = await self.run_daily_market_review(
                target_date,
                force=not resumed,
            )
            if review_result.get("skipped"):
                raise RuntimeError(
                    "Codex每日复盘未生成: "
                    f"{review_result.get('reason', 'unknown reason')}"
                )
        except Exception as exc:
            return await self._handle_stage_failure(
                target_date,
                DAILY_JOB_STAGE_REVIEW,
                exc,
            )

        self._mark_stage_running(target_date, DAILY_JOB_STAGE_NOTIFY)
        result = await self._run_notify_stage(target_date)
        if result.get("status") == "success":
            result["review"] = review_result
        return result

    async def _run_notify_stage(self, target_date: date) -> Dict[str, object]:
        try:
            feishu_result = await self.send_feishu_report(target_date)
            if feishu_result.get("skipped"):
                raise RuntimeError(
                    "飞书播报未发送: "
                    f"{feishu_result.get('reason', 'unknown reason')}"
                )
        except Exception as exc:
            return await self._handle_stage_failure(
                target_date,
                DAILY_JOB_STAGE_NOTIFY,
                exc,
            )

        self._save_daily_job_run(
            target_date,
            stage=DAILY_JOB_STAGE_NOTIFY,
            status="completed",
            attempt=0,
        )
        logger.info("每日串行任务完成: %s", target_date)
        return {
            "date": target_date.isoformat(),
            "status": "success",
            "feishu": feishu_result,
        }

    async def resume_daily_job(self, target_date: date) -> Dict[str, object]:
        """Resume today's durable workflow from its failed or interrupted stage."""
        run = self._get_daily_job_run(target_date)
        if run is None or run.status not in DAILY_JOB_ACTIVE_STATUSES:
            return {
                "date": target_date.isoformat(),
                "status": "skipped",
                "reason": "没有可恢复的每日任务",
            }
        if target_date != date.today():
            self._save_daily_job_run(
                target_date,
                stage=run.stage,
                status="failed",
                attempt=run.attempt,
                last_error="恢复任务已跨交易日，不再补跑历史播报",
            )
            return {
                "date": target_date.isoformat(),
                "status": "skipped",
                "reason": "恢复任务已跨交易日",
            }

        logger.info("恢复每日任务: %s stage=%s attempt=%s", target_date, run.stage, run.attempt)
        self._mark_stage_running(target_date, run.stage, attempt=run.attempt)
        if run.stage == DAILY_JOB_STAGE_FETCH:
            return await self._run_fetch_stage(target_date, scheduled_run=False)
        if run.stage == DAILY_JOB_STAGE_REVIEW:
            return await self._run_review_stage(target_date, resumed=True)
        if run.stage == DAILY_JOB_STAGE_NOTIFY:
            return await self._run_notify_stage(target_date)
        raise RuntimeError(f"未知每日任务阶段: {run.stage}")

    async def run_daily_job(self, target_date: Optional[date] = None):
        """Start the durable fetch -> review -> Feishu workflow for one date."""
        scheduled_run = target_date is None
        if target_date is None:
            target_date = date.today()

        logger.info("开始每日串行任务: %s", target_date)
        self._mark_stage_running(target_date, DAILY_JOB_STAGE_FETCH)
        return await self._run_fetch_stage(target_date, scheduled_run=scheduled_run)

    def schedule_daily_job(
        self,
        hour: int = DEFAULT_DATA_FETCH_HOUR,
        minute: int = DEFAULT_DATA_FETCH_MINUTE,
    ):
        """Schedule the ordered fetch -> Codex -> Feishu workflow."""
        self.scheduled_hour = hour
        self.scheduled_minute = minute
        trigger = _weekday_trigger(hour, minute)

        self.scheduler.add_job(
            self.run_daily_job,
            trigger=trigger,
            id='daily_stock_job',
            name='每日抓取、Codex复盘与飞书播报',
            replace_existing=True
        )

        logger.info(f"已设置工作日每日定时任务: {hour:02d}:{minute:02d}")

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        recovered = self._recover_persisted_jobs()
        if recovered:
            logger.info("已恢复 %s 个每日任务", recovered)
        logger.info("调度器已启动")

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        if self.daily_review_agent:
            self.daily_review_agent.close()
            self.daily_review_agent = None
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
