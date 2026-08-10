from __future__ import annotations

import json
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
