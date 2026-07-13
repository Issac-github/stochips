import os
import sys
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chain.stock.agents.codex_client import CodexSubscriptionClient


class FakeThread:
    def __init__(self):
        self.env_during_run = {}

    def run(self, prompt, **kwargs):
        del prompt, kwargs
        self.env_during_run = {
            key: os.environ.get(key)
            for key in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "no_proxy",
            )
        }
        return SimpleNamespace(final_response="Codex response")


class FakeCodex:
    def __init__(self, thread):
        self.thread = thread

    def thread_start(self, **kwargs):
        del kwargs
        return self.thread

    def models(self):
        return SimpleNamespace(data=[])


def test_codex_proxy_environment_is_scoped(monkeypatch):
    monkeypatch.setenv("CODEX_HTTP_PROXY", "http://proxy.test:7890")
    monkeypatch.setenv("CODEX_HTTPS_PROXY", "http://proxy.test:7890")
    monkeypatch.setenv("CODEX_ALL_PROXY", "http://proxy.test:7890")
    monkeypatch.setenv("CODEX_NO_PROXY", "localhost,mysql")
    monkeypatch.setenv("HTTP_PROXY", "http://original.test:8080")
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("ALL_PROXY", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)

    thread = FakeThread()
    client = CodexSubscriptionClient.__new__(CodexSubscriptionClient)
    client._ApprovalMode = SimpleNamespace(deny_all="deny_all")
    client._Sandbox = SimpleNamespace(read_only="read_only")
    client.model = None
    client.resolved_model = ""
    client.working_directory = "/app"
    client._codex = FakeCodex(thread)

    result = client.review("prompt")

    assert result == "Codex response"
    assert thread.env_during_run["HTTP_PROXY"] == "http://proxy.test:7890"
    assert thread.env_during_run["HTTPS_PROXY"] == "http://proxy.test:7890"
    assert thread.env_during_run["ALL_PROXY"] == "http://proxy.test:7890"
    assert thread.env_during_run["NO_PROXY"] == "localhost,mysql"
    assert thread.env_during_run["http_proxy"] == "http://proxy.test:7890"
    assert os.environ["HTTP_PROXY"] == "http://original.test:8080"
    assert os.environ.get("HTTPS_PROXY") is None
    assert os.environ.get("ALL_PROXY") is None
    assert os.environ.get("NO_PROXY") is None
