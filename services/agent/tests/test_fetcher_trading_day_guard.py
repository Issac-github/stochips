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
        "eastmoney_zt_pool": (0, 0),
    }
