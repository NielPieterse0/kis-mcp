from pathlib import Path

import pytest

from kis_mcp.skills.frontmatter import parse_skill_frontmatter


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("skill_id", ["kis-mcp", "mcp-development"])
def test_new_skills_define_catalogue_metadata(skill_id: str) -> None:
    content = (
        REPOSITORY_ROOT / ".agents" / "skills" / skill_id / "SKILL.md"
    ).read_text(encoding="utf-8")
    frontmatter = parse_skill_frontmatter(content)

    assert isinstance(frontmatter.get("category"), str)
    capabilities = frontmatter.get("capabilities")
    assert isinstance(capabilities, list)
    assert capabilities
    assert all(isinstance(item, str) and item.strip() for item in capabilities)
