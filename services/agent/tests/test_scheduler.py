from chain.stock.scheduler.daily_job import (
    DEFAULT_DATA_FETCH_HOUR,
    DEFAULT_DATA_FETCH_MINUTE,
    DEFAULT_FEISHU_REPORT_HOUR,
    DEFAULT_FEISHU_REPORT_MINUTE,
    DailyJobScheduler,
    _sleep_fetch_start_jitter,
)
import asyncio


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


def test_feishu_report_default_schedule_avoids_half_hour_peak():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.scheduler = FakeScheduler()

    scheduler.schedule_feishu_report()

    assert len(scheduler.scheduler.jobs) == 1
    job = scheduler.scheduler.jobs[0]
    assert job["kwargs"]["id"] == "daily_feishu_report"
    assert job["kwargs"]["name"] == "每日飞书涨停播报"
    assert str(job["trigger"]) == (
        "cron[day_of_week='mon-fri', "
        f"hour='{DEFAULT_FEISHU_REPORT_HOUR}', "
        f"minute='{DEFAULT_FEISHU_REPORT_MINUTE}']"
    )


def test_data_fetch_default_schedule_avoids_exact_market_close():
    scheduler = DailyJobScheduler.__new__(DailyJobScheduler)
    scheduler.scheduler = FakeScheduler()

    scheduler.schedule_data_fetch()

    assert len(scheduler.scheduler.jobs) == 1
    job = scheduler.scheduler.jobs[0]
    assert job["kwargs"]["id"] == "daily_data_fetch"
    assert job["kwargs"]["name"] == "每日数据抓取"
    assert str(job["trigger"]) == (
        "cron[day_of_week='mon-fri', "
        f"hour='{DEFAULT_DATA_FETCH_HOUR}', "
        f"minute='{DEFAULT_DATA_FETCH_MINUTE}']"
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
