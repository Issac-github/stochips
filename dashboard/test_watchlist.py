"""Observation provenance, persistence, isolation and write-boundary regression tests."""

from copy import deepcopy
from datetime import date
import hashlib
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import event

from test_server import (
    service,
    http_server,
    dashboard_auth,
)  # noqa: F401 -- shared fixtures
from watchlist import (
    WatchlistService,
    WatchlistStore,
    WatchlistError,
    build_candidates,
    validate_update,
    owner_key,
)
from chain.stock.models.database import (
    ContinuousLimitUp,
    DataFetchLog,
    LimitUpPool,
    LowerLimitPool,
)

USER = {"tenant_key": "tenant", "open_id": "one"}
DAY = date(2026, 10, 23)


def facts():
    stock = {
        "code": "000001",
        "name": "观察股",
        "continuous_days": 3,
        "limit_up_time": "09:35",
        "turnover_rate": 0,
    }
    return {
        "top_stocks": [stock],
        "leader_assists": [
            {
                "leader": {"code": "000002", "name": "关联高标"},
                "stock": stock,
                "shared_reason_tags": ["同属性"],
                "shared_blocks": ["同板块"],
                "board_type": "非一字",
            }
        ],
        "breakout_stocks": [
            {
                "code": "000001",
                "name": "观察股",
                "breakout_price": 10,
                "previous_high_price": 10,
                "gap_trading_days": 4,
            }
        ],
        "data_warnings": [],
    }


class FakeReports:
    def __init__(self):
        self.facts = facts()

    def report(self, _day):
        if self.facts is None:
            raise LookupError()
        return {"report": deepcopy(self.facts)}

    def watchlist_feedback(self, _day, _codes):
        return {"date": None, "stocks": {}}


def update(**changes):
    return {
        "date": DAY.isoformat(),
        "code": "000001",
        "status": "watching",
        "outcome": "pending",
        "note": "竞价待验证",
        "revision": 0,
        **changes,
    }


def test_candidate_merge_preserves_all_evidence_zero_and_raw_facts():
    result = build_candidates(facts())
    assert list(result) == ["000001"]
    item = result["000001"]
    assert item["roles"] == ["核心连板", "助攻候选", "前高观察"]
    assert len(item["evidence"]) == 3
    assert item["evidence"][0]["fact"]["turnover_rate"] == 0
    assert "换手 0%" in item["evidence"][0]["detail"]
    assert "因果" in item["risks"][1]
    assert item["checks"]
    source = facts()
    source["top_stocks"].append({"code": "invalid", "name": "无效股"})
    assert list(build_candidates(source)) == ["000001"]


def test_annotations_persist_isolate_users_dates_and_keep_missing_source_snapshot(
    tmp_path,
):
    reports = FakeReports()
    path = tmp_path / "notes.sqlite3"
    watchlist = WatchlistService(reports, WatchlistStore(path))
    assert watchlist.read(DAY, USER)["items"][0]["annotation"]["revision"] == 0
    saved = watchlist.save(update(), USER)["annotation"]
    assert saved["revision"] == 1
    assert watchlist.dates(USER) == ["2026-10-23"]
    assert watchlist.dates({**USER, "open_id": "two"}) == []
    restarted = WatchlistService(reports, WatchlistStore(path))
    assert restarted.read(DAY, USER)["items"][0]["annotation"]["note"] == "竞价待验证"
    for other_user in ({**USER, "open_id": "two"}, {**USER, "tenant_key": "other"}):
        assert (
            restarted.read(DAY, other_user)["items"][0]["annotation"]["revision"] == 0
        )
    assert (
        restarted.read(date(2026, 10, 24), USER)["items"][0]["annotation"]["revision"]
        == 0
    )
    # Changed and then missing sources do not rewrite an observation's premise.
    reports.facts["top_stocks"][0]["name"] = "来源变更"
    assert restarted.read(DAY, USER)["items"][0]["name"] == "观察股"
    reports.facts = {
        "top_stocks": [],
        "leader_assists": [],
        "breakout_stocks": [],
        "data_warnings": [],
    }
    item = restarted.read(DAY, USER)["items"][0]
    assert item["source_missing"] is True
    assert len(item["evidence"]) == 3
    assert (
        restarted.save(update(status="excluded", outcome="not_met", revision=1), USER)[
            "annotation"
        ]["revision"]
        == 2
    )
    assert (
        restarted.save(update(status="watching", revision=2), USER)["annotation"][
            "status"
        ]
        == "watching"
    )
    reports.facts = None
    assert restarted.read(DAY, USER)["items"][0]["source_missing"] is True
    with pytest.raises(LookupError):
        restarted.read(DAY, {**USER, "open_id": "two"})


def test_stale_revision_conflict_does_not_overwrite_and_unknown_stock_is_rejected(
    tmp_path,
):
    watchlist = WatchlistService(
        FakeReports(), WatchlistStore(tmp_path / "notes.sqlite3")
    )
    watchlist.save(update(note="第一页面"), USER)
    with pytest.raises(WatchlistError) as error:
        watchlist.save(update(note="第二页面"), USER)
    assert error.value.status == 409
    assert watchlist.read(DAY, USER)["items"][0]["annotation"]["note"] == "第一页面"
    with pytest.raises(WatchlistError) as error:
        watchlist.save(update(code="999999"), USER)
    assert error.value.status == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"date": "2026-02-30"},
        {"date": "20261023"},
        {"code": "x"},
        {"status": []},
        {"status": "buy"},
        {"outcome": "profit"},
        {"revision": True},
        {"revision": -1},
        {"note": "x" * 2001},
        {"note": None},
        {"owner": "someone"},
    ],
)
def test_strict_validation(changes):
    with pytest.raises(ValueError):
        validate_update(update(**changes))


def test_feedback_uses_first_available_later_date_and_preserves_unknown_absence(
    service,
):
    with service.sessions() as session:
        session.add_all(
            [
                # Weekend and missing days do not get invented; earliest real record is Monday.
                LimitUpPool(
                    id=2, date=date(2026, 10, 26), code="000001", name="测试股"
                ),
                ContinuousLimitUp(
                    id=2,
                    date=date(2026, 10, 26),
                    code="000001",
                    name="测试股",
                    continuous_days=4,
                ),
                DataFetchLog(
                    id=2,
                    date=date(2026, 10, 26),
                    data_type="lower_limit_pool",
                    status="success",
                    record_count=0,
                ),
                LowerLimitPool(
                    id=1, date=date(2026, 10, 27), code="000001", name="测试股"
                ),
            ]
        )
        session.commit()
    result = service.watchlist_feedback(DAY, ["000001", "000002"])
    assert result["date"] == "2026-10-26"
    assert result["stocks"]["000001"] == {
        "limit_up": True,
        "limit_down": False,
        "continuous_days": 4,
    }
    assert (
        result["stocks"]["000002"]["limit_up"] is None
    )  # no successful full-source fetch
    assert (
        result["stocks"]["000002"]["limit_down"] is False
    )  # confirmed zero-row success
    assert service.watchlist_feedback(date(2026, 10, 27), ["000001"])["date"] is None


def request_pool(base, sid, payload=None, **headers):
    request_headers = {
        "Cookie": f"stochips_session={sid}",
        "Origin": "http://127.0.0.1:8787",
        "X-CSRF-Token": "csrf",
        "Content-Type": "application/json",
        **headers,
    }
    return urlopen(
        Request(
            f"{base}/api/watchlist" + ("?date=2026-10-23" if payload is None else ""),
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=request_headers,
        )
    )


def test_http_roundtrip_identity_csrf_conflicts_and_market_stays_readonly(
    http_server, service, dashboard_auth
):
    base, sid = http_server
    statements = []
    event.listen(
        service.engine,
        "before_cursor_execute",
        lambda _c, _cur, statement, _p, _ctx, _many: statements.append(statement),
    )
    with request_pool(base, sid) as response:
        assert json.load(response)["items"][0]["code"] == "000001"
    with request_pool(
        base, sid, update(outcome="continue", note="人工继续核对")
    ) as response:
        assert json.load(response)["annotation"]["revision"] == 1
    with request_pool(base, sid) as response:
        assert json.load(response)["items"][0]["annotation"]["outcome"] == "continue"
    dashboard_auth.sessions[hashlib.sha256(b"other-session").hexdigest()] = {
        "user": {**USER, "open_id": "other"},
        "csrf_token": "csrf",
        "expires_at": dashboard_auth.clock() + 3600,
    }
    with request_pool(base, "other-session") as response:
        assert json.load(response)["items"][0]["annotation"]["revision"] == 0
    for payload, headers, status in [
        (update(), {}, 409),
        (update(revision=1), {"Origin": "https://evil.example"}, 403),
        (update(revision=1), {"X-CSRF-Token": "wrong"}, 403),
        (update(revision=1), {"Content-Type": "text/plain"}, 415),
        (update(revision=1, owner="other"), {}, 400),
        (update(code="999999"), {}, 404),
        (update(note="x" * 20000), {}, 413),
    ]:
        with pytest.raises(HTTPError) as error:
            request_pool(base, sid, payload, **headers)
        assert error.value.code == status
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )


def test_http_unauthenticated_rejected_before_read_or_save(
    http_server, service, monkeypatch
):
    base, _sid = http_server

    def fail(*_args):
        raise AssertionError("must authenticate first")

    monkeypatch.setattr(service, "report", fail)
    for payload in (None, update()):
        with pytest.raises(HTTPError) as error:
            request_pool(base, "invalid", payload)
        assert error.value.code == 401


def test_saved_dates_and_snapshots_remain_accessible_after_market_day_disappears(
    http_server, tmp_path, dashboard_auth
):
    base, sid = http_server
    store = WatchlistStore(tmp_path / "observations.sqlite3")
    user = next(iter(dashboard_auth.sessions.values()))["user"]
    candidate = build_candidates(facts())["000001"]
    store.save(owner_key(user), "2026-10-21", candidate, update(date="2026-10-21"))
    with urlopen(
        Request(f"{base}/api/dates", headers={"Cookie": f"stochips_session={sid}"})
    ) as response:
        assert json.load(response)["dates"] == [
            "2026-10-23",
            "2026-10-22",
            "2026-10-21",
        ]
    with urlopen(
        Request(
            f"{base}/api/watchlist?date=2026-10-21",
            headers={"Cookie": f"stochips_session={sid}"},
        )
    ) as response:
        result = json.load(response)
        assert result["items"][0]["source_missing"] is True
        assert result["items"][0]["annotation"]["status"] == "watching"
        assert "快照" in result["warnings"][0]
