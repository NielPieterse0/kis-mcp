from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

COMPLEXITIES = frozenset({"small", "medium", "large"})
RISK_TRIGGERS = frozenset(
    {
        "security",
        "secrets",
        "sensitive_data",
        "money",
        "persistent_state",
        "migration",
        "external_action",
        "deployment",
        "destructive",
        "public_contract",
        "architecture_boundary",
    }
)
REVIEW_TYPES = frozenset(
    {
        "code-quality",
        "safety-security",
        "architecture",
        "performance",
        "test-quality",
        "documentation",
        "api-contracts",
    }
)

_BASE_VERIFICATION_LIMIT = {"small": 6, "medium": 20, "large": 20}
_BASE_REVIEWS = {
    "small": (),
    "medium": ("code-quality",),
    "large": ("code-quality",),
}
_RISK_REVIEWS = {
    "security": ("safety-security",),
    "secrets": ("safety-security",),
    "sensitive_data": ("safety-security",),
    "public_contract": ("api-contracts",),
    "architecture_boundary": ("architecture",),
}


@dataclass(frozen=True, slots=True)
class ChangeControls:
    complexity: str
    risk_triggers: tuple[str, ...]
    max_verifications: int
    review_types: tuple[str, ...]


def select_change_controls(
    *,
    complexity: str,
    risk_triggers: Iterable[str] = (),
    review_types: Iterable[str] = (),
    max_verifications: int | None = None,
) -> ChangeControls:
    if complexity not in COMPLEXITIES:
        raise ValueError("complexity must be small, medium, or large")
    normalized_triggers = _canonical_values(
        risk_triggers,
        allowed=RISK_TRIGGERS,
        field="risk_triggers",
    )
    explicit_reviews = _canonical_values(
        review_types,
        allowed=REVIEW_TYPES,
        field="review_types",
    )
    if max_verifications is not None and (
        isinstance(max_verifications, bool)
        or not isinstance(max_verifications, int)
        or max_verifications < 1
        or max_verifications > 20
    ):
        raise ValueError("max_verifications must be an integer between 1 and 20")

    required_reviews = list(_BASE_REVIEWS[complexity])
    for trigger in normalized_triggers:
        required_reviews.extend(_RISK_REVIEWS.get(trigger, ()))
    required_reviews.extend(explicit_reviews)

    return ChangeControls(
        complexity=complexity,
        risk_triggers=normalized_triggers,
        max_verifications=max_verifications or _BASE_VERIFICATION_LIMIT[complexity],
        review_types=tuple(dict.fromkeys(required_reviews)),
    )


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
