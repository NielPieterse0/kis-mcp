from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Iterable, Mapping

from .contracts import InspectProjectResponse
from .errors import DiscoverError


class ResultBudgeter:
    def __init__(self, *, max_evidence: int, max_output_chars: int) -> None:
        if max_evidence < 1 or max_output_chars < 1:
            raise ValueError("result budgets must be positive")
        self.max_evidence = max_evidence
        self.max_output_chars = max_output_chars

    def apply(self, response: InspectProjectResponse) -> InspectProjectResponse:
        referenced = _referenced_evidence_ids(response)
        available = {item.id for item in response.evidence}
        missing = sorted(referenced - available)
        if missing:
            raise _reference_error(missing[0])
        if len(available) != len(response.evidence):
            raise DiscoverError(
                code="DISCOVER_EVIDENCE_ID_DUPLICATE",
                message="Discover evidence IDs must be unique.",
                reason="The response contained duplicate evidence identifiers.",
                field="evidence",
            )
        _validate_verification_handoffs(response)
        if len(referenced) > self.max_evidence:
            raise DiscoverError(
                code="DISCOVER_EVIDENCE_BUDGET_TOO_SMALL",
                message="The evidence budget cannot retain all referenced evidence.",
                reason="Material findings and handoffs reference more evidence than the configured maximum.",
                field="max_evidence",
            )

        indexed = list(enumerate(response.evidence))
        indexed.sort(key=lambda item: (item[1].id not in referenced, item[0]))
        selected = tuple(item for _, item in indexed[: self.max_evidence])
        reasons = set(response.truncation_reasons)
        if len(selected) < len(response.evidence):
            reasons.add("max_evidence")
        bounded = replace(
            response,
            evidence=selected,
            truncated=response.truncated or bool(reasons),
            truncation_reasons=tuple(sorted(reasons)),
        )
        self._validate_references(bounded)
        if _encoded_length(bounded) <= self.max_output_chars:
            return bounded

        reasons.add("max_output_chars")
        bounded = replace(
            bounded,
            truncated=True,
            truncation_reasons=tuple(sorted(reasons)),
        )
        bounded = self._compact(bounded, referenced)
        self._validate_references(bounded)
        if _encoded_length(bounded) > self.max_output_chars:
            raise DiscoverError(
                code="DISCOVER_OUTPUT_BUDGET_TOO_SMALL",
                message="The configured output budget cannot contain the minimum response contract.",
                reason="The stable envelope and material referenced evidence exceed max_output_chars.",
                field="max_output_chars",
                accepted="Increase settings.discover.limits.max_output_chars.",
                corrective_actions=(
                    "Increase the configured Discover output character limit.",
                ),
                retryable=True,
            )
        return bounded

    def _compact(
        self,
        response: InspectProjectResponse,
        referenced: set[str],
    ) -> InspectProjectResponse:
        current = response

        unreferenced = [item for item in current.evidence if item.id not in referenced]
        while unreferenced and _encoded_length(current) > self.max_output_chars:
            remove = unreferenced.pop()
            current = replace(
                current,
                evidence=tuple(item for item in current.evidence if item.id != remove.id),
            )

        while _encoded_length(current) > self.max_output_chars:
            code_atlas, code_changed = _halve_mapping_lists(
                current.code_atlas,
                preferred=("symbols", "calls", "imports", "inheritance", "modules", "diagnostics"),
            )
            repository_atlas, repository_changed = _halve_repository_atlas(
                current.repository_atlas
            )
            verification, verification_changed = _halve_verification_lists(
                current.verification,
                current.handoffs,
            )
            contracts, contracts_changed = _halve_mapping_lists(
                current.contracts,
                preferred=("artifacts",),
            )
            recent_commits = current.git.recent_commits
            git_changed = len(recent_commits) > 1
            if git_changed:
                recent_commits = recent_commits[: max(1, len(recent_commits) // 2)]
            instructions = current.instructions
            instruction_changed = len(instructions) > 1
            if instruction_changed:
                instructions = instructions[: max(1, len(instructions) // 2)]

            changed = any(
                (
                    code_changed,
                    repository_changed,
                    verification_changed,
                    contracts_changed,
                    git_changed,
                    instruction_changed,
                )
            )
            if not changed:
                break
            current = replace(
                current,
                code_atlas=code_atlas,
                repository_atlas=repository_atlas,
                verification=verification,
                contracts=contracts,
                instructions=instructions,
                git=replace(current.git, recent_commits=recent_commits, truncated=True),
            )

        if _encoded_length(current) > self.max_output_chars:
            current = replace(
                current,
                code_atlas=_summary_only(current.code_atlas),
                repository_atlas=_repository_summary_only(current.repository_atlas),
                verification=_verification_summary_only(
                    current.verification,
                    current.handoffs,
                ),
                contracts=_summary_only(current.contracts),
                instructions=(),
                recommendations=(),
                assumptions=(),
                git=replace(current.git, recent_commits=(), truncated=True),
            )
        return current

    @staticmethod
    def _validate_references(response: InspectProjectResponse) -> None:
        available = {item.id for item in response.evidence}
        missing = sorted(_referenced_evidence_ids(response) - available)
        if missing:
            raise _reference_error(missing[0])
        _validate_verification_handoffs(response)


def _referenced_evidence_ids(response: InspectProjectResponse) -> set[str]:
    values: set[str] = set()
    for value in (
        response.repository_atlas,
        response.code_atlas,
        response.verification,
        response.contracts,
        response.instructions,
        response.findings,
        response.recommendations,
        response.handoffs,
        response.assumptions,
        response.unknowns,
    ):
        _collect_evidence_ids(value, values)
    return values


def _collect_evidence_ids(value: Any, values: set[str]) -> None:
    if hasattr(value, "to_json_dict"):
        value = value.to_json_dict()
    if isinstance(value, Mapping):
        evidence_ids = value.get("evidence_ids", ())
        if isinstance(evidence_ids, Iterable) and not isinstance(
            evidence_ids, (str, bytes)
        ):
            values.update(str(item) for item in evidence_ids)
        for key, item in value.items():
            if key != "evidence_ids":
                _collect_evidence_ids(item, values)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _collect_evidence_ids(item, values)


def _validate_verification_handoffs(response: InspectProjectResponse) -> None:
    declarations = response.verification.get("declarations", ())
    declaration_ids = {
        verification_id
        for declaration in declarations
        if (verification_id := _verification_declaration_id(declaration)) is not None
    }
    for handoff in response.handoffs:
        verification_id = _handoff_verification_id(handoff)
        if verification_id is None:
            continue
        if verification_id not in declaration_ids:
            raise DiscoverError(
                code="DISCOVER_VERIFICATION_HANDOFF_INVALID",
                message="A verification handoff references an unavailable declaration.",
                reason=(
                    f"Verification declaration {verification_id} is not present in the response."
                ),
                field="handoffs.inputs.verification_id",
            )


def _required_verification_ids(handoffs: Iterable[Any]) -> set[str]:
    return {
        verification_id
        for handoff in handoffs
        if (verification_id := _handoff_verification_id(handoff)) is not None
    }


def _handoff_verification_id(handoff: Any) -> str | None:
    if hasattr(handoff, "to_json_dict"):
        handoff = handoff.to_json_dict()
    if not isinstance(handoff, Mapping) or handoff.get("workflow") != "run_verification":
        return None
    inputs = handoff.get("inputs")
    if not isinstance(inputs, Mapping):
        return None
    value = inputs.get("verification_id")
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _verification_declaration_id(declaration: Any) -> str | None:
    if hasattr(declaration, "to_json_dict"):
        declaration = declaration.to_json_dict()
    if not isinstance(declaration, Mapping):
        return None
    value = declaration.get("id")
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _reference_error(evidence_id: str) -> DiscoverError:
    return DiscoverError(
        code="DISCOVER_EVIDENCE_REFERENCE_INVALID",
        message="A response record references unavailable evidence.",
        reason=f"Evidence ID {evidence_id} does not exist in the response.",
        field="evidence_ids",
    )


def _encoded_length(response: InspectProjectResponse) -> int:
    return len(
        json.dumps(
            response.to_json_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )


def _halve_mapping_lists(
    value: Mapping[str, Any],
    *,
    preferred: tuple[str, ...],
) -> tuple[dict[str, Any], bool]:
    result = dict(value)
    keys = [*preferred, *(key for key in sorted(result) if key not in preferred)]
    for key in keys:
        item = result.get(key)
        if isinstance(item, (list, tuple)) and len(item) > 1:
            result[key] = list(item[: max(1, len(item) // 2)])
            result[f"{key}_truncated"] = True
            return result, True
    return result, False


def _halve_verification_lists(
    value: Mapping[str, Any],
    handoffs: Iterable[Any],
) -> tuple[dict[str, Any], bool]:
    result = dict(value)
    declarations = result.get("declarations")
    if isinstance(declarations, (list, tuple)) and len(declarations) > 1:
        required_ids = _required_verification_ids(handoffs)
        required_count = sum(
            1
            for declaration in declarations
            if _verification_declaration_id(declaration) in required_ids
        )
        target = max(required_count, max(1, len(declarations) // 2))
        optional_slots = target - required_count
        retained: list[Any] = []
        for declaration in declarations:
            verification_id = _verification_declaration_id(declaration)
            if verification_id in required_ids:
                retained.append(declaration)
            elif optional_slots > 0:
                retained.append(declaration)
                optional_slots -= 1
        if len(retained) < len(declarations):
            result["declarations"] = retained
            result["declarations_truncated"] = True
            return result, True
    for key in ("diagnostics", "evidence_sources"):
        item = result.get(key)
        if isinstance(item, (list, tuple)) and len(item) > 1:
            result[key] = list(item[: max(1, len(item) // 2)])
            result[f"{key}_truncated"] = True
            return result, True
    return result, False


def _halve_repository_atlas(value: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    result = dict(value)
    topology = result.get("topology")
    if isinstance(topology, Mapping):
        topology_result = dict(topology)
        for key in ("files", "directories", "excluded_paths"):
            item = topology_result.get(key)
            if isinstance(item, (list, tuple)) and len(item) > 1:
                topology_result[key] = list(item[: max(1, len(item) // 2)])
                topology_result[f"{key}_truncated"] = True
                result["topology"] = topology_result
                return result, True
    return _halve_mapping_lists(
        result,
        preferred=(
            "manifests",
            "languages",
            "modules",
            "entry_points",
            "workspaces",
            "diagnostics",
        ),
    )


def _summary_only(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"truncated": True}
    summary = value.get("summary")
    if isinstance(summary, Mapping):
        result["summary"] = dict(summary)
    for key in ("language", "project_name", "status"):
        if key in value:
            result[key] = value[key]
    return result


def _verification_summary_only(
    value: Mapping[str, Any],
    handoffs: Iterable[Any],
) -> dict[str, Any]:
    result = _summary_only(value)
    required_ids = _required_verification_ids(handoffs)
    declarations = value.get("declarations")
    if isinstance(declarations, (list, tuple)) and required_ids:
        result["declarations"] = [
            declaration
            for declaration in declarations
            if _verification_declaration_id(declaration) in required_ids
        ]
    return result


def _repository_summary_only(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _summary_only(value)
    topology = value.get("topology")
    if isinstance(topology, Mapping):
        result["topology"] = {
            key: topology[key]
            for key in ("file_count", "directory_count", "total_bytes")
            if key in topology
        }
    return result


__all__ = ["ResultBudgeter"]
