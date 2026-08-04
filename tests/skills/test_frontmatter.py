from __future__ import annotations

import pytest

from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.frontmatter import parse_skill_frontmatter


def test_frontmatter_parser_supports_quotes_lists_and_folded_text() -> None:
    parsed = parse_skill_frontmatter(
        "---\n"
        "name: sample-skill\n"
        "description: >\n"
        "  Assess modules:\n"
        "  preserve seams.\n"
        "category: 'architecture'\n"
        "capabilities: [read, analysis]\n"
        "---\n"
    )

    assert parsed == {
        "name": "sample-skill",
        "description": "Assess modules: preserve seams.",
        "category": "architecture",
        "capabilities": ["read", "analysis"],
    }


def test_frontmatter_parser_rejects_nested_or_unexpected_indentation() -> None:
    with pytest.raises(SkillsError, match="SKILLS_FRONTMATTER_INVALID"):
        parse_skill_frontmatter(
            "---\nname: sample-skill\ndescription: Summary\n  nested: nope\n---\n"
        )
