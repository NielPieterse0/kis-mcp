from __future__ import annotations

import io
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from kis_mcp.providers import ProviderBoundary, ProviderKind, ProviderRegistry, ProviderState
from kis_mcp.providers.nvidia import (
    NvidiaNimClient,
    NvidiaNimError,
    NvidiaSettingsError,
    nvidia_provider_descriptor,
    nvidia_settings_from_mapping,
    register_nvidia_provider,
)


def _settings():
    return nvidia_settings_from_mapping(
        {
            "enabled": True,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key_env": "NVIDIA_API_KEY",
            "secret_ref": "secret://provider/nvidia-nim/api-key",
            "default_profile": "super",
            "timeout_seconds": 45,
            "benchmark": {
                "enabled": True,
                "timeout_seconds": 40,
                "latency_limit_seconds": 30,
                "max_tokens": 1024,
                "models": {
                    "baseline-super": "nvidia/nemotron-3-super-120b-a12b",
                    "laguna-xs": "poolside/laguna-xs-2.1",
                },
            },
            "profiles": {
                "nano": {
                    "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                    "guidance": "Fast first-pass and focused iterative review.",
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "max_tokens": 65536,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
                "super": {
                    "model": "nvidia/nemotron-3-super-120b-a12b",
                    "guidance": "Default substantive multi-file code review.",
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_tokens": 16384,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
                "ultra": {
                    "model": "nvidia/nemotron-3-ultra-550b-a55b",
                    "guidance": "Deepest high-impact architecture and safety-sensitive review.",
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_tokens": 16384,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
            },
        }
    )


def test_nvidia_settings_require_exact_three_profiles() -> None:
    settings = _settings()

    assert settings.default_profile == "super"
    assert tuple(settings.profiles) == ("nano", "super", "ultra")
    assert settings.profile("nano").max_tokens == 65536
    assert settings.profile("super").model == "nvidia/nemotron-3-super-120b-a12b"
    assert settings.profile("ultra").model == "nvidia/nemotron-3-ultra-550b-a55b"

    bad = {
        "enabled": settings.enabled,
        "base_url": settings.base_url,
        "api_key_env": settings.api_key_env,
        "secret_ref": settings.secret_ref,
        "default_profile": settings.default_profile,
        "timeout_seconds": settings.timeout_seconds,
        "benchmark": {
            "enabled": settings.benchmark.enabled,
            "timeout_seconds": settings.benchmark.timeout_seconds,
            "latency_limit_seconds": settings.benchmark.latency_limit_seconds,
            "max_tokens": settings.benchmark.max_tokens,
            "models": dict(settings.benchmark.models),
        },
        "profiles": {
            alias: {
                "model": profile.model,
                "guidance": profile.guidance,
                "temperature": profile.temperature,
                "top_p": profile.top_p,
                "max_tokens": profile.max_tokens,
                "reasoning_budget": profile.reasoning_budget,
                "enable_thinking": profile.enable_thinking,
            }
            for alias, profile in settings.profiles.items()
            if alias != "ultra"
        },
    }
    with pytest.raises(NvidiaSettingsError, match="profiles"):
        nvidia_settings_from_mapping(bad)


@pytest.mark.parametrize(
    ("alias", "model", "temperature", "max_tokens"),
    [
        ("nano", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", 0.6, 65536),
        ("super", "nvidia/nemotron-3-super-120b-a12b", 1.0, 16384),
        ("ultra", "nvidia/nemotron-3-ultra-550b-a55b", 1.0, 16384),
    ],
)
def test_nvidia_client_sends_exact_profile_payload(
    alias: str, model: str, temperature: float, max_tokens: int
) -> None:
    captured: dict[str, object] = {}

    def send(request: Request, timeout: int) -> bytes:
        captured["request"] = request
        captured["timeout"] = timeout
        return json.dumps(
            {"choices": [{"message": {"content": "review output"}}]}
        ).encode("utf-8")

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    result = client.complete("review this diff", model_profile=alias)

    request = captured["request"]
    assert isinstance(request, Request)
    assert request.full_url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer secret-value"
    assert request.get_header("Content-type") == "application/json"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload == {
        "model": model,
        "messages": [{"role": "user", "content": "review this diff"}],
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "reasoning_budget": 16384,
        "chat_template_kwargs": {"enable_thinking": True},
        "stream": False,
    }
    assert captured["timeout"] == 45
    assert result == "review output"


def test_nvidia_client_honors_tighter_per_review_timeout_budget() -> None:
    captured: dict[str, object] = {}

    def send(request: Request, timeout: float) -> bytes:
        captured["timeout"] = timeout
        return b'{"choices":[{"message":{"content":"ok"}}]}'

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    assert client.complete("prompt", timeout_seconds=3.5) == "ok"
    assert captured["timeout"] == 3.5


def test_nvidia_client_uses_default_profile_when_omitted() -> None:
    captured: dict[str, object] = {}

    def send(request: Request, _: int) -> bytes:
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return b'{"choices":[{"message":{"content":"ok"}}]}'

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    assert client.complete("prompt") == "ok"
    assert captured["payload"]["model"] == "nvidia/nemotron-3-super-120b-a12b"


def test_nvidia_client_rejects_malformed_response_without_leaking_key() -> None:
    def send(_: Request, __: int) -> bytes:
        return b'{"choices": []}'

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete("prompt")

    assert exc_info.value.code == "NVIDIA_NIM_RESPONSE_INVALID"
    assert "secret-value" not in str(exc_info.value)


def test_nvidia_readiness_distinguishes_missing_key_and_ready_with_guidance() -> None:
    missing = nvidia_provider_descriptor(_settings(), environ={}).readiness_probe()
    ready = nvidia_provider_descriptor(
        _settings(), environ={"NVIDIA_API_KEY": "secret-value"}
    ).readiness_probe()

    assert missing.state is ProviderState.DEGRADED
    assert missing.details == {"api_key_env": "NVIDIA_API_KEY"}
    assert ready.state is ProviderState.READY
    assert ready.details["default_profile"] == "super"
    assert ready.details["profiles"]["nano"]["model"].endswith("a3b-reasoning")
    assert "Fast" in ready.details["profiles"]["nano"]["guidance"]
    assert "Default" in ready.details["profiles"]["super"]["guidance"]
    assert "Deepest" in ready.details["profiles"]["ultra"]["guidance"]
    assert ready.details["benchmark"]["enabled"] is True
    assert ready.details["benchmark"]["latency_limit_seconds"] == 30
    assert ready.details["benchmark"]["models"]["laguna-xs"] == "poolside/laguna-xs-2.1"
    assert "secret-value" not in str(ready.to_json_dict())


def test_nvidia_provider_registers_as_approved_external_connector() -> None:
    registry = ProviderRegistry()

    descriptor = register_nvidia_provider(
        registry,
        settings=_settings(),
        environ={"NVIDIA_API_KEY": "secret-value"},
    )

    assert descriptor.provider_id == "nvidia-nim"
    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert [item.capability_id for item in descriptor.capabilities] == [
        "llm.inference.nvidia-nim"
    ]
    assert descriptor.capabilities[0].tool_names == ()
    assert registry.get("nvidia-nim") is descriptor


def test_nvidia_client_uses_portable_allowlisted_benchmark_payload() -> None:
    captured: dict[str, object] = {}

    def send(request: Request, timeout: int) -> bytes:
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return b'{"choices":[{"message":{"content":"benchmark ok"}}]}'

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)
    result = client.benchmark_model("review the snippet", "laguna-xs")

    assert result == "benchmark ok"
    assert captured["timeout"] == 40
    assert captured["payload"] == {
        "model": "poolside/laguna-xs-2.1",
        "messages": [{"role": "user", "content": "review the snippet"}],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 1024,
        "stream": False,
    }


@pytest.mark.parametrize(
    ("failure", "expected_code", "expected_details"),
    [
        (
            TimeoutError("timed out"),
            "NVIDIA_NIM_TIMEOUT",
            {"timeout_seconds": 45},
        ),
        (
            URLError("connection reset"),
            "NVIDIA_NIM_TRANSPORT_FAILED",
            {"error_type": "URLError"},
        ),
    ],
)
def test_nvidia_client_types_transport_failures(
    failure: Exception,
    expected_code: str,
    expected_details: dict[str, object],
) -> None:
    def send(_: Request, __: int) -> bytes:
        raise failure

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete("prompt")

    assert exc_info.value.code == expected_code
    assert exc_info.value.details == expected_details


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (429, "NVIDIA_NIM_HTTP_RETRYABLE"),
        (503, "NVIDIA_NIM_HTTP_RETRYABLE"),
        (400, "NVIDIA_NIM_HTTP_FAILED"),
    ],
)
def test_nvidia_client_classifies_http_failures(status: int, expected_code: str) -> None:
    def send(_: Request, __: int) -> bytes:
        raise HTTPError(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            status,
            "provider error",
            hdrs=None,
            fp=None,
        )

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete("prompt")

    assert exc_info.value.code == expected_code
    assert exc_info.value.details == {"status": status}


def test_nvidia_stream_collects_sse_content_and_liveness_telemetry() -> None:
    payloads: list[dict[str, object]] = []

    def stream_send(request: Request, timeout: float):
        payloads.append(json.loads(request.data.decode("utf-8")))
        body = (
            'data: {"choices":[{"delta":{"reasoning_content":"thinking"},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{"content":"{\\"summary\\":\\"ok\\","},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{"content":"\\"findings\\":[],\\"unknowns\\":[]}"},"finish_reason":"stop"}]}\n\n'
            'data: [DONE]\n\n'
        ).encode("utf-8")
        return io.BytesIO(body)

    client = NvidiaNimClient(_settings(), api_key="secret-value", stream_sender=stream_send)
    result = client.complete_stream(
        "review", model="nvidia/example", temperature=0, top_p=1, max_tokens=1024,
        reasoning_budget=0, enable_thinking=False, timeout_seconds=5,
        soft_stall_seconds=0.5, hard_stall_seconds=1,
    )

    assert json.loads(result.content)["summary"] == "ok"
    assert result.finish_reason == "stop"
    assert result.telemetry["transport"] == "sse"
    assert result.telemetry["reasoning_delta_count"] == 1
    assert result.telemetry["content_delta_count"] == 2
    assert payloads[0]["stream"] is True


class _StallingStream:
    def readline(self) -> bytes:
        time.sleep(0.2)
        return b""

    def close(self) -> None:
        return None


def test_nvidia_stream_hard_stall_is_typed_and_bounded() -> None:
    client = NvidiaNimClient(
        _settings(), api_key="secret-value", stream_sender=lambda request, timeout: _StallingStream()
    )

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete_stream(
            "review", model="nvidia/example", temperature=0, top_p=1, max_tokens=1024,
            reasoning_budget=0, enable_thinking=False, timeout_seconds=1,
            soft_stall_seconds=0.01, hard_stall_seconds=0.03,
        )

    assert exc_info.value.code == "NVIDIA_NIM_HARD_STALL"
    assert exc_info.value.details == {"soft_stall_seconds": 0.01, "hard_stall_seconds": 0.03}


def test_nvidia_stream_rejects_length_finish_reason() -> None:
    body = b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n'
    client = NvidiaNimClient(_settings(), api_key="secret-value", stream_sender=lambda request, timeout: io.BytesIO(body))

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete_stream(
            "review", model="nvidia/example", temperature=0, top_p=1, max_tokens=1024,
            reasoning_budget=0, enable_thinking=False, timeout_seconds=1,
            soft_stall_seconds=0.1, hard_stall_seconds=0.2,
        )

    assert exc_info.value.code == "NVIDIA_NIM_TRUNCATED"
    assert exc_info.value.details == {"finish_reason": "length"}


def test_nvidia_stream_classifies_rate_capacity_and_degraded_http() -> None:
    cases = (
        (429, b"rate limited", "NVIDIA_NIM_RATE_LIMITED"),
        (503, b"capacity", "NVIDIA_NIM_CAPACITY_PRESSURE"),
        (400, b"DEGRADED function cannot be invoked", "NVIDIA_NIM_PROVIDER_DEGRADED"),
        (404, b"not found", "NVIDIA_NIM_PROVIDER_UNAVAILABLE"),
        (400, b"invalid request", "NVIDIA_NIM_HTTP_FAILED"),
    )
    for status, body, expected in cases:
        def fail(request: Request, timeout: float, *, code: int = status, data: bytes = body):
            raise HTTPError(request.full_url, code, "provider error", hdrs=None, fp=io.BytesIO(data))

        client = NvidiaNimClient(_settings(), api_key="secret-value", stream_sender=fail)
        with pytest.raises(NvidiaNimError) as exc_info:
            client.complete_stream(
                "review", model="nvidia/example", temperature=0, top_p=1, max_tokens=1024,
                reasoning_budget=0, enable_thinking=False, timeout_seconds=1,
                soft_stall_seconds=0.1, hard_stall_seconds=0.2,
            )
        assert exc_info.value.code == expected


class _CommentOnlyStream:
    def __init__(self) -> None:
        self.closed = False

    def readline(self) -> bytes:
        time.sleep(0.005)
        return b"" if self.closed else b": keepalive\n"

    def close(self) -> None:
        self.closed = True


def test_nvidia_stream_comments_do_not_count_as_heartbeats() -> None:
    stream = _CommentOnlyStream()
    client = NvidiaNimClient(
        _settings(), api_key="secret-value", stream_sender=lambda request, timeout: stream
    )
    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete_stream(
            "review", model="nvidia/example", temperature=0, top_p=1, max_tokens=1024,
            reasoning_budget=0, enable_thinking=False, timeout_seconds=1,
            soft_stall_seconds=0.01, hard_stall_seconds=0.03,
        )
    assert exc_info.value.code == "NVIDIA_NIM_HARD_STALL"
