import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.feishu_notifier import (
    BlockSummary,
    BreakoutSummary,
    FeishuStockNotifier,
    FeishuStockReport,
    IndustrySummary,
    RiskStockSummary,
    StockSummary,
    WeakBoardSummary,
)


class FakeFeishuResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = str(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


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
        continuous_distribution={4: 1, 3: 2},
        limit_up_type_distribution={"首板": 7, "连板": 3},
        suggestion_distribution={"谨慎": 1, "机会": 2},
        data_warnings=["风险评估尚未完成"],
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
        eastmoney_industries=[
            IndustrySummary(
                industry_name="专用设备",
                stock_count=6,
                leaders=[
                    "测试设备（3板）",
                    "龙头设备（2板）",
                    "强势设备（1板）",
                    "补充设备（1板）",
                ],
            ),
            IndustrySummary(
                industry_name="汽车零部件",
                stock_count=4,
                leaders=["测试汽配（1板）"],
            ),
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
            ),
            StockSummary(
                code="000007",
                name="同板股份",
                continuous_days=4,
                limit_up_time="09:40",
                block_name="机器人概念",
                reason="连板延续",
                risk_level="中",
                risk_score=60.0,
                suggestion="观察",
            )
        ],
        early_stocks=[
            StockSummary(
                code="000002",
                name="早盘股份",
                continuous_days=1,
                limit_up_time="09:31",
                block_name="新能源汽车",
                reason="快速封板",
                risk_level="低",
                risk_score=20.0,
                suggestion="机会",
            )
        ],
        weak_boards=[
            WeakBoardSummary(
                code="000003",
                name="分歧股份",
                open_count=5,
                turnover_rate=18.5,
                block_name="消费电子",
                reason="多次开板",
            )
        ],
        breakout_stocks=[
            BreakoutSummary(
                code="000006",
                name="突破股份",
                breakout_price=12.5,
                previous_high_price=11.2,
                breakout_ratio=11.607,
                previous_max_days=3,
                gap_trading_days=6,
                block_name="低空经济",
                reason="涨停突破前高",
            )
        ],
        top_risks=[
            RiskStockSummary(
                code="000004",
                name="高危股份",
                risk_level="高",
                risk_score=95.0,
                suggestion="规避",
                continuous_days=5,
                ai_analyzed=True,
            )
        ],
        opportunity_stocks=[
            RiskStockSummary(
                code="000005",
                name="机会股份",
                risk_level="低",
                risk_score=18.0,
                suggestion="机会",
                continuous_days=2,
                ai_analyzed=False,
            )
        ],
    )

    card = notifier.build_card(report)
    content = card["body"]["elements"][0]["content"]

    assert card["schema"] == "2.0"
    assert "StoChips 每日涨停播报 - 2026-07-04" == card["header"]["title"]["content"]
    assert "同花顺 10 只" in content
    assert "涨停结构" in content
    assert "4板 1只" in content
    assert "同花顺板块热度" in content
    assert "机器人概念：4 家涨停" in content
    assert "东财行业涨停" in content
    assert "专用设备：测试设备（3板）、龙头设备（2板）、强势设备（1板）、补充设备（1板）" in content
    assert "专用设备：6 只涨停" not in content
    assert "前三" not in content
    assert "核心连板" in content
    assert "4板：测试股份(000001)、同板股份(000007)" in content
    assert "早盘股份(000002)：1板" in content
    assert "分歧股份(000003)：开板 5 次" in content
    assert "突破股份(000006)：前期3板，断板6个交易日" in content
    assert "高危股份(000004)：5板" in content
    assert "机会股份(000005)：2板" in content
    assert "高风险 1 只" in content


def test_generate_sign_matches_feishu_custom_bot_algorithm():
    assert (
        FeishuStockNotifier._generate_sign("1600000000", "secret")
        == "vvU1S4ucHy95pQ90meMW66yQJ+Szge4s9g7hQUu9yP8="
    )


def test_post_with_retry_recovers_from_feishu_frequency_limit(monkeypatch):
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier.webhook_url = "https://example.test/hook"
    responses = [
        {"code": 11232, "data": {}, "msg": "frequency limited"},
        {"code": 11232, "data": {}, "msg": "frequency limited"},
        {"code": 0, "data": {}, "msg": "success"},
    ]
    sleeps = []

    def fake_post(*args, **kwargs):
        return FakeFeishuResponse(responses.pop(0))

    monkeypatch.setattr("chain.stock.agents.feishu_notifier.requests.post", fake_post)
    monkeypatch.setattr("chain.stock.agents.feishu_notifier.time.sleep", sleeps.append)

    result = notifier._post_with_retry({"msg_type": "interactive", "card": {}})

    assert result["code"] == 0
    assert sleeps == [20, 60]
    assert responses == []


def test_post_with_retry_does_not_retry_non_rate_limit_error(monkeypatch):
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier.webhook_url = "https://example.test/hook"
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeFeishuResponse({"code": 19021, "data": {}, "msg": "bad sign"})

    monkeypatch.setattr("chain.stock.agents.feishu_notifier.requests.post", fake_post)
    monkeypatch.setattr("chain.stock.agents.feishu_notifier.time.sleep", lambda delay: None)

    result = notifier._post_with_retry({"msg_type": "interactive", "card": {}})

    assert result["code"] == 19021
    assert len(calls) == 1


def test_prefer_regular_stocks_before_st_and_delisting_names():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    rows = [
        SimpleNamespace(name="*ST测试"),
        SimpleNamespace(name="国华退"),
        SimpleNamespace(name="正常股份"),
    ]

    selected = notifier._prefer_regular_stocks(rows, limit=2)

    assert [item.name for item in selected] == ["正常股份", "*ST测试"]


def test_format_breakouts_renders_previous_limit_up_breakout():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    content = notifier._format_breakouts(
        [
            BreakoutSummary(
                code="000006",
                name="突破股份",
                breakout_price=12.5,
                previous_high_price=11.2,
                breakout_ratio=11.607,
                previous_max_days=3,
                gap_trading_days=6,
                block_name="低空经济",
                reason="涨停突破前高",
            )
        ]
    )

    assert "前期3板" in content
    assert "断板6个交易日" in content
    assert "前高11.20" in content
    assert "今涨停12.50" in content
    assert "突破11.6%" in content


def test_format_stocks_keeps_special_risk_names_when_provided():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_stocks(
        [
            StockSummary(
                code="000004",
                name="国华退",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
                risk_level="未评估",
                risk_score=None,
                suggestion="",
            ),
            StockSummary(
                code="002175",
                name="*ST东智",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
                risk_level="未评估",
                risk_score=None,
                suggestion="",
            ),
        ]
    )

    assert "国华退(000004)：5板" in content
    assert "*ST东智(002175)：5板" in content


def test_format_core_continuous_groups_by_board_count():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_core_continuous(
        [
            StockSummary(
                code="000004",
                name="国华退",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
                risk_level="未评估",
                risk_score=None,
                suggestion="",
            ),
            StockSummary(
                code="002175",
                name="*ST东智",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
                risk_level="未评估",
                risk_score=None,
                suggestion="",
            ),
            StockSummary(
                code="603137",
                name="恒尚节能",
                continuous_days=4,
                limit_up_time="",
                block_name="",
                reason="",
                risk_level="未评估",
                risk_score=None,
                suggestion="",
            ),
        ]
    )

    assert "1. 5板：国华退(000004)、*ST东智(002175)" in content
    assert "2. 4板：恒尚节能(603137)" in content
    assert "风险 未评估/无评分" not in content


def test_format_industries_renders_eastmoney_industry_counts():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_industries(
        [
            IndustrySummary(
                industry_name="专用设备",
                stock_count=6,
                leaders=[
                    "测试设备（3板）",
                    "龙头设备（2板）",
                    "强势设备（1板）",
                    "补充设备（1板）",
                ],
            )
        ]
    )

    assert "专用设备：测试设备（3板）、龙头设备（2板）、强势设备（1板）、补充设备（1板）" in content
    assert "专用设备：6 只涨停" not in content
    assert "前三" not in content
    assert notifier._format_industries([]) == "- 暂无东财行业数据"
    assert (
        notifier._format_industries(
            [IndustrySummary(industry_name="未知行业", stock_count=1, leaders=[])]
        )
        == "1. 未知行业：暂无个股"
    )


def test_build_card_labels_ths_blocks_and_eastmoney_industries_separately():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    report = FeishuStockReport(
        target_date=date(2026, 7, 4),
        is_complete=True,
        continuous_count=0,
        block_count=2,
        hr_limit_up_count=1,
        em_limit_up_count=1,
        max_continuous_days=0,
        assessed_count=0,
        ai_analyzed_count=0,
        risk_distribution={},
        continuous_distribution={},
        limit_up_type_distribution={},
        suggestion_distribution={},
        data_warnings=[
            "同花顺 block_top 与 limit_up_pool 均缺少可聚合板块数量，行业热度请看东财行业涨停"
        ],
        fetch_logs=[],
        top_blocks=[],
        eastmoney_industries=[
            IndustrySummary(industry_name="电力", stock_count=8, leaders=["宝塔实业（2板）"])
        ],
        top_stocks=[],
        early_stocks=[],
        weak_boards=[],
        breakout_stocks=[],
        top_risks=[],
        opportunity_stocks=[],
    )

    content = notifier.build_card(report)["body"]["elements"][0]["content"]

    assert "同花顺板块热度" in content
    assert "暂无板块数据" in content
    assert "东财行业涨停" in content
    assert "电力：宝塔实业（2板）" in content
    assert "行业热度请看东财行业涨停" in content


def test_build_weak_boards_requires_opened_limit_up_board():
    class Query:
        def __init__(self):
            self.filter_args = []

        def filter(self, *args):
            self.filter_args.extend(args)
            return self

        def order_by(self, *args):
            return self

        def limit(self, count):
            return self

        def all(self):
            return []

    query = Query()
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    session = SimpleNamespace(query=lambda *args: query)

    assert notifier._build_weak_boards(session, date(2026, 7, 6)) == []
    assert any("open_count" in str(arg) and ">" in str(arg) for arg in query.filter_args)


def test_recent_trading_dates_excludes_weekends_from_lookback_window():
    class Query:
        def filter(self, *args):
            return self

        def group_by(self, *args):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return [
                (date(2026, 7, 6),),  # Monday
                (date(2026, 7, 5),),  # Sunday
                (date(2026, 7, 4),),  # Saturday
                (date(2026, 7, 3),),  # Friday
                (date(2026, 7, 2),),  # Thursday
            ]

    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    session = SimpleNamespace(query=lambda *args: Query())

    dates = notifier._recent_trading_dates(session, date(2026, 7, 6), lookback=2)

    assert dates == [
        date(2026, 7, 6),
        date(2026, 7, 3),
        date(2026, 7, 2),
    ]
