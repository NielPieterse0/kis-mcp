from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from ..contracts import Confidence
from ..errors import DiscoverError
from ..read_authority import ReadAuthority
from ..settings import DiscoverSettings
from .contracts import (
    ProviderAdmissionHandoff,
    ProviderAdmissionOmissions,
    ProviderAdmissionRequest,
    ProviderAdmissionResponse,
    ProviderCandidate,
    ProviderConformanceStep,
    ProviderEvidence,
    ProviderRisk,
    ProviderUnknown,
)

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "name",
        "provider_type",
        "revision",
        "license",
        "maintainer",
        "capabilities",
        "effects",
        "authentication",
        "installation",
        "compatibility",
        "readiness",
        "evidence",
        "overlaps",
    }
)
_EFFECT_KEYS = frozenset(
    {
        "reads_project",
        "writes_project",
        "executes_commands",
        "network_access",
        "credentials",
    }
)
_COMPATIBILITY_KEYS = frozenset({"mcp_protocol", "platforms"})
_READINESS_KEYS = frozenset(
    {
        "schema_present",
        "health_contract_present",
        "deterministic",
        "conformance_tests",
    }
)
_EVIDENCE_KEYS = frozenset({"kind", "path", "summary"})


class ProviderAdmissionService:
    def __init__(self, *, boundary: Path, settings: DiscoverSettings) -> None:
        self._boundary = boundary
        self._settings = settings

    def inspect(self, request: ProviderAdmissionRequest) -> ProviderAdmissionResponse:
        self._validate_budget(request)
        authority = ReadAuthority(self._boundary, self._settings)
        project = authority.resolve_project(request.project)
        try:
            read = authority.read_relative_text(
                request.project,
                request.manifest_path,
                max_bytes=self._settings.limits.max_file_bytes,
            )
        except DiscoverError:
            raise
        content = read.content
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise _error(
                "DISCOVER_PROVIDER_MANIFEST_JSON_INVALID",
                "The provider candidate manifest is not valid JSON.",
                f"JSON parsing failed at line {exc.lineno}, column {exc.colno}.",
                field="manifest_path",
            ) from exc
        manifest = _validate_manifest(payload)
        content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

        all_capabilities = _sorted_unique(manifest["capabilities"])
        all_evidence = tuple(
            ProviderEvidence(
                kind=item["kind"],
                path=item["path"],
                summary=item["summary"],
            )
            for item in sorted(
                manifest["evidence"],
                key=lambda item: (
                    item["kind"].casefold(),
                    item["path"].casefold(),
                    item["summary"],
                ),
            )
        )
        requested_effects = tuple(
            sorted(
                (name for name, enabled in manifest["effects"].items() if enabled),
                key=str.casefold,
            )
        )
        all_risks, all_unknowns = _assess(manifest, requested_effects)
        all_steps = _steps()

        capabilities = all_capabilities[: request.budget.max_capabilities]
        evidence = all_evidence[: request.budget.max_evidence]
        risks = all_risks[: request.budget.max_risks]
        steps = all_steps[: request.budget.max_steps]
        omissions = ProviderAdmissionOmissions(
            capabilities=max(0, len(all_capabilities) - len(capabilities)),
            evidence=max(0, len(all_evidence) - len(evidence)),
            risks=max(0, len(all_risks) - len(risks)),
            steps=max(0, len(all_steps) - len(steps)),
        )
        reasons = tuple(
            name
            for name in (
                "max_capabilities",
                "max_evidence",
                "max_risks",
                "max_steps",
            )
            if getattr(omissions, name.removeprefix("max_"))
        )
        candidate = ProviderCandidate(
            candidate_id=manifest["candidate_id"],
            name=manifest["name"],
            provider_type=manifest["provider_type"],
            revision=manifest["revision"],
            license=manifest["license"],
            maintainer=manifest["maintainer"],
            capabilities=capabilities,
            requested_effects=requested_effects,
            authentication=manifest["authentication"],
            installation=manifest["installation"],
            protocols=_sorted_unique(manifest["compatibility"]["mcp_protocol"]),
            platforms=_sorted_unique(manifest["compatibility"]["platforms"]),
            schema_present=manifest["readiness"]["schema_present"],
            health_contract_present=manifest["readiness"]["health_contract_present"],
            deterministic=manifest["readiness"]["deterministic"],
            conformance_tests=_sorted_unique(
                manifest["readiness"]["conformance_tests"]
            ),
            evidence=evidence,
            overlaps=_sorted_unique(manifest["overlaps"]),
            manifest_path=request.manifest_path.replace("\\", "/"),
            content_digest=content_digest,
        )
        unresolved_codes = tuple(item.code for item in all_risks)
        required_evidence = tuple(
            sorted(
                {
                    item.code.removesuffix("_DECLARED").removesuffix("_UNRESOLVED")
                    for item in all_risks
                },
                key=str.casefold,
            )
        )
        admission = ProviderAdmissionHandoff(
            request_id=f"admit:{candidate.candidate_id}:{content_digest[:12]}",
            candidate_id=candidate.candidate_id,
            decision="pending_govern",
            requested_capabilities=capabilities,
            requested_effects=requested_effects,
            unresolved_risks=unresolved_codes,
            required_evidence=required_evidence,
        )
        confidence = (
            Confidence.LOW
            if not candidate.evidence
            else Confidence.MEDIUM
            if all_risks or all_unknowns or reasons
            else Confidence.HIGH
        )
        response = ProviderAdmissionResponse(
            project=project,
            candidate=candidate,
            risks=risks,
            admission_request=admission,
            conformance_plan=steps,
            unknowns=all_unknowns,
            omissions=omissions,
            confidence=confidence,
            truncated=bool(reasons),
            truncation_reasons=reasons,
            fingerprint="0" * 64,
        )
        serialized = response.to_json_dict()
        serialized.pop("fingerprint")
        return replace(response, fingerprint=_fingerprint(serialized))

    def _validate_budget(self, request: ProviderAdmissionRequest) -> None:
        maxima = {
            "max_capabilities": self._settings.limits.max_evidence,
            "max_evidence": self._settings.limits.max_evidence,
            "max_risks": self._settings.limits.max_evidence,
            "max_steps": self._settings.limits.max_evidence,
        }
        for name, maximum in maxima.items():
            if getattr(request.budget, name) > maximum:
                raise _error(
                    "DISCOVER_PROVIDER_BUDGET_INVALID",
                    "The provider admission budget exceeds configured Discover limits.",
                    f"{name} must not exceed {maximum}.",
                    field=f"budget.{name}",
                )


def _validate_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(
            "DISCOVER_PROVIDER_MANIFEST_INVALID",
            "The provider candidate manifest root must be a JSON object.",
            "A non-object JSON value was supplied.",
        )
    if set(value) != _ROOT_KEYS:
        missing = sorted(_ROOT_KEYS.difference(value))
        unknown = sorted(set(value).difference(_ROOT_KEYS))
        raise _error(
            "DISCOVER_PROVIDER_MANIFEST_KEYS_INVALID",
            "The provider candidate manifest keys are invalid.",
            f"Missing keys: {missing}; unknown keys: {unknown}.",
        )
    if value["schema_version"] != 1:
        raise _error(
            "DISCOVER_PROVIDER_MANIFEST_VERSION_UNSUPPORTED",
            "The provider candidate manifest version is unsupported.",
            "Only schema_version 1 is accepted.",
            field="schema_version",
        )
    _require_text_fields(
        value,
        ("candidate_id", "name", "provider_type", "revision", "maintainer"),
    )
    if value["license"] is not None and not _is_text(value["license"]):
        raise _invalid("license must be null or a non-empty string")
    if value["provider_type"] not in {"mcp_server", "tool", "provider"}:
        raise _invalid("provider_type is unsupported")
    if value["authentication"] not in {"none", "operator_injected", "provider_managed"}:
        raise _invalid("authentication is unsupported")
    if value["installation"] not in {"bundled", "manual", "external_command"}:
        raise _invalid("installation is unsupported")
    _require_string_list(value["capabilities"], "capabilities")
    _require_string_list(value["overlaps"], "overlaps")
    _require_exact_object(value["effects"], _EFFECT_KEYS, "effects")
    if any(not isinstance(item, bool) for item in value["effects"].values()):
        raise _invalid("effects values must be booleans")
    _require_exact_object(value["compatibility"], _COMPATIBILITY_KEYS, "compatibility")
    _require_string_list(value["compatibility"]["mcp_protocol"], "compatibility.mcp_protocol")
    _require_string_list(value["compatibility"]["platforms"], "compatibility.platforms")
    _require_exact_object(value["readiness"], _READINESS_KEYS, "readiness")
    for name in ("schema_present", "health_contract_present", "deterministic"):
        if not isinstance(value["readiness"][name], bool):
            raise _invalid(f"readiness.{name} must be boolean")
    _require_string_list(value["readiness"]["conformance_tests"], "readiness.conformance_tests")
    if not isinstance(value["evidence"], list):
        raise _invalid("evidence must be an array")
    for index, item in enumerate(value["evidence"]):
        _require_exact_object(item, _EVIDENCE_KEYS, f"evidence[{index}]")
        _require_text_fields(item, ("kind", "path", "summary"))
    return value


def _assess(
    manifest: Mapping[str, Any],
    requested_effects: tuple[str, ...],
) -> tuple[tuple[ProviderRisk, ...], tuple[ProviderUnknown, ...]]:
    risks: list[ProviderRisk] = []
    unknowns: list[ProviderUnknown] = []
    mapping = {
        "writes_project": ("WRITE_ACCESS_DECLARED", "high", "The candidate declares project write effects."),
        "executes_commands": ("EXECUTION_DECLARED", "high", "The candidate declares process execution effects."),
        "network_access": ("NETWORK_ACCESS_DECLARED", "high", "The candidate declares network effects."),
        "credentials": ("CREDENTIAL_ACCESS_DECLARED", "high", "The candidate declares credential effects."),
    }
    for effect in requested_effects:
        if effect in mapping:
            code, severity, reason = mapping[effect]
            risks.append(ProviderRisk(code=code, severity=severity, reason=reason))
    if manifest["license"] is None:
        risks.append(
            ProviderRisk(
                code="LICENSE_UNRESOLVED",
                severity="high",
                reason="No license identifier is declared.",
            )
        )
        unknowns.append(
            ProviderUnknown(
                code="LICENSE_EVIDENCE_MISSING",
                reason="License compatibility cannot be assessed from the candidate manifest.",
            )
        )
    readiness = manifest["readiness"]
    if not readiness["schema_present"]:
        risks.append(ProviderRisk("SCHEMA_EVIDENCE_MISSING", "high", "No provider schema is declared."))
    if not readiness["health_contract_present"]:
        risks.append(ProviderRisk("HEALTH_CONTRACT_MISSING", "medium", "No health contract is declared."))
    if not readiness["deterministic"]:
        risks.append(ProviderRisk("NONDETERMINISTIC_PROVIDER", "medium", "The candidate does not claim deterministic behavior."))
    if not readiness["conformance_tests"]:
        risks.append(ProviderRisk("CONFORMANCE_EVIDENCE_MISSING", "high", "No conformance tests are declared."))
    if manifest["overlaps"]:
        risks.append(ProviderRisk("CAPABILITY_OVERLAP_DECLARED", "medium", "The candidate declares overlap with existing capabilities."))
    if manifest["installation"] == "external_command":
        risks.append(ProviderRisk("EXTERNAL_INSTALLATION_DECLARED", "high", "The candidate requires an external installation command."))
    ordered = tuple(sorted(risks, key=lambda item: (item.code, item.reason)))
    return ordered, tuple(sorted(unknowns, key=lambda item: (item.code, item.reason)))


def _steps() -> tuple[ProviderConformanceStep, ...]:
    return (
        ProviderConformanceStep("validate-manifest", "schema", "Validate the checked-in candidate manifest against the supported contract."),
        ProviderConformanceStep("review-effects", "security", "Review declared read, write, execution, network, and credential effects."),
        ProviderConformanceStep("review-license", "licensing", "Confirm license identity and compatibility from operator-approved evidence."),
        ProviderConformanceStep("review-overlap", "architecture", "Review capability overlap and select an admission boundary."),
        ProviderConformanceStep("verify-conformance", "verification", "Evaluate declared schema, health, determinism, and conformance evidence through an approved Work flow."),
    )


def _require_exact_object(value: Any, keys: frozenset[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise _invalid(f"{label} must be an object with exactly {sorted(keys)}")


def _require_text_fields(value: Mapping[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        if not _is_text(value.get(name)):
            raise _invalid(f"{name} must be a non-empty string")


def _require_string_list(value: Any, label: str) -> None:
    if not isinstance(value, list) or any(not _is_text(item) for item in value):
        raise _invalid(f"{label} must be an array of non-empty strings")


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda value: (value.casefold(), value)))


def _invalid(reason: str) -> DiscoverError:
    return _error(
        "DISCOVER_PROVIDER_MANIFEST_INVALID",
        "The provider candidate manifest is structurally invalid.",
        reason,
    )


def _error(code: str, message: str, reason: str, *, field: str | None = None) -> DiscoverError:
    return DiscoverError(
        code=code,
        message=message,
        reason=reason,
        field=field,
        accepted="A strict version-1 checked-in provider candidate JSON object.",
        corrective_actions=("Correct the candidate manifest and retry.",),
    )


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["ProviderAdmissionService"]
