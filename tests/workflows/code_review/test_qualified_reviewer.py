from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.providers.nvidia import NvidiaNimError, NvidiaStreamResult
from kis_mcp.workflows.code_review.contracts import ReviewEvidence
from kis_mcp.workflows.code_review.reviewer import CodeReviewAgent
from kis_mcp.workflows.code_review.routing import ROUTES, profile_for
from kis_mcp.workflows.code_review.settings import load_agent_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _review(findings: list[dict[str, object]] | None = None) -> str:
    return json.dumps({
        "summary": "reviewed",
        "findings": findings or [],
        "unknowns": [],
    })


def _finding(path: str = "src/example.py") -> dict[str, object]:
    return {
        "severity": "high", "path": path, "line": 7,
        "claim": "Concrete failure", "evidence": "Exact source evidence",
        "recommendation": "Fix the demonstrated failure", "confidence": "high",
    }


class Collector:
    def __init__(self, fingerprints: tuple[str, ...] = ("a" * 64,)) -> None:
        self.fingerprints = list(fingerprints)
        self.calls: list[str] = []

    def collect(self, path: Path, **kwargs: object) -> ReviewEvidence:
        del path
        self.calls.append(str(kwargs.get("review_type")))
        fingerprint = self.fingerprints.pop(0) if len(self.fingerprints) > 1 else self.fingerprints[0]
        return ReviewEvidence(
            content="bounded source evidence",
            source=str(kwargs.get("source", "working_tree")),
            source_fingerprint=fingerprint,
            changed_files=("src/example.py",),
            included_files=("src/example.py",),
            omitted_files=(),
            complete=True,
            projector="test-projector",
        )


class QualifiedBackend:
    name = "nvidia-nim"

    def __init__(self, outcomes: list[str | Exception | NvidiaStreamResult]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def available(self) -> bool:
        return True

    def complete_stream(self, prompt: str, **kwargs: object) -> NvidiaStreamResult:
        self.calls.append({"prompt": prompt, **kwargs})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, NvidiaStreamResult):
            return outcome
        return NvidiaStreamResult(
            content=outcome,
            finish_reason="stop",
            tool_calls=(),
            telemetry={"transport": "sse", "delta_count": 2},
        )


def _agent(backend: QualifiedBackend, collector: Collector | None = None) -> CodeReviewAgent:
    return CodeReviewAgent(
        load_agent_settings(REPOSITORY_ROOT),
        collector=collector or Collector(),
        backends={"nvidia-nim": backend},
    )


def test_qualified_route_matrix_is_exact() -> None:
    expected = {
        "code-quality": ("super", "ultra"),
        "safety-security": ("lightning", "ultra"),
        "architecture": ("ultra", "super"),
        "performance": ("super", "lightning"),
        "test-quality": ("super", "nano-text"),
        "documentation": ("lightning", "super"),
        "api-contracts": ("nano-omni", "super"),
    }
    assert {name: (ROUTES[name].primary, ROUTES[name].backup) for name in expected} == expected
    assert profile_for("lightning").model == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert profile_for("nano-text").model == "nvidia/nemotron-3-nano-30b-a3b"


def test_automatic_review_uses_route_streaming_and_no_codex_fallback(tmp_path: Path) -> None:
    backend = QualifiedBackend([_review()])
    result = _agent(backend).review(tmp_path, review_type="documentation")

    assert result["status"] == "completed"
    assert result["model_profile"] == "lightning"
    assert backend.calls[0]["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert backend.calls[0]["temperature"] == 0.0
    assert backend.calls[0]["soft_stall_seconds"] == 10
    assert backend.calls[0]["hard_stall_seconds"] == 30
    assert "untrusted DATA" in str(backend.calls[0]["prompt"])


def test_rate_limit_retries_then_falls_to_route_backup(tmp_path: Path) -> None:
    backend = QualifiedBackend([
        NvidiaNimError("NVIDIA_NIM_RATE_LIMITED", "rate", {"status": 429}),
        NvidiaNimError("NVIDIA_NIM_RATE_LIMITED", "rate", {"status": 429}),
        _review(),
    ])
    result = _agent(backend).review(tmp_path, review_type="performance")

    assert result["status"] == "completed"
    assert result["model_profile"] == "lightning"
    assert [item["model_profile"] for item in result["attempts"]] == ["super", "super", "lightning"]


def test_completed_review_is_rejected_when_source_changes(tmp_path: Path) -> None:
    collector = Collector(("a" * 64, "b" * 64))
    backend = QualifiedBackend([_review()])
    result = _agent(backend, collector).review(tmp_path, review_type="code-quality")

    assert result["status"] == "stale"
    assert result["findings"] == []
    assert result["diagnostics"] == ["AGENT_REVIEW_SOURCE_STALE"]
    assert collector.calls == ["code-quality", "code-quality"]


def test_unexpected_tool_call_is_never_accepted(tmp_path: Path) -> None:
    tool_result = NvidiaStreamResult(
        content=_review(),
        finish_reason="tool_calls",
        tool_calls=({"function": {"name": "inspect_project", "arguments": "{}"}},),
        telemetry={"transport": "sse"},
    )
    backend = QualifiedBackend([tool_result, tool_result])
    result = _agent(backend).review(tmp_path, review_type="code-quality")

    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["diagnostics"] == ["AGENT_QUALIFIED_ROUTES_FAILED"]
    assert all(item["code"] == "AGENT_UNEXPECTED_TOOL_CALL" for item in result["attempts"])


def test_security_discovery_is_corroborated_and_super_adjudicated(tmp_path: Path) -> None:
    discovery = _review([_finding()])
    adjudication = json.dumps({
        "decisions": [
            {"candidate_index": 0, "accepted": True, "rationale": "Exploit path is evidenced"}
        ]
    })
    backend = QualifiedBackend([discovery, adjudication])
    result = _agent(backend).review(tmp_path, review_type="safety-security")

    assert result["status"] == "completed"
    assert result["model_profile"] == "lightning"
    assert len(result["findings"]) == 1
    assert backend.calls[0]["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert backend.calls[1]["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert result["attempts"][0]["stage"] == "security-adjudication"


def test_security_cardinality_loss_fails_closed_through_adjudicator_fallback(tmp_path: Path) -> None:
    discovery = _review([_finding()])
    bad_adjudication = json.dumps({"decisions": []})
    backend = QualifiedBackend([discovery, bad_adjudication, bad_adjudication])
    result = _agent(backend).review(tmp_path, review_type="safety-security")

    assert result["status"] == "failed"
    assert result["findings"] == []
    codes = [item.get("code") for item in result["attempts"]]
    assert codes.count("AGENT_SECURITY_CARDINALITY_INVALID") == 2
