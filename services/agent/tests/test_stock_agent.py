import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.stock_agent import StockAgent


def test_daily_review_goal_plans_codex_review_without_rule_score():
    agent = StockAgent.__new__(StockAgent)
    observation = {
        "data_status": {"is_complete": True},
        "review_status": {"available": False},
        "market_snapshot": {},
    }

    plan = agent.plan(
        "更新数据并完成每日市场复盘",
        observation,
        auto_fetch=False,
        use_ai=True,
    )

    tools = [step.tool for step in plan]
    assert "run_daily_market_review" in tools
    assert "run_rule_risk_assessment" not in tools
    assert "run_enhanced_risk_assessment" not in tools
    review_step = next(step for step in plan if step.tool == "run_daily_market_review")
    assert review_step.params["force"] is True


def test_daily_review_runtime_is_created_lazily_and_reused(monkeypatch):
    class FakeResult:
        def to_dict(self):
            return {"cached": False}

    class FakeReviewAgent:
        def __init__(self):
            self.run_count = 0
            self.closed = False

        def run(self, target_date, *, force=False):
            del target_date
            del force
            self.run_count += 1
            return FakeResult()

        def close(self):
            self.closed = True

    fake_review_agent = FakeReviewAgent()
    create_calls = []

    def fake_create(database_url):
        create_calls.append(database_url)
        return fake_review_agent

    monkeypatch.setattr(
        "chain.stock.agents.stock_agent.create_daily_market_review_agent",
        fake_create,
    )
    agent = StockAgent.__new__(StockAgent)
    agent.database_url = "sqlite://"
    agent.daily_review_agent = None

    first = agent.run_daily_market_review(date(2026, 7, 10))
    second = agent.run_daily_market_review(date(2026, 7, 11))

    assert first == {"cached": False}
    assert second == {"cached": False}
    assert create_calls == ["sqlite://"]
    assert fake_review_agent.run_count == 2

    agent.close()
    assert fake_review_agent.closed is True
    assert agent.daily_review_agent is None
