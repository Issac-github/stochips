import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.ai_analyzer import AIStockAnalyzer
from chain.stock.agents.enhanced_risk_agent import EnhancedRiskAssessmentAgent


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
