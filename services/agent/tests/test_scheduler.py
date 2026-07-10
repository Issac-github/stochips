import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chain.stock.models.database import DailyJobRun
from chain.stock.scheduler.daily_job import (
    DAILY_JOB_STAGE_FETCH,
    DAILY_JOB_STAGE_NOTIFY,
    DAILY_JOB_STAGE_REVIEW,
    DEFAULT_DATA_FETCH_HOUR,
    DEFAULT_DATA_FETCH_MINUTE,
    DailyJobScheduler,
    _next_scheduled_daily_job_at,
    _sleep_fetch_start_jitter,
)


class FakeScheduler:
    def __init__(self):
        self.jobs = []
        self.started = False

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append(
            {"func": func, "trigger": trigger, "kwargs": kwargs}
        )

    def start(self):
        self.started = True


def make_scheduler(*, is_complete=True):
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.scheduler = FakeScheduler()
    scheduler.storage = SimpleNamespace(
        get_data_status=lambda target_date: {"is_complete": is_complete},
        is_fetch_skipped=lambda target_date: False,
    )
    records = {}

    def get_run(target_date):
        return records.get(target_date)

    def save_run(
        target_date,
        *,
        stage,
        status,
        attempt,
        retry_at=None,
        last_error=None,
    ):
        records[target_date] = SimpleNamespace(
            date=target_date,
            stage=stage,
            status=status,
            attempt=attempt,
            retry_at=retry_at,
            last_error=last_error,
        )

    scheduler._get_daily_job_run = get_run
    scheduler._save_daily_job_run = save_run
    scheduler._list_recoverable_job_runs = lambda: list(records.values())
    scheduler.scheduled_hour = DEFAULT_DATA_FETCH_HOUR
    scheduler.scheduled_minute = DEFAULT_DATA_FETCH_MINUTE
    return scheduler, records


def test_daily_job_schedule_runs_one_ordered_workflow():
    scheduler, _ = make_scheduler()

    scheduler.schedule_daily_job()

    assert len(scheduler.scheduler.jobs) == 1
    job = scheduler.scheduler.jobs[0]
    assert job["kwargs"]["id"] == "daily_stock_job"
    assert job["kwargs"]["name"] == "每日抓取、Codex复盘与飞书播报"
    assert str(job["trigger"]) == (
        "cron[day_of_week='mon-fri', "
        f"hour='{DEFAULT_DATA_FETCH_HOUR}', "
        f"minute='{DEFAULT_DATA_FETCH_MINUTE}']"
    )


def test_daily_job_runs_fetch_review_then_feishu_and_completes():
    scheduler, records = make_scheduler()
    events = []

    async def fake_fetch(target_date):
        events.append(("fetch", target_date))
        return {"status": "success", "errors": []}

    async def fake_review(target_date, *, force=False):
        events.append(("review", target_date, force))
        return {"cached": False}

    async def fake_feishu(target_date):
        events.append(("feishu", target_date))
        return {"sent": True}

    scheduler.fetch_and_store_data = fake_fetch
    scheduler.run_daily_market_review = fake_review
    scheduler.send_feishu_report = fake_feishu
    target_date = date(2026, 7, 10)

    result = asyncio.run(scheduler.run_daily_job(target_date))

    assert events == [
        ("fetch", target_date),
        ("review", target_date, True),
        ("feishu", target_date),
    ]
    assert result["status"] == "success"
    assert records[target_date].status == "completed"
    assert records[target_date].stage == DAILY_JOB_STAGE_NOTIFY


def test_fetch_failure_persists_retry_and_announces_time():
    scheduler, records = make_scheduler()
    broadcasts = []

    async def failing_fetch(target_date):
        raise RuntimeError("upstream unavailable")

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    scheduler.fetch_and_store_data = failing_fetch
    scheduler._send_failure_broadcast = fake_broadcast
    target_date = date.today()

    result = asyncio.run(scheduler.run_daily_job(target_date))

    assert result["status"] == "retrying"
    assert result["stage"] == DAILY_JOB_STAGE_FETCH
    assert records[target_date].status == "retrying"
    assert records[target_date].attempt == 1
    assert broadcasts[0][1] == "数据抓取"
    assert broadcasts[0][3] == records[target_date].retry_at
    assert scheduler.scheduler.jobs[-1]["kwargs"]["id"] == (
        f"daily_stock_retry_{target_date:%Y%m%d}"
    )


def test_resume_starts_from_review_without_refetching():
    scheduler, records = make_scheduler()
    target_date = date.today()
    records[target_date] = SimpleNamespace(
        date=target_date,
        stage=DAILY_JOB_STAGE_REVIEW,
        status="retrying",
        attempt=1,
        retry_at=datetime.now(),
        last_error="Codex unavailable",
    )
    events = []

    async def unexpected_fetch(target_date):
        raise AssertionError("恢复复盘时不应重新抓取")

    async def fake_review(target_date, *, force=False):
        events.append(("review", force))
        return {"cached": False}

    async def fake_feishu(target_date):
        events.append(("feishu", target_date))
        return {"sent": True}

    scheduler.fetch_and_store_data = unexpected_fetch
    scheduler.run_daily_market_review = fake_review
    scheduler.send_feishu_report = fake_feishu

    result = asyncio.run(scheduler.resume_daily_job(target_date))

    assert result["status"] == "success"
    assert events == [("review", False), ("feishu", target_date)]
    assert records[target_date].status == "completed"


def test_restart_recovers_today_pending_retry():
    scheduler, records = make_scheduler()
    target_date = date.today()
    records[target_date] = SimpleNamespace(
        date=target_date,
        stage=DAILY_JOB_STAGE_NOTIFY,
        status="retrying",
        attempt=2,
        retry_at=datetime.now() + timedelta(minutes=5),
        last_error="webhook unavailable",
    )

    recovered = scheduler._recover_persisted_jobs()

    assert recovered == 1
    job = scheduler.scheduler.jobs[-1]
    assert job["func"] == scheduler.resume_daily_job
    assert job["kwargs"]["args"] == [target_date]
    assert job["kwargs"]["id"] == f"daily_stock_retry_{target_date:%Y%m%d}"


def test_daily_job_state_persists_across_scheduler_instances(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'daily-job.db'}")
    DailyJobRun.__table__.create(engine)
    session_factory = sessionmaker(bind=engine)
    target_date = date.today()

    writer = DailyJobScheduler.__new__(DailyJobScheduler)
    writer.storage = SimpleNamespace(Session=session_factory)
    writer._save_daily_job_run(
        target_date,
        stage=DAILY_JOB_STAGE_REVIEW,
        status="retrying",
        attempt=1,
        retry_at=datetime.now() + timedelta(minutes=5),
        last_error="Codex unavailable",
    )

    reader = DailyJobScheduler.__new__(DailyJobScheduler)
    reader.storage = SimpleNamespace(Session=session_factory)
    restored = reader._get_daily_job_run(target_date)

    assert restored is not None
    assert restored.stage == DAILY_JOB_STAGE_REVIEW
    assert restored.status == "retrying"
    assert restored.attempt == 1
    assert restored.last_error == "Codex unavailable"


def test_final_stage_failure_marks_failed_and_announces_next_day():
    scheduler, records = make_scheduler()
    target_date = date.today()
    records[target_date] = SimpleNamespace(
        date=target_date,
        stage=DAILY_JOB_STAGE_NOTIFY,
        status="running",
        attempt=2,
        retry_at=None,
        last_error=None,
    )
    broadcasts = []

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    scheduler._send_failure_broadcast = fake_broadcast

    result = asyncio.run(
        scheduler._handle_stage_failure(
            target_date,
            DAILY_JOB_STAGE_NOTIFY,
            RuntimeError("webhook unavailable"),
        )
    )

    assert result["status"] == "failed"
    assert records[target_date].status == "failed"
    assert broadcasts[0][1] == "飞书播报"
    assert broadcasts[0][3] > datetime.now()


def test_failure_broadcast_prefers_alert_webhook_and_falls_back(monkeypatch):
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.database_url = "sqlite://"
    scheduler.feishu_notifier = None
    scheduler.alert_feishu_notifier = None
    created = []

    class FakeNotifier:
        def send_status_notification(self, target_date, title, content):
            return {"code": 0}

    def fake_create(database_url, webhook_url=None, webhook_secret=None):
        created.append((database_url, webhook_url, webhook_secret))
        return FakeNotifier()

    monkeypatch.setattr(
        "chain.stock.scheduler.daily_job.create_feishu_notifier",
        fake_create,
    )
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://formal.example/hook")
    monkeypatch.setenv("FEISHU_ALERT_WEBHOOK_URL", "https://alert.example/hook")
    monkeypatch.setenv("FEISHU_ALERT_WEBHOOK_SECRET", "alert-secret")

    asyncio.run(
        scheduler._send_failure_broadcast(
            date.today(),
            "数据抓取",
            RuntimeError("upstream unavailable"),
            datetime.now() + timedelta(minutes=5),
        )
    )

    assert created == [
        ("sqlite://", "https://alert.example/hook", "alert-secret")
    ]

    scheduler.alert_feishu_notifier = None
    monkeypatch.setenv("FEISHU_ALERT_WEBHOOK_URL", "")
    asyncio.run(
        scheduler._send_failure_broadcast(
            date.today(),
            "数据抓取",
            RuntimeError("upstream unavailable"),
        )
    )
    assert created[-1] == ("sqlite://", None, None)


def test_recovery_does_not_replay_a_previous_trading_day():
    scheduler, records = make_scheduler()
    target_date = date.today() - timedelta(days=1)
    records[target_date] = SimpleNamespace(
        date=target_date,
        stage=DAILY_JOB_STAGE_FETCH,
        status="retrying",
        attempt=1,
        retry_at=datetime.now(),
        last_error="upstream unavailable",
    )

    assert scheduler._recover_persisted_jobs() == 0
    assert records[target_date].status == "failed"
    assert scheduler.scheduler.jobs == []


def test_next_scheduled_daily_job_skips_weekend():
    friday_after_job = datetime(2026, 7, 10, 17, 0)

    assert _next_scheduled_daily_job_at(friday_after_job) == datetime(
        2026, 7, 13, DEFAULT_DATA_FETCH_HOUR, DEFAULT_DATA_FETCH_MINUTE
    )


def test_fetch_start_jitter_uses_random_delay(monkeypatch):
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setenv("STOCK_FETCH_START_JITTER_MIN", "5")
    monkeypatch.setenv("STOCK_FETCH_START_JITTER_MAX", "45")
    monkeypatch.setattr(
        "chain.stock.scheduler.daily_job.random.uniform",
        lambda delay_min, delay_max: 17.0,
    )
    monkeypatch.setattr(
        "chain.stock.scheduler.daily_job.asyncio.sleep",
        fake_sleep,
    )

    asyncio.run(_sleep_fetch_start_jitter())

    assert sleeps == [17.0]
