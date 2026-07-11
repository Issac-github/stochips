import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.data.storage import StockDataStorage


def test_block_top_mapping_supports_ths_limit_up_num_and_stock_list():
    storage = StockDataStorage.__new__(StockDataStorage)
    item = {
        "code": "885517",
        "name": "机器人概念",
        "change": 2.377,
        "limit_up_num": 43,
        "continuous_plate_num": 5,
        "high": "4天2板",
        "high_num": 131076,
        "stock_list": [
            {
                "code": "603286",
                "name": "日盈电子",
                "first_limit_up_time": "1783045020",
            }
        ],
    }

    leader = storage._first_list_item(item, "stock_list")

    assert (
        storage._safe_int(
            storage._first_value(
                item,
                "stock_count",
                "num",
                "count",
                "limit_up_count",
                "limit_up_num",
            )
        )
        == 43
    )
    assert str(
        storage._safe_decimal(
            storage._first_value(item, "change_percent", "change_rate", "rate", "change")
        )
    ) == "2.377"
    assert storage._safe_str(leader.get("code")) == "603286"
    assert storage._safe_str(leader.get("name")) == "日盈电子"
    assert storage._safe_int(storage._first_value(item, "continuous_plate_num")) == 5
    assert storage._safe_str(storage._first_value(item, "high")) == "4天2板"
    assert storage._safe_int(storage._first_value(item, "high_num")) == 131076


def test_save_block_top_persists_full_ths_stock_list():
    storage = StockDataStorage.__new__(StockDataStorage)

    class Query:
        def query(self, *args):
            return self

        def filter(self, *args):
            return self

        def delete(self, synchronize_session=False):
            return 0

    saved_values = []

    def fake_upsert(session, model, values, key_fields):
        saved_values.append(values)

    storage._upsert_by_keys = fake_upsert
    saved_count = storage._save_block_top_stocks(
        Query(),
        {
            "code": "885517",
            "name": "机器人概念",
            "change": 2.377,
            "limit_up_num": 43,
            "stock_list": [
                {
                    "code": "603286",
                    "name": "日盈电子",
                    "continue_num": 3,
                    "high": "3天2板",
                    "high_days": 131075,
                    "first_limit_up_time": "09:31",
                    "last_limit_up_time": "09:33",
                    "change_rate": 10.0139,
                    "latest": 23.73,
                    "reason_type": "先进封装+存储芯片",
                    "reason_info": "行业原因：先进封装景气度提升",
                    "concept": "芯片概念",
                    "market_id": 33,
                    "market_type": "HS",
                    "is_new": 0,
                    "is_st": 0,
                    "change_tag": "FIRST_LIMIT",
                },
                {
                    "code": "002031",
                    "name": "巨轮智能",
                    "continue_num": 1,
                    "first_limit_up_time": "09:45",
                },
            ],
        },
        date(2026, 7, 9),
        "885517",
        "机器人概念",
    )

    assert saved_count == 2
    assert [
        (item["code"], item["name"], item["continuous_days"], item["sort_order"])
        for item in saved_values
    ] == [
        ("603286", "日盈电子", 3, 1),
        ("002031", "巨轮智能", 1, 2),
    ]
    assert all(item["block_code"] == "885517" for item in saved_values)
    first_stock = saved_values[0]
    assert first_stock["limit_up_type"] == "3天2板"
    assert first_stock["high_days"] == 131075
    assert first_stock["last_limit_up_time"] == "09:33"
    assert str(first_stock["change_percent"]) == "10.0139"
    assert str(first_stock["latest_price"]) == "23.73"
    assert first_stock["reason_type"] == "先进封装+存储芯片"
    assert first_stock["reason_info"] == "行业原因：先进封装景气度提升"
    assert first_stock["concept"] == "芯片概念"
    assert first_stock["market_id"] == 33
    assert first_stock["market_type"] == "HS"
    assert first_stock["is_new"] == 0
    assert first_stock["is_st"] == 0
    assert first_stock["change_tag"] == "FIRST_LIMIT"
    assert json.loads(first_stock["raw_json"])["reason_type"] == "先进封装+存储芯片"


def test_limit_up_pool_prefers_ths_reason_and_first_last_time_fields():
    storage = StockDataStorage.__new__(StockDataStorage)
    item = {
        "first_limit_up_time": "1783563090",
        "last_limit_up_time": "1783567537",
        "open_num": 3,
        "currency_value": 67472008000,
        "reason_type": "中报预增+交互智能平板+AI教育+机器人",
        "reason_info": "公司聚焦智能交互显示与AI教育。",
        "330324": "09:31",
        "330329": "10:12",
        "9004": "旧原因",
    }

    assert storage._first_value(
        item, "first_limit_up_time", "limit_up_time", "330324"
    ) == "1783563090"
    assert storage._first_value(
        item, "last_limit_up_time", "last_time", "330329"
    ) == "1783567537"
    assert storage._safe_int(item.get("open_num")) == 3
    assert storage._safe_int({"open_num": None}.get("open_num")) == 0
    assert storage._safe_decimal(
        storage._first_value(item, "currency_value", "market_value", "9003")
    ) == 67472008000
    assert storage._first_value(item, "reason_type", "concept") == item["reason_type"]
    assert storage._first_value(item, "reason_info", "reason", "9004") == item["reason_info"]


def test_save_limit_up_pool_persists_open_num_and_currency_value_without_fallback():
    storage = StockDataStorage.__new__(StockDataStorage)
    saved_values = []

    class Session:
        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    storage.Session = lambda: Session()
    storage._upsert_by_keys = (
        lambda _session, _model, values, _keys: saved_values.append(values)
    )
    storage._save_log = lambda *_args: None

    success, failed = storage.save_limit_up_pool(
        [
            {
                "code": "000001",
                "name": "开板股份",
                "open_num": 3,
                "currency_value": 67472008000,
            },
            {
                "code": "000002",
                "name": "无开板数据股份",
                "open_num": None,
                "open_count": 9,
                "330325": 8,
            },
        ],
        date(2026, 7, 10),
    )

    assert (success, failed) == (2, 0)
    assert saved_values[0]["open_count"] == 3
    assert str(saved_values[0]["market_value"]) == "67472008000"
    assert saved_values[1]["open_count"] == 0


def test_save_lower_limit_pool_persists_ths_downside_fields():
    storage = StockDataStorage.__new__(StockDataStorage)
    saved_values = []

    class Session:
        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    storage.Session = lambda: Session()
    storage._upsert_by_keys = (
        lambda _session, _model, values, _keys: saved_values.append(values)
    )
    storage._save_log = lambda *_args: None

    success, failed = storage.save_lower_limit_pool(
        [
            {
                "code": "600350",
                "name": "山东高速",
                "latest": 12.14,
                "change_rate": -10.0074,
                "first_limit_down_time": "1783563565",
                "last_limit_down_time": "1783579867",
                "turnover_rate": 0.2888,
                "currency_value": 58691690000,
                "market_id": 17,
                "market_type": "HS",
                "is_again_limit": 0,
                "change_tag": "LIMIT_DOWN",
                "time_preview": [-1.56, -10.01],
            }
        ],
        date(2026, 7, 9),
    )

    assert (success, failed) == (1, 0)
    values = saved_values[0]
    assert values["first_limit_down_time"] == "1783563565"
    assert values["last_limit_down_time"] == "1783579867"
    assert str(values["change_percent"]) == "-10.0074"
    assert str(values["market_value"]) == "58691690000"
    assert json.loads(values["time_preview"]) == [-1.56, -10.01]
