from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.providers.nvidia import NvidiaNimError, NvidiaStreamResult, nvidia_settings_from_mapping
from kis_mcp.tools.codex_cli import CodexCliError, CodexSettings
from kis_mcp.workflows.code_review.contracts import ReviewEvidence
from kis_mcp.workflows.code_review.reviewer import CodeReviewAgent
from kis_mcp.workflows.code_review.settings import AgentSettings


class FakeCollector:
    def __init__(self, evidence: str = "bounded evidence", *, complete: bool = True) -> None:
        self.evidence = evidence
        self.complete = complete
        self.paths: list[Path] = []
        self.requests: list[dict[str, object]] = []

    def collect(
        self,
        path: Path,
        *,
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        review_type: str = "code-quality",
    ) -> ReviewEvidence:
        self.paths.append(path)
        self.requests.append(
            {
                "source": source,
                "commit_ref": commit_ref,
                "base_ref": base_ref,
                "head_ref": head_ref,
            }
        )
        return ReviewEvidence(
            content=self.evidence,
            source=source,
            source_fingerprint="a" * 64,
            changed_files=("src/example.py",),
            included_files=("src/example.py",) if self.complete else (),
            omitted_files=() if self.complete else ("src/example.py",),
            complete=self.complete,
            commit_ref=commit_ref,
            base_ref=base_ref,
            head_ref=head_ref,
            diagnostics=() if self.complete else ("AGENT_EVIDENCE_FILES_OMITTED",),
        )


class FakeBackend:
    def __init__(self, name: str, *, available: bool = True, output: str = "") -> None:
        self.name = name
        self._available = available
        self.output = output
        self.calls: list[tuple[Path, str, float | None]] = []

    def available(self) -> bool:
        return self._available

    def review(
        self,
        project_path: Path,
        prompt: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        self.calls.append((project_path, prompt, timeout_seconds))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class FakeNvidiaBackend(FakeBackend):
    def __init__(self, *, available: bool = True, output: str = "") -> None:
        super().__init__("nvidia-nim", available=available, output=output)
        self.model_calls: list[tuple[Path, str, str, float | None]] = []
        self.stream_calls: list[dict[str, object]] = []
        self.benchmark_calls: list[tuple[str, str]] = []

    def review_with_model(
        self,
        project_path: Path,
        prompt: str,
        model_profile: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        self.model_calls.append((project_path, prompt, model_profile, timeout_seconds))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output

    def complete_stream(self, prompt: str, **kwargs: object) -> NvidiaStreamResult:
        self.stream_calls.append({"prompt": prompt, **kwargs})
        if isinstance(self.output, Exception):
            raise self.output
        return NvidiaStreamResult(
            content=self.output,
            finish_reason="stop",
            tool_calls=(),
            telemetry={"transport": "sse", "delta_count": 1},
        )

    def benchmark_model(self, prompt: str, model_alias: str) -> str:
        self.benchmark_calls.append((prompt, model_alias))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class SequenceBackend:
    def __init__(self, name: str, outcomes: list[str | Exception]) -> None:
        self.name = name
        self.outcomes = list(outcomes)
        self.calls: list[tuple[Path, str, float | None]] = []
        self.model_calls: list[tuple[Path, str, str, float | None]] = []

    def available(self) -> bool:
        return True

    def _next(self) -> str:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def review(
        self,
        project_path: Path,
        prompt: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        self.calls.append((project_path, prompt, timeout_seconds))
        return self._next()

    def review_with_model(
        self,
        project_path: Path,
        prompt: str,
        model_profile: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        self.model_calls.append((project_path, prompt, model_profile, timeout_seconds))
        return self._next()

    def complete_stream(self, prompt: str, **kwargs: object) -> NvidiaStreamResult:
        self.calls.append((Path("."), prompt, kwargs.get("timeout_seconds")))
        output = self._next()
        return NvidiaStreamResult(
            content=output,
            finish_reason="stop",
            tool_calls=(),
            telemetry={"transport": "sse", "delta_count": 1},
        )


def _nvidia_settings():
    return nvidia_settings_from_mapping(
        {
            "enabled": True,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key_env": "NVIDIA_API_KEY",
            "secret_ref": "secret://provider/nvidia-nim/api-key",
            "default_profile": "super",
            "timeout_seconds": 30,
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
        max_backend_attempts=2,
        review_deadline_seconds=120,
        nvidia=_nvidia_settings(),
        codex=CodexSettings(
            enabled=True,
            script_path=Path("script.ps1"),
            executable=r"C:\Projects\.kis-mcp\tools\codex\0.147.0\node_modules\.bin\codex.cmd",
            home_path=Path(r"C:\Projects\.kis-mcp\agent-hosts\codex-reviewer"),
            expected_version="0.147.0",
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


def _benchmark_output() -> str:
    return json.dumps(
        {
            "summary": "two concrete defects",
            "findings": [
                {"category": "correctness", "claim": "first call can fail", "evidence": "seen[-2]"},
                {"category": "security", "claim": "ref can inject shell syntax", "evidence": "shell=True"},
            ],
        }
    )


def test_agent_rejects_unknown_review_type_before_collecting_evidence(tmp_path: Path) -> None:
    collector = FakeCollector()
    nvidia = FakeNvidiaBackend(output="unused")
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=collector, backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, backend="codex-cli", review_type="other")

    assert result["status"] == "invalid_request"
    assert result["diagnostics"] == ["AGENT_REVIEW_TYPE_UNKNOWN"]
    assert collector.paths == []
    assert nvidia.calls == []
    assert codex.calls == []


def test_codex_code_quality_review_is_direct_and_purpose_specific(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="unused")
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, backend="codex-cli", review_type="code-quality")

    assert result["review_type"] == "code-quality"
    assert result["backend"] == "codex-cli"
    assert nvidia.model_calls == []
    assert len(codex.calls) == 1
    prompt = codex.calls[0][1]
    assert "Code-quality review purpose" in prompt
    assert "correctness" in prompt
    assert "regressions" in prompt
    assert "tests" in prompt


def test_codex_safety_security_review_is_direct_and_purpose_specific(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output="unused")
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, backend="codex-cli", review_type="safety-security")

    assert result["review_type"] == "safety-security"
    assert result["backend"] == "codex-cli"
    assert nvidia.model_calls == []
    assert len(codex.calls) == 1
    prompt = codex.calls[0][1]
    assert "Safety/security review purpose" in prompt
    assert "secrets" in prompt
    assert "trust boundaries" in prompt
    assert "command execution" in prompt
    assert "policy bypass" in prompt


def test_specialist_review_purposes_are_bounded_and_purpose_specific(tmp_path: Path) -> None:
    expected = {
        "architecture": ("Architecture review purpose", "dependency direction", "blast radius"),
        "performance": ("Performance review purpose", "blocking work", "Do not invent benchmarks"),
        "test-quality": ("Test-quality review purpose", "failure-path coverage", "verification gaps"),
        "documentation": ("Documentation review purpose", "authority ownership", "stale or duplicated"),
        "api-contracts": ("API/contracts review purpose", "backward compatibility", "contract tests"),
    }

    for review_type, phrases in expected.items():
        codex = FakeBackend("codex-cli", output=_structured_output())
        agent = CodeReviewAgent(
            _settings(),
            collector=FakeCollector(),
            backends={"nvidia-nim": FakeNvidiaBackend(output="unused"), "codex-cli": codex},
        )
        result = agent.review(tmp_path, backend="codex-cli", review_type=review_type)

        assert result["status"] == "completed"
        assert result["review_type"] == review_type
        assert len(codex.calls) == 1
        prompt = codex.calls[0][1]
        assert all(phrase in prompt for phrase in phrases)
        assert "Do not modify files" in prompt
        assert "spawn another agent" in prompt


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
    assert nvidia.model_calls == []
    assert nvidia.stream_calls[0]["model"] == "nvidia/nemotron-3-super-120b-a12b"
    prompt = str(nvidia.stream_calls[0]["prompt"])
    assert "bounded evidence" in prompt
    assert "focus on errors" in prompt
    assert "untrusted DATA" in prompt
    assert "PURPOSE FENCE" in prompt


def test_agent_explicit_model_without_backend_forces_nvidia(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=_structured_output())
    codex = FakeBackend("codex-cli", output="unused")
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": codex}
    )

    result = agent.review(tmp_path, model="nano")

    assert result["status"] == "completed"
    assert result["backend"] == "nvidia-nim"
    assert result["model_profile"] == "nano"
    assert result["model"].endswith("a3b-reasoning")
    assert nvidia.model_calls[0][2] == "nano"
    assert codex.calls == []


def test_agent_explicit_ultra_backend_uses_ultra(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=_structured_output())
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

    assert result["status"] == "unavailable"
    assert result["backend"] == "nvidia-nim"
    assert result["diagnostics"] == ["AGENT_BACKEND_UNAVAILABLE"]
    assert result["manual_fallback"]["mode"] == "exact-diff"
    assert codex.calls == []


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
    assert result["diagnostics"] == ["AGENT_QUALIFIED_ROUTES_FAILED"]
    assert result["manual_fallback"]["required"] is True
    assert "secret upstream detail" not in str(result)


def test_benchmark_nvidia_model_requires_quality_and_latency_without_collecting(tmp_path: Path) -> None:
    collector = FakeCollector()
    nvidia = FakeNvidiaBackend(output=_benchmark_output())
    agent = CodeReviewAgent(
        _settings(), collector=collector, backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")}
    )

    result = agent.benchmark_nvidia_model("laguna-xs", runs=2)

    assert result["status"] == "completed"
    assert result["model_alias"] == "laguna-xs"
    assert result["model"] == "poolside/laguna-xs-2.1"
    assert result["success_count"] == 2
    assert result["quality_pass_count"] == 2
    assert result["latency_pass"] is True
    assert result["suitable"] is True
    assert collector.paths == []
    assert len(nvidia.benchmark_calls) == 2
    assert "shell=True" in nvidia.benchmark_calls[0][0]
    assert nvidia.benchmark_calls[0][1] == "laguna-xs"


def test_benchmark_nvidia_model_rejects_unknown_alias_and_invalid_runs(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=_benchmark_output())
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")}
    )

    unknown = agent.benchmark_nvidia_model("other")
    invalid_runs = agent.benchmark_nvidia_model("laguna-xs", runs=4)

    assert unknown["status"] == "invalid_request"
    assert unknown["diagnostics"] == ["AGENT_BENCHMARK_MODEL_UNKNOWN"]
    assert invalid_runs["status"] == "invalid_request"
    assert invalid_runs["diagnostics"] == ["AGENT_BENCHMARK_RUNS_INVALID"]
    assert nvidia.benchmark_calls == []


def test_benchmark_nvidia_model_redacts_backend_failure_text(tmp_path: Path) -> None:
    nvidia = FakeNvidiaBackend(output=RuntimeError("secret upstream detail"))
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")}
    )
    result = agent.benchmark_nvidia_model("laguna-xs")
    assert result["status"] == "failed"
    assert result["suitable"] is False
    assert "secret upstream detail" not in str(result)


def test_benchmark_nvidia_model_rejects_unproven_category_labels(tmp_path: Path) -> None:
    output = json.dumps(
        {
            "summary": "labels without evidence",
            "findings": [
                {"category": "correctness", "claim": "something is wrong", "evidence": "unknown"},
                {"category": "security", "claim": "something is risky", "evidence": "unknown"},
            ],
        }
    )
    nvidia = FakeNvidiaBackend(output=output)
    agent = CodeReviewAgent(
        _settings(), collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")}
    )
    result = agent.benchmark_nvidia_model("laguna-xs")
    assert result["status"] == "completed"
    assert result["quality_pass_count"] == 0
    assert result["suitable"] is False
    assert "AGENT_BENCHMARK_QUALITY_FAILED" in result["diagnostics"]


def test_benchmark_nvidia_model_respects_disabled_benchmark(tmp_path: Path) -> None:
    settings = _settings()
    settings = replace(
        settings,
        nvidia=replace(
            settings.nvidia,
            benchmark=replace(settings.nvidia.benchmark, enabled=False),
        ),
    )
    nvidia = FakeNvidiaBackend(output=_benchmark_output())
    agent = CodeReviewAgent(
        settings, collector=FakeCollector(), backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")}
    )
    result = agent.benchmark_nvidia_model("laguna-xs")
    assert result["status"] == "disabled"
    assert result["diagnostics"] == ["AGENT_BENCHMARK_DISABLED"]
    assert nvidia.benchmark_calls == []


def test_agent_retries_typed_nvidia_timeout_then_recovers(tmp_path: Path) -> None:
    nvidia = SequenceBackend(
        "nvidia-nim",
        [
            NvidiaNimError(
                "NVIDIA_NIM_TIMEOUT",
                "timed out",
                {"timeout_seconds": 30},
            ),
            _structured_output(),
        ],
    )
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": FakeBackend("codex-cli")},
    )

    result = agent.review(tmp_path, backend="nvidia-nim", review_type="architecture")

    assert result["status"] == "completed"
    assert result["backend"] == "nvidia-nim"
    assert result["attempts"] == [
        {
            "backend": "nvidia-nim",
            "attempt": 1,
            "status": "failed",
            "code": "NVIDIA_NIM_TIMEOUT",
            "category": "timeout",
            "retryable": True,
            "details": {"timeout_seconds": 30},
        },
        {
            "backend": "nvidia-nim",
            "attempt": 2,
            "status": "completed",
        },
    ]


def test_agent_retries_codex_timeout_then_recovers(tmp_path: Path) -> None:
    codex = SequenceBackend(
        "codex-cli",
        [
            CodexCliError(
                "CODEX_CLI_TIMEOUT",
                "timed out",
                {"timeout_seconds": 30},
            ),
            _structured_output(),
        ],
    )
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(tmp_path, backend="codex-cli", review_type="api-contracts")

    assert result["status"] == "completed"
    assert result["backend"] == "codex-cli"
    assert [item["status"] for item in result["attempts"]] == ["failed", "completed"]
    assert result["attempts"][0] == {
        "backend": "codex-cli",
        "attempt": 1,
        "status": "failed",
        "code": "CODEX_CLI_TIMEOUT",
        "category": "timeout",
        "retryable": True,
        "details": {"timeout_seconds": 30},
    }


def test_agent_uses_implicit_fallback_after_invalid_preferred_backend_output(
    tmp_path: Path,
) -> None:
    nvidia = FakeNvidiaBackend(output="not-json")
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": codex},
    )

    result = agent.review(tmp_path, review_type="architecture")

    assert result["status"] == "failed"
    assert result["backend"] == "nvidia-nim"
    assert result["diagnostics"] == ["AGENT_QUALIFIED_ROUTES_FAILED"]
    assert [item["model_profile"] for item in result["attempts"]] == [
        "ultra", "ultra", "super", "super"
    ]
    assert all(item["status"] == "invalid" for item in result["attempts"])
    assert len(nvidia.stream_calls) == 4
    assert codex.calls == []


def test_agent_dual_backend_failure_requires_manual_exact_diff_fallback(
    tmp_path: Path,
) -> None:
    nvidia = SequenceBackend(
        "nvidia-nim",
        [
            NvidiaNimError("NVIDIA_NIM_TIMEOUT", "timed out", {"timeout_seconds": 30}),
            NvidiaNimError("NVIDIA_NIM_TIMEOUT", "timed out", {"timeout_seconds": 30}),
        ],
    )
    codex = SequenceBackend(
        "codex-cli",
        [CodexCliError("CODEX_CLI_PROCESS_FAILED", "process failed", {"returncode": 7})],
    )
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": nvidia, "codex-cli": codex},
    )

    result = agent.review(tmp_path, review_type="architecture")

    assert result["status"] == "failed"
    assert result["diagnostics"] == ["AGENT_QUALIFIED_ROUTES_FAILED"]
    assert [item["backend"] for item in result["attempts"]] == [
        "nvidia-nim",
        "nvidia-nim",
        "nvidia-nim",
    ]
    assert [item["model_profile"] for item in result["attempts"]] == ["ultra", "ultra", "super"]
    assert [item["retryable"] for item in result["attempts"]] == [True, True, False]
    assert codex.calls == []
    assert result["manual_fallback"] == {
        "required": True,
        "mode": "exact-diff",
        "review_type": "architecture",
        "reason": "all_configured_backends_failed_or_unavailable",
    }
    assert "timed out" not in str(result)
    assert "process failed" not in str(result)


def test_agent_binds_commit_source_and_returns_kis_owned_provenance(tmp_path: Path) -> None:
    collector = FakeCollector()
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(),
        collector=collector,
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(
        tmp_path,
        backend="codex-cli",
        review_type="api-contracts",
        source="commit",
        commit_ref="abc123",
    )

    assert result["status"] == "completed"
    assert result["source"] == "commit"
    assert result["source_fingerprint"] == "a" * 64
    assert result["commit_ref"] == "abc123"
    assert result["evidence_complete"] is True
    assert collector.requests == [
        {"source": "commit", "commit_ref": "abc123", "base_ref": None, "head_ref": None}
    ]


def test_agent_rejects_incomplete_evidence_without_invoking_backend(tmp_path: Path) -> None:
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(complete=False),
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(tmp_path, backend="codex-cli")

    assert result["status"] == "incomplete"
    assert result["evidence_complete"] is False
    assert result["diagnostics"] == ["AGENT_EVIDENCE_FILES_OMITTED", "AGENT_EVIDENCE_INCOMPLETE"]
    assert codex.calls == []


def test_agent_rejects_empty_and_schema_invalid_review_output(tmp_path: Path) -> None:
    for output, diagnostic in (
        ("", "AGENT_OUTPUT_NOT_STRUCTURED"),
        (json.dumps({"summary": "", "findings": [], "unknowns": []}), "AGENT_OUTPUT_CONTRACT_INVALID"),
        (json.dumps({"summary": "ok", "findings": [{}], "unknowns": []}), "AGENT_OUTPUT_CONTRACT_INVALID"),
    ):
        codex = FakeBackend("codex-cli", output=output)
        agent = CodeReviewAgent(
            _settings(),
            collector=FakeCollector(),
            backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
        )
        result = agent.review(tmp_path, backend="codex-cli")
        assert result["status"] == "failed"
        assert result["diagnostics"] == [diagnostic]
        assert result["manual_fallback"]["required"] is True


def test_agent_stops_retrying_when_total_review_deadline_is_exhausted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    clock = iter((0.0, 0.0, 0.0, 2.0))
    monkeypatch.setattr("kis_mcp.workflows.code_review.reviewer.time.monotonic", lambda: next(clock))
    codex = SequenceBackend(
        "codex-cli",
        [CodexCliError("CODEX_CLI_TIMEOUT", "timed out", {"timeout_seconds": 1}), _structured_output()],
    )
    agent = CodeReviewAgent(
        replace(_settings(), review_deadline_seconds=1),
        collector=FakeCollector(),
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(tmp_path, backend="codex-cli")

    assert result["status"] == "failed"
    assert result["diagnostics"] == ["AGENT_REVIEW_DEADLINE_EXCEEDED"]
    assert len(codex.calls) == 1
    assert codex.calls[0][2] == 1.0
    assert result["manual_fallback"]["reason"] == "review_deadline_exceeded"


def test_agent_caps_configured_deadline_with_tighter_caller_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    clock = iter((0.0, 0.0, 0.0))
    monkeypatch.setattr("kis_mcp.workflows.code_review.reviewer.time.monotonic", lambda: next(clock))
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(
        tmp_path,
        backend="codex-cli",
        deadline_seconds=2.5,
    )

    assert result["status"] == "completed"
    assert codex.calls[0][2] == 2.5


@pytest.mark.parametrize("value", [0, -1, True, "2"])
def test_agent_rejects_invalid_caller_deadline(tmp_path: Path, value: object) -> None:
    codex = FakeBackend("codex-cli", output=_structured_output())
    agent = CodeReviewAgent(
        _settings(),
        collector=FakeCollector(),
        backends={"nvidia-nim": FakeNvidiaBackend(), "codex-cli": codex},
    )

    result = agent.review(tmp_path, backend="codex-cli", deadline_seconds=value)  # type: ignore[arg-type]

    assert result["status"] == "invalid_request"
    assert result["diagnostics"] == ["AGENT_REVIEW_DEADLINE_INVALID"]
    assert codex.calls == []
