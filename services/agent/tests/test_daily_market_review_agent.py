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
    STRATEGY_RELATIVE_PATH,
)
from chain.stock.models.database import DailyMarketReview


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


class FakeNotifier:
    def build_report(self, target_date):
        return SimpleNamespace(target_date=target_date)

    def build_analysis_material(self, report):
        return f"**涨停概览**：{report.target_date.isoformat()}，连板 6 只"

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


def test_daily_review_reads_strategy_context_and_reuses_saved_report(tmp_path):
    strategy_path = tmp_path / STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("天量弱转强是检验真龙的标准", encoding="utf-8")

    client = FakeCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{tmp_path / 'review.db'}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
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
    assert STRATEGY_RELATIVE_PATH.as_posix() in client.prompts[0]
    assert "**涨停概览**：2026-07-10，连板 6 只" in client.prompts[0]
    assert "简略原因（reason_type）：先进封装+存储芯片" in client.prompts[0]
    assert "详细原因（reason_info）：行业原因：先进封装景气度提升" in client.prompts[0]
    assert "不要沿用程序预设的评分" in client.prompts[0]

    agent.close()
    assert client.closed is True
    assert agent.codex_client is None


def test_force_daily_review_replaces_cached_content(tmp_path):
    strategy_path = tmp_path / STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")

    client = FakeCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{tmp_path / 'review.db'}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        session_factory=create_review_session(tmp_path / "review.db"),
    )
    target_date = date(2026, 7, 10)

    agent.run(target_date)
    regenerated = agent.run(target_date, force=True)

    assert regenerated.cached is False
    assert regenerated.content.endswith("测试复盘内容 2")
    assert len(client.prompts) == 2


def test_cached_review_does_not_start_codex_runtime(tmp_path, monkeypatch):
    strategy_path = tmp_path / STRATEGY_RELATIVE_PATH
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

    strategy_path = tmp_path / STRATEGY_RELATIVE_PATH
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text("交易体系", encoding="utf-8")
    database_path = tmp_path / "review.db"
    client = FailingCodexClient()
    agent = DailyMarketReviewAgent(
        f"sqlite:///{database_path}",
        codex_client=client,
        notifier=FakeNotifier(),
        project_root=tmp_path,
        session_factory=create_review_session(database_path),
    )

    with pytest.raises(RuntimeError, match="Codex unavailable"):
        agent.run(date(2026, 7, 10))

    assert client.closed is True
    assert agent.codex_client is None
