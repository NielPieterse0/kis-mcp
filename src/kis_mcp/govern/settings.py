from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_RULES = frozenset({
    "authority-order",
    "documentation-ownership",
    "owner-reference-integrity",
    "duplicate-owner",
    "duplicate-current-fact",
    "current-implementation-drift",
})


@dataclass(frozen=True, slots=True)
class GovernanceSettings:
    enabled: bool
    max_authority_documents: int
    max_file_bytes: int
    max_findings: int
    min_duplicate_paragraph_chars: int
    enabled_rules: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> "GovernanceSettings":
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "schema_version", "enabled", "max_authority_documents", "max_file_bytes",
            "max_findings", "min_duplicate_paragraph_chars", "enabled_rules",
        }
        if set(data) != expected or data.get("schema_version") != 1:
            raise ValueError("governance settings schema is invalid")
        if not isinstance(data["enabled"], bool):
            raise ValueError("governance enabled must be boolean")
        limits = {
            "max_authority_documents": (1, 100),
            "max_file_bytes": (1024, 1_000_000),
            "max_findings": (1, 1000),
            "min_duplicate_paragraph_chars": (80, 2000),
        }
        for name, (minimum, maximum) in limits.items():
            value = data[name]
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise ValueError(f"governance {name} is out of range")
        rules = data["enabled_rules"]
        if not isinstance(rules, list) or not rules or any(not isinstance(item, str) for item in rules):
            raise ValueError("governance enabled_rules must be a non-empty string array")
        if len(set(rules)) != len(rules) or not set(rules).issubset(_SUPPORTED_RULES):
            raise ValueError("governance enabled_rules contains unsupported or duplicate rules")
        return cls(
            enabled=data["enabled"],
            max_authority_documents=data["max_authority_documents"],
            max_file_bytes=data["max_file_bytes"],
            max_findings=data["max_findings"],
            min_duplicate_paragraph_chars=data["min_duplicate_paragraph_chars"],
            enabled_rules=tuple(rules),
        )


__all__ = ["GovernanceSettings"]
