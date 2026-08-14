from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    result = tuple(_text(item, label) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{label} must contain unique values")
    return result


@dataclass(frozen=True, slots=True)
class ComplexityControls:
    description: str
    max_verifications: int
    base_reviews: tuple[str, ...]
    artifacts: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.description, "complexity description")
        if (
            isinstance(self.max_verifications, bool)
            or not 1 <= self.max_verifications <= 20
        ):
            raise ValueError("max_verifications must be an integer between 1 and 20")
        if not self.artifacts or "scope.json" not in self.artifacts:
            raise ValueError("complexity artifacts must include scope.json")


@dataclass(frozen=True, slots=True)
class ChangeControlSettings:
    complexities: tuple[tuple[str, ComplexityControls], ...]
    review_types: tuple[str, ...]
    risk_reviews: tuple[tuple[str, tuple[str, ...]], ...]

    def complexity(self, name: str) -> ComplexityControls:
        for current, controls in self.complexities:
            if current == name:
                return controls
        raise ValueError(f"complexity contains unsupported value: {name}")

    def reviews_for_risk(self, name: str) -> tuple[str, ...]:
        for current, reviews in self.risk_reviews:
            if current == name:
                return reviews
        raise ValueError(f"risk_triggers contains unsupported values: {name}")


def load_change_control_settings(path: Path | None = None) -> ChangeControlSettings:
    target = path or (
        Path(__file__).resolve().parents[3]
        / "settings"
        / "change-governance.settings.json"
    )
    root = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(root, dict) or root.get("schema_version") != 1:
        raise ValueError("change-governance settings schema_version must be 1")
    if set(root) != {"schema_version", "complexities", "review_types", "risk_triggers"}:
        raise ValueError("change-governance settings keys do not match the contract")
    review_types = _strings(root["review_types"], "review_types")
    complexity_map = root["complexities"]
    risk_map = root["risk_triggers"]
    if not isinstance(complexity_map, dict) or not complexity_map:
        raise ValueError("complexities must be a non-empty object")
    if not isinstance(risk_map, dict):
        raise ValueError("risk_triggers must be an object")

    complexities: list[tuple[str, ComplexityControls]] = []
    for name, raw in complexity_map.items():
        if not isinstance(raw, dict) or set(raw) != {
            "description",
            "max_verifications",
            "base_reviews",
            "artifacts",
        }:
            raise ValueError(f"complexity settings invalid: {name}")
        controls = ComplexityControls(
            description=_text(raw["description"], f"complexities.{name}.description"),
            max_verifications=raw["max_verifications"],
            base_reviews=_strings(
                raw["base_reviews"], f"complexities.{name}.base_reviews"
            ),
            artifacts=_strings(raw["artifacts"], f"complexities.{name}.artifacts"),
        )
        if any(review not in review_types for review in controls.base_reviews):
            raise ValueError(f"complexity {name} references unknown review type")
        complexities.append((_text(name, "complexity name"), controls))

    risk_reviews: list[tuple[str, tuple[str, ...]]] = []
    for name, raw in risk_map.items():
        if not isinstance(raw, dict) or set(raw) != {"description", "reviews"}:
            raise ValueError(f"risk trigger settings invalid: {name}")
        _text(raw["description"], f"risk_triggers.{name}.description")
        reviews = _strings(raw["reviews"], f"risk_triggers.{name}.reviews")
        if any(review not in review_types for review in reviews):
            raise ValueError(f"risk trigger {name} references unknown review type")
        risk_reviews.append((_text(name, "risk trigger name"), reviews))

    return ChangeControlSettings(
        complexities=tuple(sorted(complexities)),
        review_types=review_types,
        risk_reviews=tuple(sorted(risk_reviews)),
    )


@dataclass(frozen=True, slots=True)
class ChangeControls:
    complexity: str
    risk_triggers: tuple[str, ...]
    max_verifications: int
    review_types: tuple[str, ...]


def _canonical_values(
    values: Iterable[str],
    *,
    allowed: frozenset[str],
    field: str,
) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value for value in normalized):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field} must not contain duplicate values")
    unknown = sorted(set(normalized).difference(allowed))
    if unknown:
        raise ValueError(f"{field} contains unsupported values: {', '.join(unknown)}")
    return tuple(sorted(normalized))


def select_change_controls(
    *,
    complexity: str,
    risk_triggers: Iterable[str] = (),
    review_types: Iterable[str] = (),
    max_verifications: int | None = None,
    settings: ChangeControlSettings | None = None,
) -> ChangeControls:
    configured = settings or load_change_control_settings()
    complexity_controls = configured.complexity(complexity)
    allowed_risks = frozenset(name for name, _reviews in configured.risk_reviews)
    normalized_triggers = _canonical_values(
        risk_triggers, allowed=allowed_risks, field="risk_triggers"
    )
    explicit_reviews = _canonical_values(
        review_types, allowed=frozenset(configured.review_types), field="review_types"
    )
    if max_verifications is not None and (
        isinstance(max_verifications, bool)
        or not isinstance(max_verifications, int)
        or not 1 <= max_verifications <= 20
    ):
        raise ValueError("max_verifications must be an integer between 1 and 20")
    required_reviews = list(complexity_controls.base_reviews)
    for trigger in normalized_triggers:
        required_reviews.extend(configured.reviews_for_risk(trigger))
    required_reviews.extend(explicit_reviews)
    return ChangeControls(
        complexity=complexity,
        risk_triggers=normalized_triggers,
        max_verifications=max_verifications or complexity_controls.max_verifications,
        review_types=tuple(dict.fromkeys(required_reviews)),
    )


_DEFAULT_SETTINGS = load_change_control_settings()
COMPLEXITIES = frozenset(name for name, _controls in _DEFAULT_SETTINGS.complexities)
RISK_TRIGGERS = frozenset(name for name, _reviews in _DEFAULT_SETTINGS.risk_reviews)
REVIEW_TYPES = frozenset(_DEFAULT_SETTINGS.review_types)

__all__ = [
    "COMPLEXITIES",
    "RISK_TRIGGERS",
    "REVIEW_TYPES",
    "ChangeControlSettings",
    "ChangeControls",
    "ComplexityControls",
    "load_change_control_settings",
    "select_change_controls",
]
