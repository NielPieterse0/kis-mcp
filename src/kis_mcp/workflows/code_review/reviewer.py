from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from .contracts import EvidenceCollector, ReviewBackend, ReviewEvidence
from .settings import AgentSettings

_REVIEW_PURPOSES = {
    "code-quality": (
        "Code-quality review purpose: assess correctness, regressions, error handling, "
        "tests, maintainability, and stated requirements. Report only evidence-backed findings."
    ),
    "safety-security": (
        "Safety/security review purpose: assess secrets, authentication and authorization, "
        "trust boundaries, injection and command execution, network and filesystem effects, "
        "data handling, race/TOCTOU risks, dependency and supply-chain risk, and policy bypass. "
        "Report only evidence-backed findings."
    ),
    "architecture": (
        "Architecture review purpose: assess module boundaries, dependency direction, cohesion, "
        "coupling, duplicated responsibility, public contracts, state ownership, extension seams, "
        "blast radius, and consistency with the repository architecture. Report only evidence-backed findings."
    ),
    "performance": (
        "Performance review purpose: assess algorithmic cost, blocking work, repeated I/O, "
        "unbounded loops or data growth, concurrency contention, excessive serialization, startup/runtime "
        "latency risks, and missing measurement evidence. Do not invent benchmarks. Report only evidence-backed findings."
    ),
    "test-quality": (
        "Test-quality review purpose: assess changed-behavior coverage, failure-path coverage, assertion quality, "
        "fixture realism, brittleness, isolation, determinism, missing regression tests, and verification gaps. "
        "Report only evidence-backed findings."
    ),
    "documentation": (
        "Documentation review purpose: assess public/current behavior claims, authority ownership, stale or duplicated "
        "facts, operational accuracy, missing user-facing changes, and code/documentation consistency. "
        "Treat repository authority as evidence and report only evidence-backed findings."
    ),
    "api-contracts": (
        "API/contracts review purpose: assess schema and interface compatibility, input/output invariants, versioning, "
        "error contracts, backward compatibility, serialization changes, provider/tool contracts, and missing contract tests. "
        "Report only evidence-backed findings."
    ),
}
_REVIEW_TYPES = frozenset(_REVIEW_PURPOSES)
_RETRYABLE_BACKEND_CODES = frozenset(
    {
        "CODEX_CLI_TIMEOUT",
        "NVIDIA_NIM_HTTP_RETRYABLE",
        "NVIDIA_NIM_TIMEOUT",
        "NVIDIA_NIM_TRANSPORT_FAILED",
    }
)
_FAILURE_CATEGORIES = {
    "CODEX_CLI_ENCODING_FAILED": "encoding",
    "CODEX_CLI_MUTATION_DETECTED": "safety",
    "CODEX_CLI_OUTPUT_LIMIT": "output_limit",
    "CODEX_CLI_PROCESS_FAILED": "process",
    "CODEX_CLI_RESPONSE_INVALID": "malformed_response",
    "CODEX_CLI_START_FAILED": "process_start",
    "CODEX_CLI_TIMEOUT": "timeout",
    "NVIDIA_NIM_HTTP_FAILED": "provider_http",
    "NVIDIA_NIM_HTTP_RETRYABLE": "provider_http",
    "NVIDIA_NIM_RESPONSE_INVALID": "malformed_response",
    "NVIDIA_NIM_TIMEOUT": "timeout",
    "NVIDIA_NIM_TRANSPORT_FAILED": "transport",
}
_SAFE_FAILURE_DETAIL_KEYS = frozenset(
    {"error_type", "max_output_chars", "returncode", "status", "timeout_seconds"}
)
_BENCHMARK_PROMPT = """You are being smoke-tested as a read-only software-review sub-agent. Analyze only the code below. Return exactly one JSON object with keys summary and findings. findings must be a list; each finding must contain category (exactly correctness or security), claim, and evidence. Identify at least one concrete correctness defect and at least one concrete security defect. Do not use tools or propose edits outside the snippet.

```python
import subprocess

def collect(ref, seen=[]):
    subprocess.run(f\"git show {ref}\", shell=True, check=True)
    seen.append(ref)
    return seen[-2]
```
"""


class UnavailableReviewBackend:
    def __init__(self, name: str) -> None:
        self.name = name

    def available(self) -> bool:
        return False

    def review(
        self,
        project_path: Path,
        prompt: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        del project_path, prompt, timeout_seconds
        raise RuntimeError(f"Backend unavailable: {self.name}")


def _json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            candidate = "\n".join(lines[1:-1])
            if candidate.lstrip().startswith("json"):
                candidate = candidate.lstrip()[4:].lstrip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _finding(value: Any) -> dict[str, Any] | None:
    required = {"severity", "path", "line", "claim", "evidence", "recommendation", "confidence"}
    if not isinstance(value, dict) or set(value) != required:
        return None
    normalized: dict[str, Any] = {}
    for key in ("severity", "path", "claim", "evidence", "recommendation", "confidence"):
        item = value.get(key)
        if not isinstance(item, str) or not item.strip():
            return None
        normalized[key] = item.strip()
    line = value.get("line")
    if line is not None and (not isinstance(line, int) or isinstance(line, bool) or line < 1):
        return None
    normalized["line"] = line
    return normalized


def _review_document(document: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[str]] | None:
    if set(document) != {"summary", "findings", "unknowns"}:
        return None
    summary = document.get("summary")
    findings_value = document.get("findings")
    unknowns_value = document.get("unknowns")
    if not isinstance(summary, str) or not summary.strip():
        return None
    if not isinstance(findings_value, list) or not isinstance(unknowns_value, list):
        return None
    findings: list[dict[str, Any]] = []
    for value in findings_value:
        normalized = _finding(value)
        if normalized is None:
            return None
        findings.append(normalized)
    unknowns: list[str] = []
    for value in unknowns_value:
        if not isinstance(value, str) or not value.strip():
            return None
        unknowns.append(value.strip())
    return summary.strip(), findings, unknowns


def _model_provenance(
    settings: AgentSettings, backend: str, model_profile: str | None
) -> dict[str, str]:
    if backend != "nvidia-nim" or model_profile is None:
        return {}
    return {
        "model_profile": model_profile,
        "model": settings.nvidia.profile(model_profile).model,
    }


def _safe_failure_details(exc: Exception) -> dict[str, Any]:
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return {}
    return {
        str(key): value
        for key, value in details.items()
        if str(key) in _SAFE_FAILURE_DETAIL_KEYS
        and (value is None or isinstance(value, (str, int, float, bool)))
    }


def _failure_attempt(backend: str, attempt: int, exc: Exception) -> dict[str, Any]:
    raw_code = getattr(exc, "code", None)
    code = raw_code if isinstance(raw_code, str) and raw_code else type(exc).__name__
    return {
        "backend": backend,
        "attempt": attempt,
        "status": "failed",
        "code": code,
        "category": _FAILURE_CATEGORIES.get(code, "backend"),
        "retryable": code in _RETRYABLE_BACKEND_CODES,
        "details": _safe_failure_details(exc),
    }


def _manual_fallback(
    review_type: str,
    reason: str = "all_configured_backends_failed_or_unavailable",
) -> dict[str, Any]:
    return {
        "required": True,
        "mode": "exact-diff",
        "review_type": review_type,
        "reason": reason,
    }


def _deadline_result(
    settings: AgentSettings,
    review_type: str,
    evidence: ReviewEvidence,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "agent_id": settings.agent_id,
        "status": "failed",
        "backend": None,
        "review_type": review_type,
        **evidence.provenance(),
        "summary": "The review deadline was exhausted before a valid review completed.",
        "findings": [],
        "unknowns": [],
        "diagnostics": ["AGENT_REVIEW_DEADLINE_EXCEEDED"],
        "attempts": attempts,
        "manual_fallback": _manual_fallback(review_type, "review_deadline_exceeded"),
    }


def _benchmark_quality(output: str) -> dict[str, Any]:
    document = _json_object(output)
    if document is None:
        return {"structured": False, "quality_pass": False, "categories": [], "summary": ""}
    findings = document.get("findings")
    categories: set[str] = set()
    proven: set[str] = set()
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            category = item.get("category")
            if not isinstance(category, str) or not category.strip():
                continue
            normalized = category.strip().casefold()
            categories.add(normalized)
            text = " ".join(
                value.strip().casefold()
                for value in (item.get("claim"), item.get("evidence"))
                if isinstance(value, str) and value.strip()
            )
            if normalized == "correctness" and any(
                anchor in text
                for anchor in (
                    "seen[-2]",
                    "indexerror",
                    "index error",
                    "first call",
                    "mutable default",
                    "default list",
                )
            ):
                proven.add("correctness")
            if normalized == "security" and (
                "shell=true" in text
                or "shell injection" in text
                or "command injection" in text
                or ("shell" in text and "ref" in text)
            ):
                proven.add("security")
    summary = document.get("summary")
    return {
        "structured": isinstance(findings, list),
        "quality_pass": {"correctness", "security"}.issubset(proven),
        "categories": sorted(categories),
        "summary": summary.strip() if isinstance(summary, str) else "",
    }


class CodeReviewAgent:
    """One bounded advisory reviewer with configurable provider/tool backends."""

    def __init__(
        self,
        settings: AgentSettings,
        *,
        collector: EvidenceCollector,
        backends: dict[str, ReviewBackend],
    ) -> None:
        self.settings = settings
        self._collector = collector
        self._backends = dict(backends)

    def _prompt(self, evidence: str, instructions: str, review_type: str) -> str:
        extra = instructions.strip() if isinstance(instructions, str) else ""
        purpose = _REVIEW_PURPOSES[review_type]
        return (
            "You are the kis-mcp code-reviewer agent. Review only the supplied source-bound "
            "repository evidence. Do not modify files, run mutating commands, commit, merge, "
            "or spawn another agent. Return exactly one JSON object with exactly the keys "
            "summary, findings, and unknowns. summary must be a non-empty string; findings "
            "and unknowns must be arrays. Each finding must contain exactly severity, path, "
            "line, claim, evidence, recommendation, and confidence; line may be null.\n\n"
            f"{purpose}\n\n"
            f"Additional operator instructions:\n{extra or '[none]'}\n\n"
            f"Repository evidence:\n{evidence}"
        )

    def _normalize(
        self,
        backend: str,
        output: str,
        *,
        review_type: str,
        evidence: ReviewEvidence,
        model_profile: str | None = None,
    ) -> dict[str, Any]:
        provenance = {
            **evidence.provenance(),
            **_model_provenance(self.settings, backend, model_profile),
        }
        if len(output) > self.settings.max_output_chars:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "failed",
                "backend": backend,
                "review_type": review_type,
                **provenance,
                "summary": "Review output exceeded the configured contract budget.",
                "findings": [],
                "unknowns": [],
                "diagnostics": ["AGENT_OUTPUT_TRUNCATED"],
                "manual_fallback": _manual_fallback(review_type, "review_output_truncated"),
            }
        document = _json_object(output)
        if document is None:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "failed",
                "backend": backend,
                "review_type": review_type,
                **provenance,
                "summary": "Review output was not a structured JSON object.",
                "findings": [],
                "unknowns": [],
                "diagnostics": ["AGENT_OUTPUT_NOT_STRUCTURED"],
                "manual_fallback": _manual_fallback(review_type, "review_output_not_structured"),
            }
        normalized = _review_document(document)
        if normalized is None:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "failed",
                "backend": backend,
                "review_type": review_type,
                **provenance,
                "summary": "Review output did not satisfy the strict result contract.",
                "findings": [],
                "unknowns": [],
                "diagnostics": ["AGENT_OUTPUT_CONTRACT_INVALID"],
                "manual_fallback": _manual_fallback(review_type, "review_output_contract_invalid"),
            }
        summary, findings, unknowns = normalized
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "completed",
            "backend": backend,
            "review_type": review_type,
            **provenance,
            "summary": summary,
            "findings": findings,
            "unknowns": unknowns,
            "diagnostics": [],
        }

    def _invalid_request(
        self,
        backend: str | None,
        model: str | None,
        diagnostic: str,
        summary: str,
        review_type: str | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "invalid_request",
            "backend": backend,
            "review_type": review_type,
            "model_profile": model,
            "summary": summary,
            "findings": [],
            "unknowns": [],
            "diagnostics": [diagnostic],
        }

    def benchmark_nvidia_model(self, model: str, runs: int = 1) -> dict[str, Any]:
        benchmark = self.settings.nvidia.benchmark
        if not self.settings.enabled or not self.settings.nvidia.enabled or not benchmark.enabled:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "disabled",
                "backend": "nvidia-nim",
                "model_alias": model if isinstance(model, str) else None,
                "summary": "NVIDIA benchmark is disabled.",
                "runs": [],
                "suitable": False,
                "diagnostics": ["AGENT_BENCHMARK_DISABLED"],
            }
        if not isinstance(model, str) or model not in benchmark.models:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "invalid_request",
                "backend": "nvidia-nim",
                "model_alias": model if isinstance(model, str) else None,
                "summary": "Requested NVIDIA benchmark model is not allowlisted.",
                "runs": [],
                "suitable": False,
                "diagnostics": ["AGENT_BENCHMARK_MODEL_UNKNOWN"],
            }
        if isinstance(runs, bool) or not isinstance(runs, int) or runs < 1 or runs > 3:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "invalid_request",
                "backend": "nvidia-nim",
                "model_alias": model,
                "model": benchmark.models[model],
                "summary": "Benchmark runs must be an integer from 1 through 3.",
                "runs": [],
                "suitable": False,
                "diagnostics": ["AGENT_BENCHMARK_RUNS_INVALID"],
            }

        selected = self._backends.get("nvidia-nim")
        benchmark_model = getattr(selected, "benchmark_model", None) if selected is not None else None
        if selected is None or not selected.available() or not callable(benchmark_model):
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "unavailable",
                "backend": "nvidia-nim",
                "model_alias": model,
                "model": benchmark.models[model],
                "summary": "NVIDIA benchmark backend is unavailable.",
                "runs": [],
                "suitable": False,
                "diagnostics": ["AGENT_BENCHMARK_BACKEND_UNAVAILABLE"],
            }

        run_results: list[dict[str, Any]] = []
        successful_latencies: list[int] = []
        quality_pass_count = 0
        for run_number in range(1, runs + 1):
            started = time.perf_counter()
            try:
                output = benchmark_model(_BENCHMARK_PROMPT, model)
            except Exception as exc:
                latency_ms = round((time.perf_counter() - started) * 1000)
                diagnostic = getattr(exc, "code", None)
                if not isinstance(diagnostic, str) or not diagnostic:
                    diagnostic = type(exc).__name__
                run_results.append(
                    {
                        "run": run_number,
                        "status": "failed",
                        "latency_ms": latency_ms,
                        "structured": False,
                        "quality_pass": False,
                        "categories": [],
                        "summary": "",
                        "output_chars": 0,
                        "diagnostic": diagnostic,
                    }
                )
                continue
            latency_ms = round((time.perf_counter() - started) * 1000)
            quality = _benchmark_quality(output)
            successful_latencies.append(latency_ms)
            if quality["quality_pass"]:
                quality_pass_count += 1
            run_results.append(
                {
                    "run": run_number,
                    "status": "completed",
                    "latency_ms": latency_ms,
                    **quality,
                    "output_chars": len(output),
                    "diagnostic": None,
                }
            )

        success_count = len(successful_latencies)
        median_latency_ms = (
            round(statistics.median(successful_latencies)) if successful_latencies else None
        )
        max_latency_ms = max(successful_latencies) if successful_latencies else None
        latency_limit_ms = benchmark.latency_limit_seconds * 1000
        latency_pass = (
            success_count == runs
            and max_latency_ms is not None
            and max_latency_ms <= latency_limit_ms
        )
        suitable = success_count == runs and quality_pass_count == runs and latency_pass
        status = "completed" if success_count == runs else "partial" if success_count else "failed"
        diagnostics: list[str] = []
        if success_count != runs:
            diagnostics.append("AGENT_BENCHMARK_RUN_FAILED")
        if quality_pass_count != runs:
            diagnostics.append("AGENT_BENCHMARK_QUALITY_FAILED")
        if not latency_pass:
            diagnostics.append("AGENT_BENCHMARK_LATENCY_FAILED")
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": status,
            "backend": "nvidia-nim",
            "model_alias": model,
            "model": benchmark.models[model],
            "runs_requested": runs,
            "success_count": success_count,
            "quality_pass_count": quality_pass_count,
            "latency_limit_ms": latency_limit_ms,
            "median_latency_ms": median_latency_ms,
            "max_latency_ms": max_latency_ms,
            "latency_pass": latency_pass,
            "suitable": suitable,
            "summary": "Model meets the configured benchmark bar." if suitable else "Model does not meet the configured benchmark bar.",
            "runs": run_results,
            "diagnostics": diagnostics,
        }

    def review(
        self,
        path: str | Path,
        instructions: str = "",
        backend: str | None = None,
        model: str | None = None,
        review_type: str = "code-quality",
        source: str = "working_tree",
        commit_ref: str | None = None,
        base_ref: str | None = None,
        head_ref: str | None = None,
        deadline_seconds: float | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        deadline_budget = float(self.settings.review_deadline_seconds)
        if deadline_seconds is not None:
            if (
                isinstance(deadline_seconds, bool)
                or not isinstance(deadline_seconds, (int, float))
                or deadline_seconds <= 0
            ):
                return self._invalid_request(
                    backend,
                    model,
                    "AGENT_REVIEW_DEADLINE_INVALID",
                    "Review deadline override must be a positive number of seconds.",
                    review_type if isinstance(review_type, str) else None,
                )
            deadline_budget = min(deadline_budget, float(deadline_seconds))
        deadline = started + deadline_budget
        project = Path(path).resolve()
        if not self.settings.enabled:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "disabled",
                "backend": backend,
                "review_type": review_type,
                "summary": "Code-review agent is disabled.",
                "findings": [],
                "unknowns": [],
                "diagnostics": ["AGENT_DISABLED"],
            }
        if not isinstance(review_type, str) or review_type not in _REVIEW_TYPES:
            return self._invalid_request(
                backend,
                model,
                "AGENT_REVIEW_TYPE_UNKNOWN",
                "Requested review type is not configured.",
                review_type if isinstance(review_type, str) else None,
            )
        if backend is not None and backend not in self._backends:
            return self._invalid_request(
                backend,
                model,
                "AGENT_BACKEND_UNKNOWN",
                "Requested backend is not configured.",
                review_type,
            )
        if model is not None:
            if not isinstance(model, str) or model not in self.settings.nvidia.profiles:
                return self._invalid_request(
                    backend,
                    model if isinstance(model, str) else None,
                    "AGENT_MODEL_UNKNOWN",
                    "Requested NVIDIA model profile is not configured.",
                )
            if backend is not None and backend != "nvidia-nim":
                return self._invalid_request(
                    backend,
                    model,
                    "AGENT_MODEL_BACKEND_CONFLICT",
                    "NVIDIA model profiles may be used only with the nvidia-nim backend.",
                )

        evidence = self._collector.collect(
            project,
            source=source,
            commit_ref=commit_ref,
            base_ref=base_ref,
            head_ref=head_ref,
        )
        if not evidence.complete:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "incomplete",
                "backend": None,
                "review_type": review_type,
                **evidence.provenance(),
                "summary": "Review evidence is incomplete; no backend was invoked.",
                "findings": [],
                "unknowns": [],
                "diagnostics": [*evidence.diagnostics, "AGENT_EVIDENCE_INCOMPLETE"],
                "attempts": [],
                "manual_fallback": _manual_fallback(review_type, "review_evidence_incomplete"),
            }
        prompt = self._prompt(evidence.content, instructions, review_type)
        order = (
            ["nvidia-nim"]
            if model is not None
            else ([backend] if backend is not None else [
                item
                for item in (self.settings.preferred_backend, self.settings.fallback_backend)
                if item is not None
            ])
        )
        attempts: list[dict[str, Any]] = []
        first_failure: tuple[str, str] | None = None
        first_unavailable: str | None = None
        for backend_name in order:
            if time.monotonic() >= deadline:
                return _deadline_result(self.settings, review_type, evidence, attempts)
            selected = self._backends.get(backend_name)
            if selected is None or not selected.available():
                if first_unavailable is None:
                    first_unavailable = backend_name
                attempts.append({
                    "backend": backend_name,
                    "attempt": 1,
                    "status": "unavailable",
                    "code": "AGENT_BACKEND_UNAVAILABLE",
                    "category": "availability",
                    "retryable": False,
                    "details": {},
                })
                continue
            selected_model = (
                model or self.settings.nvidia.default_profile
                if backend_name == "nvidia-nim"
                else None
            )
            for attempt_number in range(1, self.settings.max_backend_attempts + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return _deadline_result(self.settings, review_type, evidence, attempts)
                try:
                    if backend_name == "nvidia-nim" and selected_model is not None:
                        review_with_model = getattr(selected, "review_with_model", None)
                        output = (
                            review_with_model(
                                project,
                                prompt,
                                selected_model,
                                timeout_seconds=remaining,
                            )
                            if callable(review_with_model)
                            else selected.review(project, prompt, timeout_seconds=remaining)
                        )
                    else:
                        output = selected.review(project, prompt, timeout_seconds=remaining)
                except Exception as exc:
                    failure = _failure_attempt(backend_name, attempt_number, exc)
                    attempts.append(failure)
                    if first_failure is None:
                        first_failure = (backend_name, str(failure["code"]))
                    if time.monotonic() >= deadline:
                        return _deadline_result(self.settings, review_type, evidence, attempts)
                    if failure["retryable"] and attempt_number < self.settings.max_backend_attempts:
                        continue
                    break
                result = self._normalize(
                    backend_name,
                    output,
                    review_type=review_type,
                    evidence=evidence,
                    model_profile=selected_model,
                )
                attempts.append({
                    "backend": backend_name,
                    "attempt": attempt_number,
                    "status": "completed" if result["status"] == "completed" else "invalid",
                })
                if result["status"] == "completed":
                    result["attempts"] = attempts
                    return result
                implicit_fallback = backend is None and model is None and backend_name != order[-1]
                if implicit_fallback:
                    diagnostic = result.get("diagnostics", ["AGENT_OUTPUT_INVALID"])[0]
                    if first_failure is None:
                        first_failure = (backend_name, str(diagnostic))
                    break
                result["attempts"] = attempts
                return result
        provenance = evidence.provenance()
        if first_failure is not None:
            failed_backend, error_code = first_failure
            implicit_multi_backend = backend is None and model is None and len(order) > 1
            diagnostic = "AGENT_BACKENDS_FAILED" if implicit_multi_backend else f"AGENT_BACKEND_FAILED:{error_code}"
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "failed",
                "backend": failed_backend,
                "review_type": review_type,
                **provenance,
                "summary": "The configured review backend failed.",
                "findings": [],
                "unknowns": [],
                "diagnostics": [diagnostic],
                "attempts": attempts,
                "manual_fallback": _manual_fallback(review_type),
            }
        unavailable_backend = first_unavailable or (backend or self.settings.preferred_backend)
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "unavailable",
            "backend": unavailable_backend,
            "review_type": review_type,
            **provenance,
            "summary": "The requested review backend is unavailable.",
            "findings": [],
            "unknowns": [],
            "diagnostics": ["AGENT_BACKEND_UNAVAILABLE"],
            "attempts": attempts,
            "manual_fallback": _manual_fallback(review_type),
        }


__all__ = ["CodeReviewAgent", "UnavailableReviewBackend"]
