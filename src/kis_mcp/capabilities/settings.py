from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


class CapabilitySettingsError(ValueError):
    pass


_SUITABILITY_KEYS = {
    "intent_match",
    "workflow_coverage",
    "runtime_readiness",
    "prerequisite_satisfaction",
    "safety_reversibility",
    "observed_reliability",
    "user_friction",
    "context_cost",
}
_QUALITY_KEYS = {
    "schema_precision",
    "description_clarity",
    "effect_accuracy",
    "bounded_output",
    "reversibility",
    "reliability",
    "workflow_integration",
    "context_cost",
}
_TOP_LEVEL_KEYS = {
    "schema_version",
    "suitability_weights",
    "quality_weights",
    "direct_profile",
    "discovery_operations",
    "readiness",
    "result_budget",
    "skill_metadata",
}


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilitySettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _unique_text_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CapabilitySettingsError(f"{label} must be an array")
    items = tuple(_required_text(item, label) for item in value)
    if len(set(items)) != len(items):
        raise CapabilitySettingsError(f"{label} values must be unique")
    return items


def _weights(value: Any, expected: set[str], label: str) -> Mapping[str, int]:
    if not isinstance(value, dict) or set(value) != expected:
        raise CapabilitySettingsError(f"{label} must contain exactly {sorted(expected)}")
    normalized: dict[str, int] = {}
    for key in sorted(expected):
        weight = value[key]
        if not isinstance(weight, int) or weight < 0 or weight > 100:
            raise CapabilitySettingsError(f"{label}.{key} must be an integer from 0 to 100")
        normalized[key] = weight
    if sum(normalized.values()) != 100:
        raise CapabilitySettingsError(f"{label} must sum to 100")
    return MappingProxyType(normalized)


@dataclass(frozen=True, slots=True)
class SkillCapabilityMetadata:
    category: str
    capabilities: tuple[str, ...]
    activation_terms: tuple[str, ...]
    effects: tuple[str, ...]
    workflow_roles: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any, *, skill_id: str) -> "SkillCapabilityMetadata":
        expected = {"category", "capabilities", "activation_terms", "effects", "workflow_roles"}
        if not isinstance(value, dict) or set(value) != expected:
            raise CapabilitySettingsError(f"skill_metadata.{skill_id} must contain exactly {sorted(expected)}")
        category = _required_text(value["category"], f"skill_metadata.{skill_id}.category")
        if category == "uncategorized":
            raise CapabilitySettingsError(f"skill_metadata.{skill_id}.category must not be uncategorized")
        capabilities = _unique_text_list(value["capabilities"], f"skill_metadata.{skill_id}.capabilities")
        if not capabilities:
            raise CapabilitySettingsError(f"skill_metadata.{skill_id}.capabilities must not be empty")
        activation_terms = _unique_text_list(
            value["activation_terms"],
            f"skill_metadata.{skill_id}.activation_terms",
        )
        effects = _unique_text_list(
            value["effects"], f"skill_metadata.{skill_id}.effects"
        )
        workflow_roles = _unique_text_list(
            value["workflow_roles"],
            f"skill_metadata.{skill_id}.workflow_roles",
        )
        for label, items in (
            ("activation_terms", activation_terms),
            ("effects", effects),
            ("workflow_roles", workflow_roles),
        ):
            if not items:
                raise CapabilitySettingsError(
                    f"skill_metadata.{skill_id}.{label} must not be empty"
                )
        return cls(
            category=category,
            capabilities=capabilities,
            activation_terms=activation_terms,
            effects=effects,
            workflow_roles=workflow_roles,
        )


@dataclass(frozen=True, slots=True)
class ResultBudgetSettings:
    max_chars: int
    preview_items: int
    preview_string_chars: int
    preview_depth: int


@dataclass(frozen=True, slots=True)
class CapabilitySettings:
    schema_version: int
    suitability_weights: Mapping[str, int]
    quality_weights: Mapping[str, int]
    direct_operations: tuple[str, ...]
    direct_profile_max: int
    discovery_operations: tuple[str, ...]
    degraded_penalty: int
    result_budget: ResultBudgetSettings
    skill_metadata: Mapping[str, SkillCapabilityMetadata]


def _default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "settings" / "capabilities.settings.json"


def load_capability_settings(path: Path | None = None) -> CapabilitySettings:
    source = path or _default_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CapabilitySettingsError(f"capability settings could not be read: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise CapabilitySettingsError("capability settings root must be an object")
    unknown = sorted(set(payload) - _TOP_LEVEL_KEYS)
    missing = sorted(_TOP_LEVEL_KEYS - set(payload))
    if unknown:
        raise CapabilitySettingsError(f"capability settings unknown fields: {', '.join(unknown)}")
    if missing:
        raise CapabilitySettingsError(f"capability settings missing fields: {', '.join(missing)}")
    if payload["schema_version"] != 1:
        raise CapabilitySettingsError("capability settings schema_version must be 1")

    direct = payload["direct_profile"]
    if not isinstance(direct, dict) or set(direct) != {"max_operations", "operations"}:
        raise CapabilitySettingsError("direct_profile must contain max_operations and operations")
    direct_max = direct["max_operations"]
    if not isinstance(direct_max, int) or direct_max < 1 or direct_max > 30:
        raise CapabilitySettingsError("direct_profile.max_operations must be an integer from 1 to 30")
    direct_operations = _unique_text_list(direct["operations"], "direct_profile.operations")
    if len(direct_operations) > direct_max:
        raise CapabilitySettingsError("direct_profile.operations exceeds max_operations")

    readiness = payload["readiness"]
    if not isinstance(readiness, dict) or set(readiness) != {"degraded_penalty"}:
        raise CapabilitySettingsError("readiness must contain degraded_penalty")
    degraded_penalty = readiness["degraded_penalty"]
    if not isinstance(degraded_penalty, int) or not 0 <= degraded_penalty <= 100:
        raise CapabilitySettingsError("readiness.degraded_penalty must be an integer from 0 to 100")

    result_budget = payload["result_budget"]
    budget_fields = {
        "max_chars": (1_000, 1_000_000),
        "preview_items": (1, 100),
        "preview_string_chars": (100, 100_000),
        "preview_depth": (1, 10),
    }
    if not isinstance(result_budget, dict) or set(result_budget) != set(budget_fields):
        raise CapabilitySettingsError(
            "result_budget must contain max_chars, preview_items, preview_string_chars, and preview_depth"
        )
    normalized_budget: dict[str, int] = {}
    for key, (minimum, maximum) in budget_fields.items():
        value = result_budget[key]
        if not isinstance(value, int) or not minimum <= value <= maximum:
            raise CapabilitySettingsError(
                f"result_budget.{key} must be an integer from {minimum} to {maximum}"
            )
        normalized_budget[key] = value

    raw_skills = payload["skill_metadata"]
    if not isinstance(raw_skills, dict) or not raw_skills:
        raise CapabilitySettingsError("skill_metadata must be a non-empty object")
    skills = {
        _required_text(skill_id, "skill id"): SkillCapabilityMetadata.from_mapping(value, skill_id=skill_id)
        for skill_id, value in sorted(raw_skills.items())
    }

    return CapabilitySettings(
        schema_version=1,
        suitability_weights=_weights(payload["suitability_weights"], _SUITABILITY_KEYS, "suitability_weights"),
        quality_weights=_weights(payload["quality_weights"], _QUALITY_KEYS, "quality_weights"),
        direct_operations=direct_operations,
        direct_profile_max=direct_max,
        discovery_operations=_unique_text_list(payload["discovery_operations"], "discovery_operations"),
        degraded_penalty=degraded_penalty,
        result_budget=ResultBudgetSettings(**normalized_budget),
        skill_metadata=MappingProxyType(skills),
    )


__all__ = [
    "CapabilitySettings",
    "CapabilitySettingsError",
    "ResultBudgetSettings",
    "SkillCapabilityMetadata",
    "load_capability_settings",
]
