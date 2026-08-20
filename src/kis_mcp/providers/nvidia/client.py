from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import NvidiaSettings, NvidiaSettingsError

RequestSender = Callable[[Request, float], bytes]
StreamSender = Callable[[Request, float], BinaryIO]
_RETRYABLE_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class NvidiaStreamResult:
    content: str
    finish_reason: str | None
    tool_calls: tuple[dict[str, Any], ...]
    telemetry: dict[str, Any]


class NvidiaNimError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


def _default_sender(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - approved fixed HTTPS provider URL
        return response.read()


def _default_stream_sender(request: Request, timeout: float) -> BinaryIO:
    return urlopen(request, timeout=timeout)  # type: ignore[return-value]  # noqa: S310


class NvidiaNimClient:
    """Small OpenAI-compatible NVIDIA NIM chat-completions client."""

    name = "nvidia-nim"

    def __init__(
        self,
        settings: NvidiaSettings,
        *,
        api_key: str,
        sender: RequestSender | None = None,
        stream_sender: StreamSender | None = None,
    ) -> None:
        if not api_key:
            raise NvidiaNimError("NVIDIA_NIM_API_KEY_MISSING", "NVIDIA NIM API key is unavailable")
        self.settings = settings
        self._api_key = api_key
        self._sender = sender or _default_sender
        self._stream_sender = stream_sender or _default_stream_sender

    def available(self) -> bool:
        return True

    def review(
        self,
        project_path: object,
        prompt: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        del project_path
        return self.complete(prompt, timeout_seconds=timeout_seconds)

    def review_with_model(
        self,
        project_path: object,
        prompt: str,
        model_profile: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        del project_path
        return self.complete(
            prompt,
            model_profile=model_profile,
            timeout_seconds=timeout_seconds,
        )

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

    def complete(
        self,
        prompt: str,
        model_profile: str | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
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
        timeout = float(self.settings.timeout_seconds)
        if timeout_seconds is not None:
            timeout = min(timeout, max(0.001, float(timeout_seconds)))
        return self._send_payload(payload, timeout=timeout)

    def complete_stream(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        reasoning_budget: int,
        enable_thinking: bool,
        timeout_seconds: float,
        soft_stall_seconds: float,
        hard_stall_seconds: float,
    ) -> NvidiaStreamResult:
        """Run one qualified reviewer request over SSE with provider-delta liveness."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise NvidiaNimError("NVIDIA_NIM_PROMPT_INVALID", "Prompt must be a non-empty string")
        if not isinstance(model, str) or not model.strip():
            raise NvidiaNimError("NVIDIA_NIM_MODEL_INVALID", "Model must be a non-empty string")
        if soft_stall_seconds <= 0 or hard_stall_seconds <= soft_stall_seconds:
            raise NvidiaNimError("NVIDIA_NIM_LIVENESS_INVALID", "Invalid liveness thresholds")
        payload = {
            "model": model.strip(),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
            "reasoning_budget": int(reasoning_budget),
            "chat_template_kwargs": {"enable_thinking": bool(enable_thinking)},
            "stream": True,
        }
        timeout = min(float(self.settings.timeout_seconds), max(0.001, float(timeout_seconds)))
        return self._send_stream_payload(
            payload,
            timeout=timeout,
            soft_stall_seconds=float(soft_stall_seconds),
            hard_stall_seconds=float(hard_stall_seconds),
        )

    def _send_payload(self, payload: dict[str, Any], *, timeout: float) -> str:
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

    def _send_stream_payload(
        self,
        payload: dict[str, Any],
        *,
        timeout: float,
        soft_stall_seconds: float,
        hard_stall_seconds: float,
    ) -> NvidiaStreamResult:
        request = Request(
            f"{self.settings.base_url}/chat/completions",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        started = time.monotonic()
        states: list[dict[str, Any]] = []

        def mark(state: str) -> None:
            states.append({"state": state, "elapsed_ms": round((time.monotonic() - started) * 1000)})

        mark("request_sent")
        try:
            response = self._stream_sender(request, timeout)
        except HTTPError as exc:
            details: dict[str, Any] = {"status": exc.code}
            retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
            if retry_after:
                details["retry_after"] = retry_after
            error_text = ""
            try:
                raw_error = exc.read(4096)
                if isinstance(raw_error, bytes):
                    error_text = raw_error.decode("utf-8", errors="replace")
                elif isinstance(raw_error, str):
                    error_text = raw_error
            except Exception:
                error_text = ""
            degraded = (
                exc.code == 400
                and "DEGRADED" in error_text.upper()
                and "FUNCTION CANNOT BE INVOKED" in error_text.upper()
            )
            if exc.code == 429:
                code = "NVIDIA_NIM_RATE_LIMITED"
            elif exc.code == 503:
                code = "NVIDIA_NIM_CAPACITY_PRESSURE"
            elif exc.code == 404:
                code = "NVIDIA_NIM_PROVIDER_UNAVAILABLE"
            elif degraded:
                code = "NVIDIA_NIM_PROVIDER_DEGRADED"
                details["provider_state"] = "degraded"
            else:
                code = "NVIDIA_NIM_HTTP_RETRYABLE" if exc.code in _RETRYABLE_HTTP_STATUSES else "NVIDIA_NIM_HTTP_FAILED"
            raise NvidiaNimError(code, "NVIDIA NIM returned an HTTP error", details) from exc
        except TimeoutError as exc:
            raise NvidiaNimError("NVIDIA_NIM_TIMEOUT", "NVIDIA NIM request timed out", {"timeout_seconds": timeout}) from exc
        except (URLError, OSError) as exc:
            raise NvidiaNimError("NVIDIA_NIM_TRANSPORT_FAILED", "NVIDIA NIM transport failed", {"error_type": type(exc).__name__}) from exc

        mark("accepted")
        events: queue.Queue[tuple[str, Any]] = queue.Queue()
        stop = threading.Event()

        def read_lines() -> None:
            try:
                while not stop.is_set():
                    line = response.readline()
                    if not line:
                        events.put(("eof", None))
                        return
                    events.put(("line", line))
            except Exception as exc:  # transport reader boundary
                events.put(("error", exc))

        reader = threading.Thread(target=read_lines, name="kis-nvidia-sse", daemon=True)
        reader.start()
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        delta_count = 0
        reasoning_delta_count = 0
        content_delta_count = 0
        soft_stalls = 0
        last_delta_at = time.monotonic()
        soft_stall_active = False
        try:
            while True:
                silence = time.monotonic() - last_delta_at
                if silence >= hard_stall_seconds:
                    mark("hard_stall")
                    stop.set()
                    try:
                        response.close()
                    except Exception:
                        pass
                    raise NvidiaNimError(
                        "NVIDIA_NIM_HARD_STALL",
                        "NVIDIA NIM stream produced no provider delta within the hard-stall window",
                        {"soft_stall_seconds": soft_stall_seconds, "hard_stall_seconds": hard_stall_seconds},
                    )
                if silence >= soft_stall_seconds and not soft_stall_active:
                    soft_stalls += 1
                    soft_stall_active = True
                    mark("soft_stall")
                next_boundary = hard_stall_seconds - silence
                if not soft_stall_active:
                    next_boundary = min(next_boundary, soft_stall_seconds - silence)
                try:
                    kind, value = events.get(timeout=max(0.001, next_boundary))
                except queue.Empty:
                    continue
                if kind == "error":
                    error = value
                    if isinstance(error, TimeoutError):
                        raise NvidiaNimError("NVIDIA_NIM_HARD_STALL", "NVIDIA NIM stream stalled", {"hard_stall_seconds": hard_stall_seconds}) from error
                    raise NvidiaNimError("NVIDIA_NIM_TRANSPORT_FAILED", "NVIDIA NIM stream transport failed", {"error_type": type(error).__name__}) from error
                if kind == "eof":
                    break
                raw_line = value
                if isinstance(raw_line, str):
                    line = raw_line.strip()
                else:
                    try:
                        line = bytes(raw_line).decode("utf-8").strip()
                    except UnicodeDecodeError as exc:
                        raise NvidiaNimError("NVIDIA_NIM_RESPONSE_INVALID", "NVIDIA NIM stream contained invalid UTF-8") from exc
                if not line or line.startswith(":") or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    document = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise NvidiaNimError("NVIDIA_NIM_RESPONSE_INVALID", "NVIDIA NIM stream contained malformed JSON") from exc
                choices = document.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                choice = choices[0]
                if not isinstance(choice, dict):
                    raise NvidiaNimError("NVIDIA_NIM_RESPONSE_INVALID", "NVIDIA NIM stream choice was malformed")
                delta = choice.get("delta") or {}
                if not isinstance(delta, dict):
                    raise NvidiaNimError("NVIDIA_NIM_RESPONSE_INVALID", "NVIDIA NIM stream delta was malformed")
                heartbeat = False
                reasoning = delta.get("reasoning_content", delta.get("reasoning"))
                if isinstance(reasoning, str) and reasoning:
                    heartbeat = True
                    reasoning_delta_count += 1
                    mark("thinking")
                text = delta.get("content")
                if isinstance(text, str) and text:
                    heartbeat = True
                    content_parts.append(text)
                    content_delta_count += 1
                    mark("outputting")
                raw_tools = delta.get("tool_calls")
                if isinstance(raw_tools, list) and raw_tools:
                    heartbeat = True
                    mark("tool_call")
                    self._merge_tool_call_deltas(tool_calls, raw_tools)
                if heartbeat:
                    delta_count += 1
                    last_delta_at = time.monotonic()
                    soft_stall_active = False
                raw_finish = choice.get("finish_reason")
                if isinstance(raw_finish, str) and raw_finish:
                    finish_reason = raw_finish
        finally:
            stop.set()
            try:
                response.close()
            except Exception:
                pass
        content = "".join(content_parts).strip()
        if finish_reason == "length":
            raise NvidiaNimError("NVIDIA_NIM_TRUNCATED", "NVIDIA NIM stream ended at the token limit", {"finish_reason": "length"})
        if not content and not tool_calls:
            raise NvidiaNimError("NVIDIA_NIM_RESPONSE_INVALID", "NVIDIA NIM stream returned no usable content")
        mark("completed")
        telemetry = {
            "transport": "sse",
            "states": states,
            "delta_count": delta_count,
            "reasoning_delta_count": reasoning_delta_count,
            "content_delta_count": content_delta_count,
            "tool_call_count": len(tool_calls),
            "soft_stall_count": soft_stalls,
            "finish_reason": finish_reason,
            "duration_ms": round((time.monotonic() - started) * 1000),
        }
        return NvidiaStreamResult(content, finish_reason, tuple(tool_calls[index] for index in sorted(tool_calls)), telemetry)

    @staticmethod
    def _merge_tool_call_deltas(target: dict[int, dict[str, Any]], deltas: list[Any]) -> None:
        for raw in deltas:
            if not isinstance(raw, dict) or isinstance(raw.get("index"), bool) or not isinstance(raw.get("index"), int):
                raise NvidiaNimError("NVIDIA_NIM_TOOL_CALL_INVALID", "NVIDIA NIM tool call delta was malformed")
            index = raw["index"]
            current = target.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
            if isinstance(raw.get("id"), str):
                current["id"] += raw["id"]
            if isinstance(raw.get("type"), str) and raw["type"]:
                current["type"] = raw["type"]
            function = raw.get("function")
            if isinstance(function, dict):
                if isinstance(function.get("name"), str):
                    current["function"]["name"] += function["name"]
                if isinstance(function.get("arguments"), str):
                    current["function"]["arguments"] += function["arguments"]


__all__ = ["NvidiaNimClient", "NvidiaNimError", "NvidiaStreamResult", "RequestSender", "StreamSender"]
