from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("files_spec", ("files spec", "file content", "resource_link", "resource link")),
    ("resource_namespaces", ("resource", "namespace", "uri")),
    ("mcp_tasks", ("mcp task", "tasks/", "task status", "task result")),
    ("required_instructions", ("instruction", "required instruction")),
    ("elicitation_safety", ("elicitation", "sensitive", "credential", "secret")),
    ("sampling_retry", ("sampling", "retry", "max tokens")),
    ("tool_result_schema", ("tool result", "outputschema", "structuredcontent", "schema")),
)

_REUSE_STAGES: dict[str, tuple[str, ...]] = {
    "resource_namespaces": ("discovery", "scaffold", "review"),
    "mcp_tasks": ("scaffold", "task_execution", "completion"),
    "required_instructions": ("scaffold", "task_execution", "review"),
    "elicitation_safety": ("scaffold", "task_execution", "review"),
    "sampling_retry": ("task_execution", "review"),
    "tool_result_schema": ("scaffold", "task_execution", "completion"),
    "files_spec": ("discovery", "scaffold", "review"),
}


def normalize_quality_evidence(diagnostic: Mapping[str, Any]) -> dict[str, Any]:
    text = " ".join(str(value) for value in diagnostic.values() if value is not None).lower()
    category = next(
        (name for name, tokens in _CATEGORY_RULES if any(token in text for token in tokens)),
        "app_specific",
    )
    return {
        "category": category,
        "scope": "mcp_baseline" if category != "app_specific" else "app_specific",
        "reuse_stages": list(_REUSE_STAGES.get(category, ("review",))),
        "diagnostic": dict(diagnostic),
    }


def quality_evidence_summary(diagnostics: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(normalize_quality_evidence(item) for item in diagnostics)


__all__ = ["normalize_quality_evidence", "quality_evidence_summary"]
