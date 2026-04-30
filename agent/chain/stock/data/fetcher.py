"""
股票数据抓取模块
完全保留原始curl请求的所有头和参数
支持异步抓取和分页处理
"""

import asyncio
import functools
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Callable, Union
from urllib.parse import urlencode

import aiohttp
import requests

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
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

    # Cookie配置（可从环境变量或配置文件中读取）
    COOKIES = {
        'v': 'A8O1oOLurvG9TWKFqQX3KmkiVIxoOF7rkdeT3vWhHACZc-3yfQjnyqGcK9UG'
    }

    # 东方财富独立请求头（完全保留curl参数）
    EASTMONEY_HEADERS = {
        'Accept': '*/*',
        'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'https://quote.eastmoney.com/ztb/detail',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }

    # 东方财富Cookie（从curl完整复制）
    EASTMONEY_COOKIES = {
        'qgqp_b_id': 'f2bac33486bfbed93b611fa17371f876',
        'st_si': '63471290576605',
        'st_asi': 'delete',
        'st_nvi': '7EWAvd_TmjIfshYmh-zUO0566',
        'nid18': '00f4c85ed43452ac9ace58d543e696c4',
        'nid18_create_time': '1775986220300',
        'gviem': 'Ro2sFUUxjTxdwiDNGWLHs7462',
        'gviem_create_time': '1775986220300',
        'st_pvi': '71061582355408',
        'st_sp': '2026-04-12 17:30:19',
        'st_inirUrl': '',
        'st_sn': '4',
        'st_psi': '20260412173108372-113200304537-3616223390',
    }

    def __init__(self, cookie: Optional[str] = None):
        """
        初始化抓取器

        Args:
            cookie: 可选的自定义cookie字符串，用于覆盖默认cookie
        """
        if cookie:
            self.COOKIES = {'v': cookie}
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers=self.BASE_HEADERS,
            cookies=self.COOKIES
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
        headers['Referer'] = referer
        return headers

    async def fetch_continuous_limit_up(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW"
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
            target_date = date.today().strftime('%Y%m%d')

        url = "https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up"
        params = {
            'filter': filter_params,
            'date': target_date
        }

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.info(f"📊 获取连板天梯数据: date={target_date}")

        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                logger.error(f"❌ 获取连板天梯数据失败: status={response.status}")
                response.raise_for_status()

            data = await response.json()

            if data.get('status_code') != 0:
                error_msg = data.get('message', '未知错误')
                logger.error(f"❌ API返回错误: {error_msg}")
                raise Exception(f"API错误: {error_msg}")

            result = data.get('data', {}).get('data', [])
            logger.info(f"✅ 获取连板天梯数据成功: {len(result)}条记录")
            return result

    async def fetch_block_top(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW"
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
            target_date = date.today().strftime('%Y%m%d')

        url = "https://data.10jqka.com.cn/dataapi/limit_up/block_top"
        params = {
            'filter': filter_params,
            'date': target_date
        }

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.info(f"📊 获取最强风口数据: date={target_date}")

        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                logger.error(f"❌ 获取最强风口数据失败: status={response.status}")
                response.raise_for_status()

            data = await response.json()

            if data.get('status_code') != 0:
                error_msg = data.get('message', '未知错误')
                logger.error(f"❌ API返回错误: {error_msg}")
                raise Exception(f"API错误: {error_msg}")

            result = data.get('data', [])
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
        timestamp: Optional[int] = None
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
            target_date = date.today().strftime('%Y%m%d')

        url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"

        # 必需字段列表（与curl中的field参数一致）
        fields = "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004"

        params = {
            'page': page,
            'limit': limit,
            'field': fields,
            'filter': filter_params,
            'date': target_date,
            'order_field': order_field,
            'order_type': order_type,
        }

        if timestamp:
            params['_'] = timestamp

        headers = self._get_headers_with_referer(
            "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"
        )

        logger.debug(f"获取涨停强度数据: page={page}, limit={limit}, date={target_date}")

        async with self.session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                logger.error(f"获取涨停强度数据失败: status={response.status}")
                response.raise_for_status()

            data = await response.json()

            if data.get('status_code') != 0:
                error_msg = data.get('message', '未知错误')
                logger.error(f"❌ API返回错误: {error_msg}")
                raise Exception(f"API错误: {error_msg}")

            return data.get('data', {})

    async def fetch_limit_up_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
        batch_size: int = 15,
        max_pages: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
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
            target_date = date.today().strftime('%Y%m%d')

        all_data = []
        page = 1
        has_more = True

        logger.info(f"开始获取涨停强度数据（分页）: date={target_date}")

        while has_more and page <= max_pages:
            result = await self.fetch_limit_up_pool_page(
                page=page,
                limit=batch_size,
                target_date=target_date,
                filter_params=filter_params
            )

            page_data = result.get('data', [])
            all_data.extend(page_data)

            # 判断是否还有下一页
            has_more = result.get('has_more', False)

            if progress_callback:
                progress_callback(page, page)

            logger.debug(f"获取第{page}页，{len(page_data)}条记录，has_more={has_more}")

            if has_more:
                page += 1
                # 添加短暂延迟，避免请求过快
                await asyncio.sleep(0.5)

        logger.info(f"涨停强度数据获取完成: 共{page}页，{len(all_data)}条记录")
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
            start_idx = jsonp_str.find('(')
            end_idx = jsonp_str.rfind(')')

            if start_idx == -1 or end_idx == -1:
                raise ValueError(f"无效的JSONP格式: {jsonp_str[:100]}")

            # 提取JSON部分
            json_str = jsonp_str[start_idx + 1:end_idx]
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"解析JSONP失败: {e}, 原始数据: {jsonp_str[:200]}")
            raise

    async def fetch_eastmoney_zt_pool_page(
        self,
        page_index: int = 0,
        page_size: int = 20,
        target_date: Optional[str] = None,
        sort: str = "fbt:asc"
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
            target_date = date.today().strftime('%Y%m%d')

        url = "https://push2ex.eastmoney.com/getTopicZTPool"

        # 生成时间戳
        timestamp = int(datetime.now().timestamp() * 1000)

        # 生成callback名称（随机数字）
        callback_name = f"callbackdata{timestamp % 10000000}"

        params = {
            'cb': callback_name,
            'ut': '7eea3edcaed734bea9cbfc24409ed989',
            'dpt': 'wz.ztzt',
            'Pageindex': page_index,
            'pagesize': page_size,
            'sort': sort,
            'date': target_date,
            '_': timestamp,
        }

        # 使用东方财富专用请求头（完全保留curl参数）
        headers = self.EASTMONEY_HEADERS.copy()

        logger.debug(f"获取东方财富涨停池: date={target_date}, page={page_index}, size={page_size}")

        # 使用东方财富专用Cookie
        async with self.session.get(
            url,
            params=params,
            headers=headers,
            cookies=self.EASTMONEY_COOKIES
        ) as response:
            if response.status != 200:
                logger.error(f"获取东方财富涨停池失败: status={response.status}")
                response.raise_for_status()

            # 获取文本响应（JSONP格式）
            text = await response.text()

            # 解析JSONP
            data = self._parse_jsonp(text)

            return data

    async def fetch_eastmoney_zt_pool(
        self,
        target_date: Optional[str] = None,
        sort: str = "fbt:asc"
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
            target_date = date.today().strftime('%Y%m%d')

        logger.info(f"开始获取东方财富涨停池数据: date={target_date}")

        # 第一步：获取总条数（tc）
        logger.info("第一步：获取总条数（tc）")
        first_page = await self.fetch_eastmoney_zt_pool_page(
            page_index=0,
            page_size=20,
            target_date=target_date,
            sort=sort
        )

        # 提取tc参数（总条数）
        tc = first_page.get('tc', 0)
        if not tc:
            tc = first_page.get('data', {}).get('tc', 0)

        if not tc:
            logger.warning("无法获取tc参数，使用第一页数据")
            return first_page.get('data', {}).get('pool', [])

        logger.info(f"获取到总条数 tc={tc}")

        # 第二步：根据tc拉取全部数据
        logger.info(f"第二步：拉取全部{tc}条数据")
        full_data = await self.fetch_eastmoney_zt_pool_page(
            page_index=0,
            page_size=tc,  # 使用tc作为pagesize，一次性拉取全部
            target_date=target_date,
            sort=sort
        )

        # 提取数据
        pool_data = full_data.get('data', {}).get('pool', [])

        logger.info(f"东方财富涨停池数据获取完成: 共{len(pool_data)}条记录")
        return pool_data

    async def fetch_all_data(
        self,
        target_date: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有三类数据

        Args:
            target_date: 数据日期，格式YYYYMMDD，默认今天

        Returns:
            包含三类数据的字典
            {
                'continuous_limit_up': [...],
                'block_top': [...],
                'limit_up_pool': [...]
            }
        """
        if not target_date:
            target_date = date.today().strftime('%Y%m%d')

        logger.info(f"🚀 开始获取所有股票数据: date={target_date}")

        # 并发获取三类数据
        continuous_task = self.fetch_continuous_limit_up(target_date)
        block_task = self.fetch_block_top(target_date)
        pool_task = self.fetch_limit_up_pool(target_date)

        continuous_data, block_data, pool_data = await asyncio.gather(
            continuous_task,
            block_task,
            pool_task,
            return_exceptions=True
        )

        result = {
            'continuous_limit_up': [],
            'block_top': [],
            'limit_up_pool': [],
            'errors': []
        }

        # 处理结果，记录异常
        if isinstance(continuous_data, Exception):
            logger.error(f"连板天梯数据获取失败: {continuous_data}")
            result['errors'].append({'type': 'continuous_limit_up', 'error': str(continuous_data)})
        else:
            result['continuous_limit_up'] = continuous_data

        if isinstance(block_data, Exception):
            logger.error(f"最强风口数据获取失败: {block_data}")
            result['errors'].append({'type': 'block_top', 'error': str(block_data)})
        else:
            result['block_top'] = block_data

        if isinstance(pool_data, Exception):
            logger.error(f"涨停强度数据获取失败: {pool_data}")
            result['errors'].append({'type': 'limit_up_pool', 'error': str(pool_data)})
        else:
            result['limit_up_pool'] = pool_data

        logger.info(f"✅ 所有数据获取完成: "
                   f"连板天梯{len(result['continuous_limit_up'])}条, "
                   f"最强风口{len(result['block_top'])}条, "
                   f"涨停强度{len(result['limit_up_pool'])}条")

        return result


class StockDataFetcherSync:
    """同步版本的股票数据抓取器（用于非异步环境）"""

    def __init__(self, cookie: Optional[str] = None):
        self.fetcher = StockDataFetcher(cookie)

    def fetch_continuous_limit_up(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW"
    ) -> List[Dict[str, Any]]:
        """同步获取连板天梯数据"""
        return asyncio.run(self._async_fetch(
            self.fetcher.fetch_continuous_limit_up(target_date, filter_params)
        ))

    def fetch_block_top(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW"
    ) -> List[Dict[str, Any]]:
        """同步获取最强风口数据"""
        return asyncio.run(self._async_fetch(
            self.fetcher.fetch_block_top(target_date, filter_params)
        ))

    def fetch_limit_up_pool(
        self,
        target_date: Optional[str] = None,
        filter_params: str = "HS,GEM2STAR,ST,NEW",
        batch_size: int = 15,
        max_pages: int = 100
    ) -> List[Dict[str, Any]]:
        """同步获取涨停强度数据"""
        return asyncio.run(self._async_fetch(
            self.fetcher.fetch_limit_up_pool(target_date, filter_params, batch_size, max_pages)
        ))

    def fetch_eastmoney_zt_pool(
        self,
        target_date: Optional[str] = None,
        sort: str = "fbt:asc"
    ) -> List[Dict[str, Any]]:
        """同步获取东方财富涨停池数据（两步调用）"""
        return asyncio.run(self._async_fetch(
            self.fetcher.fetch_eastmoney_zt_pool(target_date, sort)
        ))

    def fetch_all_data(
        self,
        target_date: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """同步获取所有数据"""
        return asyncio.run(self._async_fetch(
            self.fetcher.fetch_all_data(target_date)
        ))

    async def _async_fetch(self, coro):
        """辅助方法：执行异步协程"""
        async with self.fetcher:
            return await coro


def create_fetcher(cookie: Optional[str] = None) -> StockDataFetcherSync:
    """
    工厂函数：创建同步数据抓取器

    Args:
        cookie: 可选的cookie字符串

    Returns:
        StockDataFetcherSync实例
    """
    return StockDataFetcherSync(cookie)
