"""Exercise the read-only API using isolated SQLite and HTTP fixtures."""

from datetime import date
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen

import pytest
from sqlalchemy import event
from sqlalchemy.schema import CreateTable

sys.path.insert(0, str(Path(__file__).parent))
from server import DashboardHandler, ReportService
from auth import AuthConfig, FeishuAuth
from watchlist import WatchlistService, WatchlistStore
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


@pytest.fixture
def service(tmp_path):
    service = ReportService(f"sqlite:///{tmp_path / 'reports.db'}")
    for model in (
        BlockTop,
        BlockTopStock,
        ContinuousLimitUp,
        DailyMarketReview,
        DataFetchLog,
        EastmoneyZTPool,
        LimitUpPool,
        LowerLimitPool,
    ):
        with service.engine.begin() as connection:
            connection.execute(CreateTable(model.__table__))
    with service.sessions() as session:
        session.add_all(
            [
                LimitUpPool(
                    id=1,
                    date=date(2026, 10, 23),
                    code="000001",
                    name="测试股",
                    limit_up_type="首板",
                    turnover_rate=12.5,
                    concept="测试概念",
                ),
                ContinuousLimitUp(
                    id=1,
                    date=date(2026, 10, 23),
                    code="000001",
                    name="测试股",
                    continuous_days=3,
                    latest_limit_up_time="09:35",
                ),
                BlockTop(
                    id=1,
                    date=date(2026, 10, 23),
                    block_code="885001",
                    block_name="测试概念",
                    stock_count=1,
                    leading_stock_name="测试股",
                    change_percent=3.2,
                ),
                BlockTopStock(
                    id=1,
                    date=date(2026, 10, 23),
                    block_code="885001",
                    block_name="测试概念",
                    code="000001",
                    name="测试股",
                    reason_type="测试属性",
                    reason_info="测试原因详情",
                ),
                EastmoneyZTPool(
                    id=1,
                    date=date(2026, 10, 23),
                    code="000001",
                    name="测试股",
                    block_name="测试行业",
                    turnover_rate=12.5,
                ),
                DataFetchLog(
                    id=1,
                    date=date(2026, 10, 22),
                    data_type="limit_up_pool",
                    status="failed",
                    record_count=0,
                    error_message="测试失败",
                ),
                DailyMarketReview(
                    date=date(2026, 10, 23),
                    content="## 测试复盘\n完整分析",
                    provider="codex",
                    model="test-model",
                    strategy_path="test.md",
                    source_material_digest="a" * 64,
                ),
            ]
        )
        session.commit()
    yield service
    service.engine.dispose()


def test_report_reads_real_models_without_any_writes(service):
    statements = []
    event.listen(
        service.engine,
        "before_cursor_execute",
        lambda _c, _cur, statement, _p, _ctx, _many: statements.append(statement),
    )
    assert service.dates() == ["2026-10-23", "2026-10-22"]
    result = service.report(date(2026, 10, 23))
    assert result["report"]["hr_limit_up_count"] == 1
    assert result["report"]["daily_review"]["content"] == "## 测试复盘\n完整分析"
    assert result["report"]["limit_up_pool_metrics"][0]["turnover_rate"] == 12.5
    assert "测试股" in result["material"] or "测试股" in result["reason_material"]
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    partial = service.report(date(2026, 10, 22))
    assert partial["report"]["is_complete"] is False
    assert partial["report"]["daily_review"] is None
    with pytest.raises(LookupError):
        service.report(date(2026, 10, 21))


@pytest.fixture
def dashboard_auth():
    auth = FeishuAuth(AuthConfig(app_id="test", app_secret="secret"))
    sid = "test-session"
    auth.sessions[__import__("hashlib").sha256(sid.encode()).hexdigest()] = {
        "user": {"open_id": "test", "name": "Test", "tenant_key": "tenant"},
        "csrf_token": "csrf",
        "expires_at": auth.clock() + 3600,
    }
    return auth


@pytest.fixture
def http_server(service, tmp_path, dashboard_auth):
    (tmp_path / "index.html").write_text("<html>Dashboard</html>")
    watchlist = WatchlistService(
        service, WatchlistStore(tmp_path / "observations.sqlite3")
    )
    handler = partial(
        DashboardHandler,
        service=service,
        auth=dashboard_auth,
        watchlist=watchlist,
        directory=str(tmp_path),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", "test-session"
    server.shutdown()
    server.server_close()
    thread.join()


def test_http_contract_and_static_root(http_server):
    base, sid = http_server
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    opener.addheaders = [("Cookie", f"stochips_session={sid}")]
    with opener.open(f"{base}/api/report?date=2026-10-23") as response:
        payload = json.load(response)
        assert payload["report"]["target_date"] == "2026-10-23"
        assert response.headers["Cache-Control"] == "no-store"
    with urlopen(f"{base}/") as response:
        assert b"Dashboard" in response.read()
    for path, status in [
        ("/api/report", 400),
        ("/api/report?date=invalid", 400),
        ("/api/report?date=2026-02-30", 400),
        ("/api/report?date=2026-10-21", 404),
        ("/api/unknown", 404),
        ("/../server.py", 404),
        ("/api/report?date=2026-10-23&date=2026-10-22", 400),
    ]:
        with pytest.raises(HTTPError) as error:
            opener.open(f"{base}{path}")
        assert error.value.code == status


def test_database_failure_hides_credentials(http_server, service, monkeypatch):
    base, sid = http_server

    def fail():
        raise RuntimeError("mysql://username:secret@private-db")

    monkeypatch.setattr(service, "dates", fail)
    with pytest.raises(HTTPError) as error:
        opener = build_opener()
        opener.addheaders = [("Cookie", f"stochips_session={sid}")]
        opener.open(f"{base}/api/dates")
    assert error.value.code == 503
    assert "secret" not in error.value.read().decode()


def test_unauthenticated_report_is_rejected_before_database_query(
    http_server, service, monkeypatch
):
    base, _sid = http_server

    def fail():
        raise AssertionError("database must not be queried before authentication")

    monkeypatch.setattr(service, "dates", fail)
    with pytest.raises(HTTPError) as error:
        urlopen(f"{base}/api/dates")
    assert error.value.code == 401


def test_auth_routes_report_status_and_protect_logout(http_server):
    base, sid = http_server
    opener = build_opener()
    # A direct request with redirect handling disabled exposes the OAuth start contract.
    from urllib.request import HTTPRedirectHandler

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None

    no_redirect = build_opener(NoRedirect())
    with pytest.raises(HTTPError) as login:
        no_redirect.open(f"{base}/api/auth/feishu/login")
    assert login.value.code == 302
    assert (
        "accounts.feishu.cn/open-apis/authen/v1/authorize"
        in login.value.headers["Location"]
    )
    assert "stochips_oauth=" in login.value.headers["Set-Cookie"]

    request = Request(
        f"{base}/api/auth/logout",
        method="POST",
        headers={
            "Cookie": f"stochips_session={sid}",
            "Origin": "http://127.0.0.1:8787",
            "X-CSRF-Token": "csrf",
        },
    )
    with opener.open(request) as response:
        assert response.status == 204
        assert "Max-Age=0" in response.headers["Set-Cookie"]
