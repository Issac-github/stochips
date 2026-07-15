import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.data.fetcher import StockDataFetcher
from chain.stock.data.storage import StockDataStorage


def test_fetch_all_data_skips_weekend_before_network_requests():
    fetcher = StockDataFetcher()

    result = asyncio.run(fetcher.fetch_all_data("20260704"))

    assert result["skipped"] is True
    assert "周末" in result["skip_reason"]
    assert result["continuous_limit_up"] == []
    assert result["eastmoney_zt_pool"] == []


def test_fetch_all_data_runs_sources_sequentially_with_delays():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    fetcher.source_delay_range = (3.0, 8.0)
    fetcher.cookies = {"v": "cookie"}
    calls = []
    delays = []

    async def fake_sleep(delay_range, reason):
        delays.append((delay_range, reason))

    async def fetch_continuous(target_date):
        calls.append(("continuous", target_date))
        return [{"code": "000001"}]

    async def fetch_block(target_date):
        calls.append(("block", target_date))
        return [{"name": "机器人概念"}]

    async def fetch_pool(target_date):
        calls.append(("pool", target_date))
        return [{"code": "000002"}]

    async def fetch_lower_pool(target_date):
        calls.append(("lower_pool", target_date))
        return [{"code": "000004"}]

    async def fetch_eastmoney(target_date):
        calls.append(("eastmoney", target_date))
        return [{"c": "000003"}]

    fetcher._sleep_random_delay = fake_sleep
    fetcher.fetch_continuous_limit_up = fetch_continuous
    fetcher.fetch_block_top = fetch_block
    fetcher.fetch_limit_up_pool = fetch_pool
    fetcher.fetch_lower_limit_pool = fetch_lower_pool
    fetcher.fetch_eastmoney_zt_pool = fetch_eastmoney
    fetcher._stale_fetch_reason = lambda result, target_date: None

    result = asyncio.run(fetcher.fetch_all_data("20260706"))

    assert calls == [
        ("continuous", "20260706"),
        ("block", "20260706"),
        ("pool", "20260706"),
        ("lower_pool", "20260706"),
        ("eastmoney", "20260706"),
    ]
    assert delays == [
        ((3.0, 8.0), "最强风口数据获取前"),
        ((3.0, 8.0), "涨停强度数据获取前"),
        ((3.0, 8.0), "同花顺跌停池数据获取前"),
        ((3.0, 8.0), "东方财富涨停池数据获取前"),
    ]
    assert result["continuous_limit_up"] == [{"code": "000001"}]
    assert result["block_top"] == [{"name": "机器人概念"}]
    assert result["limit_up_pool"] == [{"code": "000002"}]
    assert result["lower_limit_pool"] == [{"code": "000004"}]
    assert result["eastmoney_zt_pool"] == [{"c": "000003"}]
    assert result["errors"] == []


def test_limit_up_pool_uses_configured_page_delay():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    fetcher.page_delay_range = (0.8, 2.0)
    calls = []
    delays = []

    async def fake_sleep(delay_range, reason):
        delays.append((delay_range, reason))

    async def fetch_page(page, **kwargs):
        calls.append(page)
        return {
            "data": [{"code": str(page)}],
            "has_more": page == 1,
        }

    fetcher._sleep_random_delay = fake_sleep
    fetcher.fetch_limit_up_pool_page = fetch_page

    result = asyncio.run(fetcher.fetch_limit_up_pool("20260706"))

    assert calls == [1, 2]
    assert delays == [((0.8, 2.0), "涨停强度分页继续抓取前")]
    assert result == [{"code": "1"}, {"code": "2"}]


def test_limit_up_pool_requests_ths_type_field_without_narrowing_filter():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    captured = {}

    def headers(_referer):
        return {}

    async def request_json(_url, *, params, headers):
        captured.update(params)
        return {"data": {"data": [], "has_more": False}}

    fetcher._get_headers_with_referer = headers
    fetcher._request_json = request_json

    result = asyncio.run(fetcher.fetch_limit_up_pool_page(target_date="20260710"))

    assert result == {"data": [], "has_more": False}
    assert captured["field"] == (
        "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,"
        "1968584,3475914,9003,9004"
    )
    assert captured["filter"] == "HS,GEM2STAR,ST,NEW"


def test_lower_limit_pool_requests_documented_ths_fields():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    captured = {}

    async def request_json(_url, *, params, headers):
        captured.update(params)
        return {"data": {"info": [], "page": {"limit": 15, "page": 1, "total": 0}}}

    fetcher._get_headers_with_referer = lambda _referer: {}
    fetcher._request_json = request_json

    result = asyncio.run(fetcher.fetch_lower_limit_pool_page(target_date="20260709"))

    assert result == {"data": [], "has_more": False}
    assert captured["field"] == "199112,10,330333,330334,1968584,3475914,9004"
    assert captured["filter"] == "HS,GEM2STAR"
    assert captured["order_field"] == "330334"


def test_stale_fetch_reason_skips_when_ths_payload_date_differs():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    friday_timestamp = int(datetime(2026, 7, 3, 9, 25).timestamp())
    result = {
        "continuous_limit_up": [],
        "block_top": [
            {
                "name": "机器人概念",
                "stock_list": [
                    {
                        "code": "603286",
                        "name": "日盈电子",
                        "first_limit_up_time": friday_timestamp,
                    }
                ],
            }
        ],
        "limit_up_pool": [],
        "eastmoney_zt_pool": [{"c": "000595", "n": "宝塔实业"}],
    }

    reason = fetcher._stale_fetch_reason(result, date(2026, 7, 6))

    assert reason is not None
    assert "20260706" in reason
    assert "20260703" in reason
    assert "跳过保存与后续流程" in reason


def test_stale_fetch_reason_allows_matching_ths_payload_date():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    monday_timestamp = int(datetime(2026, 7, 6, 9, 25).timestamp())
    result = {
        "continuous_limit_up": [
            {
                "code": "000001",
                "name": "测试股份",
                "latest_limit_up_time": monday_timestamp,
            }
        ],
        "block_top": [],
        "limit_up_pool": [],
        "eastmoney_zt_pool": [],
    }

    assert fetcher._stale_fetch_reason(result, date(2026, 7, 6)) is None


def test_stale_fetch_reason_skips_when_ths_empty_but_eastmoney_has_data():
    fetcher = StockDataFetcher.__new__(StockDataFetcher)
    result = {
        "continuous_limit_up": [],
        "block_top": [],
        "limit_up_pool": [],
        "eastmoney_zt_pool": [{"c": "000595", "n": "宝塔实业"}],
    }

    reason = fetcher._stale_fetch_reason(result, date(2026, 7, 6))

    assert reason is not None
    assert "无法从上游返回中确认交易日期" in reason
    assert "同花顺为空但东财有数据" in reason


def test_save_all_data_marks_fetch_skipped_without_saving_rows():
    storage = StockDataStorage.__new__(StockDataStorage)
    calls = []
    storage.mark_fetch_skipped = lambda target_date, reason: calls.append(
        (target_date, reason)
    )

    result = storage.save_all_data(
        {"skipped": True, "skip_reason": "非交易日"},
        date(2026, 7, 4),
    )

    assert calls == [(date(2026, 7, 4), "非交易日")]
    assert result == {
        "continuous_limit_up": (0, 0),
        "block_top": (0, 0),
        "limit_up_pool": (0, 0),
        "lower_limit_pool": (0, 0),
        "eastmoney_zt_pool": (0, 0),
    }


def test_save_all_data_records_source_error_as_failed_log():
    storage = StockDataStorage.__new__(StockDataStorage)
    recorded = []
    storage.mark_fetch_failed = lambda target_date, data_type, error: recorded.append(
        (target_date, data_type, error)
    )
    storage.save_lower_limit_pool = lambda *_args: (_ for _ in ()).throw(
        AssertionError("failed source must not be stored as an empty success")
    )

    result = storage.save_all_data(
        {
            "lower_limit_pool": [],
            "errors": [{"type": "lower_limit_pool", "error": "403 Forbidden"}],
        },
        date(2026, 7, 9),
    )

    assert result == {"lower_limit_pool": (0, 1)}
    assert recorded == [(date(2026, 7, 9), "lower_limit_pool", "403 Forbidden")]
