from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.evidence import EvidenceConflictError
from kis_mcp.projects import ProjectDefinition
from kis_mcp.projects.recovery import ProjectRecoveryCapsule, RecoveryIdentity


def _project(tmp_path: Path) -> ProjectDefinition:
    return ProjectDefinition(
        project_id="demo",
        display_name="Demo",
        local_root=str(tmp_path),
    )


def _identity(
    project: ProjectDefinition, worktree: Path, *, revision: str = "a" * 40
) -> RecoveryIdentity:
    return RecoveryIdentity.for_project(
        project,
        worktree_root=str(worktree),
        git_revision=revision,
        git_status="clean",
        source_fingerprint="1" * 64,
        settings_fingerprint="2" * 64,
        provider_fingerprint="3" * 64,
    )


def test_capsule_uses_registered_repo_temp_and_rejects_stale_identity(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    identity = _identity(project, tmp_path)

    written = capsule.publish_discover_hint(identity, central_generation_id="4" * 64)

    assert capsule.root == (tmp_path / ".temp" / "kis").resolve()
    assert (capsule.root / ".gitignore").read_text(encoding="utf-8") == "*\n"
    assert written.status == "current"
    assert written.central_generation_id == "4" * 64
    assert capsule.inspect(identity).status == "current"

    stale = _identity(project, tmp_path, revision="b" * 40)
    inspected = capsule.inspect(stale)
    assert inspected.status == "stale"
    assert inspected.central_generation_id is None


def test_parallel_worktrees_have_independent_current_pointers(tmp_path: Path) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    one = _identity(project, tmp_path / ".work" / "one")
    two = _identity(project, tmp_path / ".work" / "two")

    first = capsule.publish_discover_hint(one, central_generation_id="5" * 64)
    second = capsule.publish_discover_hint(two, central_generation_id="6" * 64)

    assert first.namespace != second.namespace
    assert capsule.inspect(one).central_generation_id == "5" * 64
    assert capsule.inspect(two).central_generation_id == "6" * 64


def test_corrupt_capsule_is_retained_and_rebuilt(tmp_path: Path) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    identity = _identity(project, tmp_path)
    current = capsule.publish_discover_hint(identity, central_generation_id="7" * 64)
    pointer = capsule.root / Path(*current.namespace.split("/")) / "current.json"
    pointer.write_text("not-json\n", encoding="utf-8")

    corrupt = capsule.inspect(identity)

    assert corrupt.status == "corrupt"
    assert corrupt.recovered_pointer is not None
    assert not pointer.exists()
    rebuilt = capsule.publish_discover_hint(identity, central_generation_id="8" * 64)
    assert rebuilt.status == "current"
    assert capsule.inspect(identity).central_generation_id == "8" * 64


def test_operation_checkpoints_are_idempotent_and_conflict_safe(tmp_path: Path) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    identity = _identity(project, tmp_path)

    started = capsule.begin_operation(
        identity,
        operation_name="project.inspect",
        idempotency_key="request-123",
        request_fingerprint="9" * 64,
    )
    assert started.operation_state == "started"
    assert "request-123" not in json.dumps(started.to_json_dict())

    resumed = capsule.begin_operation(
        identity,
        operation_name="project.inspect",
        idempotency_key="request-123",
        request_fingerprint="9" * 64,
    )
    assert resumed.generation_id == started.generation_id

    completed = capsule.complete_operation(
        identity,
        operation_name="project.inspect",
        idempotency_key="request-123",
        request_fingerprint="9" * 64,
        result_fingerprint="a" * 64,
    )
    assert completed.operation_state == "completed"

    retry = capsule.begin_operation(
        identity,
        operation_name="project.inspect",
        idempotency_key="request-123",
        request_fingerprint="9" * 64,
    )
    assert retry.operation_state == "completed"
    assert retry.generation_id == completed.generation_id

    with pytest.raises(EvidenceConflictError, match="idempotency"):
        capsule.begin_operation(
            identity,
            operation_name="project.inspect",
            idempotency_key="request-123",
            request_fingerprint="b" * 64,
        )


def test_capsule_does_not_overwrite_an_existing_incompatible_local_ignore(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    capsule.root.mkdir(parents=True)
    marker = capsule.root / ".gitignore"
    marker.write_text("keep-this-rule\n", encoding="utf-8")

    with pytest.raises(EvidenceConflictError, match="gitignore"):
        capsule.publish_discover_hint(
            _identity(project, tmp_path),
            central_generation_id="c" * 64,
        )

    assert marker.read_text(encoding="utf-8") == "keep-this-rule\n"
    assert not (capsule.root / "sessions").exists()


def test_capsule_rechecks_registered_root_containment_before_publish(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    capsule = ProjectRecoveryCapsule(project)
    capsule._capsule_path = tmp_path.parent / "outside-kis-capsule"

    with pytest.raises(
        EvidenceConflictError, match="escapes the registered project root"
    ):
        capsule.publish_discover_hint(
            _identity(project, tmp_path),
            central_generation_id="d" * 64,
        )

    assert not (tmp_path.parent / "outside-kis-capsule").exists()
