"""
Feishu card notifier for daily stock reports.
"""

import base64
import hashlib
import hmac
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from ..config import config
from ..models.database import (
    BlockTop,
    BlockTopStock,
    ContinuousLimitUp,
    DailyMarketReview,
    DataFetchLog,
    EastmoneyZTPool,
    LowerLimitPool,
    LimitUpPool,
    get_session_maker,
    init_database,
)

logger = logging.getLogger(__name__)

FEISHU_FREQUENCY_LIMIT_CODE = 11232
FEISHU_SEND_MAX_ATTEMPTS = 3
FEISHU_SEND_RETRY_DELAYS = (20, 60)
FEISHU_SEND_JITTER_MIN = 5.0
FEISHU_SEND_JITTER_MAX = 20.0
SHANGHAI_TIMEZONE = timezone(timedelta(hours=8))


def next_feishu_send_at(
    now: Optional[datetime] = None,
    not_before: Optional[datetime] = None,
) -> datetime:
    """Return a non-exact odd-minute time that is safe for a Feishu send."""
    current = now or datetime.now()
    target = max(current, not_before) if not_before else current
    if target.minute % 2 == 1 and (target.second > 0 or target.microsecond > 0):
        return target

    if target.minute % 2 == 1:
        return target + timedelta(
            seconds=random.uniform(FEISHU_SEND_JITTER_MIN, FEISHU_SEND_JITTER_MAX)
        )

    next_minute = target.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if next_minute.minute % 2 == 0:
        next_minute += timedelta(minutes=1)
    return next_minute + timedelta(
        seconds=random.uniform(FEISHU_SEND_JITTER_MIN, FEISHU_SEND_JITTER_MAX)
    )


def wait_until_feishu_send_at(send_at: datetime) -> None:
    delay = max(0.0, (send_at - datetime.now()).total_seconds())
    if delay <= 0:
        return
    logger.info("飞书发送等待 %.2f 秒，发送时间: %s", delay, send_at)
    time.sleep(delay)


@dataclass
class BlockStockReasonSummary:
    code: str
    name: str
    reason_type: str
    reason_info: str


@dataclass
class BlockSummary:
    block_name: str
    stock_count: int
    leading_stock_name: str
    change_percent: Optional[float]
    source: str = "block_top"
    stocks: List[str] = field(default_factory=list)
    block_code: str = ""
    stock_reasons: List[BlockStockReasonSummary] = field(default_factory=list)


@dataclass
class IndustrySummary:
    industry_name: str
    stock_count: int
    leaders: List[str]


@dataclass
class StockSummary:
    code: str
    name: str
    continuous_days: int
    limit_up_time: str
    block_name: str
    reason: str


@dataclass
class WeakBoardSummary:
    code: str
    name: str
    open_count: int
    turnover_rate: Optional[float]
    block_name: str
    reason: str
    first_limit_up_time: str = ""
    last_limit_up_time: str = ""


@dataclass
class LowerLimitSummary:
    code: str
    name: str
    change_percent: Optional[float]
    first_limit_down_time: str
    last_limit_down_time: str
    turnover_rate: Optional[float]
    is_again_limit: bool


@dataclass
class LimitUpPoolAnalysisSummary:
    code: str
    name: str
    change_percent: Optional[float]
    limit_up_type: str
    first_limit_up_time: str
    last_limit_up_time: str
    open_count: int
    turnover_rate: Optional[float]


@dataclass
class PreviousHighBoardSummary:
    code: str
    name: str
    previous_continuous_days: int
    feedback: str


@dataclass
class BoardOverlapSummary:
    first_block_name: str
    second_block_name: str
    shared_stock_count: int
    first_stock_count: int
    second_stock_count: int


@dataclass
class BreakoutSummary:
    code: str
    name: str
    breakout_price: float
    previous_high_price: float
    breakout_ratio: float
    previous_max_days: int
    gap_trading_days: int
    block_name: str
    reason: str


@dataclass
class DailyReviewSummary:
    content: str
    provider: str
    model: str


@dataclass
class FeishuStockReport:
    target_date: date
    is_complete: bool
    continuous_count: int
    block_count: int
    hr_limit_up_count: int
    em_limit_up_count: int
    lower_limit_count: int
    max_continuous_days: int
    continuous_distribution: Dict[int, int]
    limit_up_type_distribution: Dict[str, int]
    data_warnings: List[str]
    fetch_logs: List[Dict[str, Any]]
    top_blocks: List[BlockSummary]
    eastmoney_industries: List[IndustrySummary]
    top_stocks: List[StockSummary]
    early_stocks: List[StockSummary]
    weak_boards: List[WeakBoardSummary]
    breakout_stocks: List[BreakoutSummary]
    lower_limit_stocks: List[LowerLimitSummary]
    daily_review: Optional[DailyReviewSummary] = None
    one_word_stocks: List[StockSummary] = field(default_factory=list)
    previous_high_feedback: List[PreviousHighBoardSummary] = field(
        default_factory=list
    )
    pool_stock_reasons: List[BlockStockReasonSummary] = field(default_factory=list)
    limit_up_pool_metrics: List[LimitUpPoolAnalysisSummary] = field(
        default_factory=list
    )
    board_overlaps: List[BoardOverlapSummary] = field(default_factory=list)


class FeishuStockNotifier:
    """Build and send daily stock report cards to a Feishu custom bot."""

    def __init__(
        self,
        database_url: str,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.database_url = database_url
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")
        self.webhook_secret = webhook_secret or os.getenv("FEISHU_WEBHOOK_SECRET", "")
        self.engine = None
        self.Session: Optional[sessionmaker[Session]] = None

    def _init_db(self):
        if not self.Session:
            self.engine = init_database(self.database_url)
            self.Session = get_session_maker(self.engine)

    def _get_session(self) -> Session:
        self._init_db()
        if not self.Session:
            raise RuntimeError("数据库会话初始化失败")
        return self.Session()

    def build_report(self, target_date: date) -> FeishuStockReport:
        """Collect the daily stock summary used by the Feishu card."""
        session = self._get_session()
        try:
            continuous_count = (
                session.query(ContinuousLimitUp)
                .filter(ContinuousLimitUp.date == target_date)
                .count()
            )
            block_count = (
                session.query(BlockTop).filter(BlockTop.date == target_date).count()
            )
            hr_limit_up_count = (
                session.query(LimitUpPool)
                .filter(LimitUpPool.date == target_date)
                .count()
            )
            em_limit_up_count = (
                session.query(EastmoneyZTPool)
                .filter(EastmoneyZTPool.date == target_date)
                .count()
            )
            lower_limit_count = (
                session.query(LowerLimitPool)
                .filter(LowerLimitPool.date == target_date)
                .count()
            )
            max_days = (
                session.query(func.max(ContinuousLimitUp.continuous_days))
                .filter(ContinuousLimitUp.date == target_date)
                .scalar()
                or 0
            )

            continuous_distribution = {
                int(days): int(count)
                for days, count in session.query(
                    ContinuousLimitUp.continuous_days,
                    func.count(ContinuousLimitUp.id),
                )
                .filter(ContinuousLimitUp.date == target_date)
                .group_by(ContinuousLimitUp.continuous_days)
                .order_by(ContinuousLimitUp.continuous_days.desc())
                .all()
                if days is not None
            }
            limit_up_type_distribution = {
                limit_type or "未知": int(count)
                for limit_type, count in session.query(
                    LimitUpPool.limit_up_type,
                    func.count(LimitUpPool.id),
                )
                .filter(LimitUpPool.date == target_date)
                .group_by(LimitUpPool.limit_up_type)
                .all()
            }

            fetch_logs = [
                {
                    "data_type": log.data_type,
                    "status": log.status,
                    "record_count": log.record_count,
                    "error_message": log.error_message,
                }
                for log in session.query(DataFetchLog)
                .filter(DataFetchLog.date == target_date)
                .order_by(DataFetchLog.data_type.asc())
                .all()
            ]
            lower_limit_log = next(
                (
                    item for item in fetch_logs
                    if item["data_type"] == "lower_limit_pool"
                ),
                None,
            )

            top_blocks = [
                self._build_block_summary(session, target_date, item)
                for item in session.query(BlockTop)
                .filter(BlockTop.date == target_date)
                .order_by(BlockTop.stock_count.desc(), BlockTop.change_percent.desc())
                .all()
            ]
            block_top_has_counts = any(item.stock_count > 0 for item in top_blocks)
            data_warnings = []
            if lower_limit_log is None:
                data_warnings.append(
                    "同花顺跌停池尚未抓取，跌停数量不能按 0 解读"
                )
            elif lower_limit_log["status"] != "success":
                data_warnings.append(
                    "同花顺跌停池抓取失败，跌停数量不能用于情绪判断"
                )
            if block_count > 0 and not block_top_has_counts:
                data_warnings.append(
                    "block_top 已入库但涨停家数字段为空，"
                    "同花顺板块热度尝试改用涨停池聚合"
                )
                top_blocks = self._aggregate_blocks_from_pool(
                    session, target_date
                )
            else:
                fallback_blocks = self._aggregate_blocks_from_pool(
                    session,
                    target_date,
                    exclude={item.block_name for item in top_blocks},
                )
                top_blocks.extend(fallback_blocks)

            if not top_blocks:
                data_warnings.append(
                    "同花顺 block_top 与 limit_up_pool 均缺少可聚合板块数量，"
                    "行业热度请看东财行业涨停"
                )

            eastmoney_industries = self._aggregate_eastmoney_industries(
                session, target_date
            )

            top_stocks = []
            continuous_rows = (
                session.query(ContinuousLimitUp)
                .filter(ContinuousLimitUp.date == target_date)
                .order_by(
                    ContinuousLimitUp.continuous_days.desc(),
                    ContinuousLimitUp.latest_limit_up_time.asc(),
                    ContinuousLimitUp.code.asc(),
                )
                .all()
            )
            for item in continuous_rows:
                pool = (
                    session.query(LimitUpPool)
                    .filter(
                        LimitUpPool.date == target_date,
                        LimitUpPool.code == item.code,
                    )
                    .one_or_none()
                )
                top_stocks.append(
                    StockSummary(
                        code=item.code,
                        name=item.name,
                        continuous_days=item.continuous_days or 0,
                        limit_up_time=self._normalize_limit_up_time(
                            item.latest_limit_up_time
                            or (pool.limit_up_time if pool else "")
                            or ""
                        ),
                        block_name=(pool.block_name if pool else "") or "",
                        reason=self._shorten(
                            (pool.concept if pool else "") or item.concept or "",
                            28,
                        ),
                    )
                )

            early_stocks = self._build_early_stocks(session, target_date)
            weak_boards = self._build_weak_boards(session, target_date)
            breakout_stocks = self._build_breakout_stocks(session, target_date)
            lower_limit_stocks = self._build_lower_limit_stocks(
                session, target_date
            )
            one_word_stocks = self._build_one_word_stocks(session, target_date)
            board_overlaps = self._build_board_overlaps(
                session, target_date, top_blocks
            )
            previous_high_feedback = self._build_previous_high_feedback(
                session, target_date
            )
            first_time_count = (
                session.query(LimitUpPool)
                .filter(
                    LimitUpPool.date == target_date,
                    LimitUpPool.limit_up_time.isnot(None),
                    LimitUpPool.limit_up_time != "",
                )
                .count()
            )
            last_time_count = (
                session.query(LimitUpPool)
                .filter(
                    LimitUpPool.date == target_date,
                    LimitUpPool.last_time.isnot(None),
                    LimitUpPool.last_time != "",
                )
                .count()
            )
            if hr_limit_up_count and first_time_count == 0:
                data_warnings.append(
                    "同花顺涨停池缺少首次涨停时间，早盘强势无法判断"
                )
            if hr_limit_up_count and last_time_count == 0 and not weak_boards:
                data_warnings.append(
                    "同花顺涨停池缺少最后涨停时间且未识别开板次数，"
                    "分歧弱板无法判断"
                )
            pool_rows = (
                session.query(LimitUpPool)
                .filter(LimitUpPool.date == target_date)
                .order_by(LimitUpPool.code.asc())
                .all()
            )
            pool_stock_reasons = [
                BlockStockReasonSummary(
                    code=item.code,
                    name=item.name,
                    reason_type=item.concept or "",
                    reason_info=item.reason or "",
                )
                for item in pool_rows
                if item.concept or item.reason
            ]
            limit_up_pool_metrics = [
                LimitUpPoolAnalysisSummary(
                    code=item.code,
                    name=item.name,
                    change_percent=self._to_float(item.change_percent),
                    limit_up_type=item.limit_up_type or "",
                    first_limit_up_time=self._normalize_limit_up_time(
                        item.limit_up_time
                    ),
                    last_limit_up_time=self._normalize_limit_up_time(item.last_time),
                    open_count=item.open_count or 0,
                    turnover_rate=self._to_float(item.turnover_rate),
                )
                for item in pool_rows
            ]
            daily_review_row = (
                session.query(DailyMarketReview)
                .filter(DailyMarketReview.date == target_date)
                .one_or_none()
            )
            daily_review = (
                DailyReviewSummary(
                    content=daily_review_row.content,
                    provider=daily_review_row.provider,
                    model=daily_review_row.model or "default",
                )
                if daily_review_row
                else None
            )

            is_complete = all(
                [
                    continuous_count > 0,
                    block_count > 0,
                    hr_limit_up_count > 0,
                    em_limit_up_count > 0,
                ]
            )

            return FeishuStockReport(
                target_date=target_date,
                is_complete=is_complete,
                continuous_count=continuous_count,
                block_count=block_count,
                hr_limit_up_count=hr_limit_up_count,
                em_limit_up_count=em_limit_up_count,
                lower_limit_count=lower_limit_count,
                max_continuous_days=int(max_days),
                continuous_distribution=continuous_distribution,
                limit_up_type_distribution=limit_up_type_distribution,
                data_warnings=data_warnings,
                fetch_logs=fetch_logs,
                top_blocks=top_blocks,
                eastmoney_industries=eastmoney_industries,
                top_stocks=top_stocks,
                early_stocks=early_stocks,
                weak_boards=weak_boards,
                breakout_stocks=breakout_stocks,
                lower_limit_stocks=lower_limit_stocks,
                daily_review=daily_review,
                one_word_stocks=one_word_stocks,
                previous_high_feedback=previous_high_feedback,
                pool_stock_reasons=pool_stock_reasons,
                limit_up_pool_metrics=limit_up_pool_metrics,
                board_overlaps=board_overlaps,
            )
        finally:
            session.close()

    def build_card(self, report: FeishuStockReport) -> Dict[str, Any]:
        """Build a Feishu Card 2.0 payload body."""
        material = self.build_analysis_material(report)
        review_parts = ["", "", "**市场复盘**"]
        if report.daily_review:
            review_parts.extend(
                [
                    report.daily_review.content,
                    "",
                    "---",
                    config.ai.output_metadata(
                        report.daily_review.provider,
                        report.daily_review.model,
                    ),
                ]
            )
        else:
            review_parts.append("- 尚未生成当日市场复盘")

        content = "\n".join([material, *review_parts])
        date_text = report.target_date.strftime("%Y-%m-%d")

        return {
            "schema": "2.0",
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"StoChips 每日涨停播报 - {date_text}",
                },
                "template": "green" if report.is_complete else "yellow",
            },
            "body": {
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content,
                    }
                ]
            },
        }

    def build_analysis_material(self, report: FeishuStockReport) -> str:
        """Render factual daily material shared by Feishu and the Codex review."""
        status_text = "基础完整" if report.is_complete else "不完整"
        if report.is_complete and report.data_warnings:
            status_text += "（部分分析字段缺失）"
        continuous_text = self._format_continuous_distribution(
            report.continuous_distribution
        )
        limit_type_text = self._format_named_distribution(
            report.limit_up_type_distribution
        )
        block_lines = self._format_blocks(report.top_blocks)
        eastmoney_industry_lines = self._format_industries(
            report.eastmoney_industries
        )
        stock_lines = self._format_core_continuous(report.top_stocks)
        early_lines = self._format_stocks(
            report.early_stocks,
            empty_message="暂无早盘强势数据",
        )
        weak_lines = self._format_weak_boards(report.weak_boards)
        breakout_lines = self._format_breakouts(report.breakout_stocks)
        lower_limit_lines = self._format_lower_limit_stocks(
            report.lower_limit_stocks
        )
        one_word_lines = self._format_stocks(
            report.one_word_stocks,
            empty_message="暂无一字板明细",
        )
        previous_high_lines = self._format_previous_high_feedback(
            report.previous_high_feedback
        )
        overlap_lines = self._format_board_overlaps(report.board_overlaps)
        warning_lines = self._format_warnings(report.data_warnings)
        log_lines = self._format_logs(report.fetch_logs)

        return "\n".join(
            [
                f"**数据状态**：{status_text}",
                (
                    f"**涨停概览**：同花顺 {report.hr_limit_up_count} 只，"
                    f"东财 {report.em_limit_up_count} 只，"
                    f"连板 {report.continuous_count} 只，"
                    f"最高 {report.max_continuous_days} 板"
                ),
                f"**涨停结构**：{limit_type_text}；连板梯队：{continuous_text}",
                f"**跌停概览**：同花顺 {report.lower_limit_count} 只",
                warning_lines,
                "",
                "**同花顺板块热度**",
                block_lines,
                "",
                "**热点板块交集（同花顺成员去重）**",
                overlap_lines,
                "",
                "**东财行业涨停**",
                eastmoney_industry_lines,
                "",
                "**核心连板**",
                stock_lines,
                "",
                "**昨日高标反馈（收盘涨停口径）**",
                previous_high_lines,
                "",
                "**一字板明细**",
                one_word_lines,
                "",
                "**早盘强势（同花顺首次涨停时间）**",
                early_lines,
                "",
                "**分歧弱板/回封样本**",
                weak_lines,
                "",
                "**同花顺跌停池**",
                lower_limit_lines,
                "",
                "**涨停前高突破**",
                breakout_lines,
                "",
                "**抓取日志**",
                log_lines,
            ]
        )

    def build_previous_trading_day_material(
        self, current_report: FeishuStockReport
    ) -> str:
        """Render a compact prior-day comparison for the Codex review only."""
        session = self._get_session()
        try:
            trading_dates = self._recent_trading_dates(
                session, current_report.target_date, lookback=1
            )
            previous_dates = [
                item for item in trading_dates if item < current_report.target_date
            ]
        finally:
            session.close()

        if not previous_dates:
            return "**前一交易日对照**\n- 暂无可用前一交易日数据"

        previous_report = self.build_report(previous_dates[0])
        previous_blocks = {
            item.block_name: item.stock_count for item in previous_report.top_blocks
        }
        current_blocks = {
            item.block_name: item.stock_count for item in current_report.top_blocks
        }
        shared_block_changes = [
            (
                name,
                previous_count,
                current_blocks[name],
            )
            for name, previous_count in previous_blocks.items()
            if name in current_blocks
        ]
        shared_block_changes.sort(
            key=lambda item: (abs(item[2] - item[1]), item[2], item[0]),
            reverse=True,
        )
        previous_top_blocks = "、".join(
            f"{item.block_name} {item.stock_count}家"
            for item in previous_report.top_blocks
        ) or "暂无"
        block_changes = "、".join(
            f"{name} {previous_count}->{current_count}家"
            for name, previous_count, current_count in shared_block_changes
        ) or "暂无同名热点板块"

        comparison_summary = "\n".join(
            [
                f"**前一交易日对照（{previous_report.target_date:%Y-%m-%d}）**",
                (
                    f"- 涨停概览：同花顺 {previous_report.hr_limit_up_count} 只，"
                    f"东财 {previous_report.em_limit_up_count} 只，"
                    f"跌停 {getattr(previous_report, 'lower_limit_count', 0)} 只，"
                    f"连板 {previous_report.continuous_count} 只，"
                    f"最高 {previous_report.max_continuous_days} 板"
                ),
                (
                    "- 涨停结构："
                    f"{self._format_named_distribution(previous_report.limit_up_type_distribution)}；"
                    f"连板梯队：{self._format_continuous_distribution(previous_report.continuous_distribution)}"
                ),
                f"- 核心连板：{self._format_core_continuous(previous_report.top_stocks)}",
                f"- 全部热点板块：{previous_top_blocks}",
                f"- 与当日共同热点变化：{block_changes}",
            ]
        )
        previous_facts = self.build_analysis_material(previous_report)
        previous_reasons = self.build_codex_reason_material(previous_report)
        return (
            f"{comparison_summary}\n\n"
            f"**前一交易日完整事实材料（{previous_report.target_date:%Y-%m-%d}）**\n"
            f"{previous_facts}\n\n"
            f"{previous_reasons}"
        )

    def build_codex_reason_material(self, report: FeishuStockReport) -> str:
        """Render full THS reason fields for Codex without bloating Feishu."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for block in report.top_blocks:
            for stock in block.stock_reasons:
                key = stock.code or stock.name
                item = grouped.setdefault(
                    key,
                    {
                        "code": stock.code,
                        "name": stock.name,
                        "blocks": [],
                        "reason_types": [],
                        "reason_infos": [],
                    },
                )
                if block.block_name not in item["blocks"]:
                    item["blocks"].append(block.block_name)
                if stock.reason_type and stock.reason_type not in item["reason_types"]:
                    item["reason_types"].append(stock.reason_type)
                if stock.reason_info and stock.reason_info not in item["reason_infos"]:
                    item["reason_infos"].append(stock.reason_info)

        for stock in getattr(report, "pool_stock_reasons", []):
            key = stock.code or stock.name
            item = grouped.setdefault(
                key,
                {
                    "code": stock.code,
                    "name": stock.name,
                    "blocks": [],
                    "reason_types": [],
                    "reason_infos": [],
                },
            )
            if stock.reason_type and stock.reason_type not in item["reason_types"]:
                item["reason_types"].append(stock.reason_type)
            if stock.reason_info and stock.reason_info not in item["reason_infos"]:
                item["reason_infos"].append(stock.reason_info)

        reason_items = [
            item
            for item in grouped.values()
            if item["reason_types"] or item["reason_infos"]
        ]
        sections = []
        if reason_items:
            lines = ["**同花顺个股涨停原因（Codex分析补充）**"]
            for index, item in enumerate(reason_items, 1):
                code = f"({item['code']})" if item["code"] else ""
                reason_types = "；".join(item["reason_types"]) or "暂无"
                reason_infos = "\n\n".join(item["reason_infos"]) or "暂无"
                lines.extend(
                    [
                        f"{index}. {item['name']}{code}",
                        f"- 所属热度板块：{'、'.join(item['blocks'])}",
                        f"- 简略原因（reason_type）：{reason_types}",
                        f"- 详细原因（reason_info）：\n{reason_infos}",
                    ]
                )
            sections.append("\n".join(lines))

        metrics = getattr(report, "limit_up_pool_metrics", [])
        if metrics:
            lines = ["**同花顺全量涨停池指标（Codex分析补充）**"]
            for index, item in enumerate(metrics, 1):
                details = []
                if item.change_percent is not None:
                    details.append(f"涨幅 {self._format_percent(item.change_percent)}")
                if item.limit_up_type:
                    details.append(item.limit_up_type)
                if item.first_limit_up_time:
                    details.append(f"首次涨停 {item.first_limit_up_time}")
                if item.last_limit_up_time:
                    details.append(f"最后涨停 {item.last_limit_up_time}")
                details.append(f"开板 {item.open_count} 次")
                if item.turnover_rate is not None:
                    details.append(f"换手 {self._format_percent(item.turnover_rate)}")
                else:
                    details.append("换手 暂无")
                lines.append(
                    f"{index}. {item.name}({item.code})：{'，'.join(details)}"
                )
            sections.append("\n".join(lines))

        if not sections:
            return "**同花顺个股涨停原因（Codex分析补充）**\n- 暂无原因和涨停池指标数据"
        return "\n\n".join(sections)

    def send_report(self, target_date: date) -> Dict[str, Any]:
        """Collect stock data and send a Feishu card."""
        if not self.webhook_url:
            raise ValueError("未设置 FEISHU_WEBHOOK_URL，无法发送飞书播报")

        report = self.build_report(target_date)
        card = self.build_card(report)
        result = self._send_card(card)

        logger.info("飞书播报发送成功: %s", target_date)
        return {
            "feishu_response": result,
            "date": target_date.isoformat(),
            "is_complete": report.is_complete,
            "hr_limit_up_count": report.hr_limit_up_count,
            "em_limit_up_count": report.em_limit_up_count,
            "lower_limit_count": report.lower_limit_count,
            "daily_review_available": report.daily_review is not None,
        }

    def send_status_notification(
        self,
        target_date: date,
        title: str,
        content: str,
    ) -> Dict[str, Any]:
        """Send an operational status card through the same guarded webhook path."""
        if not self.webhook_url:
            raise ValueError("未设置 FEISHU_WEBHOOK_URL，无法发送飞书通知")

        card = {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "red",
            },
            "body": {
                "elements": [{"tag": "markdown", "content": content}]
            },
        }
        result = self._send_card(card)
        logger.info("飞书状态通知发送成功: %s", target_date)
        return {"feishu_response": result, "date": target_date.isoformat()}

    def _send_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }
        if self.webhook_secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._generate_sign(timestamp, self.webhook_secret)

        result = self._post_with_retry(payload)

        if result.get("code", 0) != 0:
            raise RuntimeError(f"飞书发送失败: {result}")
        return result

    def _post_with_retry(
        self,
        payload: Dict[str, Any],
        *,
        not_before: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Post the Feishu payload, retrying recoverable platform rate limits."""
        result: Dict[str, Any] = {}
        scheduled_at = not_before
        for attempt in range(1, FEISHU_SEND_MAX_ATTEMPTS + 1):
            send_at = next_feishu_send_at(not_before=scheduled_at)
            wait_until_feishu_send_at(send_at)
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            try:
                result = response.json()
            except ValueError as exc:
                raise RuntimeError(f"飞书返回非JSON响应: {response.text}") from exc

            if result.get("code", 0) != FEISHU_FREQUENCY_LIMIT_CODE:
                return result

            if attempt >= FEISHU_SEND_MAX_ATTEMPTS:
                return result

            retry_after = FEISHU_SEND_RETRY_DELAYS[attempt - 1]
            retry_not_before = datetime.now() + timedelta(seconds=retry_after)
            scheduled_at = next_feishu_send_at(not_before=retry_not_before)
            logger.warning(
                "飞书发送被限流，将在 %s 重试: attempt=%s/%s code=%s msg=%s",
                scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
                attempt,
                FEISHU_SEND_MAX_ATTEMPTS,
                result.get("code"),
                result.get("msg"),
            )

        return result

    def _aggregate_blocks_from_pool(
        self,
        session: Session,
        target_date: date,
        limit: Optional[int] = None,
        exclude: Optional[set[str]] = None,
    ) -> List[BlockSummary]:
        exclude = exclude or set()
        query = (
            session.query(
                LimitUpPool.block_name,
                func.count(LimitUpPool.id),
                func.min(LimitUpPool.limit_up_time),
            )
            .filter(
                LimitUpPool.date == target_date,
                LimitUpPool.block_name.isnot(None),
                LimitUpPool.block_name != "",
            )
            .group_by(LimitUpPool.block_name)
            .order_by(
                func.count(LimitUpPool.id).desc(),
                func.min(LimitUpPool.limit_up_time).asc(),
            )
        )
        if limit is not None:
            query = query.limit(limit + len(exclude))
        rows = query.all()

        blocks = []
        for block_name, stock_count, _first_time in rows:
            if block_name in exclude:
                continue
            leader = self._find_block_leader(session, target_date, block_name)
            blocks.append(
                BlockSummary(
                    block_name=block_name,
                    stock_count=int(stock_count),
                    leading_stock_name=leader,
                    change_percent=None,
                    source="limit_up_pool",
                )
            )
            if limit is not None and len(blocks) >= limit:
                break
        return blocks

    def _build_block_summary(
        self,
        session: Session,
        target_date: date,
        item: BlockTop,
    ) -> BlockSummary:
        rows = self._block_stock_rows(session, target_date, item.block_code)
        return BlockSummary(
            block_name=item.block_name,
            stock_count=item.stock_count or 0,
            leading_stock_name=item.leading_stock_name or item.leading_stock or "",
            change_percent=self._to_float(item.change_percent),
            stocks=[self._block_stock_label(stock) for stock in rows],
            block_code=item.block_code,
            stock_reasons=[
                BlockStockReasonSummary(
                    code=stock.code,
                    name=stock.name,
                    reason_type=stock.reason_type or "",
                    reason_info=stock.reason_info or "",
                )
                for stock in rows
            ],
        )

    def _build_board_overlaps(
        self,
        session: Session,
        target_date: date,
        blocks: List[BlockSummary],
    ) -> List[BoardOverlapSummary]:
        board_names_by_code = {
            item.block_code: item.block_name
            for item in blocks
            if item.source == "block_top" and item.block_code
        }
        if len(board_names_by_code) < 2:
            return []

        members_by_code: Dict[str, set[str]] = {
            block_code: set() for block_code in board_names_by_code
        }
        rows = (
            session.query(BlockTopStock.block_code, BlockTopStock.code)
            .filter(
                BlockTopStock.date == target_date,
                BlockTopStock.block_code.in_(board_names_by_code),
            )
            .all()
        )
        for block_code, stock_code in rows:
            if stock_code:
                members_by_code[block_code].add(stock_code)

        active_codes = [
            block_code
            for block_code, members in members_by_code.items()
            if members
        ]
        overlaps = []
        for index, first_code in enumerate(active_codes):
            first_members = members_by_code[first_code]
            for second_code in active_codes[index + 1 :]:
                second_members = members_by_code[second_code]
                shared_count = len(first_members & second_members)
                if shared_count < 3:
                    continue
                overlaps.append(
                    BoardOverlapSummary(
                        first_block_name=board_names_by_code[first_code],
                        second_block_name=board_names_by_code[second_code],
                        shared_stock_count=shared_count,
                        first_stock_count=len(first_members),
                        second_stock_count=len(second_members),
                    )
                )

        return sorted(
            overlaps,
            key=lambda item: (
                item.shared_stock_count,
                min(item.first_stock_count, item.second_stock_count),
                item.first_block_name,
                item.second_block_name,
            ),
            reverse=True,
        )

    @staticmethod
    def _block_stock_label(stock: BlockTopStock) -> str:
        height = stock.limit_up_type or f"{int(stock.continuous_days or 1)}板"
        return f"{stock.name}（{height}）"

    def _block_stock_rows(
        self, session: Session, target_date: date, block_code: str
    ) -> List[BlockTopStock]:
        if not block_code:
            return []

        return (
            session.query(BlockTopStock)
            .filter(
                BlockTopStock.date == target_date,
                BlockTopStock.block_code == block_code,
            )
            .order_by(
                BlockTopStock.continuous_days.desc(),
                BlockTopStock.first_limit_up_time.asc(),
                BlockTopStock.sort_order.asc(),
                BlockTopStock.code.asc(),
            )
            .all()
        )

    def _aggregate_eastmoney_industries(
        self, session: Session, target_date: date, limit: Optional[int] = None
    ) -> List[IndustrySummary]:
        query = (
            session.query(
                EastmoneyZTPool.block_name,
                func.count(EastmoneyZTPool.id),
            )
            .filter(
                EastmoneyZTPool.date == target_date,
                EastmoneyZTPool.block_name.isnot(None),
                EastmoneyZTPool.block_name != "",
            )
            .group_by(EastmoneyZTPool.block_name)
            .order_by(
                func.count(EastmoneyZTPool.id).desc(),
                EastmoneyZTPool.block_name.asc(),
            )
        )
        if limit is not None:
            query = query.limit(limit)
        rows = query.all()

        industries = []
        for industry_name, stock_count in rows:
            leader_rows = (
                session.query(
                    EastmoneyZTPool,
                    func.coalesce(ContinuousLimitUp.continuous_days, 1),
                )
                .outerjoin(
                    ContinuousLimitUp,
                    (ContinuousLimitUp.date == EastmoneyZTPool.date)
                    & (ContinuousLimitUp.code == EastmoneyZTPool.code),
                )
                .filter(
                    EastmoneyZTPool.date == target_date,
                    EastmoneyZTPool.block_name == industry_name,
                )
                .order_by(
                    func.coalesce(ContinuousLimitUp.continuous_days, 0).desc(),
                    EastmoneyZTPool.first_limit_up_time.asc(),
                    EastmoneyZTPool.code.asc(),
                )
                .all()
            )
            industries.append(
                IndustrySummary(
                    industry_name=industry_name,
                    stock_count=int(stock_count),
                    leaders=[
                        f"{item.name}（{int(continuous_days or 1)}板）"
                        for item, continuous_days in leader_rows
                    ],
                )
            )
        return industries

    def _find_block_leader(
        self, session: Session, target_date: date, block_name: str
    ) -> str:
        item = (
            session.query(LimitUpPool)
            .filter(
                LimitUpPool.date == target_date,
                LimitUpPool.block_name == block_name,
            )
            .order_by(
                LimitUpPool.open_count.asc(),
                LimitUpPool.limit_up_time.asc(),
                LimitUpPool.code.asc(),
            )
            .first()
        )
        if not item:
            return ""
        return item.name

    def _build_stock_summary(
        self,
        item: Any,
        continuous_days: int = 1,
    ) -> StockSummary:
        return StockSummary(
            code=item.code,
            name=item.name,
            continuous_days=continuous_days,
            limit_up_time=self._normalize_limit_up_time(
                getattr(item, "limit_up_time", "")
                or getattr(item, "first_limit_up_time", "")
                or ""
            ),
            block_name=getattr(item, "block_name", "") or "",
            reason=self._shorten(
                getattr(item, "concept", "") or getattr(item, "reason", "") or "",
                28,
            ),
        )

    def _build_early_stocks(
        self,
        session: Session,
        target_date: date,
    ) -> List[StockSummary]:
        continuous_days_by_code = {
            item.code: item.continuous_days or 1
            for item in session.query(ContinuousLimitUp)
            .filter(ContinuousLimitUp.date == target_date)
            .all()
        }
        rows = (
            session.query(LimitUpPool)
            .filter(
                LimitUpPool.date == target_date,
                LimitUpPool.limit_up_time.isnot(None),
                LimitUpPool.limit_up_time != "",
            )
            .order_by(LimitUpPool.limit_up_time.asc(), LimitUpPool.code.asc())
            .all()
        )
        return [
            self._build_stock_summary(
                item,
                continuous_days_by_code.get(item.code, 1),
            )
            for item in rows
        ]

    def _build_weak_boards(
        self, session: Session, target_date: date
    ) -> List[WeakBoardSummary]:
        rows = (
            session.query(LimitUpPool)
            .filter(
                LimitUpPool.date == target_date,
                LimitUpPool.open_count > 0,
            )
            .order_by(
                LimitUpPool.open_count.desc(),
                LimitUpPool.turnover_rate.desc(),
                LimitUpPool.code.asc(),
            )
            .all()
        )
        if rows:
            return [
                WeakBoardSummary(
                    code=item.code,
                    name=item.name,
                    open_count=item.open_count or 0,
                    turnover_rate=self._to_float(item.turnover_rate),
                    block_name=item.block_name or "",
                    reason=self._shorten(item.concept or item.reason or "", 24),
                )
                for item in rows
            ]

        pool_samples: Dict[str, WeakBoardSummary] = {}
        for item in (
            session.query(LimitUpPool)
            .filter(LimitUpPool.date == target_date)
            .all()
        ):
            first_time = self._normalize_limit_up_time(item.limit_up_time)
            last_time = self._normalize_limit_up_time(item.last_time)
            if not first_time or not last_time or last_time <= first_time:
                continue
            pool_samples[item.code] = WeakBoardSummary(
                code=item.code,
                name=item.name,
                open_count=0,
                turnover_rate=self._to_float(item.turnover_rate),
                block_name=item.block_name or "",
                reason=self._shorten(item.concept or item.reason or "", 24),
                first_limit_up_time=first_time,
                last_limit_up_time=last_time,
            )
        if pool_samples:
            return sorted(
                pool_samples.values(),
                key=lambda item: (
                    self._limit_up_time_gap_minutes(item),
                    item.code,
                ),
                reverse=True,
            )

        samples: Dict[str, WeakBoardSummary] = {}
        for item in (
            session.query(BlockTopStock)
            .filter(BlockTopStock.date == target_date)
            .all()
        ):
            first_time = self._normalize_limit_up_time(item.first_limit_up_time)
            last_time = self._normalize_limit_up_time(item.last_limit_up_time)
            if not first_time or not last_time or last_time <= first_time:
                continue
            sample = WeakBoardSummary(
                code=item.code,
                name=item.name,
                open_count=0,
                turnover_rate=None,
                block_name=item.block_name or "",
                reason=self._shorten(item.reason_type or "", 24),
                first_limit_up_time=first_time,
                last_limit_up_time=last_time,
            )
            existing = samples.get(item.code)
            if (
                existing is None
                or self._limit_up_time_gap_minutes(sample)
                > self._limit_up_time_gap_minutes(existing)
            ):
                samples[item.code] = sample

        return sorted(
            samples.values(),
            key=lambda item: (
                self._limit_up_time_gap_minutes(item),
                item.code,
            ),
            reverse=True,
        )

    def _build_one_word_stocks(
        self, session: Session, target_date: date
    ) -> List[StockSummary]:
        continuous_days_by_code = {
            item.code: item.continuous_days or 1
            for item in session.query(ContinuousLimitUp)
            .filter(ContinuousLimitUp.date == target_date)
            .all()
        }
        rows = (
            session.query(LimitUpPool)
            .filter(
                LimitUpPool.date == target_date,
                LimitUpPool.limit_up_type.contains("一字"),
            )
            .order_by(LimitUpPool.limit_up_time.asc(), LimitUpPool.code.asc())
            .all()
        )
        return [
            StockSummary(
                code=item.code,
                name=item.name,
                continuous_days=continuous_days_by_code.get(item.code, 1),
                limit_up_time=self._normalize_limit_up_time(item.limit_up_time),
                block_name=item.block_name or "",
                reason=self._shorten(item.concept or item.reason or "", 28),
            )
            for item in rows
        ]

    def _build_lower_limit_stocks(
        self, session: Session, target_date: date
    ) -> List[LowerLimitSummary]:
        rows = (
            session.query(LowerLimitPool)
            .filter(LowerLimitPool.date == target_date)
            .order_by(
                LowerLimitPool.first_limit_down_time.asc(),
                LowerLimitPool.code.asc(),
            )
            .all()
        )
        return [
            LowerLimitSummary(
                code=item.code,
                name=item.name,
                change_percent=self._to_float(item.change_percent),
                first_limit_down_time=self._normalize_limit_up_time(
                    item.first_limit_down_time
                ),
                last_limit_down_time=self._normalize_limit_up_time(
                    item.last_limit_down_time
                ),
                turnover_rate=self._to_float(item.turnover_rate),
                is_again_limit=bool(item.is_again_limit),
            )
            for item in rows
        ]

    def _build_previous_high_feedback(
        self, session: Session, target_date: date
    ) -> List[PreviousHighBoardSummary]:
        trading_dates = self._recent_trading_dates(session, target_date, lookback=1)
        previous_dates = [item for item in trading_dates if item < target_date]
        if not previous_dates:
            return []

        previous_date = previous_dates[0]
        rows = (
            session.query(ContinuousLimitUp)
            .filter(ContinuousLimitUp.date == previous_date)
            .order_by(
                ContinuousLimitUp.continuous_days.desc(),
                ContinuousLimitUp.code.asc(),
            )
            .all()
        )
        if not rows:
            return []

        highest_days = max(item.continuous_days or 0 for item in rows)
        high_rows = [
            item
            for item in rows
            if (item.continuous_days or 0) >= max(highest_days - 1, 2)
        ]
        current_continuous_days = {
            item.code: item.continuous_days or 0
            for item in session.query(ContinuousLimitUp)
            .filter(ContinuousLimitUp.date == target_date)
            .all()
        }
        current_limit_up_codes = {
            item.code
            for item in session.query(LimitUpPool.code)
            .filter(LimitUpPool.date == target_date)
            .all()
        }

        feedback = []
        for item in high_rows:
            if item.code in current_continuous_days:
                result = f"今日晋级至 {current_continuous_days[item.code]}板"
            elif item.code in current_limit_up_codes:
                result = "今日仍涨停，但未进入连板池"
            else:
                result = "今日未进入涨停池"
            feedback.append(
                PreviousHighBoardSummary(
                    code=item.code,
                    name=item.name,
                    previous_continuous_days=item.continuous_days or 0,
                    feedback=result,
                )
            )
        return feedback

    def _build_breakout_stocks(
        self, session: Session, target_date: date
    ) -> List[BreakoutSummary]:
        trading_dates = self._recent_trading_dates(session, target_date, lookback=60)
        previous_dates = [item for item in trading_dates if item < target_date]
        if not previous_dates:
            return []

        current_continuous_codes = {
            item.code
            for item in session.query(ContinuousLimitUp)
            .filter(ContinuousLimitUp.date == target_date)
            .all()
        }
        candidates = (
            session.query(LimitUpPool)
            .filter(LimitUpPool.date == target_date)
            .all()
        )

        results = []
        for pool in candidates:
            if pool.code in current_continuous_codes:
                continue

            breakout_price = self._stock_price(pool)
            if breakout_price is None:
                continue

            chain_rows = (
                session.query(ContinuousLimitUp)
                .filter(
                    ContinuousLimitUp.code == pool.code,
                    ContinuousLimitUp.date.in_(previous_dates),
                    ContinuousLimitUp.continuous_days >= 2,
                )
                .order_by(ContinuousLimitUp.date.desc())
                .all()
            )
            if not chain_rows:
                continue

            chain_segment = self._latest_chain_segment(chain_rows, previous_dates)
            if not chain_segment:
                continue

            chain_end = max(item.date for item in chain_segment)
            gap_trading_days = len(
                [
                    item
                    for item in previous_dates
                    if chain_end < item < target_date
                ]
            )
            if gap_trading_days < 1:
                continue

            previous_high = self._chain_high_price(session, chain_segment)
            if previous_high is None or previous_high <= 0:
                continue
            if breakout_price <= previous_high:
                continue

            previous_max_days = max(item.continuous_days or 0 for item in chain_segment)
            results.append(
                BreakoutSummary(
                    code=pool.code,
                    name=pool.name,
                    breakout_price=breakout_price,
                    previous_high_price=previous_high,
                    breakout_ratio=(breakout_price - previous_high)
                    / previous_high
                    * 100,
                    previous_max_days=previous_max_days,
                    gap_trading_days=gap_trading_days,
                    block_name=pool.block_name or "",
                    reason=self._shorten(pool.concept or pool.reason or "", 24),
                )
            )

        return sorted(
            results,
            key=lambda item: (
                item.breakout_ratio,
                item.previous_max_days,
                -item.gap_trading_days,
            ),
            reverse=True,
        )

    def _recent_trading_dates(
        self, session: Session, target_date: date, lookback: int
    ) -> List[date]:
        fetch_dates = {
            item[0]
            for item in (
                session.query(DataFetchLog.date)
                .filter(
                    DataFetchLog.date <= target_date,
                    DataFetchLog.data_type == "limit_up_pool",
                    DataFetchLog.status == "success",
                )
                .group_by(DataFetchLog.date)
                .all()
            )
            if item[0].weekday() < 5
        }
        if len(fetch_dates) < lookback + 1:
            fetch_dates.update(
                item[0]
                for item in (
                    session.query(LimitUpPool.date)
                    .filter(LimitUpPool.date <= target_date)
                    .group_by(LimitUpPool.date)
                    .all()
                )
                if item[0].weekday() < 5
            )
        return sorted(fetch_dates, reverse=True)[: lookback + 1]

    def _latest_chain_segment(
        self, chain_rows: List[ContinuousLimitUp], previous_dates: List[date]
    ) -> List[ContinuousLimitUp]:
        by_date = {item.date: item for item in chain_rows}
        latest_date = max(by_date)
        segment = []
        started = False
        for trading_date in previous_dates:
            if trading_date == latest_date:
                started = True
            if not started:
                continue
            row = by_date.get(trading_date)
            if not row:
                break
            segment.append(row)
        return segment

    def _chain_high_price(
        self, session: Session, chain_segment: List[ContinuousLimitUp]
    ) -> Optional[float]:
        prices = []
        for item in chain_segment:
            price = self._stock_price(item)
            if price is None:
                pool = (
                    session.query(LimitUpPool)
                    .filter(
                        LimitUpPool.date == item.date,
                        LimitUpPool.code == item.code,
                    )
                    .one_or_none()
                )
                price = self._stock_price(pool)
            if price is not None:
                prices.append(price)
        if not prices:
            return None
        return max(prices)

    def _prefer_regular_stocks(self, rows: List[Any], limit: int) -> List[Any]:
        regular = [item for item in rows if not self._is_special_stock(item.name)]
        special = [item for item in rows if self._is_special_stock(item.name)]
        return (regular + special)[:limit]

    @staticmethod
    def _is_special_stock(name: str) -> bool:
        normalized = (name or "").upper()
        return "ST" in normalized or "退" in normalized

    def _stock_price(self, item: Any) -> Optional[float]:
        if item is None:
            return None
        for attr in ("limit_up_price", "latest_price"):
            value = getattr(item, attr, None)
            price = self._to_float(value)
            if price is not None and price > 0:
                return price
        return None

    @staticmethod
    def _normalize_limit_up_time(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.isdigit() and len(text) >= 10:
            try:
                return datetime.fromtimestamp(
                    int(text), tz=timezone.utc
                ).astimezone(SHANGHAI_TIMEZONE).strftime("%H:%M")
            except (OverflowError, OSError, ValueError):
                return ""

        if len(text) >= 5 and text[2] == ":":
            return text[:5]

        compact = text.replace(":", "")
        if compact.isdigit() and len(compact) <= 6:
            normalized = compact.zfill(6)
            hour, minute = int(normalized[:2]), int(normalized[2:4])
            if hour < 24 and minute < 60:
                return f"{hour:02d}:{minute:02d}"
        return text

    @staticmethod
    def _limit_up_time_sort_key(value: str) -> int:
        try:
            hour, minute = value.split(":", 1)
            return int(hour) * 60 + int(minute)
        except (TypeError, ValueError):
            return 24 * 60

    def _limit_up_time_gap_minutes(self, item: WeakBoardSummary) -> int:
        return max(
            0,
            self._limit_up_time_sort_key(item.last_limit_up_time)
            - self._limit_up_time_sort_key(item.first_limit_up_time),
        )

    @staticmethod
    def _generate_sign(timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        cleaned = " ".join((value or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1] + "..."

    def _format_blocks(self, blocks: List[BlockSummary]) -> str:
        if not blocks:
            return "- 暂无板块数据"
        lines = []
        for index, item in enumerate(blocks, 1):
            summary = self._format_block_summary(item, include_leader=not item.stocks)
            stock_text = "、".join(item.stocks)
            if summary and stock_text:
                stock_text = f"{summary}，{stock_text}"
            elif summary:
                stock_text = summary
            lines.append(f"{index}. {item.block_name}：{stock_text}")
        return "\n".join(lines)

    def _format_block_summary(
        self, item: BlockSummary, include_leader: bool = True
    ) -> str:
        parts = []
        if item.stock_count:
            parts.append(f"{item.stock_count} 家涨停")
        if item.change_percent is not None:
            parts.append(f"涨幅 {self._format_percent(item.change_percent)}")
        if include_leader and item.leading_stock_name:
            parts.append(f"龙头 {item.leading_stock_name}")
        return "，".join(parts) if parts else "暂无个股"

    def _format_industries(self, industries: List[IndustrySummary]) -> str:
        if not industries:
            return "- 暂无东财行业数据"
        lines = []
        for index, item in enumerate(industries, 1):
            leaders = "、".join(item.leaders) if item.leaders else "暂无个股"
            lines.append(f"{index}. {item.industry_name}：{leaders}")
        return "\n".join(lines)

    def _format_core_continuous(self, stocks: List[StockSummary]) -> str:
        if not stocks:
            return "- 暂无连板数据"

        grouped: Dict[int, List[StockSummary]] = {}
        for item in stocks:
            grouped.setdefault(item.continuous_days, []).append(item)

        lines = []
        for index, days in enumerate(sorted(grouped.keys(), reverse=True), 1):
            labels = "、".join(
                f"{item.name}({item.code})" for item in grouped[days]
            )
            lines.append(f"{index}. {days}板：{labels}")
        return "\n".join(lines)

    def _format_stocks(
        self,
        stocks: List[StockSummary],
        *,
        empty_message: str = "暂无股票数据",
    ) -> str:
        if not stocks:
            return f"- {empty_message}"
        lines = []
        for index, item in enumerate(stocks, 1):
            reason = f"，{item.reason}" if item.reason else ""
            block = f"，{item.block_name}" if item.block_name else ""
            time_text = f"，{item.limit_up_time}" if item.limit_up_time else ""
            lines.append(
                f"{index}. {item.name}({item.code})：{item.continuous_days}板"
                f"{time_text}{block}{reason}"
            )
        return "\n".join(lines)

    def _format_weak_boards(self, stocks: List[WeakBoardSummary]) -> str:
        if not stocks:
            return "- 暂无分歧弱板数据"
        lines = []
        if stocks[0].first_limit_up_time:
            lines.append(
                "- 同花顺开板次数缺失，以下根据首次与最后涨停时间推断回封分歧样本"
            )
        for index, item in enumerate(stocks, 1):
            turnover = self._format_percent(item.turnover_rate)
            block = f"，{item.block_name}" if item.block_name else ""
            reason = f"，{item.reason}" if item.reason else ""
            if item.first_limit_up_time:
                gap_minutes = self._limit_up_time_gap_minutes(item)
                lines.append(
                    f"{index}. {item.name}({item.code})：首次涨停 {item.first_limit_up_time}，"
                    f"最后涨停 {item.last_limit_up_time}，间隔 {gap_minutes} 分钟"
                    f"{block}{reason}"
                )
                continue
            lines.append(
                f"{index}. {item.name}({item.code})：开板 {item.open_count} 次，"
                f"换手 {turnover}{block}{reason}"
            )
        return "\n".join(lines)

    def _format_lower_limit_stocks(
        self, stocks: List[LowerLimitSummary]
    ) -> str:
        if not stocks:
            return "- 暂无跌停数据"
        lines = []
        for index, item in enumerate(stocks, 1):
            details = [f"跌幅 {self._format_percent(item.change_percent)}"]
            if item.first_limit_down_time:
                details.append(f"首次跌停 {item.first_limit_down_time}")
            if item.last_limit_down_time:
                details.append(f"最后跌停 {item.last_limit_down_time}")
            if item.turnover_rate is not None:
                details.append(f"换手 {self._format_percent(item.turnover_rate)}")
            if item.is_again_limit:
                details.append("再次跌停")
            lines.append(f"{index}. {item.name}({item.code})：{'，'.join(details)}")
        return "\n".join(lines)

    @staticmethod
    def _format_previous_high_feedback(
        stocks: List[PreviousHighBoardSummary],
    ) -> str:
        if not stocks:
            return "- 暂无可对照的前一交易日连板数据"
        lines = [
            "- 仅对照今日是否仍在涨停池；按钮、反包、强势横盘等盘口数据仍需额外数据源"
        ]
        lines.extend(
            f"{index}. {item.name}({item.code})：昨日 {item.previous_continuous_days}板，{item.feedback}"
            for index, item in enumerate(stocks, 1)
        )
        return "\n".join(lines)

    @staticmethod
    def _format_board_overlaps(overlaps: List[BoardOverlapSummary]) -> str:
        if not overlaps:
            return "- 暂无显著交集数据"
        return "\n".join(
            f"{index}. {item.first_block_name} ∩ {item.second_block_name}："
            f"{item.shared_stock_count} 只共同涨停"
            f"（占前者 {item.shared_stock_count / item.first_stock_count:.0%}，"
            f"占后者 {item.shared_stock_count / item.second_stock_count:.0%}）"
            for index, item in enumerate(overlaps, 1)
        )

    def _format_breakouts(self, stocks: List[BreakoutSummary]) -> str:
        windows = (
            (5, "5个交易日内涨停前高突破"),
            (10, "6-10个交易日内涨停前高突破"),
            (30, "11-30个交易日内涨停前高突破"),
            (60, "31-60个交易日内涨停前高突破"),
        )
        lines: List[str] = []
        lower_bound = 0
        for upper_bound, title in windows:
            grouped = [
                item
                for item in stocks
                if lower_bound < item.gap_trading_days <= upper_bound
            ]
            lines.append(f"**{title}**")
            if not grouped:
                lines.append("- 暂无")
            else:
                for index, item in enumerate(grouped, 1):
                    block = f"，{item.block_name}" if item.block_name else ""
                    reason = f"，{item.reason}" if item.reason else ""
                    lines.append(
                        f"{index}. {item.name}({item.code})："
                        f"前期{item.previous_max_days}板，断板{item.gap_trading_days}个交易日，"
                        f"前高{item.previous_high_price:.2f}，"
                        f"今涨停{item.breakout_price:.2f}，"
                        f"突破{item.breakout_ratio:.1f}%{block}{reason}"
                    )
            lower_bound = upper_bound
        # Feishu Markdown collapses single line breaks, so each time window must
        # be a separate block rather than a run-on sequence of headings and text.
        return "\n\n".join(lines)

    def _format_logs(self, logs: List[Dict[str, Any]]) -> str:
        if not logs:
            return "- 暂无抓取日志"
        lines = []
        for item in logs:
            suffix = ""
            if item.get("status") != "success" and item.get("error_message"):
                suffix = f"，{self._shorten(str(item['error_message']), 40)}"
            lines.append(
                f"- {item['data_type']}：{item['status']}，{item['record_count']} 条{suffix}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_warnings(warnings: List[str]) -> str:
        if not warnings:
            return ""
        return "\n".join(f"**数据提示**：{item}" for item in warnings)

    @staticmethod
    def _format_percent(value: Optional[float]) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}%"

    @staticmethod
    def _format_continuous_distribution(distribution: Dict[int, int]) -> str:
        if not distribution:
            return "暂无连板梯队"
        return "，".join(
            f"{days}板 {count}只"
            for days, count in sorted(distribution.items(), reverse=True)
        )

    @staticmethod
    def _format_named_distribution(distribution: Dict[str, int]) -> str:
        if not distribution:
            return "暂无"
        return "，".join(
            f"{name} {count}只"
            for name, count in sorted(
                distribution.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )


def create_feishu_notifier(
    database_url: str,
    webhook_url: Optional[str] = None,
    webhook_secret: Optional[str] = None,
) -> FeishuStockNotifier:
    return FeishuStockNotifier(
        database_url,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
    )
