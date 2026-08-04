from __future__ import annotations

import re
from pathlib import Path

import pytest

from kis_mcp.skills.config import SkillsConfig, SkillsLimits, SkillsValidation


@pytest.fixture
def skills_config(tmp_path: Path) -> SkillsConfig:
    root = tmp_path / "skills"
    staging = tmp_path / "staging"
    root.mkdir()
    staging.mkdir()
    return SkillsConfig(
        root=root,
        staging_root=staging,
        limits=SkillsLimits(
            max_file_bytes=10_000,
            max_skill_bytes=50_000,
            list_default_limit=2,
            list_max_limit=10,
            search_default_limit=5,
            search_max_limit=10,
            file_search_default_limit=5,
            file_search_max_limit=10,
        ),
        validation=SkillsValidation(
            skill_id_pattern=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
            allowed_suffixes=(
                ".md",
                ".json",
                ".yaml",
                ".yml",
                ".py",
                ".ps1",
                ".sh",
                ".txt",
                ".toml",
                ".png",
            ),
            reject_links=True,
            reject_reparse_points=True,
            reject_hard_links=True,
            reject_backslashes=True,
        ),
    )


@pytest.fixture
def make_skill(skills_config: SkillsConfig):
    def create(
        skill_id: str,
        *,
        description: str | None = None,
        category: str = "uncategorized",
        capabilities: tuple[str, ...] = (),
        extra_files: dict[str, str] | None = None,
    ) -> Path:
        root = skills_config.root / skill_id
        root.mkdir()
        capability_lines = "\n".join(f"  - {item}" for item in capabilities)
        capability_block = (
            f"capabilities:\n{capability_lines}\n" if capabilities else ""
        )
        (root / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_id}\n"
            f"description: {description or f'Summary for {skill_id}'}\n"
            f"category: {category}\n"
            f"{capability_block}"
            "status: active\n"
            "---\n\n"
            f"# {skill_id}\n",
            encoding="utf-8",
        )
        for relative, content in (extra_files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return root

    return create
