"""
通用辅助函数
"""

import functools
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, List, Optional, TypeVar, Iterator

T = TypeVar('T')


def safe_decimal(value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
    """
    安全转换为Decimal

    Args:
        value: 输入值
        default: 默认值

    Returns:
        Decimal值或默认值
    """
    if value is None or value == '' or value == '-':
        return default
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数

    Args:
        value: 输入值
        default: 默认值

    Returns:
        整数值或默认值
    """
    if value is None or value == '' or value == '-':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """
    安全转换为字符串

    Args:
        value: 输入值
        default: 默认值

    Returns:
        字符串值或默认值
    """
    if value is None:
        return default
    return str(value)


def parse_date(date_str: str) -> Optional[date]:
    """
    解析日期字符串

    支持格式:
    - YYYYMMDD
    - YYYY-MM-DD
    - YYYY/MM/DD

    Args:
        date_str: 日期字符串

    Returns:
        date对象或None
    """
    if not date_str:
        return None

    formats = [
        '%Y%m%d',
        '%Y-%m-%d',
        '%Y/%m/%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def format_date(dt: date, fmt: str = '%Y%m%d') -> str:
    """
    格式化日期

    Args:
        dt: date对象
        fmt: 格式字符串

    Returns:
        格式化后的日期字符串
    """
    return dt.strftime(fmt)


def chunk_list(lst: List[T], chunk_size: int) -> Iterator[List[T]]:
    """
    将列表分块

    Args:
        lst: 输入列表
        chunk_size: 每块大小

    Yields:
        分块后的列表
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


class timer:
    """
    计时器上下文管理器

    Usage:
        with timer("操作名称"):
            # 执行操作
            pass
    """

    def __init__(self, name: str = "操作", logger=None):
        self.name = name
        self.logger = logger
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        if self.logger:
            self.logger.info(f"⏱️ 开始: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time

        if self.logger:
            if exc_type:
                self.logger.error(f"❌ {self.name} 失败 ({elapsed:.2f}s): {exc_val}")
            else:
                self.logger.info(f"✅ {self.name} 完成 ({elapsed:.2f}s)")

    @property
    def elapsed(self) -> float:
        """获取已用时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
