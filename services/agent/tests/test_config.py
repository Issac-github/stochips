import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.config import AIConfig


def test_moonshot_fallback_default_model_is_32k(monkeypatch):
    monkeypatch.delenv("MOONSHOT_MODEL", raising=False)
    monkeypatch.delenv("MOONSHOT_CONTEXT_WINDOW", raising=False)

    config = AIConfig()

    assert config.model == "kimi-k2.5"
    assert config.moonshot_context_window == 262144


def test_ai_config_reads_daily_review_strategy_path(monkeypatch):
    monkeypatch.setenv("DAILY_REVIEW_STRATEGY_PATH", "private/strategy.md")

    config = AIConfig()

    assert config.daily_review_strategy_path == "private/strategy.md"
