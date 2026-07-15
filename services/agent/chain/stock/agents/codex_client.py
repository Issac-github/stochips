"""Direct client for the official Python Codex SDK."""

from contextlib import contextmanager
import logging
import os
from typing import Any, Dict, Iterator, List, Optional


logger = logging.getLogger(__name__)

ANALYSIS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit_up_reason_analysis": {"type": "string"},
        "concept_heat": {"type": "string"},
        "market_sentiment": {"type": "string"},
        "fundamental_assessment": {"type": "string"},
        "technical_analysis": {"type": "string"},
        "ai_risk_score": {"type": "number", "minimum": 0, "maximum": 100},
        "ai_suggestion": {"type": "string", "enum": ["机会", "观望", "谨慎", "规避"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "key_factors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "factor": {"type": "string"},
                    "impact": {"type": "string"},
                    "weight": {"type": "number"},
                },
                "required": ["factor", "impact", "weight"],
                "additionalProperties": False,
            },
        },
        "similar_cases": {"type": "string"},
        "tomorrow_prediction": {"type": "string"},
    },
    "required": [
        "limit_up_reason_analysis", "concept_heat", "market_sentiment",
        "fundamental_assessment", "technical_analysis", "ai_risk_score",
        "ai_suggestion", "confidence", "key_factors", "similar_cases",
        "tomorrow_prediction",
    ],
    "additionalProperties": False,
}


class CodexSubscriptionClient:
    """Run analysis with a local ChatGPT-authenticated Codex app-server."""

    def __init__(self, model: Optional[str] = None, working_directory: Optional[str] = None):
        from openai_codex import ApprovalMode, Codex, Sandbox

        self._ApprovalMode = ApprovalMode
        self._Codex = Codex
        self._Sandbox = Sandbox
        self.model = model or os.getenv("CODEX_MODEL") or None
        self.resolved_model = self.model or ""
        self.working_directory = working_directory or os.getenv(
            "CODEX_WORKING_DIRECTORY", "/tmp"
        )
        self._codex = None

    @property
    def is_available(self) -> bool:
        return self._Codex is not None

    def analyze(self, messages: List[Dict[str, str]]) -> str:
        prompt = "\n\n".join(
            f"{('系统要求' if item['role'] == 'system' else '分析数据')}：\n{item['content']}"
            for item in messages
        )
        return self._run(prompt, output_schema=ANALYSIS_SCHEMA)

    def review(self, prompt: str) -> str:
        """Run a free-form qualitative review without the legacy score schema."""
        return self._run(prompt)

    def _run(
        self,
        prompt: str,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        with _codex_proxy_environment():
            codex = self._get_codex()
            thread = codex.thread_start(
                model=self.model,
                cwd=self.working_directory,
                ephemeral=True,
                approval_mode=self._ApprovalMode.deny_all,
                sandbox=self._Sandbox.read_only,
            )
            run_options: Dict[str, Any] = {
                "cwd": self.working_directory,
                "model": self.model,
                "approval_mode": self._ApprovalMode.deny_all,
                "sandbox": self._Sandbox.read_only,
            }
            if output_schema is not None:
                run_options["output_schema"] = output_schema
            result = thread.run(prompt, **run_options)
            if not result.final_response:
                raise RuntimeError("Codex 未返回分析结果")
            self._resolve_default_model()
            return result.final_response

    def _get_codex(self) -> Any:
        """Start the app-server after its scoped proxy environment is installed."""
        if self._codex is None:
            self._codex = self._Codex()
        return self._codex

    def _resolve_default_model(self) -> None:
        """Resolve the SDK-selected model for user-visible output metadata."""
        if self.resolved_model:
            return
        try:
            models = self._codex.models().data
            default_model = next((item for item in models if item.is_default), None)
            self.resolved_model = default_model.model if default_model else "default"
        except Exception:
            self.resolved_model = "default"

    def close(self) -> None:
        if self._codex is not None:
            self._codex.close()
            self._codex = None


def login_chatgpt_device_code() -> None:
    """Perform one device-code login and persist it in Codex's home directory."""
    from openai_codex import Codex

    with _codex_proxy_environment():
        with Codex() as codex:
            login = codex.login_chatgpt_device_code()
            print(f"请打开: {login.verification_url}")
            print(f"请输入设备码: {login.user_code}")
            result = login.wait()
            print(f"Codex 登录{'成功' if result.success else '失败'}")


@contextmanager
def _codex_proxy_environment() -> Iterator[None]:
    """Apply CODEX_* proxy variables only while calling the Codex SDK."""
    https_proxy = os.getenv("CODEX_HTTPS_PROXY")
    http_proxy = os.getenv("CODEX_HTTP_PROXY")
    configured_all_proxy = os.getenv("CODEX_ALL_PROXY")
    # Codex traffic is HTTPS. Keep ALL_PROXY aligned with the HTTPS bridge because
    # some SDK transports prefer ALL_PROXY over protocol-specific proxy variables.
    effective_all_proxy = https_proxy or http_proxy or configured_all_proxy
    if (
        configured_all_proxy
        and effective_all_proxy
        and configured_all_proxy != effective_all_proxy
    ):
        logger.warning(
            "CODEX_ALL_PROXY与HTTPS/HTTP代理不一致，Codex将使用协议代理: %s",
            effective_all_proxy,
        )

    proxy_mapping = {
        "HTTP_PROXY": (http_proxy, ("HTTP_PROXY", "http_proxy")),
        "HTTPS_PROXY": (https_proxy, ("HTTPS_PROXY", "https_proxy")),
        "ALL_PROXY": (effective_all_proxy, ("ALL_PROXY", "all_proxy")),
        "NO_PROXY": (os.getenv("CODEX_NO_PROXY"), ("NO_PROXY", "no_proxy")),
    }
    target_keys = [
        key
        for _, targets in proxy_mapping.values()
        for key in targets
    ]
    original = {key: os.environ.get(key) for key in target_keys}

    try:
        for value, target_keys_for_source in proxy_mapping.values():
            if not value:
                continue
            for target_key in target_keys_for_source:
                os.environ[target_key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
