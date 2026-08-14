from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import kis_mcp.discover.intelligence as intelligence_module
from kis_mcp.config import load_runtime_config
from kis_mcp.discover.intelligence import ProjectIntelligenceService
from kis_mcp.evidence import EvidenceConflictError
from kis_mcp.projects import ProjectDefinition, ProjectRegistry

ROOT = Path(__file__).resolve().parents[2]


def _service(tmp_path: Path, project: Path) -> ProjectIntelligenceService:
    settings = load_runtime_config(ROOT).discover_settings
    settings = replace(
        settings,
        memory=replace(
            settings.memory,
            state_root=str(tmp_path / "central-state"),
            max_stored_bytes=2_000_000,
            max_files=100,
            max_modules=100,
            max_symbols=100,
            max_relationships=200,
        ),
    )
    registry = ProjectRegistry(
        default_project_id="demo",
        projects=(ProjectDefinition("demo", "Demo", str(project)),),
    )
    return ProjectIntelligenceService(
        boundary=tmp_path,
        settings=settings,
        projects=registry,
    )


def test_discover_publishes_repo_local_recovery_hint_after_central_generation(
    tmp_path: Path,
) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    service = _service(tmp_path, project)

    cold = service.get(str(project))
    warm = service.get(str(project))

    recovery = cold.persistence["recovery_capsule"]
    assert recovery["status"] == "current"
    assert Path(str(recovery["root"])) == (project / ".temp" / "kis").resolve()
    assert recovery["central_generation_id"] == cold.persistence["generation_id"]
    assert warm.persistence["status"] == "reused"
    assert (
        warm.persistence["recovery_capsule"]["central_generation_id"]
        == warm.persistence["generation_id"]
    )


def test_discover_degrades_when_recovery_capsule_construction_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    service = _service(tmp_path, project)

    class BrokenCapsule:
        def __init__(self, _definition: ProjectDefinition) -> None:
            raise EvidenceConflictError("capsule containment rejected")

    monkeypatch.setattr(intelligence_module, "ProjectRecoveryCapsule", BrokenCapsule)

    result = service.get(str(project))

    assert result.persistence["status"] == "created"
    assert result.persistence["recovery_capsule"] == {
        "status": "degraded",
        "available": True,
        "root": str(project / ".temp" / "kis"),
        "error": "EvidenceConflictError",
    }
