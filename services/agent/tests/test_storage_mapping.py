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
