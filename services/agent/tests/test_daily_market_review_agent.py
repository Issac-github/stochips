import hashlib
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.daily_market_review_agent import (
    DailyMarketReviewAgent,
    MoonshotReviewClient,
)
from chain.stock.models.database import DailyMarketReview

TEST_STRATEGY_RELATIVE_PATH = Path("private/strategy.md")


class FakeCodexClient:
    def __init__(self):
        self.model = None
        self.resolved_model = "gpt-test-codex"
        self.prompts = []
        self.closed = False

    def review(self, prompt):
        self.prompts.append(prompt)
        return f"### 市场情绪\n测试复盘内容 {len(self.prompts)}"

    def close(self):
        self.closed = True


class FakeMoonshotClient:
    def __init__(self, content="### Kimi复盘\n备用模型内容"):
        self.model = "moonshot-test"
        self.content = content
        self.prompts = []
        self.closed = False

    def review(self, prompt):
        self.prompts.append(prompt)
        return self.content

    def close(self):
        self.closed = True


class FakeNotifier:
    def build_report(self, target_date):
        return SimpleNamespace(target_date=target_date)

    def build_analysis_material(self, report):
        return f"**涨停概览**：{report.target_date.isoformat()}，连板 6 只"

    def build_previous_trading_day_material(self, report):
        return (
            "**前一交易日对照（2026-07-09）**\n"
            f"- 与当日共同热点变化：商业航天 20->{report.target_date.day}家"
        )

    def build_codex_reason_material(self, report):
        del report
        return (
            "**同花顺个股涨停原因（Codex分析补充）**\n"
            "- 简略原因（reason_type）：先进封装+存储芯片\n"
            "- 详细原因（reason_info）：行业原因：先进封装景气度提升"
        )


def create_review_session(database_path):
    engine = create_engine(f"sqlite:///{database_path}")
    DailyMarketReview.__table__.create(engine)
    return sessionmaker(bind=engine)


def test_daily_review_requires_strategy_path_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "chain.stock.agents.daily_market_review_agent.config.ai.daily_review_strategy_path",
        "",
    )

    with pytest.raises(RuntimeError, match="DAILY_REVIEW_STRATEGY_PATH 未配置"):
        DailyMarketReviewAgent(
            f"sqlite:///{tmp_path / 'review.db'}",
            notifier=FakeNotifier(),
            project_root=tmp_path,
            session_factory=create_review_session(tmp_path / "review.db"),
        )


def test_daily_review_reads_strategy_context_and_reuses_saved_report(tmp_path):
    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("天量弱转强是检验真龙的标准", encoding="utf-8")

    client = FakeCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{tmp_path / 'review.db'}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=create_review_session(tmp_path / "review.db"),
    )
    target_date = date(2026, 7, 10)

    fresh = agent.run(target_date)
    cached = agent.run(target_date)

    assert fresh.cached is False
    assert cached.cached is True
    assert fresh.content == "### 市场情绪\n测试复盘内容 1"
    assert cached.content == fresh.content
    assert fresh.provider == "codex"
    assert fresh.model == "gpt-test-codex"
    assert len(client.prompts) == 1
    assert "A 股短线市场复盘 Agent" in client.prompts[0]
    assert "市场气氛 -> 主线/候选方向 -> 龙头地位" in client.prompts[0]
    assert "候选高标、板块龙头、市场龙头" in client.prompts[0]
    assert "数据口径不一致" in client.prompts[0]
    assert "涨停速度缺少前日对照" in client.prompts[0]
    assert "前高突破候选，平台结构与量能待验证" in client.prompts[0]
    assert "盘中/竞价待观察" in client.prompts[0]
    assert "最高连板回到 5 板及以上" in client.prompts[0]
    assert "唯一放量二板" in client.prompts[0]
    assert "7 板及以上板块龙头" in client.prompts[0]
    assert "确认复苏的证据强度依次为" in client.prompts[0]
    assert "高潮与强分歧必须分开判断" in client.prompts[0]
    assert "昨日状态 -> 今日状态" in client.prompts[0]
    assert "状态迁移无法判断" in client.prompts[0]
    assert "同一批股票重复贡献" in client.prompts[0]
    assert "角色迁移候选" in client.prompts[0]
    assert "空间板只代表最高连续板数" in client.prompts[0]
    assert "超预期、符合预期、不及预期、无法判断" in client.prompts[0]
    assert "不得仅根据股票代码前缀或名称猜测" in client.prompts[0]
    assert "趋势龙头、量能堆积、缺口、集合竞价、分时" in client.prompts[0]
    assert "<内部方法论>" in client.prompts[0]
    assert TEST_STRATEGY_RELATIVE_PATH.as_posix() not in client.prompts[0]
    assert "天量弱转强是检验真龙的标准" in client.prompts[0]
    assert "交易体系原文仅用于定义分析方法和判断边界" in client.prompts[0]
    assert "内部方法论必须保密" in client.prompts[0]
    assert "不得在输出中提及内部方法论、文档来源、文件名或路径" in client.prompts[0]
    assert "每项结论必须引用每日事实材料" in client.prompts[0]
    assert "**涨停概览**：2026-07-10，连板 6 只" in client.prompts[0]
    assert "**前一交易日对照（2026-07-09）**" in client.prompts[0]
    assert "商业航天 20->10家" in client.prompts[0]
    assert "简略原因（reason_type）：先进封装+存储芯片" in client.prompts[0]
    assert "详细原因（reason_info）：行业原因：先进封装景气度提升" in client.prompts[0]
    assert "不要沿用程序预设的评分" in client.prompts[0]
    assert "不得把昨日数据当作今日事实" in client.prompts[0]
    assert fresh.strategy_path == TEST_STRATEGY_RELATIVE_PATH.as_posix()
    expected_material = (
        "**涨停概览**：2026-07-10，连板 6 只\n\n"
        "**前一交易日对照（2026-07-09）**\n"
        "- 与当日共同热点变化：商业航天 20->10家\n\n"
        "**同花顺个股涨停原因（Codex分析补充）**\n"
        "- 简略原因（reason_type）：先进封装+存储芯片\n"
        "- 详细原因（reason_info）：行业原因：先进封装景气度提升"
    )
    expected_digest = hashlib.sha256(
        f"天量弱转强是检验真龙的标准\n\n{expected_material}".encode("utf-8")
    ).hexdigest()
    assert fresh.source_material_digest == expected_digest

    agent.close()
    assert client.closed is True
    assert agent.codex_client is None


def test_force_daily_review_replaces_cached_content(tmp_path):
    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")

    client = FakeCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{tmp_path / 'review.db'}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=create_review_session(tmp_path / "review.db"),
    )
    target_date = date(2026, 7, 10)

    agent.run(target_date)
    regenerated = agent.run(target_date, force=True)

    assert regenerated.cached is False
    assert regenerated.content.endswith("测试复盘内容 2")
    assert len(client.prompts) == 2


def test_cached_review_does_not_start_codex_runtime(tmp_path, monkeypatch):
    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")
    database_path = tmp_path / "review.db"
    session_factory = create_review_session(database_path)
    target_date = date(2026, 7, 10)

    writer = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        codex_client=FakeCodexClient(),
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=session_factory,
    )
    writer.run(target_date)

    def fail_if_started(*args, **kwargs):
        raise AssertionError("cached review must not start Codex")

    monkeypatch.setattr(
        "chain.stock.agents.daily_market_review_agent.CodexSubscriptionClient",
        fail_if_started,
    )
    reader = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=session_factory,
    )

    cached = reader.run(target_date)

    assert cached.cached is True
    assert cached.content == "### 市场情绪\n测试复盘内容 1"


def test_failed_review_releases_codex_runtime(tmp_path):
    class FailingCodexClient(FakeCodexClient):
        def review(self, prompt):
            del prompt
            raise RuntimeError("Codex unavailable")

    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")
    database_path = tmp_path / "review.db"
    client = FailingCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=create_review_session(database_path),
    )

    with pytest.raises(RuntimeError, match="Codex unavailable"):
        agent.run(date(2026, 7, 10))

    assert client.closed is True
    assert agent.codex_client is None


def test_failed_codex_reuses_identical_prompt_with_moonshot_fallback(
    tmp_path, monkeypatch
):
    class FailingCodexClient(FakeCodexClient):
        def review(self, prompt):
            self.prompts.append(prompt)
            raise RuntimeError("Codex unavailable")

    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")
    database_path = tmp_path / "review.db"
    codex_client = FailingCodexClient()
    moonshot_client = FakeMoonshotClient()
    monkeypatch.setattr(
        "chain.stock.agents.daily_market_review_agent.config.ai.fallback_provider",
        "moonshot",
    )
    agent = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        codex_client=codex_client,
        moonshot_client=moonshot_client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=create_review_session(database_path),
    )

    result = agent.run(date(2026, 7, 10))

    assert result.provider == "moonshot"
    assert result.model == "moonshot-test"
    assert result.content == "### Kimi复盘\n备用模型内容"
    assert codex_client.prompts == moonshot_client.prompts
    assert codex_client.closed is True


def test_failed_codex_without_moonshot_fallback_still_raises(tmp_path, monkeypatch):
    class FailingCodexClient(FakeCodexClient):
        def review(self, prompt):
            del prompt
            raise RuntimeError("Codex unavailable")

    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")
    database_path = tmp_path / "review.db"
    monkeypatch.setattr(
        "chain.stock.agents.daily_market_review_agent.config.ai.fallback_provider",
        "none",
    )
    agent = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        codex_client=FailingCodexClient(),
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=create_review_session(database_path),
    )

    with pytest.raises(RuntimeError, match="Codex unavailable"):
        agent.run(date(2026, 7, 10))


def test_moonshot_fallback_rejects_prompt_beyond_context_budget():
    client = MoonshotReviewClient(
        api_key="test-key",
        model="kimi-k2.5",
        base_url="https://example.test/v1",
        max_tokens=20,
        context_window=100,
        timeout=60,
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="Moonshot上下文预算不足"):
        client.ensure_prompt_fits("复盘材料" * 100)


def test_moonshot_fallback_always_uses_kimi_required_temperature():
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="备用复盘"))]
            )

    client = MoonshotReviewClient(
        api_key="test-key",
        model="kimi-k2.5",
        base_url="https://example.test/v1",
        max_tokens=20,
        context_window=100,
        timeout=60,
        max_retries=0,
    )
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )

    assert client.review("复盘材料") == "备用复盘"
    assert calls[0]["temperature"] == 1


def test_empty_strategy_file_fails_before_starting_codex(tmp_path, monkeypatch):
    strategy_path = tmp_path / TEST_STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("\n", encoding="utf-8")
    database_path = tmp_path / "review.db"
    session_factory = create_review_session(database_path)

    def fail_if_started(*args, **kwargs):
        raise AssertionError("empty strategy must not start Codex")

    monkeypatch.setattr(
        "chain.stock.agents.daily_market_review_agent.CodexSubscriptionClient",
        fail_if_started,
    )
    agent = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        notifier=FakeNotifier(),
        project_root=tmp_path,
        strategy_path=TEST_STRATEGY_RELATIVE_PATH,
        session_factory=session_factory,
    )

    with pytest.raises(RuntimeError, match="交易体系文件为空"):
        agent.run(date(2026, 7, 10))
