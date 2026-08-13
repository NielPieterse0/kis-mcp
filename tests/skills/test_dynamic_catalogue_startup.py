from dataclasses import replace

import pytest

from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.config import load_skills_config
from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.models import SkillCard
from kis_mcp.skills.platform import skill_capability_contributions


def test_production_settings_require_canonical_kis_mcp() -> None:
    assert load_skills_config().required_skills == ("kis-mcp",)


def test_unclassified_valid_skill_has_no_private_contribution() -> None:
    card = SkillCard(
        id="bayesian-modeler",
        summary="Valid shared skill without KIS capability metadata",
        category="uncategorized",
        capabilities=(),
        status="active",
    )
    assert skill_capability_contributions((card,), load_capability_settings()) == ()


def test_catalogue_requires_configured_kis_mcp(skills_config, make_skill) -> None:
    make_skill("bayesian-modeler")
    configured = replace(skills_config, required_skills=("kis-mcp",))
    with pytest.raises(SkillsError, match="SKILLS_REQUIRED_MISSING"):
        SkillCatalogue(configured)


def test_catalogue_accepts_required_and_unclassified_skills(skills_config, make_skill) -> None:
    make_skill("kis-mcp")
    make_skill("bayesian-modeler")
    catalogue = SkillCatalogue(replace(skills_config, required_skills=("kis-mcp",)))
    assert [item.id for item in catalogue.list_skills(limit=10).skills] == [
        "bayesian-modeler",
        "kis-mcp",
    ]
