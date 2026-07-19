import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.feishu_notifier import (
    BlockSummary,
    BlockStockReasonSummary,
    BoardOverlapSummary,
    BreakoutSummary,
    DailyReviewSummary,
    FeishuStockNotifier,
    FeishuStockReport,
    IndustrySummary,
    LeaderAssistSummary,
    LimitUpPoolAnalysisSummary,
    LowerLimitSummary,
    StockSummary,
    WeakBoardSummary,
    next_feishu_send_at,
)
from chain.stock.models.database import (
    BlockTop,
    BlockTopStock,
    ContinuousLimitUp,
    DailyMarketReview,
    DataFetchLog,
    EastmoneyZTPool,
    LimitUpPool,
    LowerLimitPool,
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
        lower_limit_count=2,
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
                leading_turnover_rate=12.3,
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
                leader_turnover_rates=[8.2, 6.5, 4.1, 2.8],
            ),
            IndustrySummary(
                industry_name="汽车零部件",
                stock_count=4,
                leaders=["测试汽配（1板）"],
                leader_turnover_rates=[3.6],
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
                turnover_rate=12.5,
                reason_type="机器人+业绩增长",
                reason_info="行业原因：机器人产业提速。公司原因：订单增长。",
            ),
            StockSummary(
                code="000007",
                name="同板股份",
                continuous_days=4,
                limit_up_time="09:40",
                block_name="机器人概念",
                reason="连板延续",
                turnover_rate=9.5,
                reason_type="机器人",
                reason_info="板块连板延续。",
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
        lower_limit_stocks=[
            LowerLimitSummary(
                code="000010",
                name="跌停股份",
                change_percent=-10.01,
                first_limit_down_time="09:31",
                last_limit_down_time="14:51",
                turnover_rate=3.2,
                is_again_limit=False,
            )
        ],
        daily_review=DailyReviewSummary(
            content="### 情绪阶段\n市场处于试错修复期。",
            provider="codex",
            model="gpt-test-codex",
        ),
    )

    card = notifier.build_card(report)
    elements = card["body"]["elements"]
    content = elements[0]["content"]
    tables = {element["element_id"]: element for element in elements if element["tag"] == "table"}
    charts = {element["element_id"]: element for element in elements if element["tag"] == "chart"}
    review_content = elements[-1]["content"]
    breakout_content = elements[-2]["content"]

    assert card["schema"] == "2.0"
    assert "StoChips 每日涨停播报 - 2026-07-04" == card["header"]["title"]["content"]
    assert "同花顺 10 只" in content
    assert "涨停结构" in content
    assert "**跌停概览**：同花顺 2 只" in content
    assert "4板 1只" in content
    assert set(tables) == {
        "hot_blocks",
        "continuous_ladder",
        "high_turnover_high_boards",
        "eastmoney_industries",
        "lower_limit_pool",
    }
    assert set(charts) == {
        "limit_up_structure",
        "continuous_ladder_chart",
        "hot_blocks_chart",
        "eastmoney_industry",
    }
    element_ids = [
        element["element_id"]
        for element in elements
        if element["tag"] in {"chart", "table"}
    ]
    assert len(element_ids) == len(set(element_ids))
    assert charts["limit_up_structure"]["chart_spec"]["data"]["values"] == [
        {"name": "首板", "value": 7},
        {"name": "连板", "value": 3},
    ]
    assert charts["continuous_ladder_chart"]["chart_spec"]["data"]["values"] == [
        {"name": "3板", "value": 2},
        {"name": "4板", "value": 1},
    ]
    assert charts["hot_blocks_chart"]["chart_spec"]["direction"] == "horizontal"
    assert charts["eastmoney_industry"]["chart_spec"]["direction"] == "horizontal"
    assert tables["hot_blocks"]["rows"] == [
        {
            "block": "机器人概念",
            "count": 4,
            "leader": "测试龙头（换手 12.30%）",
            "stocks": (
                "测试股份（4板）\n"
                "同板股份（4板）\n"
                "补涨股份（1板）\n"
                "低位股份（1板）"
            ),
            "change": "3.21%",
        }
    ]
    assert [column["width"] for column in tables["hot_blocks"]["columns"]] == [
        "140px",
        "80px",
        "auto",
        "320px",
        "90px",
    ]
    assert tables["continuous_ladder"]["rows"][0] == {
        "days": "4板",
        "stock": "测试股份(000001)",
        "turnover": "12.50%",
        "time": "09:35",
        "reason_type": "机器人+业绩增长",
        "reason_info": "行业原因：机器人产业提速。公司原因：订单增长。",
    }
    assert [column["width"] for column in tables["continuous_ladder"]["columns"]] == [
        "80px",
        "auto",
        "90px",
        "80px",
        "180px",
        "320px",
    ]
    assert tables["high_turnover_high_boards"]["rows"] == [
        {
            "days": "4板",
            "stock": "测试股份(000001)",
            "turnover": "12.50%",
            "time": "09:35",
            "reason_type": "机器人+业绩增长",
            "reason_info": "行业原因：机器人产业提速。公司原因：订单增长。",
        }
    ]
    assert tables["eastmoney_industries"]["rows"][0] == {
        "industry": "专用设备",
        "count": 6,
        "leaders": (
            "测试设备（3板）（换手 8.20%）\n"
            "龙头设备（2板）（换手 6.50%）\n"
            "强势设备（1板）（换手 4.10%）\n"
            "补充设备（1板）（换手 2.80%）"
        ),
    }
    assert [column["width"] for column in tables["eastmoney_industries"]["columns"]] == [
        "130px",
        "80px",
        "auto",
    ]
    assert tables["lower_limit_pool"]["rows"] == [
        {
            "stock": "跌停股份(000010)",
            "change": "-10.01%",
            "turnover": "3.20%",
            "time": "09:31",
            "status": "封死",
        }
    ]
    assert [column["width"] for column in tables["lower_limit_pool"]["columns"]] == [
        "auto",
        "90px",
        "90px",
        "80px",
        "90px",
    ]
    assert "市场复盘" in review_content
    assert "市场处于试错修复期" in review_content
    assert "Agent: main | Model: gpt-test-codex" in review_content
    assert "Provider: openai-codex" in review_content
    assert "涨停前高突破" in breakout_content
    assert "5个交易日内涨停前高突破" in breakout_content

    empty_early = notifier._format_stocks(
        [],
        empty_message="暂无早盘强势数据",
    )
    assert empty_early == "- 暂无早盘强势数据"

    material = notifier.build_analysis_material(report)
    assert "市场复盘" not in material
    assert "风险评估" not in material
    assert "龙头助攻明细" in material

    reason_material = notifier.build_codex_reason_material(report)
    assert "简略原因（reason_type）：机器人+业绩增长" in reason_material
    assert "详细原因（reason_info）" in reason_material
    assert "行业原因：机器人产业提速" in reason_material
    assert "同花顺全量涨停池指标" not in reason_material
    assert "东财行业代表涨停股换手（Codex分析补充）" in reason_material
    assert "测试设备（3板）（换手 8.20%）" in reason_material


def test_build_report_uses_pool_reason_type_and_block_reason_info_fallback():
    engine = create_engine("sqlite://")
    for model in (
        ContinuousLimitUp,
        BlockTop,
        BlockTopStock,
        LimitUpPool,
        EastmoneyZTPool,
        LowerLimitPool,
        DailyMarketReview,
    ):
        model.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(CreateTable(DataFetchLog.__table__))
    session = sessionmaker(bind=engine)()
    target_date = date(2026, 7, 15)
    detailed_reason = "行业原因：机器人产业提速。公司原因：订单持续增长。"
    try:
        session.add_all(
            [
                ContinuousLimitUp(
                    id=1,
                    date=target_date,
                    code="000001",
                    name="测试股份",
                    continuous_days=4,
                    latest_limit_up_time="09:35",
                ),
                BlockTop(
                    id=1,
                    date=target_date,
                    block_code="885001",
                    block_name="机器人概念",
                    stock_count=1,
                ),
                BlockTopStock(
                    id=1,
                    date=target_date,
                    block_code="885001",
                    block_name="机器人概念",
                    code="000001",
                    name="测试股份",
                    reason_type="最强风口简因",
                    reason_info=detailed_reason,
                ),
                LimitUpPool(
                    id=1,
                    date=target_date,
                    code="000001",
                    name="测试股份",
                    concept="机器人+业绩增长",
                    turnover_rate=12.5,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    notifier = FeishuStockNotifier("sqlite://")
    notifier.Session = sessionmaker(bind=engine)
    notifier._aggregate_blocks_from_pool = lambda *_args, **_kwargs: []
    notifier._aggregate_eastmoney_industries = lambda *_args, **_kwargs: []
    notifier._build_early_stocks = lambda *_args, **_kwargs: []
    notifier._build_weak_boards = lambda *_args, **_kwargs: []
    notifier._build_breakout_stocks = lambda *_args, **_kwargs: []
    notifier._build_lower_limit_stocks = lambda *_args, **_kwargs: []
    notifier._build_one_word_stocks = lambda *_args, **_kwargs: []
    notifier._build_leader_assists = lambda *_args, **_kwargs: []
    notifier._build_board_overlaps = lambda *_args, **_kwargs: []
    notifier._build_previous_high_feedback = lambda *_args, **_kwargs: []

    report = notifier.build_report(target_date)

    assert report.top_stocks[0].reason_type == "机器人+业绩增长"
    assert report.top_stocks[0].reason_info == detailed_reason
    assert report.top_blocks[0].stocks == [
        "测试股份（1板）（换手 12.50%）"
    ]


def test_pool_block_summary_includes_all_stocks_with_turnover():
    engine = create_engine("sqlite://")
    LimitUpPool.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    target_date = date(2026, 7, 15)
    try:
        session.add_all(
            [
                LimitUpPool(
                    id=index,
                    date=target_date,
                    code=f"{index:06d}",
                    name=f"测试股份{index}",
                    block_name="机器人概念",
                    limit_up_time=f"09{index:02d}00",
                    turnover_rate=index,
                )
                for index in range(1, 12)
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

        blocks = notifier._aggregate_blocks_from_pool(session, target_date)
    finally:
        session.close()

    assert len(blocks[0].stocks) == 11
    assert blocks[0].stocks[0] == "测试股份1（换手 1.00%）"
    assert blocks[0].stocks[-1] == "测试股份11（换手 11.00%）"


def test_build_leader_assists_requires_shared_evidence_earlier_time_and_lower_board():
    engine = create_engine("sqlite://")
    for table in (ContinuousLimitUp.__table__, LimitUpPool.__table__, BlockTopStock.__table__):
        table.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        target_date = date(2026, 7, 15)
        session.add_all(
            [
                ContinuousLimitUp(
                    id=1, date=target_date, code="000001", name="龙头", continuous_days=4
                ),
                ContinuousLimitUp(
                    id=2, date=target_date, code="000002", name="助攻", continuous_days=2
                ),
                ContinuousLimitUp(
                    id=3, date=target_date, code="000003", name="同属性但晚", continuous_days=1
                ),
                ContinuousLimitUp(
                    id=4, date=target_date, code="000004", name="同板但同高", continuous_days=4
                ),
                LimitUpPool(
                    id=1, date=target_date, code="000001", name="龙头", limit_up_time="10:00",
                    concept="机器人+业绩增长", block_name="机器人概念",
                ),
                LimitUpPool(
                    id=2, date=target_date, code="000002", name="助攻", limit_up_time="09:35",
                    concept="机器人+订单增长", block_name="其他板块",
                ),
                LimitUpPool(
                    id=3, date=target_date, code="000003", name="同属性但晚", limit_up_time="10:05",
                    concept="机器人", block_name="其他板块",
                ),
                LimitUpPool(
                    id=4, date=target_date, code="000004", name="同板但同高", limit_up_time="09:30",
                    concept="无关", block_name="机器人概念",
                ),
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        leader = StockSummary("000001", "龙头", 4, "10:00", "机器人概念", "机器人+业绩增长")

        assists = notifier._build_leader_assists(
            session,
            target_date,
            [leader],
            session.query(LimitUpPool).all(),
        )

        assert len(assists) == 1
        assert assists[0].stock.code == "000002"
        assert assists[0].shared_reason_tags == ["机器人"]
        assert notifier._format_leader_assists(assists) == (
            "1. 龙头 龙头(000001)：4板 10:00\n"
            "   助攻：助攻(000002) 2板 09:35（同属性 机器人）"
        )
    finally:
        session.close()


def test_feishu_table_keeps_all_rows_and_pages_at_ten():
    rows = [{"stock": f"测试{i}"} for i in range(11)]

    table = FeishuStockNotifier._build_table(
        "test_table",
        [("stock", "股票", "text")],
        rows,
    )

    assert table["page_size"] == 10
    assert table["rows"] == rows


def test_feishu_charts_keep_all_blocks_and_industries():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    report = SimpleNamespace(
        limit_up_type_distribution={},
        continuous_distribution={},
        top_blocks=[
            BlockSummary(f"板块{i}", i, f"龙头{i}", None)
            for i in range(1, 11)
        ],
        eastmoney_industries=[
            IndustrySummary(f"行业{i}", i, [])
            for i in range(1, 12)
        ],
    )

    charts = {
        item["element_id"]: item
        for item in notifier._build_card_charts(report)
    }

    block_chart = charts["hot_blocks_chart"]
    industry_chart = charts["eastmoney_industry"]
    assert len(block_chart["chart_spec"]["data"]["values"]) == 10
    assert block_chart["chart_spec"]["data"]["values"][-1] == {
        "name": "板块10",
        "value": 10,
    }
    assert block_chart["chart_spec"]["title"]["text"] == "热门板块"
    assert block_chart["height"] == "360px"
    assert len(industry_chart["chart_spec"]["data"]["values"]) == 11
    assert industry_chart["chart_spec"]["data"]["values"][-1] == {
        "name": "行业11",
        "value": 11,
    }
    assert industry_chart["chart_spec"]["title"]["text"] == "东财行业涨停"
    assert industry_chart["height"] == "388px"


def test_high_turnover_high_boards_use_strict_height_and_turnover_thresholds():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    def stock(code, days, turnover):
        return StockSummary(
            code=code,
            name=f"测试{code}",
            continuous_days=days,
            limit_up_time="09:35",
            block_name="测试板块",
            reason="测试",
            turnover_rate=turnover,
        )

    elements = notifier._build_high_turnover_high_boards(
        SimpleNamespace(
            top_stocks=[
                stock("000001", 3, 10.0),
                stock("000002", 2, 20.0),
                stock("000003", 3, 10.01),
                stock("000004", 4, 12.5),
            ]
        )
    )

    assert elements[1]["rows"] == [
        {
            "days": "4板",
            "stock": "测试000004(000004)",
            "turnover": "12.50%",
            "time": "09:35",
            "reason_type": "-",
            "reason_info": "-",
        },
        {
            "days": "3板",
            "stock": "测试000003(000003)",
            "turnover": "10.01%",
            "time": "09:35",
            "reason_type": "-",
            "reason_info": "-",
        },
    ]

    empty_elements = notifier._build_high_turnover_high_boards(
        SimpleNamespace(top_stocks=[])
    )
    assert empty_elements[1] == {"tag": "markdown", "content": "- 暂无"}


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


def test_format_breakouts_groups_all_stocks_by_trading_day_window():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    content = notifier._format_breakouts(
        [
            BreakoutSummary(
                code="000006",
                name="五日突破",
                breakout_price=12.5,
                previous_high_price=11.2,
                breakout_ratio=11.607,
                previous_max_days=3,
                gap_trading_days=5,
                block_name="低空经济",
                reason="涨停突破前高",
            ),
            BreakoutSummary(
                code="000007",
                name="十日突破",
                breakout_price=13.5,
                previous_high_price=11.2,
                breakout_ratio=20.536,
                previous_max_days=2,
                gap_trading_days=6,
                block_name="商业航天",
                reason="涨停突破前高",
            ),
            BreakoutSummary(
                code="000008",
                name="三十日突破",
                breakout_price=14.5,
                previous_high_price=11.2,
                breakout_ratio=29.464,
                previous_max_days=2,
                gap_trading_days=11,
                block_name="芯片",
                reason="涨停突破前高",
            ),
            BreakoutSummary(
                code="000009",
                name="六十日突破",
                breakout_price=15.5,
                previous_high_price=11.2,
                breakout_ratio=38.393,
                previous_max_days=2,
                gap_trading_days=60,
                block_name="机器人",
                reason="涨停突破前高",
            ),
        ]
    )

    assert "5个交易日内涨停前高突破" in content
    assert "6-10个交易日内涨停前高突破" in content
    assert "11-30个交易日内涨停前高突破" in content
    assert "31-60个交易日内涨停前高突破" in content
    assert all(name in content for name in ["五日突破", "十日突破", "三十日突破", "六十日突破"])
    assert "前期3板" in content
    assert "断板5个交易日" in content
    assert "前高11.20" in content
    assert "今涨停12.50" in content
    assert "突破11.6%" in content


def test_format_breakouts_keeps_all_windows_when_there_are_no_stocks():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_breakouts([])

    assert "5个交易日内涨停前高突破" in content
    assert "6-10个交易日内涨停前高突破" in content
    assert "11-30个交易日内涨停前高突破" in content
    assert "31-60个交易日内涨停前高突破" in content
    assert content.count("- 暂无") == 4
    assert content == (
        "**5个交易日内涨停前高突破**\n\n- 暂无\n\n"
        "**6-10个交易日内涨停前高突破**\n\n- 暂无\n\n"
        "**11-30个交易日内涨停前高突破**\n\n- 暂无\n\n"
        "**31-60个交易日内涨停前高突破**\n\n- 暂无"
    )


def test_normalize_limit_up_time_accepts_ths_timestamp_and_clock_values():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    assert notifier._normalize_limit_up_time("09:31") == "09:31"
    assert notifier._normalize_limit_up_time("093000") == "09:30"
    assert notifier._normalize_limit_up_time("09:31:00") == "09:31"
    assert notifier._normalize_limit_up_time("1783563090") == "10:11"


def test_format_board_overlaps_shows_shared_count_and_coverage():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_board_overlaps(
        [
            BoardOverlapSummary(
                first_block_name="商业航天",
                second_block_name="军工",
                shared_stock_count=20,
                first_stock_count=29,
                second_stock_count=24,
            )
        ]
    )

    assert "商业航天 ∩ 军工：20 只共同涨停" in content
    assert "占前者 69%" in content
    assert "占后者 83%" in content
    assert notifier._format_board_overlaps([]) == "- 暂无显著交集数据"


def test_previous_trading_day_material_is_compact_and_compares_shared_boards():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier._get_session = lambda: SimpleNamespace(close=lambda: None)
    notifier._recent_trading_dates = lambda *_args, **_kwargs: [
        date(2026, 7, 10),
        date(2026, 7, 9),
    ]
    previous = SimpleNamespace(
        target_date=date(2026, 7, 9),
        hr_limit_up_count=80,
        em_limit_up_count=81,
        continuous_count=8,
        max_continuous_days=4,
        limit_up_type_distribution={"首板": 70, "连板": 10},
        continuous_distribution={4: 1, 2: 7},
        top_stocks=[
            StockSummary(
                code="000001",
                name="昨日龙头",
                continuous_days=4,
                limit_up_time="",
                block_name="商业航天",
                reason="",
            )
        ],
        top_blocks=[
            BlockSummary("商业航天", 20, "昨日龙头", 1.5),
            BlockSummary("军工", 10, "昨日军工", 1.0),
        ],
    )
    notifier.build_report = lambda _target_date: previous
    notifier.build_analysis_material = (
        lambda report: f"前一日完整事实：{report.target_date.isoformat()}"
    )
    notifier.build_codex_reason_material = (
        lambda report: f"前一日完整原因：{report.target_date.isoformat()}"
    )
    current = SimpleNamespace(
        target_date=date(2026, 7, 10),
        top_blocks=[
            BlockSummary("商业航天", 29, "今日龙头", 2.0),
            BlockSummary("军工", 24, "今日军工", 1.7),
        ],
    )

    content = notifier.build_previous_trading_day_material(current)

    assert "前一交易日对照（2026-07-09）" in content
    assert "同花顺 80 只" in content
    assert "核心连板：1. 4板：昨日龙头(000001)" in content
    assert "全部热点板块：商业航天 20家、军工 10家" in content
    assert "商业航天 20->29家" in content
    assert "军工 10->24家" in content
    assert "前一交易日完整事实材料（2026-07-09）" in content
    assert "前一日完整事实：2026-07-09" in content
    assert "前一日完整原因：2026-07-09" in content


def test_format_weak_boards_marks_time_based_samples_as_inferred():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)

    content = notifier._format_weak_boards(
        [
            WeakBoardSummary(
                code="000003",
                name="回封股份",
                open_count=0,
                turnover_rate=None,
                block_name="商业航天",
                reason="回封样本",
                first_limit_up_time="09:31",
                last_limit_up_time="10:12",
            )
        ]
    )

    assert "同花顺开板次数缺失" in content
    assert "首次涨停 09:31，最后涨停 10:12，间隔 41 分钟" in content


def test_codex_reason_material_includes_ths_pool_reason_fields():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    report = SimpleNamespace(
        top_blocks=[],
        pool_stock_reasons=[
            BlockStockReasonSummary(
                code="002841",
                name="视源股份",
                reason_type="中报预增+交互智能平板+AI教育+机器人",
                reason_info="公司聚焦智能交互显示与AI教育。",
            )
        ],
    )

    content = notifier.build_codex_reason_material(report)

    assert "中报预增+交互智能平板+AI教育+机器人" in content
    assert "公司聚焦智能交互显示与AI教育" in content


def test_codex_reason_material_includes_turnover_for_every_limit_up_stock():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    report = SimpleNamespace(
        top_blocks=[],
        pool_stock_reasons=[],
        limit_up_pool_metrics=[
            LimitUpPoolAnalysisSummary(
                code="000001",
                name="换手股份",
                change_percent=10.01,
                limit_up_type="换手板",
                first_limit_up_time="09:31",
                last_limit_up_time="14:20",
                open_count=2,
                turnover_rate=18.5,
            ),
            LimitUpPoolAnalysisSummary(
                code="000002",
                name="无换手字段",
                change_percent=9.99,
                limit_up_type="一字板",
                first_limit_up_time="09:25",
                last_limit_up_time="09:25",
                open_count=0,
                turnover_rate=None,
            ),
        ],
    )

    content = notifier.build_codex_reason_material(report)

    assert "同花顺全量涨停池指标（Codex分析补充）" in content
    assert "换手股份(000001)：涨幅 10.01%，换手板，首次涨停 09:31，最后涨停 14:20，开板 2 次，换手 18.50%" in content
    assert "无换手字段(000002)" in content
    assert "换手 暂无" in content


def test_ths_pool_supplies_early_strength_and_previous_high_feedback():
    engine = create_engine("sqlite://")
    for model in (ContinuousLimitUp, LimitUpPool):
        model.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add_all(
            [
                ContinuousLimitUp(
                    id=1,
                    date=date(2026, 7, 9),
                    code="000001",
                    name="昨日龙头",
                    continuous_days=3,
                ),
                ContinuousLimitUp(
                    id=2,
                    date=date(2026, 7, 10),
                    code="000001",
                    name="昨日龙头",
                    continuous_days=4,
                ),
                LimitUpPool(
                    id=1,
                    date=date(2026, 7, 10),
                    code="000001",
                    name="昨日龙头",
                    limit_up_time="093500",
                ),
                LimitUpPool(
                    id=2,
                    date=date(2026, 7, 10),
                    code="000002",
                    name="早盘股份",
                    limit_up_time="093100",
                ),
            ]
        )
        session.commit()

        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        notifier._recent_trading_dates = lambda *_args, **_kwargs: [
            date(2026, 7, 10),
            date(2026, 7, 9),
        ]
        early = notifier._build_early_stocks(session, date(2026, 7, 10))
        feedback = notifier._build_previous_high_feedback(
            session, date(2026, 7, 10)
        )
    finally:
        session.close()

    assert [item.code for item in early] == ["000002", "000001"]
    assert early[0].limit_up_time == "09:31"
    assert feedback[0].feedback == "今日晋级至 4板"


def test_early_strength_keeps_ths_first_limit_up_time_order_for_special_stocks():
    engine = create_engine("sqlite://")
    for model in (ContinuousLimitUp, LimitUpPool):
        model.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add_all(
            [
                LimitUpPool(
                    id=1,
                    date=date(2026, 7, 10),
                    code="000001",
                    name="*ST早封",
                    limit_up_time="093000",
                ),
                LimitUpPool(
                    id=2,
                    date=date(2026, 7, 10),
                    code="000002",
                    name="普通股份",
                    limit_up_time="093100",
                ),
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        early = notifier._build_early_stocks(session, date(2026, 7, 10))
    finally:
        session.close()

    assert [item.code for item in early] == ["000001", "000002"]


def test_early_strength_and_weak_boards_do_not_truncate_after_ten_items():
    engine = create_engine("sqlite://")
    for model in (ContinuousLimitUp, LimitUpPool):
        model.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add_all(
            [
                LimitUpPool(
                    id=index,
                    date=date(2026, 7, 10),
                    code=f"{index:06d}",
                    name=f"测试股份{index}",
                    limit_up_time=f"09{index:02d}00",
                    open_count=index,
                    turnover_rate=index,
                )
                for index in range(1, 12)
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        early = notifier._build_early_stocks(session, date(2026, 7, 10))
        weak = notifier._build_weak_boards(session, date(2026, 7, 10))
    finally:
        session.close()

    assert len(early) == 11
    assert len(weak) == 11


def test_board_overlaps_do_not_truncate_after_ten_pairs():
    engine = create_engine("sqlite://")
    BlockTopStock.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    target_date = date(2026, 7, 10)
    blocks = [
        BlockSummary(
            block_name=f"板块{index}",
            stock_count=3,
            leading_stock_name="共同龙头",
            change_percent=1.0,
            block_code=f"B{index}",
        )
        for index in range(11)
    ]
    try:
        session.add_all(
            [
                BlockTopStock(
                    id=index * 10 + stock_index,
                    date=target_date,
                    block_code=f"B{index}",
                    block_name=f"板块{index}",
                    code=f"00000{stock_index}",
                    name=f"共同股{stock_index}",
                )
                for index in range(11)
                for stock_index in range(1, 4)
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        overlaps = notifier._build_board_overlaps(session, target_date, blocks)
    finally:
        session.close()

    assert len(overlaps) == 55


def test_previous_trading_day_material_contains_full_prior_facts_and_reasons():
    notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
    notifier._get_session = lambda: SimpleNamespace(close=lambda: None)
    notifier._recent_trading_dates = lambda *_args, **_kwargs: [
        date(2026, 7, 10),
        date(2026, 7, 9),
    ]
    previous = FeishuStockReport(
        target_date=date(2026, 7, 9),
        is_complete=True,
        continuous_count=1,
        block_count=1,
        hr_limit_up_count=2,
        em_limit_up_count=2,
        lower_limit_count=1,
        max_continuous_days=2,
        continuous_distribution={2: 1},
        limit_up_type_distribution={"连板": 1, "首板": 1},
        data_warnings=[],
        fetch_logs=[],
        top_blocks=[
            BlockSummary(
                "商业航天",
                2,
                "昨日龙头",
                1.0,
                stock_reasons=[
                    BlockStockReasonSummary(
                        code="000001",
                        name="昨日龙头",
                        reason_type="商业航天+业绩增长",
                        reason_info="昨日详细原因",
                    )
                ],
            )
        ],
        eastmoney_industries=[],
        top_stocks=[
            StockSummary("000001", "昨日龙头", 2, "09:30", "商业航天", "商业航天")
        ],
        early_stocks=[
            StockSummary("000002", "昨日早盘", 1, "09:31", "商业航天", "早封")
        ],
        weak_boards=[],
        breakout_stocks=[],
        lower_limit_stocks=[
            LowerLimitSummary(
                code="000004",
                name="昨日跌停",
                change_percent=-10.0,
                first_limit_down_time="09:32",
                last_limit_down_time="09:32",
                turnover_rate=1.0,
                is_again_limit=False,
            )
        ],
        one_word_stocks=[
            StockSummary("000003", "昨日一字", 1, "09:25", "商业航天", "一字")
        ],
        pool_stock_reasons=[
            BlockStockReasonSummary(
                code="000002",
                name="昨日早盘",
                reason_type="AI教育",
                reason_info="昨日涨停池详细原因",
            )
        ],
    )
    notifier.build_report = lambda _target_date: previous
    current = SimpleNamespace(
        target_date=date(2026, 7, 10),
        top_blocks=[BlockSummary("商业航天", 3, "今日龙头", 2.0)],
    )

    content = notifier.build_previous_trading_day_material(current)

    assert "前一交易日完整事实材料（2026-07-09）" in content
    assert "早盘强势（同花顺首次涨停时间）" in content
    assert "昨日早盘(000002)：1板，09:31" in content
    assert "一字板明细" in content
    assert "商业航天+业绩增长" in content
    assert "昨日详细原因" in content
    assert "AI教育" in content
    assert "昨日涨停池详细原因" in content
    assert "昨日跌停(000004)" in content


def test_recent_trading_dates_uses_successful_fetch_logs_and_skips_weekends():
    engine = create_engine("sqlite://")
    DataFetchLog.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        for identifier, item in enumerate([
            date(2026, 7, 9),
            date(2026, 7, 10),
            date(2026, 7, 11),
            date(2026, 7, 13),
        ], 1):
            session.add(
                DataFetchLog(
                    id=identifier,
                    date=item,
                    data_type="limit_up_pool",
                    status="success",
                    record_count=1,
                )
            )
        session.commit()

        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        trading_dates = notifier._recent_trading_dates(
            session,
            date(2026, 7, 13),
            lookback=2,
        )
    finally:
        session.close()

    assert trading_dates == [
        date(2026, 7, 13),
        date(2026, 7, 10),
        date(2026, 7, 9),
    ]


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

    assert (
        "专用设备：测试设备（3板）（换手 -）、龙头设备（2板）（换手 -）、"
        "强势设备（1板）（换手 -）、补充设备（1板）（换手 -）"
    ) in content
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
        lower_limit_count=0,
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
        lower_limit_stocks=[],
    )

    card = notifier.build_card(report)
    elements = card["body"]["elements"]
    content = elements[0]["content"]
    tables = {element["element_id"]: element for element in elements if element["tag"] == "table"}

    assert "行业热度请看东财行业涨停" in content
    assert set(tables) == {"eastmoney_industries"}
    assert tables["eastmoney_industries"]["rows"] == [
        {"industry": "电力", "count": 8, "leaders": "宝塔实业（2板）（换手 -）"}
    ]


def test_lower_limit_pool_is_rendered_in_full_time_order():
    engine = create_engine("sqlite://")
    LowerLimitPool.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add_all(
            [
                LowerLimitPool(
                    id=1,
                    date=date(2026, 7, 9),
                    code="000002",
                    name="晚跌停",
                    change_percent=-10.0,
                    first_limit_down_time="1783565385",
                    last_limit_down_time="1783579821",
                    turnover_rate=8.2,
                ),
                LowerLimitPool(
                    id=2,
                    date=date(2026, 7, 9),
                    code="000001",
                    name="早跌停",
                    change_percent=-10.01,
                    first_limit_down_time="1783563565",
                    last_limit_down_time="1783579867",
                    turnover_rate=0.28,
                    is_again_limit=1,
                ),
            ]
        )
        session.commit()
        notifier = FeishuStockNotifier.__new__(FeishuStockNotifier)
        stocks = notifier._build_lower_limit_stocks(session, date(2026, 7, 9))
    finally:
        session.close()

    assert [item.code for item in stocks] == ["000001", "000002"]
    content = notifier._format_lower_limit_stocks(stocks)
    assert "早跌停(000001)：跌幅 -10.01%，首次跌停 10:19，最后跌停 14:51，换手 0.28%，再次跌停" in content
    assert "晚跌停(000002)" in content


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
