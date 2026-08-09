from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from kis_mcp.config import load_runtime_config
from kis_mcp.discover.intelligence import ProjectIntelligenceService
from kis_mcp.projects import ProjectDefinition, ProjectRegistry

ROOT = Path(__file__).resolve().parents[2]


def _settings(state_root: Path):
    settings = load_runtime_config(ROOT).discover_settings
    return replace(
        settings,
        memory=replace(
            settings.memory,
            state_root=str(state_root),
            max_stored_bytes=2_000_000,
            max_files=100,
            max_modules=100,
            max_symbols=100,
            max_relationships=200,
        ),
    )


def _registry(project_id: str, root: Path) -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id=project_id,
        projects=(
            ProjectDefinition(
                project_id=project_id,
                display_name=project_id,
                local_root=str(root),
            ),
        ),
    )


def test_cold_creation_warm_reuse_and_same_size_dirty_invalidation(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    source = project / "module.py"
    source.write_text("def one():\n    return 1\n", encoding="utf-8")
    settings = _settings(tmp_path / "state")
    service = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=settings,
        projects=_registry("demo", project),
    )

    cold = service.get(str(project))
    warm = service.get(str(project))

    assert cold.persistence["status"] == "created"
    assert warm.persistence["status"] == "reused"
    assert cold.persistence["generation_id"] == warm.persistence["generation_id"]
    assert cold.code_atlas == warm.code_atlas
    assert cold.symbol_atlas == warm.symbol_atlas
    assert cold.relationship_graph == warm.relationship_graph

    source.write_text("def two():\n    return 2\n", encoding="utf-8")
    refreshed = service.get(str(project))
    assert refreshed.persistence["status"] == "refreshed"
    assert refreshed.persistence["generation_id"] != warm.persistence["generation_id"]
    assert refreshed.source_fingerprint != warm.source_fingerprint


def test_registered_project_and_worktree_state_are_isolated(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    worktree = project / ".work" / "worktrees" / "feature"
    worktree.mkdir(parents=True)
    (worktree / "main.py").write_text("VALUE = 2\n", encoding="utf-8")
    service = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=_settings(tmp_path / "state"),
        projects=_registry("demo", project),
    )

    canonical = service.get(str(project))
    isolated = service.get(str(worktree))

    assert canonical.project.project_id == "demo"
    assert isolated.project.project_id == "demo"
    assert canonical.project.canonical_path != isolated.project.canonical_path
    assert canonical.persistence["namespace"] != isolated.persistence["namespace"]
    assert canonical.persistence["generation_id"] != isolated.persistence["generation_id"]


def test_unregistered_project_never_persists(tmp_path: Path) -> None:
    registered = tmp_path / "registered"
    registered.mkdir()
    unregistered = tmp_path / "other"
    unregistered.mkdir()
    (unregistered / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    service = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=_settings(tmp_path / "state"),
        projects=_registry("registered", registered),
    )

    result = service.get(str(unregistered))

    assert result.persistence["status"] == "unregistered"
    assert result.persistence["generation_id"] is None
    assert not (tmp_path / "state").exists()


class _SemanticProvider:
    provider_id = "semantic-test"

    def __init__(self, version: str) -> None:
        self.provider_version = version
        self.state_fingerprint = f"state-{version}"

    def read(self, project_path: str, source_paths: tuple[str, ...] = ()):
        from kis_mcp.discover.semantic import SemanticEvidence, SemanticSymbol

        del project_path
        path = source_paths[0] if source_paths else "module.py"
        return SemanticEvidence(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            status="ready",
            symbols=(
                SemanticSymbol(
                    qualified_name=f"{path}::semantic",
                    name="semantic",
                    kind="function",
                    path=path,
                    line=1,
                    language="python",
                ),
            ),
        )


def test_settings_and_provider_version_invalidate_persisted_generation(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / "module.py").write_text("def one():\n    return 1\n", encoding="utf-8")
    state_root = tmp_path / "state"
    settings = _settings(state_root)
    registry = _registry("demo", project)

    first = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=settings,
        projects=registry,
        semantic_provider=_SemanticProvider("1"),
    ).get(str(project))
    provider_refresh = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=settings,
        projects=registry,
        semantic_provider=_SemanticProvider("2"),
    ).get(str(project))
    settings_refresh = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=replace(settings, memory=replace(settings.memory, max_symbols=1)),
        projects=registry,
        semantic_provider=_SemanticProvider("2"),
    ).get(str(project))

    assert provider_refresh.persistence["status"] == "refreshed"
    assert provider_refresh.persistence["generation_id"] != first.persistence["generation_id"]
    assert settings_refresh.persistence["status"] == "refreshed"
    assert settings_refresh.persistence["generation_id"] != provider_refresh.persistence["generation_id"]
    assert settings_refresh.truncated is True
    assert "memory_max_symbols" in settings_refresh.truncation_reasons


def test_corrupt_current_pointer_is_retained_and_recovered(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    (project / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    state_root = tmp_path / "state"
    settings = _settings(state_root)
    service = ProjectIntelligenceService(
        boundary=tmp_path,
        settings=settings,
        projects=_registry("demo", project),
    )
    first = service.get(str(project))
    namespace = str(first.persistence["namespace"])
    current = state_root.joinpath(*namespace.split("/"), "current.json")
    current.write_text("{broken\n", encoding="utf-8")

    recovered = service.get(str(project))

    assert recovered.persistence["current"] is True
    assert recovered.persistence["generation_id"] != first.persistence["generation_id"]
    assert "recovered_pointer" in recovered.persistence
    recovery = state_root / str(recovered.persistence["recovered_pointer"])
    assert recovery.is_file()
    assert recovery.read_text(encoding="utf-8") == "{broken\n"
