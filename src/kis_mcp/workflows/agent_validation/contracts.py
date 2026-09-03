from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import quality_evidence_summary


@dataclass(frozen=True, slots=True)
class AgentValidationResult:
    project: str
    target: str
    strict: bool
    max_files: int
    version: str
    files_checked: int
    diagnostics: tuple[dict[str, Any], ...]
    errors: int
    warnings: int
    info: int
    truncated: bool = False

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "contract": "agent-configuration-validation-v1",
            "tool": "validate_agent_configuration",
            "project": self.project,
            "target": self.target,
            "strict": self.strict,
            "max_files": self.max_files,
            "version": self.version,
            "files_checked": self.files_checked,
            "summary": {"errors": self.errors, "warnings": self.warnings, "info": self.info},
            "diagnostics": [dict(item) for item in self.diagnostics],
            "quality_evidence": [dict(item) for item in quality_evidence_summary(self.diagnostics)],
            "truncated": self.truncated,
        }


__all__ = ["AgentValidationResult"]
