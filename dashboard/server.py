"""Read-only Feishu report adapter and static dashboard server."""

import argparse
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


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, service, auth=None, directory, **kwargs):
        self.service = service
        self.auth = auth or FeishuAuth(AuthConfig())
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
                cookie = self.auth.callback(parse_qs(url.query), self.headers.get("Cookie", ""))
                self.redirect("/", cookie)
            except AuthError as error:
                clear_flow = self.auth.cookie("stochips_oauth", "", 0)
                self.redirect("/?login_error=" + error.code, clear_flow)
            return
        if url.path == "/api/auth/session":
            session = self.auth.session(self.headers.get("Cookie", ""))
            self.send_json(200, {
                "configured": self.auth.config.configured,
                "authenticated": session is not None,
                "user": session["user"] if session else None,
                "csrf_token": session["csrf_token"] if session else None,
            })
            return
        if url.path.startswith("/api/"):
            try:
                if not self.auth.session(self.headers.get("Cookie", "")):
                    self.send_json(401, {"error": "登录状态已失效，请重新登录"})
                    return
                if url.path == "/api/dates":
                    self.send_json(200, {"dates": self.service.dates()})
                elif url.path == "/api/report":
                    values = parse_qs(url.query).get("date", [])
                    if len(values) != 1 or len(values[0]) != 10:
                        raise ValueError("请选择 YYYY-MM-DD 格式日期")
                    target = date.fromisoformat(values[0])
                    self.send_json(200, self.service.report(target))
                else:
                    self.send_json(404, {"error": "接口不存在"})
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
        if urlsplit(self.path).path != "/api/auth/logout":
            self.send_json(404, {"error": "接口不存在"})
            return
        try:
            cookie = self.auth.logout(
                self.headers.get("Cookie", ""), self.headers.get("Origin", ""),
                self.headers.get("X-CSRF-Token", ""),
            )
            self.send_response(204)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Set-Cookie", cookie)
            self.end_headers()
        except AuthError as error:
            self.send_json(401 if error.code == "unauthorized" else 403, {"error": "登录状态无效"})

    def do_HEAD(self):
        self.send_error(405)


def main():
    parser = argparse.ArgumentParser(description="飞书播报只读看板")
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
    handler = partial(
        DashboardHandler, service=service, auth=auth, directory=str(Path(__file__).parent / "dist")
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
