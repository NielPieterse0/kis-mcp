from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.config import SkillsConfig
from kis_mcp.skills.errors import SkillsError


def test_refresh_and_list_are_deterministic_and_paginated(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill("beta-skill", category="testing")
    make_skill("alpha-skill", category="architecture", capabilities=("read",))
    make_skill("gamma-skill")

    catalogue = SkillCatalogue(skills_config)
    first = catalogue.list_skills(limit=2)
    second = catalogue.list_skills(limit=2, cursor=first.next_cursor)

    assert [item.id for item in first.skills] == ["alpha-skill", "beta-skill"]
    assert [item.id for item in second.skills] == ["gamma-skill"]
    assert first.skill_count == 3
    assert first.snapshot_id == second.snapshot_id
    assert len(first.snapshot_id) == 16
    assert second.next_cursor is None
    assert catalogue.refresh_skills().snapshot_id == first.snapshot_id


def test_search_load_file_read_and_evaluation_use_active_snapshot(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill(
        "modularity-assessment",
        description="Assess module boundaries and coupling.",
        category="architecture",
        capabilities=("read", "analysis"),
        extra_files={
            "references/rubric.md": "cohesion coupling blast radius",
            "scripts/check.py": "print('ok')\n",
        },
    )
    catalogue = SkillCatalogue(skills_config)

    matches = catalogue.search_skills("coupling architecture")
    loaded = catalogue.load_skill("modularity-assessment")
    files = catalogue.search_skill_files("modularity-assessment", "rubric")
    file_record = catalogue.read_skill_file(
        "modularity-assessment", "references/rubric.md"
    )
    evaluation = catalogue.evaluate_skill("modularity-assessment")

    assert [item.id for item in matches.skills] == ["modularity-assessment"]
    assert loaded.skill.summary == "Assess module boundaries and coupling."
    assert loaded.file_count == 3
    assert loaded.sha256 == hashlib.sha256(
        (root / "SKILL.md").read_bytes()
    ).hexdigest()
    assert dict(loaded.reference_group_counts) == {
        "references": 1,
        "root": 1,
        "scripts": 1,
    }
    assert [item.path for item in files.files] == ["references/rubric.md"]
    assert file_record.content == "cohesion coupling blast radius"
    assert evaluation.evidence.file_count == 3
    assert evaluation.evidence.supported_file_count == 3
    assert evaluation.evidence.entrypoint_sha256 == loaded.sha256


def test_refresh_invalidates_old_cursor(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill("alpha-skill")
    make_skill("beta-skill")
    make_skill("gamma-skill")
    catalogue = SkillCatalogue(skills_config)
    page = catalogue.list_skills(limit=2)
    assert page.next_cursor is not None

    make_skill("delta-skill")
    catalogue.refresh_skills()

    with pytest.raises(SkillsError, match="SKILLS_CURSOR_INVALID"):
        catalogue.list_skills(limit=2, cursor=page.next_cursor)


def test_catalogue_rejects_traversal_backslashes_and_unknown_files(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill("alpha-skill", extra_files={"references/note.md": "safe"})
    catalogue = SkillCatalogue(skills_config)

    for unsafe in ("../SKILL.md", r"references\note.md", "/absolute.md"):
        with pytest.raises(SkillsError, match="SKILLS_PATH_UNSAFE"):
            catalogue.read_skill_file("alpha-skill", unsafe)

    with pytest.raises(SkillsError, match="SKILLS_FILE_UNKNOWN"):
        catalogue.read_skill_file("alpha-skill", "references/missing.md")


def test_refresh_rejects_invalid_skill_without_replacing_active_snapshot(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    original = catalogue.snapshot_id

    broken = skills_config.root / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")

    with pytest.raises(SkillsError, match="SKILLS_REFRESH_REJECTED"):
        catalogue.refresh_skills()

    assert catalogue.snapshot_id == original
    assert [item.id for item in catalogue.list_skills().skills] == ["alpha-skill"]


def test_validate_create_and_replacement_are_read_only(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    before_bytes = (root / "SKILL.md").read_bytes()
    before = before_bytes.decode("utf-8")
    replacement = before.replace("Summary for alpha-skill", "Improved summary")

    create = catalogue.validate_create(
        "new-skill",
        "---\nname: new-skill\ndescription: New skill\n---\n# New\n",
    )
    target = catalogue.validate_replacement(
        "alpha-skill", "SKILL.md", replacement
    )

    assert create.skill_id == "new-skill"
    assert create.after_sha256 == hashlib.sha256(
        create.content.encode("utf-8")
    ).hexdigest()
    assert target.before_sha256 == hashlib.sha256(before_bytes).hexdigest()
    assert target.after_sha256 == hashlib.sha256(
        replacement.encode("utf-8")
    ).hexdigest()
    assert (root / "SKILL.md").read_bytes() == before_bytes

    with pytest.raises(SkillsError, match="SKILLS_ALREADY_EXISTS"):
        catalogue.validate_create("alpha-skill", before)

    with pytest.raises(SkillsError, match="SKILLS_ID_MISMATCH"):
        catalogue.validate_create("different-id", before)


def test_catalogue_rejects_disallowed_suffix_and_oversize_file(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill("alpha-skill")
    (root / "binary.exe").write_bytes(b"MZ")

    with pytest.raises(SkillsError, match="SKILLS_REFRESH_REJECTED"):
        SkillCatalogue(skills_config)

    (root / "binary.exe").unlink()
    (root / "large.md").write_text(
        "x" * (skills_config.limits.max_file_bytes + 1), encoding="utf-8"
    )
    with pytest.raises(SkillsError, match="SKILLS_REFRESH_REJECTED"):
        SkillCatalogue(skills_config)
