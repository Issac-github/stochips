import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.risk_agent import RiskAssessmentAgent


def test_rule_risk_score_includes_limit_up_time_factor():
    agent = RiskAssessmentAgent.__new__(RiskAssessmentAgent)

    risk_level, risk_score, factors, suggestion, reason = agent.calculate_risk_score(
        {"continuous_days": 3},
        {
            "limit_up_time": "145000",
            "strength": 3.5,
            "turnover_rate": 4,
            "open_count": 1,
        },
    )

    factor_by_name = {factor.name: factor for factor in factors}

    assert factor_by_name["连板天数风险"].weight == 0.35
    assert factor_by_name["封板时间风险"].weight == 0.15
    assert factor_by_name["封单强度"].weight == 0.20
    assert factor_by_name["换手率风险"].weight == 0.20
    assert factor_by_name["开板次数风险"].weight == 0.10
    assert factor_by_name["封板时间风险"].score == 80
    assert risk_score == 44.25
    assert risk_level.value == "中"
    assert suggestion.value == "观望"
    assert "封板时间偏晚" in reason


def test_early_limit_up_time_lowers_rule_risk_score():
    agent = RiskAssessmentAgent.__new__(RiskAssessmentAgent)

    _level, risk_score, factors, _suggestion, reason = agent.calculate_risk_score(
        {"continuous_days": 3},
        {
            "limit_up_time": "09:25:00",
            "strength": 3.5,
            "turnover_rate": 4,
            "open_count": 1,
        },
    )

    factor_by_name = {factor.name: factor for factor in factors}

    assert factor_by_name["封板时间风险"].score == 20
    assert risk_score == 35.25
    assert "早盘快速封板" in reason


def test_continuous_limit_up_time_is_used_when_pool_time_missing():
    agent = RiskAssessmentAgent.__new__(RiskAssessmentAgent)

    _level, _score, factors, _suggestion, reason = agent.calculate_risk_score(
        {"continuous_days": 5, "latest_limit_up_time": "10:15"},
        {
            "strength": 2,
            "turnover_rate": 10,
            "open_count": 0,
        },
    )

    factor_by_name = {factor.name: factor for factor in factors}

    assert factor_by_name["封板时间风险"].score == 50
    assert "盘中封板" in reason
