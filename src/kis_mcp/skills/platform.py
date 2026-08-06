from __future__ import annotations

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality, normalize_effects
from ..capabilities.settings import CapabilitySettings
from .models import SkillCard


def enrich_skill_card(card: SkillCard, settings: CapabilitySettings) -> SkillCard:
    metadata = settings.skill_metadata.get(card.id)
    if metadata is None:
        return card
    return SkillCard(
        id=card.id,
        summary=card.summary,
        category=metadata.category,
        capabilities=metadata.capabilities,
        status=card.status,
    )


def skill_capability_contributions(
    cards: tuple[SkillCard, ...],
    settings: CapabilitySettings,
) -> tuple[CapabilityContribution, ...]:
    contributions: list[CapabilityContribution] = []
    for raw_card in sorted(cards, key=lambda item: item.id):
        card = enrich_skill_card(raw_card, settings)
        metadata = settings.skill_metadata.get(card.id)
        if card.category == "uncategorized" or not card.capabilities:
            raise ValueError(f"skill capability metadata is incomplete: {card.id}")
        effects = normalize_effects(metadata.effects if metadata is not None else ("read_only",))
        contribution_id = f"skill.{card.id}"
        state = ReadinessState.READY if card.status == "active" else ReadinessState.DISABLED
        contributions.append(
            CapabilityContribution(
                contribution_id=contribution_id,
                domain=CapabilityDomain.SKILL,
                category=card.category,
                capabilities=card.capabilities,
                operations=(),
                dependencies=(),
                effects=effects,
                readiness_probe=lambda contribution_id=contribution_id, state=state: ReadinessSnapshot(
                    contribution_id=contribution_id,
                    state=state,
                    summary="Skill metadata is available." if state is ReadinessState.READY else "Skill is disabled.",
                ),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=65),
                quality=default_quality(context_cost=10, reliability=85, workflow_integration=90),
            )
        )
    return tuple(contributions)


__all__ = ["enrich_skill_card", "skill_capability_contributions"]
