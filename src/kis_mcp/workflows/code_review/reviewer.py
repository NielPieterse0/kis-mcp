from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import EvidenceCollector, ReviewBackend
from .settings import AgentSettings


class UnavailableReviewBackend:
    def __init__(self, name: str) -> None:
        self.name = name

    def available(self) -> bool:
        return False

    def review(self, project_path: Path, prompt: str) -> str:
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
    if not isinstance(value, dict):
        return None
    claim = value.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        return None
    normalized: dict[str, Any] = {"claim": claim.strip()}
    for key in ("severity", "path", "evidence", "recommendation", "confidence"):
        item = value.get(key)
        normalized[key] = item.strip() if isinstance(item, str) else ""
    line = value.get("line")
    normalized["line"] = line if isinstance(line, int) and not isinstance(line, bool) else None
    return normalized


def _model_provenance(
    settings: AgentSettings, backend: str, model_profile: str | None
) -> dict[str, str]:
    if backend != "nvidia-nim" or model_profile is None:
        return {}
    return {
        "model_profile": model_profile,
        "model": settings.nvidia.profile(model_profile).model,
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

    def _prompt(self, evidence: str, instructions: str) -> str:
        extra = instructions.strip() if isinstance(instructions, str) else ""
        return (
            "You are the kis-mcp code-reviewer agent. Review only the supplied current "
            "working-tree evidence. Do not modify files, run mutating commands, commit, "
            "merge, or spawn another agent. Return one JSON object with keys summary, "
            "findings, and unknowns. Each finding must contain severity, path, line, "
            "claim, evidence, recommendation, and confidence.\n\n"
            f"Additional operator instructions:\n{extra or '[none]'}\n\n"
            f"Repository evidence:\n{evidence}"
        )

    def _normalize(
        self,
        backend: str,
        output: str,
        *,
        model_profile: str | None = None,
    ) -> dict[str, Any]:
        diagnostics: list[str] = []
        bounded = output
        provenance = _model_provenance(self.settings, backend, model_profile)
        if len(bounded) > self.settings.max_output_chars:
            bounded = bounded[: self.settings.max_output_chars]
            diagnostics.append("AGENT_OUTPUT_TRUNCATED")
        document = _json_object(bounded)
        if document is None:
            diagnostics.append("AGENT_OUTPUT_NOT_STRUCTURED")
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "completed_unstructured",
                "backend": backend,
                **provenance,
                "summary": bounded.strip(),
                "findings": [],
                "unknowns": [],
                "diagnostics": diagnostics,
            }
        summary = document.get("summary")
        findings_value = document.get("findings")
        unknowns_value = document.get("unknowns")
        findings = []
        if isinstance(findings_value, list):
            findings = [item for value in findings_value if (item := _finding(value))]
        unknowns = (
            [item.strip() for item in unknowns_value if isinstance(item, str) and item.strip()]
            if isinstance(unknowns_value, list)
            else []
        )
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "completed",
            "backend": backend,
            **provenance,
            "summary": summary.strip() if isinstance(summary, str) else "",
            "findings": findings,
            "unknowns": unknowns,
            "diagnostics": diagnostics,
        }

    def _invalid_request(
        self, backend: str | None, model: str | None, diagnostic: str, summary: str
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "invalid_request",
            "backend": backend,
            "model_profile": model,
            "summary": summary,
            "findings": [],
            "unknowns": [],
            "diagnostics": [diagnostic],
        }

    def review(
        self,
        path: str | Path,
        instructions: str = "",
        backend: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        project = Path(path).resolve()
        if not self.settings.enabled:
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "disabled",
                "backend": backend,
                "summary": "Code-review agent is disabled.",
                "findings": [],
                "unknowns": [],
                "diagnostics": ["AGENT_DISABLED"],
            }
        if backend is not None and backend not in self._backends:
            return self._invalid_request(
                backend,
                model,
                "AGENT_BACKEND_UNKNOWN",
                "Requested backend is not configured.",
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

        evidence = self._collector.collect(project)
        prompt = self._prompt(evidence, instructions)
        order = (
            ["nvidia-nim"]
            if model is not None
            else (
                [backend]
                if backend is not None
                else [
                    item
                    for item in (
                        self.settings.preferred_backend,
                        self.settings.fallback_backend,
                    )
                    if item is not None
                ]
            )
        )
        first_failure: tuple[str, str] | None = None
        first_unavailable: str | None = None
        for backend_name in order:
            selected = self._backends.get(backend_name)
            if selected is None or not selected.available():
                if first_unavailable is None:
                    first_unavailable = backend_name
                continue
            selected_model = (
                model or self.settings.nvidia.default_profile
                if backend_name == "nvidia-nim"
                else None
            )
            try:
                if backend_name == "nvidia-nim" and selected_model is not None:
                    review_with_model = getattr(selected, "review_with_model", None)
                    output = (
                        review_with_model(project, prompt, selected_model)
                        if callable(review_with_model)
                        else selected.review(project, prompt)
                    )
                else:
                    output = selected.review(project, prompt)
            except Exception as exc:
                if first_failure is None:
                    first_failure = (backend_name, type(exc).__name__)
                continue
            return self._normalize(
                backend_name,
                output,
                model_profile=selected_model,
            )
        if first_failure is not None:
            failed_backend, error_type = first_failure
            return {
                "schema_version": 1,
                "agent_id": self.settings.agent_id,
                "status": "failed",
                "backend": failed_backend,
                "summary": "The configured review backend failed.",
                "findings": [],
                "unknowns": [],
                "diagnostics": [f"AGENT_BACKEND_FAILED:{error_type}"],
            }
        unavailable_backend = first_unavailable or (backend or self.settings.preferred_backend)
        return {
            "schema_version": 1,
            "agent_id": self.settings.agent_id,
            "status": "unavailable",
            "backend": unavailable_backend,
            "summary": "The requested review backend is unavailable.",
            "findings": [],
            "unknowns": [],
            "diagnostics": ["AGENT_BACKEND_UNAVAILABLE"],
        }


__all__ = ["CodeReviewAgent", "UnavailableReviewBackend"]
