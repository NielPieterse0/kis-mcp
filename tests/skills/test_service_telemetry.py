from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.service import SkillsService
from kis_mcp.skills.telemetry import SkillTelemetryEvent, SkillTelemetryStore


class NoOpBackend:
    async def create_directory(self, path: str) -> None:
        del path

    async def write_text(self, path: str, content: str) -> None:
        del path, content

    async def move(self, source: str, destination: str) -> None:
        del source, destination

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        del path, old_string, new_string


class FilesystemBackend:
    async def create_directory(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=False)

    async def write_text(self, path: str, content: str) -> None:
        with Path(path).open("w", encoding="utf-8", newline="") as handle:
            handle.write(content)

    async def move(self, source: str, destination: str) -> None:
        shutil.move(source, destination)

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        target = Path(path)
        assert target.read_text(encoding="utf-8") == old_string
        with target.open("w", encoding="utf-8", newline="") as handle:
            handle.write(new_string)


def _service(skills_config, tmp_path: Path) -> tuple[SkillsService, SkillTelemetryStore]:
    store = SkillTelemetryStore(tmp_path / "skills-telemetry.sqlite3")
    return SkillsService(SkillCatalogue(skills_config), NoOpBackend(), telemetry=store), store


def test_read_operations_record_versioned_observed_activity(
    skills_config, make_skill, tmp_path: Path
) -> None:
    root = make_skill(
        "alpha-skill",
        extra_files={"references/note.md": "bounded evidence"},
    )
    service, store = _service(skills_config, tmp_path)

    loaded = service.load_skill(
        "alpha-skill", activation_id="activation-1", project_id="project-alpha"
    )
    service.read_skill_file(
        "alpha-skill",
        "references/note.md",
        activation_id="activation-1",
        project_id="project-alpha",
    )
    service.evaluate_skill("alpha-skill")

    groups = store.report(skill_id="alpha-skill").groups
    assert len(groups) == 2
    version_group = next(
        group for group in groups
        if group.content_sha256 == loaded.sha256 and group.project_id == "project-alpha"
    )
    assert version_group.loaded_count == 1
    assert version_group.resource_read_count == 1
    assert sum(group.evaluated_count for group in groups) == 1
    assert (root / "SKILL.md").is_file()


def test_reported_outcome_requires_matching_observed_load(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    service, store = _service(skills_config, tmp_path)
    loaded = service.load_skill(
        "alpha-skill", activation_id="activation-1", project_id="project-alpha"
    )

    service.record_skill_outcome(
        skill_id="alpha-skill",
        activation_id="activation-1",
        snapshot_id=loaded.snapshot_id,
        content_sha256=loaded.sha256,
        project_id="project-alpha",
        phase="completed",
        total_tokens=123,
        tool_calls=4,
        retries=0,
        verification_passed=True,
    )

    group = next(
        item for item in store.report(skill_id="alpha-skill").groups
        if item.content_sha256 == loaded.sha256
    )
    assert group.loaded_count == 1
    assert group.completed_count == 1
    assert group.total_tokens == 123
    with pytest.raises(SkillsError, match="SKILLS_TELEMETRY_ATTRIBUTION_REQUIRED"):
        service.record_skill_outcome(
            skill_id="alpha-skill",
            activation_id="missing-activation",
            snapshot_id=loaded.snapshot_id,
            content_sha256=loaded.sha256,
            project_id="project-alpha",
            phase="completed",
        )


def test_search_query_is_not_persisted(skills_config, make_skill, tmp_path: Path) -> None:
    make_skill("alpha-skill")
    service, store = _service(skills_config, tmp_path)

    result = service.search_skills("super-secret-query alpha")

    assert result.skills[0].id == "alpha-skill"
    assert b"super-secret-query" not in store.path.read_bytes()
    assert sum(
        group.discovered_count for group in store.report(skill_id="alpha-skill").groups
    ) == 1


def test_failed_load_is_error_not_successful_load(
    skills_config, tmp_path: Path
) -> None:
    service, store = _service(skills_config, tmp_path)

    with pytest.raises(SkillsError, match="SKILLS_UNKNOWN"):
        service.load_skill("missing-skill", activation_id="activation-1")

    group = store.report(skill_id="missing-skill").groups[0]
    assert group.loaded_count == 0
    assert group.error_count == 1


def test_mutations_record_versioned_events(skills_config, tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills-telemetry.sqlite3")
    service = SkillsService(
        SkillCatalogue(skills_config), FilesystemBackend(), telemetry=store
    )
    original = "---\nname: new-skill\ndescription: New skill\n---\n# New\n"
    created = asyncio.run(service.create_skill("new-skill", original))
    updated = original.replace("# New", "# Improved")

    asyncio.run(
        service.improve_skill(
            "new-skill", "SKILL.md", created.after_sha256, updated
        )
    )

    groups = store.report(skill_id="new-skill").groups
    assert sum(group.mutation_count for group in groups) == 2


def test_reported_outcome_requires_same_delivery_path_as_observed_load(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    service, store = _service(skills_config, tmp_path)
    loaded = service.load_skill(
        "alpha-skill", activation_id="activation-1", project_id="project-alpha"
    )

    with pytest.raises(SkillsError, match="SKILLS_TELEMETRY_ATTRIBUTION_REQUIRED"):
        service.record_skill_outcome(
            skill_id="alpha-skill",
            activation_id="activation-1",
            snapshot_id=loaded.snapshot_id,
            content_sha256=loaded.sha256,
            project_id="project-alpha",
            phase="completed",
            delivery_path="mcp_resource",
        )

    store.record(
        SkillTelemetryEvent(
            event_name="skill_loaded",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id=loaded.snapshot_id,
            content_sha256=loaded.sha256,
            project_id="project-alpha",
            activation_id="activation-1",
            delivery_path="mcp_resource",
            resource_uri="skill:///alpha-skill/SKILL.md",
            resource_class="SKILL.md",
            server_origin="kis-test",
            digest_verified=True,
        )
    )
    event = service.record_skill_outcome(
        skill_id="alpha-skill",
        activation_id="activation-1",
        snapshot_id=loaded.snapshot_id,
        content_sha256=loaded.sha256,
        project_id="project-alpha",
        phase="completed",
        delivery_path="mcp_resource",
    )
    assert event.delivery_path == "mcp_resource"
