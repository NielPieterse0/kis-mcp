from __future__ import annotations

from kis_mcp.skills.frontmatter import parse_skill_frontmatter


def test_skill_frontmatter_supports_optional_catalogue_metadata() -> None:
    content = """---
name: example-skill
description: Example reusable procedure.
category: development
capabilities:
  - code.change.plan
  - verification.execute
---
# Example
"""
    frontmatter = parse_skill_frontmatter(content)

    assert frontmatter["category"] == "development"
    capabilities = frontmatter["capabilities"]
    assert capabilities == ["code.change.plan", "verification.execute"]
