import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.feishu_notifier import (
    BlockSummary,
    BlockStockReasonSummary,
    BreakoutSummary,
    DailyReviewSummary,
    FeishuStockNotifier,
    FeishuStockReport,
    IndustrySummary,
    StockSummary,
    WeakBoardSummary,
    next_feishu_send_at,
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
        continuous_distribution={4: 1, 3: 2},
        limit_up_type_distribution={"首板": 7, "连板": 3},
        data_warnings=[],
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
                stocks=[
                    "测试股份（4板）",
                    "同板股份（4板）",
                    "补涨股份（1板）",
                    "低位股份（1板）",
                ],
                stock_reasons=[
                    BlockStockReasonSummary(
                        code="000001",
                        name="测试股份",
                        reason_type="机器人+业绩增长",
                        reason_info="行业原因：机器人产业提速。\n公司原因：订单增长。",
                    )
                ],
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
            ),
            StockSummary(
                code="000007",
                name="同板股份",
                continuous_days=4,
                limit_up_time="09:40",
                block_name="机器人概念",
                reason="连板延续",
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
        daily_review=DailyReviewSummary(
            content="### 情绪阶段\n市场处于试错修复期。",
            provider="codex",
            model="gpt-test-codex",
        ),
    )

    card = notifier.build_card(report)
    content = card["body"]["elements"][0]["content"]

    assert card["schema"] == "2.0"
    assert "StoChips 每日涨停播报 - 2026-07-04" == card["header"]["title"]["content"]
    assert "同花顺 10 只" in content
    assert "涨停结构" in content
    assert "4板 1只" in content
    assert "同花顺板块热度" in content
    assert "机器人概念：4 家涨停，涨幅 3.21%，测试股份（4板）、同板股份（4板）、补涨股份（1板）、低位股份（1板）" in content
    assert "风口接口" not in content
    assert "涨停池聚合" not in content
    assert "东财行业涨停" in content
    assert "专用设备：测试设备（3板）、龙头设备（2板）、强势设备（1板）、补充设备（1板）" in content
    assert "专用设备：6 只涨停" not in content
    assert "前三" not in content
    assert "核心连板" in content
    assert "4板：测试股份(000001)、同板股份(000007)" in content
    assert "早盘股份(000002)：1板" in content
    assert "分歧股份(000003)：开板 5 次" in content
    assert "突破股份(000006)：前期3板，断板6个交易日" in content
    assert "风险评估" not in content
    assert "未评估/无评分" not in content
    assert "建议分布" not in content
    assert "高风险关注" not in content
    assert "机会观察" not in content
    assert "Codex 市场复盘" in content
    assert "市场处于试错修复期" in content
    assert "Agent: main | Model: gpt-test-codex" in content
    assert "Provider: openai-codex" in content
    assert "行业原因：机器人产业提速" not in content

    material = notifier.build_analysis_material(report)
    assert "Codex 市场复盘" not in material
    assert "风险评估" not in material

    reason_material = notifier.build_codex_reason_material(report)
    assert "简略原因（reason_type）：机器人+业绩增长" in reason_material
    assert "详细原因（reason_info）" in reason_material
    assert "行业原因：机器人产业提速" in reason_material


def test_generate_sign_matches_feishu_custom_bot_algorithm():
    assert (
        FeishuStockNotifier._generate_sign("1600000000", "secret")
        == "vvU1S4ucHy95pQ90meMW66yQJ+Szge4s9g7hQUu9yP8="
    )


def test_codex_reason_material_deduplicates_stocks_across_hot_blocks():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    reason = BlockStockReasonSummary(
        code="002185",
        name="华天科技",
        reason_type="先进封装+存储芯片",
        reason_info="行业原因：先进封装景气度提升。",
    )
    report = SimpleNamespace(
        top_blocks=[
            BlockSummary(
                block_name="芯片概念",
                stock_count=31,
                leading_stock_name="华天科技",
                change_percent=3.22,
                stock_reasons=[reason],
            ),
            BlockSummary(
                block_name="先进封装",
                stock_count=22,
                leading_stock_name="华天科技",
                change_percent=5.52,
                stock_reasons=[reason],
            ),
        ]
    )

    material = notifier.build_codex_reason_material(report)

    assert material.count("华天科技(002185)") == 1
    assert "所属热度板块：芯片概念、先进封装" in material
    assert material.count("行业原因：先进封装景气度提升") == 1


def test_post_with_retry_recovers_from_feishu_frequency_limit(monkeypatch):
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier.webhook_url = "https://example.test/hook"
    responses = [
        {"code": 11232, "data": {}, "msg": "frequency limited"},
        {"code": 11232, "data": {}, "msg": "frequency limited"},
        {"code": 0, "data": {}, "msg": "success"},
    ]
    send_windows = []

    def fake_post(*args, **kwargs):
        return FakeFeishuResponse(responses.pop(0))

    def fake_next_send_at(now=None, not_before=None):
        send_windows.append(not_before)
        return datetime.now()

    monkeypatch.setattr("chain.stock.agents.feishu_notifier.requests.post", fake_post)
    monkeypatch.setattr(
        "chain.stock.agents.feishu_notifier.next_feishu_send_at",
        fake_next_send_at,
    )
    monkeypatch.setattr(
        "chain.stock.agents.feishu_notifier.wait_until_feishu_send_at",
        lambda send_at: None,
    )

    result = notifier._post_with_retry({"msg_type": "interactive", "card": {}})

    assert result["code"] == 0
    assert len(send_windows) == 5
    assert send_windows[0] is None
    assert all(send_window is not None for send_window in send_windows[1:])
    assert responses == []


def test_post_with_retry_does_not_retry_non_rate_limit_error(monkeypatch):
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier.webhook_url = "https://example.test/hook"
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeFeishuResponse({"code": 19021, "data": {}, "msg": "bad sign"})

    monkeypatch.setattr("chain.stock.agents.feishu_notifier.requests.post", fake_post)
    monkeypatch.setattr(
        "chain.stock.agents.feishu_notifier.next_feishu_send_at",
        lambda now=None, not_before=None: datetime.now(),
    )
    monkeypatch.setattr(
        "chain.stock.agents.feishu_notifier.wait_until_feishu_send_at",
        lambda send_at: None,
    )

    result = notifier._post_with_retry({"msg_type": "interactive", "card": {}})

    assert result["code"] == 19021
    assert len(calls) == 1


def test_next_feishu_send_at_uses_non_exact_odd_minutes(monkeypatch):
    monkeypatch.setattr(
        "chain.stock.agents.feishu_notifier.random.uniform",
        lambda delay_min, delay_max: 7.0,
    )

    assert next_feishu_send_at(now=datetime(2026, 7, 10, 16, 21, 5)) == datetime(
        2026, 7, 10, 16, 21, 5
    )
    assert next_feishu_send_at(now=datetime(2026, 7, 10, 16, 21, 0)) == datetime(
        2026, 7, 10, 16, 21, 7
    )
    assert next_feishu_send_at(now=datetime(2026, 7, 10, 16, 20, 30)) == datetime(
        2026, 7, 10, 16, 21, 7
    )
    assert next_feishu_send_at(
        now=datetime(2026, 7, 10, 16, 20, 30),
        not_before=datetime(2026, 7, 10, 16, 21, 5),
    ) == datetime(2026, 7, 10, 16, 21, 5)


def test_status_notification_uses_a_red_interactive_card():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier.webhook_url = "https://example.test/hook"
    captured = []
    notifier._send_card = lambda card: captured.append(card) or {"code": 0}

    result = notifier.send_status_notification(
        date(2026, 7, 10),
        "StoChips 任务失败通知",
        "**预计重试时间**：2026-07-10 16:25:00",
    )

    assert result == {"feishu_response": {"code": 0}, "date": "2026-07-10"}
    assert captured[0]["header"]["template"] == "red"
    assert "预计重试时间" in captured[0]["body"]["elements"][0]["content"]


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


def test_format_stocks_keeps_special_names_when_provided():
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
            ),
            StockSummary(
                code="002175",
                name="*ST东智",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
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
            ),
            StockSummary(
                code="002175",
                name="*ST东智",
                continuous_days=5,
                limit_up_time="",
                block_name="",
                reason="",
            ),
            StockSummary(
                code="603137",
                name="恒尚节能",
                continuous_days=4,
                limit_up_time="",
                block_name="",
                reason="",
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


def test_format_blocks_renders_all_stocks_without_source_label():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_blocks(
        [
            BlockSummary(
                block_name="芯片概念",
                stock_count=2,
                leading_stock_name="龙头芯片",
                change_percent=2.5,
                stocks=["龙头芯片（3板）", "跟涨芯片（1板）"],
            ),
            BlockSummary(
                block_name="机器人概念",
                stock_count=1,
                leading_stock_name="机器龙头",
                change_percent=None,
                source="limit_up_pool",
                stocks=[],
            ),
        ]
    )

    assert "芯片概念：2 家涨停，涨幅 2.50%，龙头芯片（3板）、跟涨芯片（1板）" in content
    assert "机器人概念：1 家涨停，龙头 机器龙头" in content
    assert "风口接口" not in content
    assert "涨停池聚合" not in content


def test_format_blocks_without_stock_detail_falls_back_to_summary_not_fake_list():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_blocks(
        [
            BlockSummary(
                block_name="芯片概念",
                stock_count=31,
                leading_stock_name="华天科技",
                change_percent=3.22,
                stocks=[],
            )
        ]
    )

    assert "芯片概念：31 家涨停，涨幅 3.22%，龙头 华天科技" in content
    assert "芯片概念：华天科技" not in content
    assert "风口接口" not in content


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
        continuous_distribution={},
        limit_up_type_distribution={},
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
