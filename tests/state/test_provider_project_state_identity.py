from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from kis_mcp.projects import ProjectDefinition, ProjectRegistry
from kis_mcp.providers import commissioning as commissioning_module
from kis_mcp.providers.commissioning import (
    commissioning_evidence_path,
    commissioning_evidence_root,
    read_commissioning_evidence,
    write_commissioning_evidence,
)


def _registry() -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="kis-mcp",
        projects=(
            ProjectDefinition(
                project_id="kis-mcp",
                display_name="kis-mcp",
                local_root=r"C:\Projects\kis-mcp",
            ),
        ),
    )


def test_dbhub_commissioning_uses_canonical_source_namespace(monkeypatch) -> None:
    monkeypatch.setattr(
        commissioning_module,
        "load_runtime_config",
        lambda root: SimpleNamespace(state_root=r"C:\Projects\.kis-mcp"),
    )
    monkeypatch.setattr(
        commissioning_module,
        "load_project_registry_settings",
        lambda path: _registry(),
    )

    main_root = commissioning_evidence_root(
        Path(r"C:\Projects\kis-mcp"), provider_id="dbhub"
    )
    worktree_root = commissioning_evidence_root(
        Path(r"C:\Projects\kis-mcp\.work\worktrees\255-provider-project-state-identity"),
        provider_id="dbhub",
    )
    docker_root = commissioning_evidence_root(
        Path(r"C:\Projects\kis-mcp"), provider_id="dockerhub-mcp"
    )

    assert "projects\\kis-mcp\\sources\\" in str(main_root)
    assert str(main_root).endswith("\\evidence\\provider-commissioning")
    assert worktree_root != main_root
    assert "change-255-provider-project-state-identity" in str(worktree_root)
    assert docker_root == Path(r"C:\Projects\.kis-mcp\commissioning\providers")


def test_valid_legacy_commissioning_is_copied_without_deletion(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    canonical_root = tmp_path / "canonical"
    identity = {"source_revision": "rev-1", "expected_tools": ["alpha"]}
    legacy_path = write_commissioning_evidence(
        legacy_root, "dbhub", identity, ("alpha",)
    )

    result = read_commissioning_evidence(
        canonical_root,
        "dbhub",
        identity,
        legacy_roots=(legacy_root,),
    )
    canonical_path = commissioning_evidence_path(
        canonical_root, "dbhub", identity
    )
    assert result is not None
    assert result["verified_tools"] == ["alpha"]
    assert canonical_path.is_file()
    assert legacy_path.is_file()


def test_ambiguous_or_mismatched_legacy_commissioning_is_rejected(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    canonical_root = tmp_path / "canonical"
    identity = {"source_revision": "rev-1", "expected_tools": ["alpha"]}
    stale = {"source_revision": "rev-2", "expected_tools": ["alpha"]}
    write_commissioning_evidence(legacy_root, "dbhub", stale, ("alpha",))

    assert (
        read_commissioning_evidence(
            canonical_root,
            "dbhub",
            identity,
            legacy_roots=(legacy_root,),
        )
        is None
    )
    assert not commissioning_evidence_path(
        canonical_root, "dbhub", identity
    ).exists()
