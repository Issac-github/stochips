"""Read-only market adapter, personal observations and static dashboard."""

import argparse
import hmac
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/agent"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, union
from sqlalchemy.orm import sessionmaker

from chain.stock.agents.feishu_notifier import FeishuStockNotifier
from chain.stock.models.database import (
    BlockTop,
    ContinuousLimitUp,
    DailyMarketReview,
    DataFetchLog,
    EastmoneyZTPool,
    LimitUpPool,
    LowerLimitPool,
)
from auth import AuthConfig, AuthError, FeishuAuth
from watchlist import WatchlistError, WatchlistService, WatchlistStore, parse_date
from strategy_evidence import build_strategy_evidence

logger = logging.getLogger(__name__)


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Unsupported JSON type: {type(value).__name__}")


class ReportService:
    def __init__(self, database_url):
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.sessions = sessionmaker(bind=self.engine)

    def dates(self):
        tables = (
            LimitUpPool,
            ContinuousLimitUp,
            BlockTop,
            EastmoneyZTPool,
            LowerLimitPool,
            DailyMarketReview,
            DataFetchLog,
        )
        dates = union(
            *(select(table.date.label("date")) for table in tables)
        ).subquery()
        with self.sessions() as session:
            return [
                item.isoformat()
                for item in session.execute(
                    select(dates.c.date)
                    .where(dates.c.date.is_not(None))
                    .order_by(dates.c.date.desc())
                ).scalars()
            ]

    def report(self, target_date):
        notifier = FeishuStockNotifier(database_url="")
        # Bypass notifier.init_database(): browsing must never create tables.
        notifier.engine = self.engine
        notifier.Session = self.sessions
        report = notifier.build_report(target_date)
        if not any(
            (
                report.hr_limit_up_count,
                report.em_limit_up_count,
                report.continuous_count,
                report.block_count,
                report.lower_limit_count,
                report.fetch_logs,
                report.daily_review,
            )
        ):
            raise LookupError("该日期暂无播报数据")
        return {
            "report": asdict(report),
            "material": notifier.build_analysis_material(report),
            "previous_day_material": notifier.build_previous_trading_day_material(
                report
            ),
            "reason_material": notifier.build_codex_reason_material(report),
        }

    def watchlist_feedback(self, target_date, codes):
        """Later recorded market facts, never an inferred trading outcome."""
        if not codes:
            return {"date": None, "stocks": {}}
        sources = (LimitUpPool, ContinuousLimitUp, LowerLimitPool)
        later = union(
            *[select(model.date).where(model.date > target_date) for model in sources],
            select(DataFetchLog.date).where(
                DataFetchLog.date > target_date,
                DataFetchLog.data_type.in_(
                    ("limit_up_pool", "continuous_limit_up", "lower_limit_pool")
                ),
                DataFetchLog.status == "success",
            ),
        ).subquery()
        with self.sessions() as session:
            day = session.execute(
                select(later.c.date).order_by(later.c.date).limit(1)
            ).scalar()
            if day is None:
                return {"date": None, "stocks": {}}
            successful = set(
                session.execute(
                    select(DataFetchLog.data_type).where(
                        DataFetchLog.date == day,
                        DataFetchLog.status == "success",
                    )
                ).scalars()
            )
            pools = []
            available = []
            for model, source in zip(
                sources, ("limit_up_pool", "continuous_limit_up", "lower_limit_pool")
            ):
                rows = (
                    session.execute(
                        select(model).where(model.date == day, model.code.in_(codes))
                    )
                    .scalars()
                    .all()
                )
                pools.append({row.code: row for row in rows})
                # Presence proves membership. Absence is conclusive only with
                # an explicitly successful full-source fetch for this date.
                available.append(source in successful)
            up, continuous, down = pools
            return {
                "date": day.isoformat(),
                "stocks": {
                    code: {
                        "limit_up": (
                            True
                            if code in up or code in continuous
                            else False if available[0] else None
                        ),
                        "limit_down": (
                            True if code in down else False if available[2] else None
                        ),
                        "continuous_days": (
                            continuous[code].continuous_days
                            if code in continuous
                            else None
                        ),
                    }
                    for code in codes
                },
            }

    def strategy_evidence(self, target_date):
        report = self.report(target_date)["report"]
        return build_strategy_evidence(self.sessions, target_date, report)


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, service, auth=None, watchlist=None, directory, **kwargs):
        self.service = service
        self.auth = auth or FeishuAuth(AuthConfig())
        self.watchlist = watchlist
        super().__init__(*args, directory=directory, **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(
            payload, ensure_ascii=False, default=json_default, allow_nan=False
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location, cookie=None):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def log_message(self, fmt, *args):
        # OAuth callback URLs contain one-use codes and state; never log query strings.
        path = urlsplit(self.path).path
        logger.info("%s %s", self.command, path)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/api/auth/feishu/login":
            try:
                location, cookie = self.auth.start(self.headers.get("Cookie", ""))
                self.redirect(location, cookie)
            except AuthError as error:
                self.redirect("/?login_error=" + error.code)
            return
        if url.path == "/api/auth/feishu/callback":
            try:
                cookie = self.auth.callback(
                    parse_qs(url.query), self.headers.get("Cookie", "")
                )
                self.redirect("/", cookie)
            except AuthError as error:
                clear_flow = self.auth.cookie("stochips_oauth", "", 0)
                self.redirect("/?login_error=" + error.code, clear_flow)
            return
        if url.path == "/api/auth/session":
            session = self.auth.session(self.headers.get("Cookie", ""))
            self.send_json(
                200,
                {
                    "configured": self.auth.config.configured,
                    "authenticated": session is not None,
                    "user": session["user"] if session else None,
                    "csrf_token": session["csrf_token"] if session else None,
                },
            )
            return
        if url.path.startswith("/api/"):
            try:
                session = self.auth.session(self.headers.get("Cookie", ""))
                if not session:
                    self.send_json(401, {"error": "登录状态已失效，请重新登录"})
                    return
                if url.path == "/api/dates":
                    dates = self.service.dates()
                    if self.watchlist is not None:
                        dates = sorted(
                            set(dates) | set(self.watchlist.dates(session["user"])),
                            reverse=True,
                        )
                    self.send_json(200, {"dates": dates})
                elif url.path == "/api/report":
                    values = parse_qs(url.query).get("date", [])
                    if len(values) != 1 or len(values[0]) != 10:
                        raise ValueError("请选择 YYYY-MM-DD 格式日期")
                    target = date.fromisoformat(values[0])
                    self.send_json(200, self.service.report(target))
                elif url.path == "/api/watchlist":
                    values = parse_qs(url.query, keep_blank_values=True).get("date", [])
                    if len(values) != 1:
                        raise ValueError("请选择一个日期")
                    if self.watchlist is None:
                        raise WatchlistError(503, "观察记录存储未配置")
                    self.send_json(
                        200, self.watchlist.read(parse_date(values[0]), session["user"])
                    )
                elif url.path == "/api/strategy-evidence":
                    values = parse_qs(url.query, keep_blank_values=True).get("date", [])
                    if len(values) != 1:
                        raise ValueError("请选择一个日期")
                    self.send_json(
                        200, self.service.strategy_evidence(parse_date(values[0]))
                    )
                else:
                    self.send_json(404, {"error": "接口不存在"})
            except WatchlistError as error:
                self.send_json(error.status, {"error": str(error)})
            except ValueError:
                self.send_json(400, {"error": "日期无效，请使用 YYYY-MM-DD"})
            except LookupError:
                self.send_json(404, {"error": "该日期暂无播报数据"})
            except Exception:
                logger.exception("Dashboard query failed")
                self.send_json(
                    503, {"error": "数据暂不可用，请检查数据库连接与表结构后重试"}
                )
            return
        # Only built assets can be served; no directory listing or repo files.
        if url.path == "/":
            self.path = "/index.html"
        target = Path(self.translate_path(self.path)).resolve()
        root = Path(self.directory).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            self.send_error(404, "Build the dashboard first: npm run build")
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path == "/api/watchlist":
            self.save_watchlist()
            return
        if urlsplit(self.path).path != "/api/auth/logout":
            self.send_json(404, {"error": "接口不存在"})
            return
        try:
            cookie = self.auth.logout(
                self.headers.get("Cookie", ""),
                self.headers.get("Origin", ""),
                self.headers.get("X-CSRF-Token", ""),
            )
            self.send_response(204)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Set-Cookie", cookie)
            self.end_headers()
        except AuthError as error:
            self.send_json(
                401 if error.code == "unauthorized" else 403, {"error": "登录状态无效"}
            )

    def save_watchlist(self):
        try:
            session = self.auth.session(self.headers.get("Cookie", ""))
            if not session:
                raise WatchlistError(401, "登录状态已失效，请重新登录")
            if self.headers.get(
                "Origin", ""
            ) != self.auth.config.origin or not hmac.compare_digest(
                session["csrf_token"].encode(),
                self.headers.get("X-CSRF-Token", "").encode(),
            ):
                raise WatchlistError(403, "请求验证失败，请刷新登录状态")
            if self.headers.get_content_type() != "application/json":
                raise WatchlistError(415, "请使用 JSON 请求")
            if self.headers.get("Transfer-Encoding"):
                raise WatchlistError(400, "不支持此请求编码")
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 16384:
                raise WatchlistError(413, "请求内容为空或过大")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if self.watchlist is None:
                raise WatchlistError(503, "观察记录存储未配置")
            self.send_json(200, self.watchlist.save(payload, session["user"]))
        except WatchlistError as error:
            self.send_json(error.status, {"error": str(error)})
        except (ValueError, UnicodeError):
            self.send_json(400, {"error": "观察记录无效，请检查日期、状态和备注长度"})
        except LookupError:
            self.send_json(404, {"error": "该日期暂无观察来源"})
        except Exception:
            logger.exception("Watchlist save failed")
            self.send_json(503, {"error": "观察记录暂时无法保存，请稍后重试"})

    def do_HEAD(self):
        self.send_error(405)


def main():
    parser = argparse.ArgumentParser(description="飞书复盘与观察看板")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    auth = FeishuAuth(AuthConfig.from_env())
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("请在根目录 .env 或环境变量中设置 DATABASE_URL")
    logging.basicConfig(level=logging.INFO)
    service = ReportService(database_url)
    store = WatchlistStore(
        os.getenv("DASHBOARD_WATCHLIST_DB")
        or str(ROOT / "dashboard/data/watchlist.sqlite3")
    )
    handler = partial(
        DashboardHandler,
        service=service,
        auth=auth,
        watchlist=WatchlistService(service, store),
        directory=str(Path(__file__).parent / "dist"),
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    logger.info("Dashboard: http://%s:%s", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.engine.dispose()


if __name__ == "__main__":
    main()
