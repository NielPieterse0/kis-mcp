from __future__ import annotations

from pathlib import Path

from ..capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from ..capabilities.normalization import default_quality, normalize_effects
from ..capabilities.settings import CapabilitySettings, load_capability_settings
from ..runtime_observability import get_runtime_observability
from .delivery_telemetry import register_skill_delivery_telemetry
from .metadata import enrich_skill_card
from .models import SkillCard
from .resources import register_skill_resources
from .sep2640 import register_sep2640_extension
from .service import SkillsService
from .status import (
    SkillsRuntimeStatus,
    degraded_skills_runtime_status,
    ready_skills_runtime_status,
)
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


def _degraded_skill_capability_contribution(
    status: SkillsRuntimeStatus,
) -> CapabilityContribution:
    code = status.code or "SKILLS_UNAVAILABLE"
    return CapabilityContribution(
        contribution_id="skills.catalogue",
        domain=CapabilityDomain.SKILL,
        category="skills",
        capabilities=("skills.catalogue",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="skills.catalogue",
            state=ReadinessState.DEGRADED,
            summary=f"Skills catalogue unavailable: {code}",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE, priority=90),
        quality=default_quality(context_cost=5, reliability=100, workflow_integration=90),
    )


def skills_runtime_status(service: object) -> SkillsRuntimeStatus:
    if isinstance(service, SkillsService):
        return ready_skills_runtime_status()
    code = getattr(service, "failure_code", "SKILLS_UNAVAILABLE")
    return degraded_skills_runtime_status(str(code))


def current_skill_capability_contributions(
    service: object,
    startup_cards: tuple[SkillCard, ...],
    settings: CapabilitySettings,
) -> tuple[CapabilityContribution, ...]:
    if isinstance(service, SkillsService):
        return active_skill_capability_contributions(service, settings)
    runtime_status = skills_runtime_status(service)
    return (_degraded_skill_capability_contribution(runtime_status),)


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
    register_sep2640_extension(server, service.catalogue)
    if telemetry is not None:
        register_skill_delivery_telemetry(server, service.catalogue, telemetry)
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
    "skills_runtime_status",
]
