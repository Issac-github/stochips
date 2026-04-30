"""
装饰器工具

提供常用的函数装饰器
"""

import asyncio
import functools
import logging
import time
from typing import Callable, TypeVar, Tuple, Type

T = TypeVar('T')
logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None
):
    """
    异步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始重试间隔（秒）
        exceptions: 需要捕获的异常类型
        on_retry: 重试时的回调函数，参数(异常, 重试次数)

    Usage:
        @async_retry(max_retries=3, delay=1.0)
        async def fetch_data():
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if on_retry:
                        on_retry(e, attempt + 1)
                    else:
                        logger.warning(
                            f"⚠️ {func.__name__} 第{attempt + 1}次尝试失败: {e}"
                        )

                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # 指数退避
                        logger.info(f"⏳ {wait_time:.1f}秒后重试...")
                        await asyncio.sleep(wait_time)

            logger.error(f"❌ {func.__name__} 在{max_retries}次尝试后仍然失败")
            raise last_exception

        return wrapper
    return decorator


def sync_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None
):
    """
    同步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始重试间隔（秒）
        exceptions: 需要捕获的异常类型
        on_retry: 重试时的回调函数

    Usage:
        @sync_retry(max_retries=3, delay=1.0)
        def fetch_data():
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if on_retry:
                        on_retry(e, attempt + 1)
                    else:
                        logger.warning(
                            f"⚠️ {func.__name__} 第{attempt + 1}次尝试失败: {e}"
                        )

                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.info(f"⏳ {wait_time:.1f}秒后重试...")
                        time.sleep(wait_time)

            logger.error(f"❌ {func.__name__} 在{max_retries}次尝试后仍然失败")
            raise last_exception

        return wrapper
    return decorator


def log_execution(
    level: str = "info",
    log_args: bool = False,
    log_result: bool = False,
    logger_name: str = None
):
    """
    记录函数执行的装饰器

    Args:
        level: 日志级别 (debug/info/warning/error)
        log_args: 是否记录参数
        log_result: 是否记录返回值
        logger_name: 自定义logger名称

    Usage:
        @log_execution(level="info", log_args=True)
        def process_data(x, y):
            return x + y
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        log = logging.getLogger(logger_name or func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()

            # 构建参数描述
            args_desc = ""
            if log_args:
                args_str = ", ".join([str(a) for a in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                args_desc = f" 参数: [{all_args}]"

            getattr(log, level)(f"▶️ 开始 {func.__name__}{args_desc}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                result_desc = ""
                if log_result:
                    result_desc = f" 结果: {result}"

                getattr(log, level)(
                    f"✅ 完成 {func.__name__} ({elapsed:.2f}s){result_desc}"
                )

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log.error(f"❌ 失败 {func.__name__} ({elapsed:.2f}s): {e}")
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()

            # 构建参数描述
            args_desc = ""
            if log_args:
                args_str = ", ".join([str(a) for a in args])
                kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                all_args = ", ".join(filter(None, [args_str, kwargs_str]))
                args_desc = f" 参数: [{all_args}]"

            getattr(log, level)(f"▶️ 开始 {func.__name__}{args_desc}")

            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                result_desc = ""
                if log_result:
                    result_desc = f" 结果: {result}"

                getattr(log, level)(
                    f"✅ 完成 {func.__name__} ({elapsed:.2f}s){result_desc}"
                )

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log.error(f"❌ 失败 {func.__name__} ({elapsed:.2f}s): {e}")
                raise

        # 根据函数类型返回对应的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator
