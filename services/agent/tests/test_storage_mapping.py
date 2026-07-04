import sys
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
