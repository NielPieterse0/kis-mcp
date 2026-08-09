from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.providers.serena import load_serena_settings
from kis_mcp.providers.serena.memory import (
    quarantine_serena_memory_delete,
    resolve_serena_memory_artifacts,
)
from kis_mcp.quarantine import QuarantineService

ROOT = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path):
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    install_root = tmp_path / "serena"
    return replace(
        settings,
        install_root=install_root,
        project_data_root=install_root / "projects",
    )


def test_hr3_07_quarantines_complete_pinned_delete_artifact_and_restores(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    affected = resolve_serena_memory_artifacts(
        settings,
        "topic/demo",
        project_root=str(project),
    )
    assert affected.pinned_version == "1.6.1"
    assert affected.catalogue_model == "derived_from_markdown_files"
    assert len(affected.artifacts) == 1

    memory = Path(affected.artifacts[0])
    expected_memory_root = settings.project_data_path(str(project)) / "memories"
    assert memory.is_relative_to(expected_memory_root)
    assert not memory.is_relative_to(project)
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text("proof\n", encoding="utf-8")
    quarantine = QuarantineService(
        project_boundary=settings.project_boundary,
        quarantine_root=str(tmp_path / "quarantine"),
    )
    result = quarantine_serena_memory_delete(
        settings,
        "topic/demo",
        project_root=str(project),
        quarantine=quarantine,
    )
    assert result.status == "quarantined"
    assert result.forwarded_delete is False
    assert tuple(record.original_path for record in result.records) == affected.artifacts
    assert not memory.exists()

    restored = quarantine.restore(result.records[0].operation_id)
    assert restored.original_path == str(memory)
    assert memory.read_text(encoding="utf-8") == "proof\n"

    names = sorted(
        str(item.relative_to(expected_memory_root).with_suffix(""))
        .replace("\\", "/")
        for item in expected_memory_root.rglob("*.md")
    )
    assert names == ["topic/demo"]


def test_hr3_07_rejects_wildcards_aliases_and_traversal(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    for name in ("../demo", "topic/*", "topic/?", "mem:demo", "/absolute"):
        with pytest.raises(ValueError):
            resolve_serena_memory_artifacts(
                settings,
                name,
                project_root=str(project),
            )


def test_hr3_07_missing_memory_is_safe_noop(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    quarantine = QuarantineService(
        project_boundary=settings.project_boundary,
        quarantine_root=str(tmp_path / "quarantine"),
    )

    result = quarantine_serena_memory_delete(
        settings,
        "missing",
        project_root=str(project),
        quarantine=quarantine,
    )
    assert result.status == "not_found"
    assert result.records == ()
    assert result.forwarded_delete is False
