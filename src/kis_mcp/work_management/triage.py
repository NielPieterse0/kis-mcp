from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .backend import ProjectItem, ProjectItemKind
from .canonical_contracts import load_canonical_work_contracts
from .command_settings import CommandPlaneSettings

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_MISSING = object()


def _field(item: ProjectItem, name: str) -> object:
    target = name.casefold()
    for value in item.field_values:
        if value.field_name.casefold() == target:
            return value.value
    return _MISSING


def _present(value: object) -> bool:
    return value is not _MISSING and value is not None and (
        not isinstance(value, str) or bool(value.strip())
    )


def _headings(body: str) -> frozenset[str]:
    return frozenset(match.group(1).strip().casefold() for match in _HEADING.finditer(body))


@dataclass(frozen=True, slots=True)
class TriageEvaluation:
    fingerprint: str
    ready: bool
    attention_reasons: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "ready": self.ready,
            "attention_reasons": list(self.attention_reasons),
        }


def evaluate_triage(
    item: ProjectItem,
    issue_body: str,
    settings: CommandPlaneSettings,
) -> TriageEvaluation:
    if not isinstance(item, ProjectItem):
        raise ValueError("item must be a ProjectItem")
    if not isinstance(issue_body, str):
        raise ValueError("issue_body must be a string")
    reasons: list[str] = []
    if item.kind is not ProjectItemKind.ISSUE:
        reasons.append("not_issue")
    if item.state is not None and item.state.casefold() != "open":
        reasons.append("source_not_open")
    headings = _headings(issue_body)
    for section in settings.readiness.required_issue_sections:
        if section.casefold() not in headings:
            reasons.append(f"missing_issue_section:{section}")

    semantics = load_canonical_work_contracts().work_item
    record_type = semantics.vocabulary_token("record_type", _field(item, "Record Type"))
    semantic_required = semantics.required_fields_for(
        state="ready", record_type=record_type
    )
    required_fields = tuple(
        dict.fromkeys((*settings.readiness.required_project_fields, *semantic_required))
    )
    for field_name in required_fields:
        value = _field(item, field_name)
        if not _present(value):
            reasons.append(f"missing_required:{field_name}")
            continue
        field_contract = semantics.field(field_name)
        if (
            field_contract.vocabulary is not None
            and semantics.vocabulary_token(field_contract.vocabulary, value) is None
        ):
            reasons.append(f"invalid_canonical:{field_name}")

    blocker = _field(item, settings.queue.blocked_by_field)
    if blocker is _MISSING and settings.readiness.requires_dependencies_understood:
        reasons.append("dependency_evidence_unavailable")
    elif _present(blocker):
        reasons.append("native_dependency_blocking")
    owner = _field(item, settings.claim.execution_owner_field)
    if _present(owner):
        reasons.append(f"already_claimed:{str(owner).strip()}")

    relevant = {
        "target": {
            "item_id": item.item_id,
            "repository": item.repository,
            "number": item.number,
        },
        "body_sha256": hashlib.sha256(issue_body.encode("utf-8")).hexdigest(),
        "fields": {
            name: None if _field(item, name) is _MISSING else _field(item, name)
            for name in (
                *required_fields,
                settings.queue.blocked_by_field,
                settings.claim.execution_owner_field,
            )
        },
        "source_state": item.state,
    }
    payload = json.dumps(relevant, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return TriageEvaluation(
        fingerprint=fingerprint,
        ready=not reasons,
        attention_reasons=tuple(reasons),
    )


__all__ = ["TriageEvaluation", "evaluate_triage"]
