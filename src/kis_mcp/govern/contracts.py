from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GovernanceCapability:
    rule_id: str
    title: str
    description: str

    def to_json_dict(self) -> dict[str, str]:
        return {"rule_id": self.rule_id, "title": self.title, "description": self.description}


@dataclass(frozen=True, slots=True)
class AuthorityReference:
    order: int
    path: str
    description: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"order": self.order, "path": self.path, "description": self.description}


@dataclass(frozen=True, slots=True)
class OwnershipDeclaration:
    topic: str
    owner: str

    def to_json_dict(self) -> dict[str, str]:
        return {"topic": self.topic, "owner": self.owner}


@dataclass(frozen=True, slots=True)
class GovernanceFinding:
    finding_id: str
    rule_id: str
    severity: str
    title: str
    path: str | None
    observation: str
    evidence: tuple[str, ...]
    remediation: str
    confidence: str = "high"

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "path": self.path,
            "observation": self.observation,
            "evidence": list(self.evidence),
            "remediation": self.remediation,
            "confidence": self.confidence,
            "owning_plane": "govern",
        }


@dataclass(frozen=True, slots=True)
class GovernanceEvidence:
    project: str
    agents_text: str | None
    documents: tuple[tuple[str, str], ...]
    missing_paths: tuple[str, ...] = ()
    implementation_identifiers: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class RepositoryGovernanceReport:
    project: str
    authority_order: tuple[AuthorityReference, ...]
    ownership: tuple[OwnershipDeclaration, ...]
    findings: tuple[GovernanceFinding, ...]
    unknowns: tuple[str, ...]
    truncated: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool": "inspect_repository_governance",
            "project": self.project,
            "authority_order": [item.to_json_dict() for item in self.authority_order],
            "ownership": [item.to_json_dict() for item in self.ownership],
            "findings": [item.to_json_dict() for item in self.findings],
            "unknowns": list(self.unknowns),
            "truncated": self.truncated,
            "policy_effect": "advisory_only",
        }


__all__ = [
    "AuthorityReference",
    "GovernanceCapability",
    "GovernanceEvidence",
    "GovernanceFinding",
    "OwnershipDeclaration",
    "RepositoryGovernanceReport",
]
