from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import NvidiaSettings, NvidiaSettingsError

RequestSender = Callable[[Request, int], bytes]
_RETRYABLE_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


class NvidiaNimError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _default_sender(request: Request, timeout: int) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - approved fixed HTTPS provider URL
        return response.read()


class NvidiaNimClient:
    """Small OpenAI-compatible NVIDIA NIM chat-completions client."""

    name = "nvidia-nim"

    def __init__(
        self,
        settings: NvidiaSettings,
        *,
        api_key: str,
        sender: RequestSender | None = None,
    ) -> None:
        if not api_key:
            raise NvidiaNimError("NVIDIA_NIM_API_KEY_MISSING", "NVIDIA NIM API key is unavailable")
        self.settings = settings
        self._api_key = api_key
        self._sender = sender or _default_sender

    def available(self) -> bool:
        return True

    def review(self, project_path: object, prompt: str) -> str:
        del project_path
        return self.complete(prompt)

    def review_with_model(
        self, project_path: object, prompt: str, model_profile: str
    ) -> str:
        del project_path
        return self.complete(prompt, model_profile=model_profile)

    def benchmark_model(self, prompt: str, model_alias: str) -> str:
        """Run one allowlisted benchmark candidate with a portable minimal payload."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise NvidiaNimError("NVIDIA_NIM_PROMPT_INVALID", "Prompt must be a non-empty string")
        if not self.settings.benchmark.enabled:
            raise NvidiaNimError("NVIDIA_NIM_BENCHMARK_DISABLED", "NVIDIA NIM benchmark is disabled")
        try:
            model = self.settings.benchmark.model(model_alias)
        except NvidiaSettingsError as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_BENCHMARK_MODEL_INVALID",
                "NVIDIA NIM benchmark model is invalid",
            ) from exc
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": self.settings.benchmark.max_tokens,
            "stream": False,
        }
        return self._send_payload(payload, timeout=self.settings.benchmark.timeout_seconds)

    def complete(self, prompt: str, model_profile: str | None = None) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise NvidiaNimError("NVIDIA_NIM_PROMPT_INVALID", "Prompt must be a non-empty string")
        selected = model_profile or self.settings.default_profile
        try:
            profile = self.settings.profile(selected)
        except NvidiaSettingsError as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_MODEL_PROFILE_INVALID",
                "NVIDIA NIM model profile is invalid",
            ) from exc
        payload = {
            "model": profile.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "max_tokens": profile.max_tokens,
            "reasoning_budget": profile.reasoning_budget,
            "chat_template_kwargs": {"enable_thinking": profile.enable_thinking},
            "stream": False,
        }
        return self._send_payload(payload, timeout=self.settings.timeout_seconds)

    def _send_payload(self, payload: dict[str, Any], *, timeout: int) -> str:
        request = Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            raw = self._sender(request, timeout)
        except HTTPError as exc:
            code = (
                "NVIDIA_NIM_HTTP_RETRYABLE"
                if exc.code in _RETRYABLE_HTTP_STATUSES
                else "NVIDIA_NIM_HTTP_FAILED"
            )
            raise NvidiaNimError(
                code,
                "NVIDIA NIM returned an HTTP error",
                {"status": exc.code},
            ) from exc
        except TimeoutError as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_TIMEOUT",
                "NVIDIA NIM request timed out",
                {"timeout_seconds": timeout},
            ) from exc
        except (URLError, OSError) as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_TRANSPORT_FAILED",
                "NVIDIA NIM transport failed",
                {"error_type": type(exc).__name__},
            ) from exc
        try:
            document = json.loads(raw.decode("utf-8"))
            content = document["choices"][0]["message"]["content"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_RESPONSE_INVALID",
                "NVIDIA NIM response did not contain a chat message",
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise NvidiaNimError(
                "NVIDIA_NIM_RESPONSE_INVALID",
                "NVIDIA NIM response did not contain a chat message",
            )
        return content.strip()


__all__ = ["NvidiaNimClient", "NvidiaNimError", "RequestSender"]
