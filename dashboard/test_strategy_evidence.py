"""Actual bounded pool coverage, honest capability states and authenticated API."""

from copy import deepcopy
from datetime import date
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import event

from test_server import service, http_server, dashboard_auth  # noqa: F401 -- fixtures
from strategy_evidence import CATALOG, assess_concept, build_capabilities, read_coverage
from chain.stock.models.database import ContinuousLimitUp, EastmoneyZTPool

DAY = date(2026, 10, 23)


def test_coverage_is_bounded_and_distinguishes_zero_volume_from_uncollected_field(
    service,
):
    with service.sessions() as session:
        session.add_all(
            [
                ContinuousLimitUp(
                    id=2,
                    date=date(2026, 10, 22),
                    code="000001",
                    name="测试股",
                    continuous_days=2,
                    volume=0,
                    limit_up_price=0,
                ),
                ContinuousLimitUp(
                    id=3,
                    date=date(2026, 10, 26),
                    code="000001",
                    name="测试股",
                    continuous_days=4,
                    volume=999999,
                    limit_up_price=20,
                ),
                EastmoneyZTPool(
                    id=2,
                    date=date(2026, 10, 26),
                    code="000001",
                    name="测试股",
                    volume=999999,
                    latest_price=20,
                ),
            ]
        )
        session.commit()
    statements = []
    event.listen(
        service.engine,
        "before_cursor_execute",
        lambda _c, _cur, statement, _p, _ctx, _many: statements.append(statement),
    )
    coverage = {row["source"]: row for row in read_coverage(service.sessions, DAY)}
    chain = coverage["continuous_limit_up"]
    assert chain["rows"] == 2
    assert chain["dates"] == 2
    assert chain["stocks"] == 1
    assert chain["first_date"] == "2026-10-22"
    assert chain["last_date"] == "2026-10-23"
    assert chain["positive_price_rows"] == 0
    assert chain["positive_volume_rows"] == 0
    assert coverage["limit_up_pool"]["positive_volume_rows"] is None
    assert coverage["eastmoney_zt_pool"]["positive_volume_rows"] == 0
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )


def test_pool_volume_never_becomes_complete_daily_history_or_confirmed_platform(
    service,
):
    with service.sessions() as session:
        row = session.get(EastmoneyZTPool, 1)
        row.volume, row.latest_price = 10000, 12
        session.commit()
    result = service.strategy_evidence(DAY)
    concepts = {item["key"]: item for item in result["concepts"]}
    assert len(concepts) == len(CATALOG["concepts"])
    small = concepts["small_platform"]
    requirements = {item["key"]: item for item in small["requirements"]}
    assert requirements["volume"]["state"] == "partial"
    assert requirements["prices"]["state"] == "partial"
    assert requirements["daily_bars"]["state"] == "not_integrated"
    assert small["status"] == "data_gap"
    assert "未实现" in small["explanation"]
    assert small["stock_count"] == 1  # related core stock, not a pattern match
    assert concepts["mainline_ladder"]["status"] == "facts_available"
    assert concepts["core_leader"]["status"] == "candidate"
    assert concepts["risk_review"]["status"] == "manual"
    assert concepts["auction_demand"]["requirements"][0]["state"] == "not_integrated"


def test_missing_volume_is_measured_not_a_static_catalog_claim(service):
    report = service.report(DAY)["report"]
    coverage = read_coverage(service.sessions, DAY)
    capabilities = build_capabilities(report, coverage)
    assert capabilities["volume"]["state"] == "missing"
    assert "0 条正成交量" in capabilities["volume"]["detail"]
    concept = next(
        item for item in CATALOG["concepts"] if item["key"] == "one_word_assist"
    )
    absent = assess_concept(concept, report, capabilities)
    assert absent["status"] == "no_observations"
    changed = deepcopy(report)
    changed["leader_assists"] = [
        {"stock": {"code": "000002"}, "leader": {"code": "000001"}}
    ] * 2
    candidate = assess_concept(concept, changed, capabilities)
    assert candidate["status"] == "candidate"
    assert candidate["stock_count"] == 1
    assert candidate["source_counts"][0]["rows"] == 2


def test_even_available_inputs_do_not_claim_an_unimplemented_pattern_matches(service):
    report = service.report(DAY)["report"]
    capabilities = build_capabilities(report, read_coverage(service.sessions, DAY))
    for requirement in capabilities.values():
        requirement["state"] = "available"
    pattern = next(
        item for item in CATALOG["concepts"] if item["key"] == "small_platform"
    )
    assert assess_concept(pattern, report, capabilities)["status"] == "not_implemented"


def test_evidence_api_requires_login_validates_dates_and_returns_no_store(
    http_server, service, monkeypatch
):
    base, sid = http_server
    path = "/api/strategy-evidence"
    with urlopen(
        Request(
            f"{base}{path}?date=2026-10-23",
            headers={"Cookie": f"stochips_session={sid}"},
        )
    ) as response:
        result = json.load(response)
        assert result["date"] == "2026-10-23"
        assert len(result["concepts"]) == 16
        assert response.headers["Cache-Control"] == "no-store"
    for query, status in [
        ("", 400),
        ("?date=", 400),
        ("?date=invalid", 400),
        ("?date=2026-02-30", 400),
        ("?date=2026-10-23&date=2026-10-22", 400),
        ("?date=2026-10-21", 404),
    ]:
        with pytest.raises(HTTPError) as error:
            urlopen(
                Request(
                    f"{base}{path}{query}",
                    headers={"Cookie": f"stochips_session={sid}"},
                )
            )
        assert error.value.code == status

    def fail(*_args):
        raise AssertionError("must authenticate before querying")

    monkeypatch.setattr(service, "strategy_evidence", fail)
    with pytest.raises(HTTPError) as error:
        urlopen(f"{base}{path}?date=2026-10-23")
    assert error.value.code == 401


def test_evidence_query_failure_returns_generic_error(
    http_server, service, monkeypatch
):
    base, sid = http_server

    def fail(*_args):
        raise RuntimeError("mysql://private:secret@database")

    monkeypatch.setattr(service, "strategy_evidence", fail)
    with pytest.raises(HTTPError) as error:
        urlopen(
            Request(
                f"{base}/api/strategy-evidence?date=2026-10-23",
                headers={"Cookie": f"stochips_session={sid}"},
            )
        )
    assert error.value.code == 503
    assert "secret" not in error.value.read().decode()
