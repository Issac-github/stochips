"""Personal observation notes, isolated from the read-only market database."""

from contextlib import closing
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

CODE = re.compile(r"[0-9]{6}")
STATUSES = {"candidate", "watching", "excluded"}
OUTCOMES = {"pending", "met", "not_met", "continue"}
CONCEPTS = {
    item["key"]
    for item in json.loads(
        Path(__file__).with_name("strategy-concepts.json").read_text(encoding="utf-8")
    )["concepts"]
}


class WatchlistError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def parse_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("请选择 YYYY-MM-DD 格式日期")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("日期格式无效")
    return result


def owner_key(user):
    # Identity always comes from the authenticated session, never the request.
    return hashlib.sha256(
        json.dumps(
            [user["tenant_key"], user["open_id"]],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def display(value):
    return "—" if value is None or value == "" else str(value)


def build_candidates(report):
    """Merge existing observations without ranking or interpreting free-text AI."""
    items = {}

    def add(stock, role, source, detail, risks, checks, fact=None):
        code = stock.get("code", "")
        if not isinstance(code, str) or not CODE.fullmatch(code):
            return
        item = items.setdefault(
            code,
            {
                "code": code,
                "name": stock.get("name") or code,
                "roles": [],
                "evidence": [],
                "risks": [],
                "checks": [],
            },
        )
        if role not in item["roles"]:
            item["roles"].append(role)
        evidence = {"source": source, "detail": detail, "fact": fact or stock}
        if evidence not in item["evidence"]:
            item["evidence"].append(evidence)
        for key, values in (("risks", risks), ("checks", checks)):
            for value in values:
                if value not in item[key]:
                    item[key].append(value)

    for stock in report["top_stocks"]:
        turnover = (
            f"{stock['turnover_rate']}%"
            if stock.get("turnover_rate") is not None
            else "—"
        )
        add(
            stock,
            "核心连板",
            "top_stocks",
            f"连板 {display(stock.get('continuous_days'))} 板；封板 {display(stock.get('limit_up_time'))}；换手 {turnover}",
            ["连板高度本身不能确认龙头地位；换手率不能证明历史天量。"],
            [
                "核对所属方向及梯队延续，结合完整复盘确认观察前提。",
                "竞价、开盘与首次承接仍需下一交易日人工验证。",
            ],
        )
    for assist in report["leader_assists"]:
        stock, leader = assist["stock"], assist["leader"]
        basis = (
            " / ".join(
                assist.get("shared_reason_tags", []) + assist.get("shared_blocks", [])
            )
            or "—"
        )
        add(
            stock,
            "助攻候选",
            "leader_assists",
            f"关联高标 {display(leader.get('name'))}（{display(leader.get('code'))}）；共同属性/板块 {basis}；板型 {display(assist.get('board_type'))}",
            ["收盘回溯候选，包含非一字及首板；不证明盘中助攻有效或因果带动。"],
            ["观察候选竞价与封单延续，并核对关联高标的盘中响应。"],
            assist,
        )
    for stock in report["breakout_stocks"]:
        add(
            stock,
            "前高观察",
            "breakout_stocks",
            f"目标价 {display(stock.get('breakout_price'))}；历史前高 {display(stock.get('previous_high_price'))}；距前段连板结束 {display(stock.get('gap_trading_days'))} 个交易日",
            ["涨停价触及或突破前高的记录，不能代替平台形态、量能与承接验证。"],
            ["核对历史量价、突破位置及次日回落/承接，条件不足保持待验证。"],
        )
    return items


def default_annotation():
    return {
        "status": "candidate",
        "outcome": "pending",
        "note": "",
        "revision": 0,
        "updated_at": None,
        "concepts": [],
    }


class WatchlistStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS observations (
                owner TEXT NOT NULL, date TEXT NOT NULL, code TEXT NOT NULL,
                snapshot TEXT NOT NULL, status TEXT NOT NULL, outcome TEXT NOT NULL,
                note TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY (owner, date, code)
            )"""
            )
            # Separate table keeps the original nine-column observation schema
            # writable by older dashboard versions during rollback/rolling use.
            connection.execute(
                """CREATE TABLE IF NOT EXISTS observation_concepts (
                owner TEXT NOT NULL, date TEXT NOT NULL, code TEXT NOT NULL,
                concepts TEXT NOT NULL, PRIMARY KEY(owner,date,code)
            )"""
            )

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def read(self, owner, target):
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """SELECT o.*, COALESCE(c.concepts, '[]') AS concepts FROM observations o
                LEFT JOIN observation_concepts c USING(owner,date,code)
                WHERE o.owner=? AND o.date=? ORDER BY o.code""",
                (owner, target),
            ).fetchall()
        return {
            row["code"]: {
                "snapshot": json.loads(row["snapshot"]),
                "annotation": {
                    key: json.loads(row[key]) if key == "concepts" else row[key]
                    for key in default_annotation()
                },
            }
            for row in rows
        }

    def dates(self, owner):
        with closing(self.connect()) as connection:
            return [
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT date FROM observations WHERE owner=? ORDER BY date DESC",
                    (owner,),
                )
            ]

    def save(self, owner, target, candidate, payload):
        with closing(self.connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT o.revision, COALESCE(c.concepts, '[]') AS concepts FROM observations o
                LEFT JOIN observation_concepts c USING(owner,date,code)
                WHERE o.owner=? AND o.date=? AND o.code=?""",
                (owner, target, candidate["code"]),
            ).fetchone()
            revision = row["revision"] if row else 0
            if revision != payload["revision"]:
                raise WatchlistError(
                    409,
                    "记录已在其他页面更新，请重新读取后再保存；当前编辑内容仍保留。",
                )
            annotation = {key: payload[key] for key in ("status", "outcome", "note")}
            annotation.update(
                revision=revision + 1, updated_at=datetime.now(timezone.utc).isoformat()
            )
            annotation["concepts"] = payload.get(
                "concepts", json.loads(row["concepts"]) if row else []
            )
            connection.execute(
                """INSERT INTO observations (owner,date,code,snapshot,status,outcome,note,revision,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(owner,date,code) DO UPDATE SET snapshot=excluded.snapshot,
                status=excluded.status,outcome=excluded.outcome,note=excluded.note,
                revision=excluded.revision,updated_at=excluded.updated_at""",
                (
                    owner,
                    target,
                    candidate["code"],
                    json.dumps(candidate, ensure_ascii=False, default=str),
                    annotation["status"],
                    annotation["outcome"],
                    annotation["note"],
                    annotation["revision"],
                    annotation["updated_at"],
                ),
            )
            connection.execute(
                """INSERT INTO observation_concepts VALUES (?,?,?,?)
                ON CONFLICT(owner,date,code) DO UPDATE SET concepts=excluded.concepts""",
                (
                    owner,
                    target,
                    candidate["code"],
                    json.dumps(annotation["concepts"]),
                ),
            )
            return annotation


def validate_update(payload):
    required = {"date", "code", "status", "outcome", "note", "revision"}
    if (
        not isinstance(payload, dict)
        or not required <= set(payload)
        or set(payload) - required - {"concepts"}
    ):
        raise ValueError("观察记录字段不完整或包含未知字段")
    target = parse_date(payload["date"])
    if not isinstance(payload["code"], str) or not CODE.fullmatch(payload["code"]):
        raise ValueError("股票代码须为六位数字")
    if not isinstance(payload["status"], str) or payload["status"] not in STATUSES:
        raise ValueError("观察状态无效")
    if not isinstance(payload["outcome"], str) or payload["outcome"] not in OUTCOMES:
        raise ValueError("验证结果无效")
    if not isinstance(payload["note"], str) or len(payload["note"]) > 2000:
        raise ValueError("备注不能超过2000字")
    if type(payload["revision"]) is not int or payload["revision"] < 0:
        raise ValueError("记录版本无效")
    if "concepts" in payload:
        values = payload["concepts"]
        if (
            not isinstance(values, list)
            or len(values) > len(CONCEPTS)
            or any(
                not isinstance(value, str) or value not in CONCEPTS for value in values
            )
            or len(set(values)) != len(values)
        ):
            raise ValueError("人工模式分类无效")
    return target


class WatchlistService:
    def __init__(self, reports, store):
        self.reports, self.store = reports, store

    def load_sources(self, target, owner):
        saved = self.store.read(owner, target.isoformat())
        try:
            report = self.reports.report(target)["report"]
        except LookupError:
            if not saved:
                raise
            return {}, saved, ["该日期的行情来源已不可用，仅显示已保存快照。"]
        warnings = list(report["data_warnings"])
        if not report.get("daily_review"):
            warnings.append("尚未保存当日复盘，情绪与主线前提需另行核对。")
        return build_candidates(report), saved, warnings

    def dates(self, user):
        return self.store.dates(owner_key(user))

    def read(self, target, user):
        current, saved, warnings = self.load_sources(target, owner_key(user))
        # Saved evidence is a snapshot. Refreshing market facts must not rewrite
        # a user's recorded observation premise or silently remove saved rows.
        items = []
        for code in dict.fromkeys([*current, *saved]):
            record = saved.get(code)
            items.append(
                {
                    **(record["snapshot"] if record else current[code]),
                    "saved": record is not None,
                    "source_missing": code not in current,
                    "annotation": (
                        record["annotation"] if record else default_annotation()
                    ),
                }
            )
        feedback = self.reports.watchlist_feedback(
            target, [item["code"] for item in items]
        )
        return {
            "date": target.isoformat(),
            "items": items,
            "warnings": warnings,
            "feedback": feedback,
        }

    def save(self, payload, user):
        target = validate_update(payload)
        owner = owner_key(user)
        current, saved, _warnings = self.load_sources(target, owner)
        code = payload["code"]
        candidate = saved[code]["snapshot"] if code in saved else current.get(code)
        if candidate is None:
            raise WatchlistError(404, "该股票不在此日期的观察来源中，请刷新观察池")
        return {
            "annotation": self.store.save(owner, target.isoformat(), candidate, payload)
        }
