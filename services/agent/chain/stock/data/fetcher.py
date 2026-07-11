"""
股票数据抓取模块
完全保留原始curl请求的所有头和参数
支持异步抓取和分页处理
"""

import asyncio
import functools
import json
import logging
import os
import random
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Set

import aiohttp

logger = logging.getLogger(__name__)


def async_retry(max_retries: int = 3, delay: float = 1.0, exceptions=(Exception,)):
    """
    异步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要捕获的异常类型
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} 第{attempt + 1}次尝试失败: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))  # 递增延迟
            logger.error(f"{func.__name__} 在{max_retries}次尝试后仍然失败")
            raise last_exception

        return wrapper

    return decorator


class StockDataFetcher:
    """股票数据抓取器"""

    # 基础请求头（所有接口通用）
    BASE_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    # Cookie配置：不要在代码里写入真实Cookie，运行时从环境变量或参数传入。
    COOKIES = {}

    # 东方财富独立请求头（完全保留curl参数）
    EASTMONEY_HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "https://quote.eastmoney.com/ztb/detail",
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    # 东方财富接口一般可匿名访问；如后续确需Cookie，也应从配置注入。
    EASTMONEY_COOKIES = {}

    def __init__(
        self,
        cookie: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        source_delay_range: Optional[tuple[float, float]] = None,
        page_delay_range: Optional[tuple[float, float]] = None,
    ):
        """
        初始化抓取器

        Args:
            cookie: 可选的自定义cookie字符串，用于覆盖默认cookie
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            source_delay_range: 数据源之间的随机延迟范围（秒）
            page_delay_range: 分页请求之间的随机延迟范围（秒）
        """
        cookie = cookie or os.getenv("STOCK_COOKIE")
        self.cookies = self._parse_cookie(cookie, default_name="v")
        self.timeout = timeout or int(os.getenv("STOCK_FETCH_TIMEOUT", "30"))
        self.max_retries = max_retries or int(os.getenv("STOCK_FETCH_MAX_RETRIES", "3"))
        self.retry_delay = retry_delay or float(
            os.getenv("STOCK_FETCH_RETRY_DELAY", "1.0")
        )
        self.source_delay_range = source_delay_range or self._read_delay_range(
            "STOCK_FETCH_SOURCE_DELAY_MIN",
            "STOCK_FETCH_SOURCE_DELAY_MAX",
            3.0,
            8.0,
        )
        self.page_delay_range = page_delay_range or self._read_delay_range(
            "STOCK_FETCH_PAGE_DELAY_MIN",
            "STOCK_FETCH_PAGE_DELAY_MAX",
            0.8,
            2.0,
        )
        self.session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def _read_delay_range(
        min_key: str,
        max_key: str,
        default_min: float,
        default_max: float,
    ) -> tuple[float, float]:
        delay_min = float(os.getenv(min_key, str(default_min)))
        delay_max = float(os.getenv(max_key, str(default_max)))
        if delay_min < 0 or delay_max < 0:
            raise ValueError(f"{min_key}/{max_key} 不能为负数")
        if delay_min > delay_max:
            raise ValueError(f"{min_key} 不能大于 {max_key}")
        return delay_min, delay_max

    async def _sleep_random_delay(
        self,
        delay_range: tuple[float, float],
        reason: str,
    ) -> None:
        delay_min, delay_max = delay_range
        if delay_max <= 0:
            return
        delay = random.uniform(delay_min, delay_max)
        if delay <= 0:
            return
        logger.debug("%s，随机等待 %.2f 秒", reason, delay)
        await asyncio.sleep(delay)

    @staticmethod
    def _parse_cookie(cookie: Optional[str], default_name: str) -> Dict[str, str]:
        """解析完整 Cookie 头或单个 cookie 值。"""
        if not cookie:
            return {}

        cookie = cookie.strip()
        if not cookie:
            return {}

        if "=" not in cookie:
            return {default_name: cookie}

        cookies: Dict[str, str] = {}
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name and value:
                cookies[name] = value
        return cookies

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers=self.BASE_HEADERS,
            cookies=self.cookies,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    def _get_headers_with_referer(self, referer: str) -> Dict[str, str]:
        """
        获取带Referer的请求头

        Args:
            referer: Referer URL

        Returns:
            完整的请求头字典
        """
        headers = self.BASE_HEADERS.copy()
        headers["Referer"] = referer
        return headers

    async def _request_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        jsonp: bool = False,
    ) -> Any:
        """发送GET请求并解析JSON/JSONP响应。"""
        if not self.session:
            raise RuntimeError(
                "StockDataFetcher must be used as an async context manager"
            )

        retrying = async_retry(
            max_retries=self.max_retries,
            delay=self.retry_delay,
            exceptions=(aiohttp.ClientError, asyncio.TimeoutError, ValueError),
        )(self._request_json_once)

        return await retrying(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            jsonp=jsonp,
        )

    async def _request_json_once(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        jsonp: bool = False,
    ) -> Any:
        session = self.session
        if not session:
            raise RuntimeError(
                "StockDataFetcher must be used as an async context manager"
            )

        async with session.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
        ) as response:
            if response.status != 200:
                logger.error(f"请求失败: url={url}, status={response.status}")
                response.raise_for_status()

            if jsonp:
                return self._parse_jsonp(await response.text())
            return await response.json()

    def _extract_api_records(
        self, payload: Any, data_type: str
    ) -> List[Dict[str, Any]]:
        """兼容同花顺接口返回 dict 或直接返回 list 的情况。"""
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
            return (
                self._flatten_continuous_groups(records)
                if data_type == "continuous_limit_up"
                else records
            )

        if not isinstance(payload, dict):
            raise ValueError(f"{data_type} 返回格式异常: {type(payload).__name__}")

        status_code = payload.get("status_code")
        if status_code not in (None, 0):
            error_msg = payload.get("message", "未知错误")
            logger.error(f"❌ API返回错误: {error_msg}")
            raise Exception(f"API错误: {error_msg}")

        data = payload.get("data", [])
        if isinstance(data, dict):
            data = data.get("data", data.get("list", data.get("items", [])))

        if isinstance(data, list):
            records = [item for item in data if isinstance(item, dict)]
            return (
                self._flatten_continuous_groups(records)
                if data_type == "continuous_limit_up"
                else records
            )

        raise ValueError(f"{data_type} data字段格式异常: {type(data).__name__}")

    def _flatten_continuous_groups(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """展开连板天梯按高度分组的响应。"""
        flattened: List[Dict[str, Any]] = []

        for group in records:
            code_list = group.get("code_list")
            if not isinstance(code_list, list):
                flattened.append(group)
                continue

            height = group.get("height")
            for stock in code_list:
                if not isinstance(stock, dict):
                    continue

                item = stock.copy()
                item.setdefault("continuous_days", stock.get("continue_num", height))
                item.setdefault("height", height)
                flattened.append(item)

        return flattened

    def _extract_limit_up_pool_page(
        self,
        payload: Any,
        page: int,
        limit: int,
    ) -> Dict[str, Any]:
        """解析涨停强度分页响应，兼容 data/info/list 等字段名。"""
        if not isinstance(payload, dict):
            raise ValueError(f"limit_up_pool 返回格式异常: {type(payload).__name__}")

        status_code = payload.get("status_code")
        if status_code not in (None, 0):
            error_msg = payload.get("message", "未知错误")
            logger.error(f"❌ API返回错误: {error_msg}")
            raise Exception(f"API错误: {error_msg}")

        data = payload.get("data", {})
        if isinstance(data, list):
            records = [item for item in data if isinstance(item, dict)]
            return {"data": records, "has_more": len(records) >= limit}

        if not isinstance(data, dict):
            raise ValueError(f"limit_up_pool data字段格式异常: {type(data).__name__}")

        records = []
        for key in ("data", "info", "list", "items"):
            value = data.get(key)
            if isinstance(value, list):
                records = [item for item in value if isinstance(item, dict)]
                break

        has_more = data.get("has_more")
        if has_more is None:
            page_info = data.get("page") if isinstance(data.get("page"), dict) else {}
            total = self._safe_positive_int(
                data.get("total")
                or data.get("count")
                or data.get("total_count")
                or page_info.get("total")
                or page_info.get("count")
            )
            current_page = (
                self._safe_positive_int(
                    data.get("page")
                    if not isinstance(data.get("page"), dict)
                    else page_info.get("page")
                )
                or page
            )
            page_size = (
                self._safe_positive_int(data.get("limit") or page_info.get("limit"))
                or limit
            )
            has_more = (
                (current_page * page_size < total) if total else len(records) >= limit
            )

        return {"data": records, "has_more": bool(has_more)}

    @staticmethod
    def _safe_positive_int(value: Any) -> int:
        try:
            number = int(value)
            return number if number > 0 else 0
        except (TypeError, ValueError):
            return 0

    async def fetch_continuous_limit_up(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
    ) -> List[Dict[str, Any]]:
        """
        获取连板天梯数据

        对应curl:
        https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天
            filter_params: 过滤参数，默认"HS,GEM2STAR,ST,NEW"

        Returns:
            连板天梯数据列表
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        url = "https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up"
        params = {"filter": filter_params, "date": target_date}

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.info(f"📊 获取连板天梯数据: date={target_date}")

        data = await self._request_json(url, params=params, headers=headers)
        result = self._extract_api_records(data, "continuous_limit_up")
        logger.info(f"✅ 获取连板天梯数据成功: {len(result)}条记录")
        return result

    async def fetch_block_top(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
    ) -> List[Dict[str, Any]]:
        """
        获取最强风口数据

        对应curl:
        https://data.10jqka.com.cn/dataapi/limit_up/block_top

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天
            filter_params: 过滤参数，默认"HS,GEM2STAR,ST,NEW"

        Returns:
            最强风口数据列表
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        url = "https://data.10jqka.com.cn/dataapi/limit_up/block_top"
        params = {"filter": filter_params, "date": target_date}

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.info(f"📊 获取最强风口数据: date={target_date}")

        data = await self._request_json(url, params=params, headers=headers)
        result = self._extract_api_records(data, "block_top")
        logger.info(f"✅ 获取最强风口数据成功: {len(result)}条记录")
        return result

    async def fetch_limit_up_pool_page(
        self,
        page: int = 1,
        limit: int = 15,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
        order_field: str = "330324",
        order_type: int = 0,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取涨停强度数据（单页）

        对应curl:
        https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool

        Args:
            page: 页码，从1开始
            limit: 每页条数，默认15
            target_date: 数据日期，格式YYYYMMDD，默认今天
            filter_params: 过滤参数
            order_field: 排序字段，默认330324（涨停时间）
            order_type: 排序类型，0=降序，1=升序
            timestamp: 时间戳，可选

        Returns:
            API返回的原始数据，包含data和has_more字段
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"

        # 必需字段列表（与curl中的field参数一致）
        fields = (
            "199112,10,9001,330323,330324,9002,330329,133971,133970,"
            "1968584,3475914,9003,9004,currency_value,open_num,first_limit_up_time,last_limit_up_time,"
            "reason_type,reason_info"
        )

        params = {
            "page": page,
            "limit": limit,
            "field": fields,
            "filter": filter_params,
            "date": target_date,
            "order_field": order_field,
            "order_type": order_type,
        }

        if timestamp:
            params["_"] = timestamp

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.debug(
            f"获取涨停强度数据: page={page}, limit={limit}, date={target_date}"
        )

        data = await self._request_json(url, params=params, headers=headers)
        return self._extract_limit_up_pool_page(data, page, limit)

    async def fetch_limit_up_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
        batch_size: int = 15,
        max_pages: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取所有涨停强度数据（自动分页）

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天
            filter_params: 过滤参数
            batch_size: 每页条数
            max_pages: 最大抓取页数，防止无限循环
            progress_callback: 进度回调函数，参数(当前页, 总页数)

        Returns:
            所有涨停强度数据列表
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        all_data = []
        page = 1
        has_more = True

        logger.info(f"开始获取涨停强度数据（分页）: date={target_date}")

        while has_more and page <= max_pages:
            result = await self.fetch_limit_up_pool_page(
                page=page,
                limit=batch_size,
                target_date=target_date,
                filter_params=filter_params,
            )

            page_data = result.get("data", [])
            all_data.extend(page_data)

            # 判断是否还有下一页
            has_more = result.get("has_more", False)

            if progress_callback:
                progress_callback(page, page)

            logger.debug(f"获取第{page}页，{len(page_data)}条记录，has_more={has_more}")

            if has_more:
                page += 1
                await self._sleep_random_delay(
                    self.page_delay_range,
                    "涨停强度分页继续抓取前",
                )

        logger.info(f"涨停强度数据获取完成: 共{page}页，{len(all_data)}条记录")
        return all_data

    async def fetch_lower_limit_pool_page(
        self,
        page: int = 1,
        limit: int = 15,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR",
        order_field: str = "330334",
        order_type: int = 0,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取同花顺跌停池单页数据。"""
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        params = {
            "page": page,
            "limit": limit,
            "field": "199112,10,330333,330334,1968584,3475914,9004",
            "filter": filter_params,
            "date": target_date,
            "order_field": order_field,
            "order_type": order_type,
        }
        if timestamp:
            params["_"] = timestamp

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )
        logger.debug("获取同花顺跌停池: page=%s, limit=%s, date=%s", page, limit, target_date)
        data = await self._request_json(
            "https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool",
            params=params,
            headers=headers,
        )
        return self._extract_limit_up_pool_page(data, page, limit)

    async def fetch_lower_limit_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR",
        batch_size: int = 15,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取同花顺全部跌停池数据。"""
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        all_data: List[Dict[str, Any]] = []
        page = 1
        has_more = True
        logger.info("开始获取同花顺跌停池（分页）: date=%s", target_date)
        while has_more and page <= max_pages:
            result = await self.fetch_lower_limit_pool_page(
                page=page,
                limit=batch_size,
                target_date=target_date,
                filter_params=filter_params,
            )
            all_data.extend(result.get("data", []))
            has_more = result.get("has_more", False)
            logger.debug("跌停池第%s页，%s条记录，has_more=%s", page, len(result.get("data", [])), has_more)
            if has_more:
                page += 1
                await self._sleep_random_delay(
                    self.page_delay_range,
                    "跌停池分页继续抓取前",
                )

        logger.info("同花顺跌停池获取完成: 共%s页，%s条记录", page, len(all_data))
        return all_data

    def _parse_jsonp(self, jsonp_str: str) -> Dict[str, Any]:
        """
        解析JSONP格式数据

        Args:
            jsonp_str: JSONP字符串，如 callbackdata123({"data": [...]})

        Returns:
            解析后的JSON字典
        """
        try:
            # 找到第一个(和最后一个)的位置
            start_idx = jsonp_str.find("(")
            end_idx = jsonp_str.rfind(")")

            if start_idx == -1 or end_idx == -1:
                raise ValueError(f"无效的JSONP格式: {jsonp_str[:100]}")

            # 提取JSON部分
            json_str = jsonp_str[start_idx + 1 : end_idx]
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"解析JSONP失败: {e}, 原始数据: {jsonp_str[:200]}")
            raise

    async def fetch_eastmoney_zt_pool_page(
        self,
        page_index: int = 0,
        page_size: int = 20,
        target_date: Optional[str] = None,
        sort: str = "fbt:asc",
    ) -> Dict[str, Any]:
        """
        获取东方财富涨停池数据（单页）

        对应curl:
        https://push2ex.eastmoney.com/getTopicZTPool

        Args:
            page_index: 页码，从0开始
            page_size: 每页条数
            target_date: 数据日期，格式YYYYMMDD，默认今天
            sort: 排序方式，默认fbt:asc（首次涨停时间升序）

        Returns:
            API返回的原始数据字典，包含data和tc字段
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        url = "https://push2ex.eastmoney.com/getTopicZTPool"

        # 生成时间戳
        timestamp = int(datetime.now().timestamp() * 1000)

        # 生成callback名称（随机数字）
        callback_name = f"callbackdata{timestamp % 10000000}"

        params = {
            "cb": callback_name,
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": page_index,
            "pagesize": page_size,
            "sort": sort,
            "date": target_date,
            "_": timestamp,
        }

        # 使用东方财富专用请求头（完全保留curl参数）
        headers = self.EASTMONEY_HEADERS.copy()

        logger.debug(
            f"获取东方财富涨停池: date={target_date}, page={page_index}, size={page_size}"
        )

        data = await self._request_json(
            url,
            params=params,
            headers=headers,
            cookies=self.EASTMONEY_COOKIES,
            jsonp=True,
        )
        return data

    async def fetch_eastmoney_zt_pool(
        self, target_date: Optional[str] = None, sort: str = "fbt:asc"
    ) -> List[Dict[str, Any]]:
        """
        获取东方财富涨停池全部数据（两步调用）

        流程：
        1. 先调用一次，获取tc（总条数）
        2. 根据tc重新调用，获取全部数据

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天
            sort: 排序方式，默认fbt:asc（首次涨停时间升序）

        Returns:
            所有涨停池数据列表
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        logger.info(f"开始获取东方财富涨停池数据: date={target_date}")

        # 第一步：获取总条数（tc）
        logger.info("第一步：获取总条数（tc）")
        first_page = await self.fetch_eastmoney_zt_pool_page(
            page_index=0, page_size=20, target_date=target_date, sort=sort
        )

        # 提取tc参数（总条数）
        tc = first_page.get("tc", 0)
        if not tc:
            tc = first_page.get("data", {}).get("tc", 0)

        if not tc:
            logger.warning("无法获取tc参数，使用第一页数据")
            return first_page.get("data", {}).get("pool", [])

        logger.info(f"获取到总条数 tc={tc}")

        # 第二步：根据tc拉取全部数据
        logger.info(f"第二步：拉取全部{tc}条数据")
        full_data = await self.fetch_eastmoney_zt_pool_page(
            page_index=0,
            page_size=tc,  # 使用tc作为pagesize，一次性拉取全部
            target_date=target_date,
            sort=sort,
        )

        # 提取数据
        pool_data = full_data.get("data", {}).get("pool", [])

        logger.info(f"东方财富涨停池数据获取完成: 共{len(pool_data)}条记录")
        return pool_data

    async def fetch_all_data(
        self, target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取所有股票数据

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天

        Returns:
            包含各类数据的字典
            {
                'continuous_limit_up': [...],
                'block_top': [...],
                'limit_up_pool': [...],
                'lower_limit_pool': [...],
                'eastmoney_zt_pool': [...]
            }
        """
        if not target_date:
            target_date = date.today().strftime("%Y%m%d")

        logger.info(f"🚀 开始获取所有股票数据: date={target_date}")
        target_date_obj = datetime.strptime(target_date, "%Y%m%d").date()
        if target_date_obj.weekday() >= 5:
            reason = f"{target_date} 为周末，跳过抓取与后续流程"
            logger.info(reason)
            return self._skipped_fetch_result(target_date, reason)

        result: Dict[str, List[Dict[str, Any]]] = {
            "continuous_limit_up": [],
            "block_top": [],
            "limit_up_pool": [],
            "lower_limit_pool": [],
            "eastmoney_zt_pool": [],
            "errors": [],
        }

        fetch_steps = [
            ("continuous_limit_up", "连板天梯", self.fetch_continuous_limit_up),
            ("block_top", "最强风口", self.fetch_block_top),
            ("limit_up_pool", "涨停强度", self.fetch_limit_up_pool),
            ("lower_limit_pool", "同花顺跌停池", self.fetch_lower_limit_pool),
            ("eastmoney_zt_pool", "东方财富涨停池", self.fetch_eastmoney_zt_pool),
        ]
        for index, (data_type, label, fetch_func) in enumerate(fetch_steps):
            if index > 0:
                await self._sleep_random_delay(
                    self.source_delay_range,
                    f"{label}数据获取前",
                )

            try:
                result[data_type] = await fetch_func(target_date)
            except Exception as exc:
                logger.error("%s数据获取失败: %s", label, exc)
                result["errors"].append({"type": data_type, "error": str(exc)})

        logger.info(
            f"✅ 所有数据获取完成: "
            f"连板天梯{len(result['continuous_limit_up'])}条, "
            f"最强风口{len(result['block_top'])}条, "
            f"涨停强度{len(result['limit_up_pool'])}条, "
            f"同花顺跌停池{len(result['lower_limit_pool'])}条, "
            f"东财涨停池{len(result['eastmoney_zt_pool'])}条"
        )

        skip_reason = self._stale_fetch_reason(result, target_date_obj)
        if skip_reason:
            logger.warning(skip_reason)
            return self._skipped_fetch_result(target_date, skip_reason)

        self._warn_if_cookie_expired(result)

        return result

    @staticmethod
    def _skipped_fetch_result(target_date: str, reason: str) -> Dict[str, Any]:
        return {
            "continuous_limit_up": [],
            "block_top": [],
            "limit_up_pool": [],
            "lower_limit_pool": [],
            "eastmoney_zt_pool": [],
            "errors": [],
            "skipped": True,
            "skip_reason": reason,
            "requested_date": target_date,
        }

    def _stale_fetch_reason(
        self, result: Dict[str, Any], target_date: date
    ) -> Optional[str]:
        actual_dates = self._infer_actual_trade_dates(result)
        if actual_dates and target_date not in actual_dates:
            actual_text = ", ".join(
                sorted(item.strftime("%Y%m%d") for item in actual_dates)
            )
            return (
                f"请求日期 {target_date:%Y%m%d} 与上游返回交易日期 {actual_text} 不一致，"
                "可能为节假日或源站回退到上一交易日，跳过保存与后续流程"
            )

        ths_total = (
            len(result["continuous_limit_up"])
            + len(result["block_top"])
            + len(result["limit_up_pool"])
            + len(result.get("lower_limit_pool", []))
        )
        em_total = len(result["eastmoney_zt_pool"])
        if not actual_dates and ths_total == 0 and em_total > 0:
            return (
                f"请求日期 {target_date:%Y%m%d} 无法从上游返回中确认交易日期，"
                "且同花顺为空但东财有数据，可能为节假日旧数据或同花顺 Cookie 失效，"
                "跳过保存与后续流程"
            )
        return None

    def _infer_actual_trade_dates(self, result: Dict[str, Any]) -> Set[date]:
        dates: Set[date] = set()
        for key in (
            "continuous_limit_up",
            "block_top",
            "limit_up_pool",
            "lower_limit_pool",
        ):
            for item in result.get(key, []):
                dates.update(self._extract_dates_from_payload(item))
        return dates

    def _extract_dates_from_payload(self, value: Any) -> Set[date]:
        dates: Set[date] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if self._looks_like_unix_time_key(key):
                    parsed = self._date_from_unix_seconds(child)
                    if parsed:
                        dates.add(parsed)
                dates.update(self._extract_dates_from_payload(child))
        elif isinstance(value, list):
            for child in value:
                dates.update(self._extract_dates_from_payload(child))
        return dates

    @staticmethod
    def _looks_like_unix_time_key(key: str) -> bool:
        normalized = key.lower()
        return "limit_up_time" in normalized or normalized.endswith("_time")

    @staticmethod
    def _date_from_unix_seconds(value: Any) -> Optional[date]:
        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return None
        if timestamp < 1_000_000_000:
            return None
        return datetime.fromtimestamp(timestamp).date()

    def _warn_if_cookie_expired(
        self, result: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Emit a loud warning when THS endpoints look like they lost auth.

        THS (`continuous_limit_up`, `block_top`, `limit_up_pool`,
        `lower_limit_pool`) depend on
        STOCK_COOKIE; EastMoney does not. If THS comes back fully empty while
        EastMoney has data, the cookie has almost certainly expired.
        """
        if not self.cookies:
            logger.warning(
                "⚠️ STOCK_COOKIE 未配置，同花顺接口数据将全部为空。"
                "请在 .env 中设置 STOCK_COOKIE（从浏览器 data.10jqka.com.cn 复制 v=... 值）"
            )
            return

        ths_total = (
            len(result["continuous_limit_up"])
            + len(result["block_top"])
            + len(result["limit_up_pool"])
            + len(result.get("lower_limit_pool", []))
        )
        em_total = len(result["eastmoney_zt_pool"])
        if ths_total == 0 and em_total > 0:
            logger.warning(
                "⚠️ 同花顺四个接口均返回 0 条但东方财富有数据 — "
                "STOCK_COOKIE 大概率已过期。请到浏览器 DevTools 重新复制 "
                "data.10jqka.com.cn 的 v=... cookie 写入 .env 并重启服务。"
            )


class StockDataFetcherSync:
    """同步版本的股票数据抓取器（用于非异步环境）"""

    def __init__(
        self,
        cookie: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        source_delay_range: Optional[tuple[float, float]] = None,
        page_delay_range: Optional[tuple[float, float]] = None,
    ):
        self.fetcher = StockDataFetcher(
            cookie=cookie,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            source_delay_range=source_delay_range,
            page_delay_range=page_delay_range,
        )

    def fetch_continuous_limit_up(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
    ) -> List[Dict[str, Any]]:
        """同步获取连板天梯数据"""
        return asyncio.run(
            self._async_fetch(
                self.fetcher.fetch_continuous_limit_up(target_date, filter_params)
            )
        )

    def fetch_block_top(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
    ) -> List[Dict[str, Any]]:
        """同步获取最强风口数据"""
        return asyncio.run(
            self._async_fetch(self.fetcher.fetch_block_top(target_date, filter_params))
        )

    def fetch_limit_up_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
        batch_size: int = 15,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """同步获取涨停强度数据"""
        return asyncio.run(
            self._async_fetch(
                self.fetcher.fetch_limit_up_pool(
                    target_date, filter_params, batch_size, max_pages
                )
            )
        )

    def fetch_lower_limit_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR",
        batch_size: int = 15,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """同步获取同花顺跌停池数据。"""
        return asyncio.run(
            self._async_fetch(
                self.fetcher.fetch_lower_limit_pool(
                    target_date, filter_params, batch_size, max_pages
                )
            )
        )

    def fetch_eastmoney_zt_pool(
        self, target_date: Optional[str] = None, sort: str = "fbt:asc"
    ) -> List[Dict[str, Any]]:
        """同步获取东方财富涨停池数据（两步调用）"""
        return asyncio.run(
            self._async_fetch(self.fetcher.fetch_eastmoney_zt_pool(target_date, sort))
        )

    def fetch_all_data(
        self, target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步获取所有数据"""
        return asyncio.run(self._async_fetch(self.fetcher.fetch_all_data(target_date)))

    async def _async_fetch(self, coro):
        """辅助方法：执行异步协程"""
        async with self.fetcher:
            return await coro


def create_fetcher(
    cookie: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    source_delay_range: Optional[tuple[float, float]] = None,
    page_delay_range: Optional[tuple[float, float]] = None,
) -> StockDataFetcherSync:
    """
    工厂函数：创建同步数据抓取器

    Args:
        cookie: 可选的cookie字符串
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        source_delay_range: 数据源之间的随机延迟范围（秒）
        page_delay_range: 分页请求之间的随机延迟范围（秒）

    Returns:
        StockDataFetcherSync实例
    """
    return StockDataFetcherSync(
        cookie,
        timeout,
        max_retries,
        retry_delay,
        source_delay_range,
        page_delay_range,
    )
