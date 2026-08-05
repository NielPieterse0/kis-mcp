from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.providers.nvidia import NvidiaSettings
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


def _settings() -> AgentSettings:
    return AgentSettings(
        enabled=True,
        agent_id="code-reviewer",
        preferred_backend="nvidia-nim",
        fallback_backend="codex-cli",
        max_evidence_chars=120000,
        max_output_chars=30000,
        nvidia=NvidiaSettings(
            enabled=True,
            base_url="https://integrate.api.nvidia.com/v1",
            model="model",
            api_key_env="NVIDIA_API_KEY",
            timeout_seconds=30,
            temperature=0.1,
            max_tokens=1000,
        ),
        codex=CodexSettings(
            enabled=True,
            script_path=Path("script.ps1"),
            executable="codex",
            timeout_seconds=30,
            max_output_chars=30000,
        ),
    )


def test_agent_uses_preferred_backend_and_normalizes_structured_result(tmp_path: Path) -> None:
    output = json.dumps(
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
    nvidia = FakeBackend("nvidia-nim", output=output)
    codex = FakeBackend("codex-cli", output="unused")
    collector = FakeCollector()
    agent = CodeReviewAgent(
        _settings(), collector=collector, backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, instructions="focus on errors")

    assert result["agent_id"] == "code-reviewer"
    assert result["status"] == "completed"
    assert result["backend"] == "nvidia-nim"
    assert result["summary"] == "one issue"
    assert result["findings"][0]["severity"] == "medium"
    assert result["unknowns"] == ["runtime behavior not exercised"]
    assert codex.calls == []
    assert "bounded evidence" in nvidia.calls[0][1]
    assert "focus on errors" in nvidia.calls[0][1]
    assert "Do not modify files" in nvidia.calls[0][1]


def test_agent_falls_back_when_preferred_backend_is_unavailable(tmp_path: Path) -> None:
    nvidia = FakeBackend("nvidia-nim", available=False)
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


def test_agent_explicit_backend_does_not_silently_switch(tmp_path: Path) -> None:
    nvidia = FakeBackend("nvidia-nim", available=False)
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
    nvidia = FakeBackend("nvidia-nim", output=RuntimeError("secret upstream detail"))
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
