from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

import pytest

from kis_mcp.providers import ProviderBoundary, ProviderKind, ProviderRegistry, ProviderState
from kis_mcp.providers.nvidia import (
    NvidiaNimClient,
    NvidiaNimError,
    NvidiaSettings,
    nvidia_provider_descriptor,
    register_nvidia_provider,
)


def _settings() -> NvidiaSettings:
    return NvidiaSettings(
        enabled=True,
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.3-70b-instruct",
        api_key_env="NVIDIA_API_KEY",
        timeout_seconds=45,
        temperature=0.1,
        max_tokens=2048,
    )


def test_nvidia_client_sends_openai_compatible_chat_completion() -> None:
    captured: dict[str, object] = {}

    def send(request: Request, timeout: int) -> bytes:
        captured["request"] = request
        captured["timeout"] = timeout
        return json.dumps(
            {"choices": [{"message": {"content": "review output"}}]}
        ).encode("utf-8")

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    result = client.complete("review this diff")

    request = captured["request"]
    assert isinstance(request, Request)
    assert request.full_url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer secret-value"
    assert request.get_header("Content-type") == "application/json"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload == {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "review this diff"}],
        "temperature": 0.1,
        "max_tokens": 2048,
        "stream": False,
    }
    assert captured["timeout"] == 45
    assert result == "review output"


def test_nvidia_client_rejects_malformed_response_without_leaking_key() -> None:
    def send(_: Request, __: int) -> bytes:
        return b'{"choices": []}'

    client = NvidiaNimClient(_settings(), api_key="secret-value", sender=send)

    with pytest.raises(NvidiaNimError) as exc_info:
        client.complete("prompt")

    assert exc_info.value.code == "NVIDIA_NIM_RESPONSE_INVALID"
    assert "secret-value" not in str(exc_info.value)


def test_nvidia_readiness_distinguishes_missing_key_and_ready() -> None:
    missing = nvidia_provider_descriptor(_settings(), environ={}).readiness_probe()
    ready = nvidia_provider_descriptor(
        _settings(), environ={"NVIDIA_API_KEY": "secret-value"}
    ).readiness_probe()

    assert missing.state is ProviderState.DEGRADED
    assert missing.details == {"api_key_env": "NVIDIA_API_KEY"}
    assert ready.state is ProviderState.READY
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
