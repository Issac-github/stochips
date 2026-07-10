import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.ai_analyzer import AIStockAnalyzer
from chain.stock.agents.enhanced_risk_agent import EnhancedRiskAssessmentAgent
from chain.stock.config import config


def test_parse_analysis_json_normalizes_suggestion_and_clamps_numbers():
    payload = """
    模型说明：
    {
      "limit_up_reason_analysis": "封板较强",
      "concept_heat": "热点",
      "market_sentiment": "乐观",
      "fundamental_assessment": "估值偏高",
      "technical_analysis": "换手充分",
      "ai_risk_score": 140,
      "ai_suggestion": "强烈推荐",
      "confidence": 2,
      "key_factors": [{"factor": "封单", "impact": "正面", "weight": 0.5}],
      "similar_cases": "无足够数据",
      "tomorrow_prediction": "分歧加大"
    }
    """

    parsed = AIStockAnalyzer.parse_analysis_json(payload)

    assert parsed["ai_risk_score"] == 100.0
    assert parsed["confidence"] == 1.0
    assert parsed["ai_suggestion"] == "机会"


def test_parse_analysis_json_rejects_invalid_content():
    try:
        AIStockAnalyzer.parse_analysis_json("没有 json")
    except ValueError as exc:
        assert "无法解析LLM返回的JSON" in str(exc)
    else:
        raise AssertionError("invalid LLM content should be rejected")


def test_enhanced_assessment_reuses_cached_ai_result(monkeypatch):
    agent = EnhancedRiskAssessmentAgent.__new__(EnhancedRiskAssessmentAgent)
    agent.ai_analyzer = SimpleNamespace(llm=object())

    def fake_base_assessment(code, name, target_date):
        return {
            "risk_score": 50,
            "risk_factors": "[]",
            "continuous_days": 3,
            "assessment_reason": "规则结果",
        }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("cached AI assessment should skip fresh LLM call")

    monkeypatch.setattr(
        EnhancedRiskAssessmentAgent.__mro__[1],
        "assess_stock",
        lambda self, code, name, target_date: fake_base_assessment(code, name, target_date),
    )
    monkeypatch.setattr(agent.ai_analyzer, "analyze_stock", fail_if_called, raising=False)
    monkeypatch.setattr(
        agent,
        "_get_cached_ai_analysis",
        lambda code, target_date: {
            "ai_score": 30.0,
            "ai_confidence": 0.9,
            "ai_suggestion": "机会",
            "ai_analysis_report": "缓存报告",
            "ai_factors": json.dumps([{"factor": "封单", "impact": "正面"}], ensure_ascii=False),
        },
    )

    result = agent.assess_stock_enhanced(
        "000001",
        "测试股票",
        date(2026, 5, 22),
        use_ai=True,
    )

    assert result["ai_score"] == 30.0
    assert result["ai_confidence"] == 0.9
    assert result["suggestion"] == "机会"
    assert result["ai_source"] == "cached"


def test_codex_analysis_schema_contains_existing_risk_fields():
    from chain.stock.agents.codex_client import ANALYSIS_SCHEMA

    assert "ai_risk_score" in ANALYSIS_SCHEMA["required"]
    assert "ai_suggestion" in ANALYSIS_SCHEMA["required"]
    assert ANALYSIS_SCHEMA["additionalProperties"] is False


def test_codex_provider_is_available_with_sdk_configuration(monkeypatch):
    monkeypatch.setattr(config.ai, "provider", "codex")
    monkeypatch.setattr(config.ai, "codex_model", "")
    monkeypatch.setattr(config.ai, "codex_working_directory", "/tmp")

    class FakeCodexClient:
        is_available = True

    monkeypatch.setattr(
        "chain.stock.agents.ai_analyzer.CodexSubscriptionClient",
        lambda **kwargs: FakeCodexClient(),
    )

    analyzer = AIStockAnalyzer("mysql+pymysql://stock:stock123@localhost/stock_analysis")

    assert analyzer.llm is None
    assert analyzer.codex_client is not None
    assert analyzer.is_available is True


def test_codex_failure_falls_back_to_moonshot(monkeypatch):
    monkeypatch.setattr(config.ai, "provider", "codex")
    monkeypatch.setattr(config.ai, "fallback_provider", "moonshot")
    monkeypatch.setattr(config.ai, "max_retries", 0)

    class FailingCodexClient:
        def analyze(self, messages):
            raise RuntimeError("subscription limit")

    class MoonshotClient:
        def invoke(self, messages):
            return SimpleNamespace(content='{"ai_risk_score": 50}')

    analyzer = AIStockAnalyzer.__new__(AIStockAnalyzer)
    analyzer.provider = "codex"
    analyzer.codex_client = FailingCodexClient()
    analyzer.fallback_llm = MoonshotClient()
    analyzer.llm = None
    analyzer.last_provider = ""
    analyzer.last_model = ""

    result = analyzer._invoke_llm_with_retry([{"role": "user", "content": "test"}])

    assert result == '{"ai_risk_score": 50}'
    assert analyzer.last_provider == "moonshot_fallback"
    assert analyzer.last_model == config.ai.model


def test_invalid_codex_json_falls_back_to_moonshot(monkeypatch):
    monkeypatch.setattr(config.ai, "max_retries", 0)

    class MoonshotClient:
        def invoke(self, messages):
            return SimpleNamespace(
                content='{"ai_risk_score": 35, "ai_suggestion": "观望"}'
            )

    analyzer = AIStockAnalyzer.__new__(AIStockAnalyzer)
    analyzer.last_provider = "codex"
    analyzer.last_model = ""
    analyzer.fallback_llm = MoonshotClient()

    result = analyzer._parse_with_fallback(
        [{"role": "user", "content": "test"}],
        "not-json",
    )

    assert result["ai_risk_score"] == 35.0
    assert analyzer.last_provider == "moonshot_fallback"


def test_ai_report_contains_actual_provider_metadata():
    analyzer = AIStockAnalyzer.__new__(AIStockAnalyzer)

    report = analyzer._generate_report(
        {},
        provider="moonshot_fallback",
        model="moonshot-v1-8k",
    )

    assert "Agent: main" in report
    assert "Model: moonshot-v1-8k" in report
    assert "Provider: moonshot" in report
