import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from chain.stock.scheduler.daily_job import (
    CODEX_RETRY_DELAYS,
    DEFAULT_DATA_FETCH_HOUR,
    DEFAULT_DATA_FETCH_MINUTE,
    DailyJobScheduler,
    _next_scheduled_daily_job_at,
    _sleep_fetch_start_jitter,
)


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "kwargs": kwargs,
            }
        )


def test_daily_job_schedule_runs_one_ordered_workflow():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.scheduler = FakeScheduler()

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


def test_daily_job_waits_for_fetch_and_review_before_feishu():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.storage = SimpleNamespace(
        get_data_status=lambda target_date: {"is_complete": True}
    )
    events = []

    async def fake_fetch(target_date):
        events.append(("fetch", target_date))
        return {"status": "success", "errors": []}

    async def fake_review(target_date):
        events.append(("review", target_date))
        return {"cached": False}

    async def fake_feishu(target_date):
        events.append(("feishu", target_date))
        return {"sent": True}

    scheduler.fetch_and_store_data = fake_fetch
    scheduler._run_daily_review_with_retry = fake_review
    scheduler.send_feishu_report = fake_feishu
    target_date = date(2026, 7, 10)

    result = asyncio.run(scheduler.run_daily_job(target_date))

    assert events == [
        ("fetch", target_date),
        ("review", target_date),
        ("feishu", target_date),
    ]
    assert result["status"] == "success"


def test_daily_job_stops_before_review_when_fetch_is_incomplete():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.storage = SimpleNamespace(
        get_data_status=lambda target_date: {"is_complete": False}
    )
    events = []

    async def fake_fetch(target_date):
        events.append(("fetch", target_date))
        return {"status": "success", "errors": []}

    async def fake_broadcast(*args, **kwargs):
        events.append(("failure_broadcast", args[1]))

    scheduler.fetch_and_store_data = fake_fetch
    scheduler._send_failure_broadcast = fake_broadcast
    target_date = date(2026, 7, 10)

    with pytest.raises(RuntimeError, match="数据抓取不完整"):
        asyncio.run(scheduler.run_daily_job(target_date))

    assert events == [("fetch", target_date), ("failure_broadcast", "数据抓取")]


def test_daily_job_announces_next_run_when_fetch_raises():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    broadcasts = []

    async def failing_fetch(target_date):
        raise RuntimeError("upstream unavailable")

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    scheduler.fetch_and_store_data = failing_fetch
    scheduler._send_failure_broadcast = fake_broadcast
    target_date = date(2026, 7, 10)

    with pytest.raises(RuntimeError, match="upstream unavailable"):
        asyncio.run(scheduler.run_daily_job(target_date))

    assert broadcasts[0][1] == "数据抓取"
    assert broadcasts[0][3] is not None


def test_daily_job_does_not_send_feishu_when_codex_review_fails():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.storage = SimpleNamespace(
        get_data_status=lambda target_date: {"is_complete": True}
    )
    events = []

    async def fake_fetch(target_date):
        events.append(("fetch", target_date))
        return {"status": "success", "errors": []}

    async def failing_review(target_date):
        events.append(("review", target_date))
        raise RuntimeError("Codex unavailable")

    async def fake_feishu(target_date):
        events.append(("feishu", target_date))
        return {"sent": True}

    scheduler.fetch_and_store_data = fake_fetch
    scheduler._run_daily_review_with_retry = failing_review
    scheduler.send_feishu_report = fake_feishu
    target_date = date(2026, 7, 10)

    with pytest.raises(RuntimeError, match="Codex unavailable"):
        asyncio.run(scheduler.run_daily_job(target_date))

    assert events == [("fetch", target_date), ("review", target_date)]


def test_daily_job_announces_next_run_when_feishu_raises():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.storage = SimpleNamespace(
        get_data_status=lambda target_date: {"is_complete": True}
    )
    broadcasts = []

    async def fake_fetch(target_date):
        return {"status": "success", "errors": []}

    async def fake_review(target_date):
        return {"cached": False}

    async def failing_feishu(target_date):
        raise RuntimeError("webhook unavailable")

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    scheduler.fetch_and_store_data = fake_fetch
    scheduler._run_daily_review_with_retry = fake_review
    scheduler.send_feishu_report = failing_feishu
    scheduler._send_failure_broadcast = fake_broadcast
    target_date = date(2026, 7, 10)

    with pytest.raises(RuntimeError, match="webhook unavailable"):
        asyncio.run(scheduler.run_daily_job(target_date))

    assert broadcasts[0][1] == "飞书播报"
    assert broadcasts[0][3] is not None


def test_codex_review_retries_and_announces_the_next_retry_time(monkeypatch):
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    attempts = []
    broadcasts = []
    sleeps = []

    async def flaky_review(target_date, *, force=False):
        attempts.append((target_date, force))
        if len(attempts) < 3:
            raise RuntimeError(f"temporary failure {len(attempts)}")
        return {"cached": False}

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    async def fake_sleep(delay):
        sleeps.append(delay)

    scheduler.run_daily_market_review = flaky_review
    scheduler._send_failure_broadcast = fake_broadcast
    monkeypatch.setattr(
        "chain.stock.scheduler.daily_job.asyncio.sleep",
        fake_sleep,
    )
    target_date = date(2026, 7, 10)

    result = asyncio.run(scheduler._run_daily_review_with_retry(target_date))

    assert result == {"cached": False}
    assert attempts == [(target_date, True)] * 3
    assert [item[1] for item in broadcasts] == ["Codex每日复盘", "Codex每日复盘"]
    assert all(item[3] is not None for item in broadcasts)
    assert sleeps == pytest.approx(CODEX_RETRY_DELAYS, abs=1)


def test_codex_final_failure_announces_next_scheduled_run(monkeypatch):
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    broadcasts = []

    async def failing_review(target_date, *, force=False):
        raise RuntimeError("Codex unavailable")

    async def fake_broadcast(target_date, stage, error, retry_at=None):
        broadcasts.append((target_date, stage, str(error), retry_at))

    async def fake_sleep(delay):
        return None

    scheduler.run_daily_market_review = failing_review
    scheduler._send_failure_broadcast = fake_broadcast
    monkeypatch.setattr(
        "chain.stock.scheduler.daily_job.asyncio.sleep",
        fake_sleep,
    )

    with pytest.raises(RuntimeError, match="Codex unavailable"):
        asyncio.run(
            scheduler._run_daily_review_with_retry(date(2026, 7, 10))
        )

    assert len(broadcasts) == len(CODEX_RETRY_DELAYS) + 1
    assert broadcasts[-1][3] is not None


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
