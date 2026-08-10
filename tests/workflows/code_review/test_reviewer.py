from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.providers.nvidia import nvidia_settings_from_mapping
from kis_mcp.tools.codex_cli import CodexSettings
from kis_mcp.workflows.code_review.reviewer import CodeReviewAgent
from kis_mcp.workflows.code_review.settings import AgentSettings


class FakeCollector:
    def __init__(self, evidence: str = "bounded evidence") -> None:
        self.evidence = evidence
        self.paths: list[Path] = []

    def collect(self, path: Path) -> str:
        self.paths.append(path)
        return self.evidence


class FakeBackend:
    def __init__(self, name: str, *, available: bool = True, output: str = "") -> None:
        self.name = name
        self._available = available
        self.output = output
        self.calls: list[tuple[Path, str]] = []

    def available(self) -> bool:
        return self._available

    def review(self, project_path: Path, prompt: str) -> str:
        self.calls.append((project_path, prompt))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class FakeNvidiaBackend(FakeBackend):
    def __init__(self, *, available: bool = True, output: str = "") -> None:
        super().__init__("nvidia-nim", available=available, output=output)
        self.model_calls: list[tuple[Path, str, str]] = []

    def review_with_model(self, project_path: Path, prompt: str, model_profile: str) -> str:
        self.model_calls.append((project_path, prompt, model_profile))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def _nvidia_settings():
    return nvidia_settings_from_mapping(
        {
            "enabled": True,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key_env": "NVIDIA_API_KEY",
            "secret_ref": "secret://provider/nvidia-nim/api-key",
            "default_profile": "super",
            "timeout_seconds": 30,
            "profiles": {
                "nano": {
                    "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                    "guidance": "Fast review.",
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "max_tokens": 65536,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
                "super": {
                    "model": "nvidia/nemotron-3-super-120b-a12b",
                    "guidance": "Default review.",
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_tokens": 16384,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
                "ultra": {
                    "model": "nvidia/nemotron-3-ultra-550b-a55b",
                    "guidance": "Deep review.",
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_tokens": 16384,
                    "reasoning_budget": 16384,
                    "enable_thinking": True,
                },
            },
        }
    )


def _settings() -> AgentSettings:
    return AgentSettings(
        enabled=True,
        agent_id="code-reviewer",
        preferred_backend="nvidia-nim",
        fallback_backend="codex-cli",
        max_evidence_chars=120000,
        max_output_chars=30000,
        nvidia=_nvidia_settings(),
        codex=CodexSettings(
            enabled=True,
            script_path=Path("script.ps1"),
            executable="codex",
            timeout_seconds=30,
            max_output_chars=30000,
        ),
    )


def _structured_output() -> str:
    return json.dumps(
        {
            "summary": "one issue",
            "findings": [
                {
                    "severity": "medium",
                    "path": "src/example.py",
                    "line": 7,
                    "claim": "Error is discarded",
                    "evidence": "Exception is swallowed",
                    "recommendation": "Propagate it",
                    "confidence": "high",
                }
            ],
            "unknowns": ["runtime behavior not exercised"],
        }
    )


def test_agent_uses_default_super_model_and_returns_provenance(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=_structured_output())
    codex = FakeBackend("codex-cli", output="unused")
    collector = FakeCollector()
    agent = CodeReviewAgent(
        _settings(), collector=collector, backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, instructions="focus on errors")

    assert result["agent_id"] == "code-reviewer"
    assert result["status"] == "completed"
    assert result["backend"] == "nvidia-nim"
    assert result["model_profile"] == "super"
    assert result["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert result["summary"] == "one issue"
    assert result["findings"][0]["severity"] == "medium"
    assert result["unknowns"] == ["runtime behavior not exercised"]
    assert codex.calls == []
    assert nvidia.model_calls[0][2] == "super"
    assert "bounded evidence" in nvidia.model_calls[0][1]
    assert "focus on errors" in nvidia.model_calls[0][1]
    assert "Do not modify files" in nvidia.model_calls[0][1]


def test_agent_explicit_model_without_backend_forces_nvidia(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="nano review")
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, model="nano")

    assert result["status"] == "completed_unstructured"
    assert result["backend"] == "nvidia-nim"
    assert result["model_profile"] == "nano"
    assert result["model"].endswith("a3b-reasoning")
    assert nvidia.model_calls[0][2] == "nano"
    assert codex.calls == []


def test_agent_explicit_ultra_backend_uses_ultra(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="ultra review")
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")},
    )

    result = agent.review(tmp_path, backend="nvidia-nim", model="ultra")

    assert result["backend"] == "nvidia-nim"
    assert result["model_profile"] == "ultra"
    assert result["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert nvidia.model_calls[0][2] == "ultra"


def test_agent_rejects_invalid_model_without_backend_calls(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="unused")
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, model="other")

    assert result["status"] == "invalid_request"
    assert result["diagnostics"] == ["AGENT_MODEL_UNKNOWN"]
    assert nvidia.calls == []
    assert nvidia.model_calls == []
    assert codex.calls == []


def test_agent_rejects_nvidia_model_with_codex_backend(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="unused")
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, backend="codex-cli", model="nano")

    assert result["status"] == "invalid_request"
    assert result["diagnostics"] == ["AGENT_MODEL_BACKEND_CONFLICT"]
    assert nvidia.model_calls == []
    assert codex.calls == []


def test_agent_model_selection_does_not_fallback_when_nvidia_unavailable(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(available=False)
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, model="nano")

    assert result["status"] == "unavailable"
    assert result["backend"] == "nvidia-nim"
    assert codex.calls == []


def test_agent_falls_back_when_preferred_backend_is_unavailable_without_model(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(available=False)
    codex = FakeBackend("codex-cli", output="plain review")
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": codex},
    )

    result = agent.review(tmp_path)

    assert result["status"] == "completed_unstructured"
    assert result["backend"] == "codex-cli"
    assert result["summary"] == "plain review"
    assert result["diagnostics"] == ["AGENT_OUTPUT_NOT_STRUCTURED"]
    assert "model_profile" not in result


def test_agent_explicit_backend_does_not_silently_switch(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(available=False)
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": codex},
    )

    result = agent.review(tmp_path, backend="nvidia-nim")

    assert result["status"] == "unavailable"
    assert result["backend"] == "nvidia-nim"
    assert codex.calls == []
    assert result["diagnostics"] == ["AGENT_BACKEND_UNAVAILABLE"]


def test_agent_returns_bounded_failure_without_exception_text(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=RuntimeError("secret upstream detail"))
    codex = FakeBackend("codex-cli", available=False)
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": codex},
    )

    result = agent.review(tmp_path)

    assert result["status"] == "failed"
    assert result["backend"] == "nvidia-nim"
    assert result["diagnostics"] == ["AGENT_BACKEND_FAILED:RuntimeError"]
    assert "secret upstream detail" not in str(result)
