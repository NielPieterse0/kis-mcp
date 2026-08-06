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
from ..capabilities.settings import CapabilitySettings, load_capability_settings
from .metadata import enrich_skill_card
from .models import SkillCard
from .service import SkillsService
from .tools import register_skills_tools



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


def register_platform_skills(server):
    service = register_skills_tools(server)
    if not isinstance(service, SkillsService):
        return service, ()
    response = service.list_skills(limit=service.catalogue.config.limits.list_max_limit)
    settings = load_capability_settings()
    cards = tuple(enrich_skill_card(card, settings) for card in response.skills)
    return service, cards


__all__ = [
    "enrich_skill_card",
    "register_platform_skills",
    "skill_capability_contributions",
]
