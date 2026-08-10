from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import NvidiaSettings, NvidiaSettingsError

RequestSender = Callable[[Request, int], bytes]


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
            raw = self._sender(request, self.settings.timeout_seconds)
        except HTTPError as exc:
            raise NvidiaNimError(
                "NVIDIA_NIM_HTTP_FAILED",
                "NVIDIA NIM returned an HTTP error",
                {"status": exc.code},
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
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
