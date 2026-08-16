from __future__ import annotations

from pathlib import Path

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
from ..runtime_observability import get_runtime_observability
from .metadata import enrich_skill_card
from .models import SkillCard
from .resources import register_skill_resources
from .service import SkillsService
from .telemetry import SkillTelemetryStore
from .tools import register_skills_tools


def skill_capability_contributions(
    cards: tuple[SkillCard, ...],
    settings: CapabilitySettings,
) -> tuple[CapabilityContribution, ...]:
    contributions: list[CapabilityContribution] = []
    for raw_card in sorted(cards, key=lambda item: item.id):
        metadata = settings.skill_metadata.get(raw_card.id)
        if metadata is None:
            continue
        card = enrich_skill_card(raw_card, settings)
        if card.category == "uncategorized" or not card.capabilities:
            raise ValueError(f"skill capability metadata is incomplete: {card.id}")
        effects = normalize_effects(metadata.effects)
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


def active_skill_capability_contributions(
    service: SkillsService,
    settings: CapabilitySettings,
) -> tuple[CapabilityContribution, ...]:
    cards: list[SkillCard] = []
    cursor: str | None = None
    while True:
        page = service._list_catalogue_skills(
            limit=service.catalogue.config.limits.list_max_limit,
            cursor=cursor,
        )
        cards.extend(page.skills)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    return skill_capability_contributions(tuple(cards), settings)


def current_skill_capability_contributions(
    service: object,
    startup_cards: tuple[SkillCard, ...],
    settings: CapabilitySettings,
) -> tuple[CapabilityContribution, ...]:
    if isinstance(service, SkillsService):
        return active_skill_capability_contributions(service, settings)
    return skill_capability_contributions(startup_cards, settings)


def register_platform_skills(server, *, state_root: Path | str | None = None):
    telemetry = None
    if state_root is not None:
        telemetry = SkillTelemetryStore(
            Path(state_root) / "telemetry" / "skills.sqlite3",
            observability=get_runtime_observability(),
        )
    service = register_skills_tools(server, telemetry=telemetry)
    if not isinstance(service, SkillsService):
        return service, ()
    register_skill_resources(server, service.catalogue)
    response = service._list_catalogue_skills(
        limit=service.catalogue.config.limits.list_max_limit
    )
    settings = load_capability_settings()
    cards = tuple(enrich_skill_card(card, settings) for card in response.skills)
    return service, cards


__all__ = [
    "active_skill_capability_contributions",
    "current_skill_capability_contributions",
    "enrich_skill_card",
    "register_platform_skills",
    "skill_capability_contributions",
]
