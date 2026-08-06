from __future__ import annotations

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


__all__ = ["enrich_skill_card"]
