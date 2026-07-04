"""
Feishu card notifier for daily stock reports.
"""

import base64
import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from ..models.database import (
    BlockTop,
    ContinuousLimitUp,
    DataFetchLog,
    EastmoneyZTPool,
    LimitUpPool,
    RiskAssessment,
    get_session_maker,
    init_database,
)

logger = logging.getLogger(__name__)


@dataclass
class BlockSummary:
    block_name: str
    stock_count: int
    leading_stock_name: str
    change_percent: Optional[float]


@dataclass
class StockSummary:
    code: str
    name: str
    continuous_days: int
    limit_up_time: str
    block_name: str
    reason: str
    risk_level: str
    risk_score: Optional[float]
    suggestion: str


@dataclass
class FeishuStockReport:
    target_date: date
    is_complete: bool
    continuous_count: int
    block_count: int
    hr_limit_up_count: int
    em_limit_up_count: int
    max_continuous_days: int
    assessed_count: int
    ai_analyzed_count: int
    risk_distribution: Dict[str, int]
    fetch_logs: List[Dict[str, Any]]
    top_blocks: List[BlockSummary]
    top_stocks: List[StockSummary]


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
            max_days = (
                session.query(func.max(ContinuousLimitUp.continuous_days))
                .filter(ContinuousLimitUp.date == target_date)
                .scalar()
                or 0
            )

            risk_rows = (
                session.query(RiskAssessment.risk_level, func.count(RiskAssessment.id))
                .filter(RiskAssessment.date == target_date)
                .group_by(RiskAssessment.risk_level)
                .all()
            )
            risk_distribution = {
                level or "未知": int(count) for level, count in risk_rows
            }
            assessed_count = sum(risk_distribution.values())
            ai_analyzed_count = (
                session.query(RiskAssessment)
                .filter(
                    RiskAssessment.date == target_date,
                    RiskAssessment.is_ai_analyzed == 1,
                )
                .count()
            )

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

            top_blocks = [
                BlockSummary(
                    block_name=item.block_name,
                    stock_count=item.stock_count or 0,
                    leading_stock_name=(
                        item.leading_stock_name or item.leading_stock or ""
                    ),
                    change_percent=self._to_float(item.change_percent),
                )
                for item in session.query(BlockTop)
                .filter(BlockTop.date == target_date)
                .order_by(BlockTop.stock_count.desc(), BlockTop.change_percent.desc())
                .limit(3)
                .all()
            ]

            risk_by_code = {
                item.code: item
                for item in session.query(RiskAssessment)
                .filter(RiskAssessment.date == target_date)
                .all()
            }
            top_stocks = []
            for item in (
                session.query(ContinuousLimitUp)
                .filter(ContinuousLimitUp.date == target_date)
                .order_by(
                    ContinuousLimitUp.continuous_days.desc(),
                    ContinuousLimitUp.latest_limit_up_time.asc(),
                    ContinuousLimitUp.code.asc(),
                )
                .limit(8)
                .all()
            ):
                pool = (
                    session.query(LimitUpPool)
                    .filter(
                        LimitUpPool.date == target_date,
                        LimitUpPool.code == item.code,
                    )
                    .one_or_none()
                )
                risk = risk_by_code.get(item.code)
                top_stocks.append(
                    StockSummary(
                        code=item.code,
                        name=item.name,
                        continuous_days=item.continuous_days or 0,
                        limit_up_time=item.latest_limit_up_time
                        or (pool.limit_up_time if pool else "")
                        or "",
                        block_name=(pool.block_name if pool else "") or "",
                        reason=self._shorten(
                            (pool.reason if pool else "") or item.concept or "",
                            28,
                        ),
                        risk_level=(risk.risk_level if risk else "") or "未评估",
                        risk_score=self._to_float(risk.risk_score) if risk else None,
                        suggestion=(risk.suggestion if risk else "") or "",
                    )
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
                max_continuous_days=int(max_days),
                assessed_count=assessed_count,
                ai_analyzed_count=ai_analyzed_count,
                risk_distribution=risk_distribution,
                fetch_logs=fetch_logs,
                top_blocks=top_blocks,
                top_stocks=top_stocks,
            )
        finally:
            session.close()

    def build_card(self, report: FeishuStockReport) -> Dict[str, Any]:
        """Build a Feishu Card 2.0 payload body."""
        status_text = "完整" if report.is_complete else "不完整"
        risk_text = self._format_risk_distribution(report.risk_distribution)
        block_lines = self._format_blocks(report.top_blocks)
        stock_lines = self._format_stocks(report.top_stocks)
        log_lines = self._format_logs(report.fetch_logs)
        date_text = report.target_date.strftime("%Y-%m-%d")

        content = "\n".join(
            [
                f"**数据状态**：{status_text}",
                (
                    f"**涨停概览**：同花顺 {report.hr_limit_up_count} 只，"
                    f"东财 {report.em_limit_up_count} 只，"
                    f"连板 {report.continuous_count} 只，"
                    f"最高 {report.max_continuous_days} 板"
                ),
                (
                    f"**风险评估**：已评估 {report.assessed_count} 只，"
                    f"AI 已分析 {report.ai_analyzed_count} 只，{risk_text}"
                ),
                "",
                "**最强风口 Top 3**",
                block_lines,
                "",
                "**重点连板 Top 8**",
                stock_lines,
                "",
                "**抓取日志**",
                log_lines,
            ]
        )

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

    def send_report(self, target_date: date) -> Dict[str, Any]:
        """Collect stock data and send a Feishu card."""
        if not self.webhook_url:
            raise ValueError("未设置 FEISHU_WEBHOOK_URL，无法发送飞书播报")

        report = self.build_report(target_date)
        card = self.build_card(report)
        payload: Dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }
        if self.webhook_secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = self._generate_sign(timestamp, self.webhook_secret)

        response = requests.post(self.webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(f"飞书返回非JSON响应: {response.text}") from exc

        if result.get("code", 0) != 0:
            raise RuntimeError(f"飞书发送失败: {result}")

        logger.info("飞书播报发送成功: %s", target_date)
        return {
            "feishu_response": result,
            "date": target_date.isoformat(),
            "is_complete": report.is_complete,
            "hr_limit_up_count": report.hr_limit_up_count,
            "em_limit_up_count": report.em_limit_up_count,
            "assessed_count": report.assessed_count,
        }

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
            change = self._format_percent(item.change_percent)
            leader = f"，龙头 {item.leading_stock_name}" if item.leading_stock_name else ""
            lines.append(
                f"{index}. {item.block_name}："
                f"{item.stock_count} 家涨停，涨幅 {change}{leader}"
            )
        return "\n".join(lines)

    def _format_stocks(self, stocks: List[StockSummary]) -> str:
        if not stocks:
            return "- 暂无连板数据"
        lines = []
        for index, item in enumerate(stocks, 1):
            score = (
                f"{item.risk_score:.0f}分"
                if item.risk_score is not None
                else "无评分"
            )
            reason = f"，{item.reason}" if item.reason else ""
            block = f"，{item.block_name}" if item.block_name else ""
            time_text = f"，{item.limit_up_time}" if item.limit_up_time else ""
            suggestion = f"，{item.suggestion}" if item.suggestion else ""
            lines.append(
                f"{index}. {item.name}({item.code})：{item.continuous_days}板"
                f"{time_text}{block}，风险 {item.risk_level}/{score}{suggestion}{reason}"
            )
        return "\n".join(lines)

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
    def _format_percent(value: Optional[float]) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}%"

    @staticmethod
    def _format_risk_distribution(distribution: Dict[str, int]) -> str:
        if not distribution:
            return "暂无风险分布"
        preferred = ["高", "中", "低"]
        parts = [
            f"{level}风险 {distribution[level]} 只"
            for level in preferred
            if level in distribution
        ]
        parts.extend(
            f"{level} {count} 只"
            for level, count in distribution.items()
            if level not in preferred
        )
        return "，".join(parts)


def create_feishu_notifier(database_url: str) -> FeishuStockNotifier:
    return FeishuStockNotifier(database_url)
