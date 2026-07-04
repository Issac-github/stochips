import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.feishu_notifier import (
    BlockSummary,
    FeishuStockNotifier,
    FeishuStockReport,
    StockSummary,
)


def test_build_card_contains_daily_report_sections():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    report = FeishuStockReport(
        target_date=date(2026, 7, 4),
        is_complete=True,
        continuous_count=3,
        block_count=2,
        hr_limit_up_count=10,
        em_limit_up_count=11,
        max_continuous_days=4,
        assessed_count=3,
        ai_analyzed_count=2,
        risk_distribution={"高": 1, "中": 2},
        fetch_logs=[
            {
                "data_type": "limit_up_pool",
                "status": "success",
                "record_count": 10,
                "error_message": None,
            }
        ],
        top_blocks=[
            BlockSummary(
                block_name="机器人概念",
                stock_count=4,
                leading_stock_name="测试龙头",
                change_percent=3.21,
            )
        ],
        top_stocks=[
            StockSummary(
                code="000001",
                name="测试股份",
                continuous_days=4,
                limit_up_time="09:35",
                block_name="机器人概念",
                reason="题材发酵",
                risk_level="高",
                risk_score=88.0,
                suggestion="谨慎",
            )
        ],
    )

    card = notifier.build_card(report)
    content = card["body"]["elements"][0]["content"]

    assert card["schema"] == "2.0"
    assert "StoChips 每日涨停播报 - 2026-07-04" == card["header"]["title"]["content"]
    assert "同花顺 10 只" in content
    assert "机器人概念：4 家涨停" in content
    assert "测试股份(000001)：4板" in content
    assert "高风险 1 只" in content


def test_generate_sign_matches_feishu_custom_bot_algorithm():
    assert (
        FeishuStockNotifier._generate_sign("1600000000", "secret")
        == "vvU1S4ucHy95pQ90meMW66yQJ+Szge4s9g7hQUu9yP8="
    )
