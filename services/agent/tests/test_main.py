import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as agent_main


def test_run_stops_before_review_when_fetch_is_not_complete(monkeypatch, capsys):
    review_calls = []
    monkeypatch.setattr(agent_main, "cmd_fetch", lambda _target_date: False)
    monkeypatch.setattr(
        agent_main,
        "cmd_assess_daily_review",
        lambda *_args, **_kwargs: review_calls.append(True),
    )

    agent_main.cmd_run("20260710")

    assert review_calls == []
    assert "抓取未完整成功，停止后续市场复盘" in capsys.readouterr().out
