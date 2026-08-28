from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from kis_mcp.quarantine import QuarantineError
from kis_mcp.state.diagnostics import StateDiagnosticsService


def _service(tmp_path: Path) -> StateDiagnosticsService:
    boundary = tmp_path / "projects"
    state_root = boundary / ".kis-mcp"
    quarantine = state_root / "quarantine"
    boundary.mkdir()
    state_root.mkdir()
    return StateDiagnosticsService(
        state_root=state_root,
        project_boundary=boundary,
        quarantine_root=quarantine,
        current_sources={"kis-mcp": {"change-256-state-ownership-diagnostics-cleanup"}},
    )


def test_inventory_classifies_canonical_state_without_reading_payloads(tmp_path: Path) -> None:
    service = _service(tmp_path)
    root = service.state_root
    (root / "global" / "auth" / "github-oauth").mkdir(parents=True)
    stale = root / "projects" / "retired" / "sources" / "change-100-old" / "reconstructible" / "cache"
    stale.mkdir(parents=True)
    (stale / "secret-looking.txt").write_text("do-not-read", encoding="utf-8")

    result = service.inventory(limit=20)
    entries = {item.relative_path: item for item in result.entries}

    auth = entries["global\\auth\\github-oauth"]
    assert auth.ownership_class == "shared-auth"
    assert auth.authoritative is True
    assert auth.safe_to_cleanup is False

    candidate = entries[
        "projects\\retired\\sources\\change-100-old\\reconstructible\\cache"
    ]
    assert candidate.ownership_class == "reconstructible-cache"
    assert candidate.stale is True
    assert candidate.stale_reason == "project_not_registered"
    assert candidate.safe_to_cleanup is False
    assert "do-not-read" not in str(result.to_json_dict())


def test_inventory_does_not_follow_directory_links_outside_state_root(tmp_path: Path) -> None:
    service = _service(tmp_path)
    external = tmp_path / "external-state"
    external_cache = external / "kis-mcp" / "sources" / "change-777-external" / "reconstructible" / "secret-cache"
    external_cache.mkdir(parents=True)
    projects_link = service.state_root / "projects"
    try:
        os.symlink(external, projects_link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    result = service.inventory(limit=50)
    assert result.entries == ()
    assert "secret-cache" not in str(result.to_json_dict())


def test_inventory_treats_canonical_namespace_as_payload_opaque_leaf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    cache = service.state_root / "projects" / "retired" / "sources" / "change-104-payload" / "reconstructible" / "cache"
    cache.mkdir(parents=True)
    for index in range(200):
        (cache / f"payload-{index:03d}").mkdir()
    original_iterdir = Path.iterdir

    def guarded_iterdir(path: Path):
        if path == cache:
            raise AssertionError("payload namespace must not be traversed")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    result = service.inventory(limit=20)
    assert [entry.relative_path for entry in result.entries] == [
        "projects\\retired\\sources\\change-104-payload\\reconstructible\\cache"
    ]


def test_current_reconstructible_cache_is_not_cleanup_candidate(tmp_path: Path) -> None:
    service = _service(tmp_path)
    current = (
        service.state_root
        / "projects"
        / "kis-mcp"
        / "sources"
        / "change-256-state-ownership-diagnostics-cleanup"
        / "reconstructible"
        / "discover"
    )
    current.mkdir(parents=True)

    entry = service.inventory().entries[0]
    assert entry.stale is False
    assert entry.safe_to_cleanup is False


def test_cleanup_previews_then_quarantines_only_stale_reconstructible_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = (
        service.state_root
        / "projects"
        / "kis-mcp"
        / "sources"
        / "change-100-old"
        / "reconstructible"
        / "cache"
    )
    candidate.mkdir(parents=True)
    (candidate / "payload.txt").write_text("cache", encoding="utf-8")
    relative = str(candidate.relative_to(service.state_root))

    preview = service.cleanup(relative, apply=False)
    assert preview["mode"] == "preview"
    assert preview["preview_token"]
    assert candidate.is_dir()

    with pytest.raises(ValueError, match="preview_token"):
        service.cleanup(relative, apply=True)

    applied = service.cleanup(
        relative,
        apply=True,
        idempotency_key="cleanup-basic",
        preview_token=str(preview["preview_token"]),
    )
    assert applied["mode"] == "apply"
    assert applied["action"] == "quarantined"
    assert not candidate.exists()
    assert applied["quarantine_operation_id"]

    with pytest.raises(ValueError, match="not eligible"):
        service.cleanup(relative, apply=True)
    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-basic")
    assert replay == applied


def test_inventory_refreshes_current_sources_before_classifying_staleness(tmp_path: Path) -> None:
    boundary = tmp_path / "projects"
    state_root = boundary / ".kis-mcp"
    boundary.mkdir()
    state_root.mkdir()
    current_sources: dict[str, set[str]] = {"kis-mcp": {"main"}}
    service = StateDiagnosticsService(
        state_root=state_root,
        project_boundary=boundary,
        quarantine_root=state_root / "quarantine",
        current_sources_provider=lambda: current_sources,
    )
    candidate = state_root / "projects" / "kis-mcp" / "sources" / "change-999-new-worktree" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)

    assert service.inventory().entries[0].stale is True
    current_sources["kis-mcp"].add("change-999-new-worktree")
    assert service.inventory().entries[0].stale is False


def test_cleanup_idempotency_key_replays_exact_target_and_rejects_conflicts(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.state_root / "projects" / "kis-mcp" / "sources" / "change-100-old" / "reconstructible" / "cache"
    first.mkdir(parents=True)
    relative = str(first.relative_to(service.state_root))

    preview = service.cleanup(relative, apply=False)
    applied = service.cleanup(
        relative,
        apply=True,
        idempotency_key="cleanup-1",
        preview_token=str(preview["preview_token"]),
    )
    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-1")
    assert replay == applied
    first.mkdir(parents=True)
    occupied_replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-1")
    assert occupied_replay == applied

    second = service.state_root / "projects" / "kis-mcp" / "sources" / "change-101-other" / "reconstructible" / "cache"
    second.mkdir(parents=True)
    with pytest.raises(ValueError, match="different state path"):
        service.cleanup(str(second.relative_to(service.state_root)), apply=True, idempotency_key="cleanup-1")


def test_cleanup_rolls_back_if_source_becomes_current_at_mutation_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    boundary = tmp_path / "projects"
    state_root = boundary / ".kis-mcp"
    boundary.mkdir()
    state_root.mkdir()
    current_sources: dict[str, set[str]] = {"kis-mcp": {"main"}}
    service = StateDiagnosticsService(
        state_root=state_root,
        project_boundary=boundary,
        quarantine_root=state_root / "quarantine",
        current_sources_provider=lambda: current_sources,
    )
    candidate = state_root / "projects" / "kis-mcp" / "sources" / "change-998-race" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(state_root))
    original_quarantine = service.quarantine.quarantine

    def become_current_then_quarantine(path: str, **kwargs: object):
        current_sources["kis-mcp"].add("change-998-race")
        return original_quarantine(path, **kwargs)

    preview = service.cleanup(relative, apply=False)
    monkeypatch.setattr(service.quarantine, "quarantine", become_current_then_quarantine)
    with pytest.raises(QuarantineError, match="became current"):
        service.cleanup(
            relative,
            apply=True,
            idempotency_key="cleanup-race",
            preview_token=str(preview["preview_token"]),
        )
    assert candidate.is_dir()
    assert service.quarantine.list_records() == []


def test_failed_cleanup_releases_new_idempotency_reservation(tmp_path: Path) -> None:
    boundary = tmp_path / "projects"
    state_root = boundary / ".kis-mcp"
    boundary.mkdir()
    state_root.mkdir()
    calls = 0

    def current_sources_provider() -> dict[str, set[str]]:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("transient registry read failure")
        return {"kis-mcp": {"main"}}

    service = StateDiagnosticsService(
        state_root=state_root,
        project_boundary=boundary,
        quarantine_root=state_root / "quarantine",
        current_sources_provider=current_sources_provider,
    )
    candidate = state_root / "projects" / "kis-mcp" / "sources" / "change-997-retry" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(state_root))

    preview = service.cleanup(relative, apply=False)
    with pytest.raises(RuntimeError, match="transient registry read failure"):
        service.cleanup(
            relative,
            apply=True,
            idempotency_key="cleanup-retry",
            preview_token=str(preview["preview_token"]),
        )
    assert candidate.is_dir()
    assert not service.idempotency.binding_path("cleanup-retry").exists()

    calls = 0
    service._current_sources_provider = lambda: {"kis-mcp": {"main"}}
    applied = service.cleanup(
        relative,
        apply=True,
        idempotency_key="cleanup-retry",
        preview_token=str(preview["preview_token"]),
    )
    assert applied["action"] == "quarantined"


def test_idempotency_lock_serializes_service_instances(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-105-lock" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    second = StateDiagnosticsService(
        state_root=service.state_root,
        project_boundary=service.project_boundary,
        quarantine_root=service.quarantine_root,
        current_sources={"kis-mcp": {"change-256-state-ownership-diagnostics-cleanup"}},
    )

    preview = second.cleanup(relative, apply=False)
    handle = service.idempotency.acquire_lock("cleanup-lock")
    try:
        with pytest.raises(ValueError, match="already reserved"):
            second.cleanup(
                relative,
                apply=True,
                idempotency_key="cleanup-lock",
                preview_token=str(preview["preview_token"]),
            )
    finally:
        service.idempotency.release_lock(handle)

    applied = second.cleanup(
        relative,
        apply=True,
        idempotency_key="cleanup-lock",
        preview_token=str(preview["preview_token"]),
    )
    assert applied["action"] == "quarantined"


def test_cleanup_idempotency_binding_survives_service_restart(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-102-old" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))

    preview = service.cleanup(relative, apply=False)
    applied = service.cleanup(
        relative,
        apply=True,
        idempotency_key="cleanup-restart",
        preview_token=str(preview["preview_token"]),
    )
    restarted = StateDiagnosticsService(
        state_root=service.state_root,
        project_boundary=service.project_boundary,
        quarantine_root=service.quarantine_root,
        current_sources={"kis-mcp": {"change-256-state-ownership-diagnostics-cleanup"}},
    )
    replay = restarted.cleanup(relative, apply=True, idempotency_key="cleanup-restart")
    assert replay == applied

    other = service.state_root / "projects" / "kis-mcp" / "sources" / "change-103-other" / "reconstructible" / "cache"
    other.mkdir(parents=True)
    with pytest.raises(ValueError, match="different state path"):
        restarted.cleanup(str(other.relative_to(service.state_root)), apply=True, idempotency_key="cleanup-restart")


def test_inventory_covers_canonical_ownership_classes(tmp_path: Path) -> None:
    service = _service(tmp_path)
    root = service.state_root
    paths = [
        root / "global" / "authority" / "a",
        root / "global" / "cache" / "c",
        root / "global" / "auth" / "oauth",
        root / "projects" / "kis-mcp" / "state" / "p",
        root / "projects" / "kis-mcp" / "sources" / "change-256-state-ownership-diagnostics-cleanup" / "state" / "w",
        root / "projects" / "kis-mcp" / "sources" / "change-256-state-ownership-diagnostics-cleanup" / "reconstructible" / "r",
        root / "projects" / "kis-mcp" / "sources" / "change-256-state-ownership-diagnostics-cleanup" / "evidence" / "e",
        root / "runtime" / "run-1" / "state" / "rt",
        root / "runtime" / "run-1" / "projects" / "kis-mcp" / "sources" / "change-256-state-ownership-diagnostics-cleanup" / "ephemeral" / "tmp",
        root / "quarantine",
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    classes = {entry.ownership_class for entry in service.inventory(limit=50).entries}
    assert classes == {
        "global-authority", "global-cache", "shared-auth", "project-specific",
        "worktree-specific", "reconstructible-cache", "durable-evidence",
        "runtime-instance-specific", "ephemeral", "recovery-quarantine",
    }
    runtime = next(entry for entry in service.inventory(limit=50).entries if entry.ownership_class == "runtime-instance-specific")
    assert runtime.stale is None
    assert runtime.stale_reason == "runtime_liveness_not_inferred_from_storage"
    assert runtime.safe_to_cleanup is False


def test_cleanup_rejects_authoritative_and_global_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    targets = [
        service.state_root / "projects" / "retired" / "state" / "authority",
        service.state_root / "global" / "authority" / "policy",
        service.state_root / "global" / "auth" / "github-oauth",
    ]
    for target in targets:
        target.mkdir(parents=True)
        with pytest.raises(ValueError, match="not eligible"):
            service.cleanup(str(target.relative_to(service.state_root)), apply=True)
        assert target.exists()


def test_cleanup_idempotency_state_is_not_owned_by_quarantine_namespace(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.idempotency.root == (
        service.state_root / "global" / "authority" / "state-cleanup-idempotency"
    )
    assert service.quarantine_root not in service.idempotency.root.parents


def test_cleanup_refuses_unregistered_project_cache_as_unsafe(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = (
        service.state_root / "projects" / "retired" / "sources" / "change-200-old"
        / "reconstructible" / "cache"
    )
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    entry = service.inventory().entries[0]
    assert entry.stale is True
    assert entry.stale_reason == "project_not_registered"
    assert entry.safe_to_cleanup is False
    with pytest.raises(ValueError, match="not eligible"):
        service.cleanup(relative, apply=False)
    with pytest.raises(ValueError, match="not eligible"):
        service.cleanup(relative, apply=True, idempotency_key="unregistered", preview_token="invalid")
    assert candidate.exists()
    assert service.quarantine.list_records() == []
    assert not service.idempotency.binding_path("unregistered").exists()


def test_cleanup_holds_project_admission_guard_through_quarantine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-777-old" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    observed: list[bool] = []
    preview = service.cleanup(relative, apply=False)
    original = service.quarantine.quarantine

    def guarded_quarantine(path: str, **kwargs: object):
        observed.append(service.admission_guard.is_held("kis-mcp"))
        return original(path, **kwargs)

    monkeypatch.setattr(service.quarantine, "quarantine", guarded_quarantine)
    service.cleanup(relative, apply=True, idempotency_key="guarded", preview_token=str(preview["preview_token"]))
    assert observed == [True]


def test_cleanup_absent_path_requires_durable_cleanup_binding(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-106-foreign" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    service.quarantine.quarantine(str(candidate))

    with pytest.raises(ValueError, match="not eligible"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-foreign")


def test_cleanup_replay_rejects_different_active_quarantine_operation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-107-replay" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)
    applied = service.cleanup(relative, apply=True, idempotency_key="cleanup-replay", preview_token=str(preview["preview_token"]))
    service.quarantine.restore(str(applied["quarantine_operation_id"]))
    second = service.quarantine.quarantine(str(candidate))
    assert second.operation_id != applied["quarantine_operation_id"]

    with pytest.raises(ValueError, match="replay conflicts"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-replay")


def test_cleanup_replay_recovers_after_quarantine_commit_before_binding_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-108-interrupt" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)
    original_complete = service.idempotency.complete

    def interrupt_complete(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt("simulated binding completion interruption")

    monkeypatch.setattr(service.idempotency, "complete", interrupt_complete)
    with pytest.raises(KeyboardInterrupt, match="binding completion interruption"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-interrupt", preview_token=str(preview["preview_token"]))
    assert not candidate.exists()

    monkeypatch.setattr(service.idempotency, "complete", original_complete)
    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-interrupt")
    assert replay["action"] == "already_quarantined"
    assert replay["quarantine_operation_id"]


def test_cleanup_retries_same_operation_after_pre_move_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-109-premov" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)
    real_move = __import__("shutil").move

    def interrupt_move(source: str, destination: str) -> str:
        raise KeyboardInterrupt("simulated pre-move interruption")

    monkeypatch.setattr("kis_mcp.quarantine.shutil.move", interrupt_move)
    with pytest.raises(KeyboardInterrupt, match="pre-move interruption"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-premov", preview_token=str(preview["preview_token"]))
    assert candidate.exists()

    monkeypatch.setattr("kis_mcp.quarantine.shutil.move", real_move)
    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-premov", preview_token=str(preview["preview_token"]))
    assert replay["action"] == "quarantined"
    assert not candidate.exists()


def test_idempotency_binding_publish_is_atomic_across_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    store = service.idempotency
    original_replace = store._replace_write_through

    def interrupt_replace(source: Path, destination: Path, *, replace: bool = True) -> None:
        raise KeyboardInterrupt("simulated binding publish interruption")

    monkeypatch.setattr(store, "_replace_write_through", interrupt_replace)
    with pytest.raises(KeyboardInterrupt, match="binding publish interruption"):
        store.reserve("cleanup-atomic", "target", "20260828T210000000000Z-abcdefabcdef")
    assert not store.binding_path("cleanup-atomic").exists()

    monkeypatch.setattr(store, "_replace_write_through", original_replace)
    created, binding = store.reserve("cleanup-atomic", "target", "20260828T210000000000Z-abcdefabcdef")
    assert created is True
    assert binding["quarantine_operation_id"] == "20260828T210000000000Z-abcdefabcdef"


def test_cleanup_replay_uses_exact_operation_lookup_not_history_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-110-exact" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)
    original_complete = service.idempotency.complete

    monkeypatch.setattr(service.idempotency, "complete", lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-exact", preview_token=str(preview["preview_token"]))
    monkeypatch.setattr(service.idempotency, "complete", original_complete)
    monkeypatch.setattr(
        service.quarantine,
        "find_active_record_by_original_path",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("history scan must not be used")),
    )

    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-exact")
    assert replay["action"] == "already_quarantined"


def test_failed_cleanup_releases_new_binding_despite_older_active_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-111-old-active" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    (candidate / "payload.txt").write_text("old", encoding="utf-8")

    def occupy_source_and_fail() -> None:
        candidate.mkdir(parents=True, exist_ok=True)
        (candidate / "replacement.txt").write_text("new", encoding="utf-8")
        raise RuntimeError("preserve older active quarantine")

    with pytest.raises(QuarantineError, match="payload preserved"):
        service.quarantine.quarantine(str(candidate), post_move_validator=occupy_source_and_fail)
    assert candidate.exists()
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)

    monkeypatch.setattr(service.quarantine, "quarantine", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("new cleanup failure")))
    with pytest.raises(RuntimeError, match="new cleanup failure"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-new-failure", preview_token=str(preview["preview_token"]))
    assert not service.idempotency.binding_path("cleanup-new-failure").exists()


def test_cleanup_replay_recovers_interrupted_payload_when_original_is_recreated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-112-recreated" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    (candidate / "payload.txt").write_text("old", encoding="utf-8")
    relative = str(candidate.relative_to(service.state_root))
    preview = service.cleanup(relative, apply=False)
    original_write = service.quarantine._write_metadata

    monkeypatch.setattr(
        service.quarantine,
        "_write_metadata",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt("metadata interruption")),
    )
    with pytest.raises(KeyboardInterrupt, match="metadata interruption"):
        service.cleanup(relative, apply=True, idempotency_key="cleanup-recreated", preview_token=str(preview["preview_token"]))
    assert not candidate.exists()

    candidate.mkdir(parents=True)
    (candidate / "replacement.txt").write_text("new", encoding="utf-8")
    monkeypatch.setattr(service.quarantine, "_write_metadata", original_write)
    replay = service.cleanup(relative, apply=True, idempotency_key="cleanup-recreated")
    assert replay["action"] == "already_quarantined"
    assert candidate.exists()

    repeated = service.cleanup(relative, apply=True, idempotency_key="cleanup-recreated")
    assert repeated == replay


def test_cleanup_rejects_forged_and_cross_target_preview_tokens(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.state_root / "projects" / "kis-mcp" / "sources" / "change-120-first" / "reconstructible" / "cache"
    second = service.state_root / "projects" / "kis-mcp" / "sources" / "change-121-second" / "reconstructible" / "cache"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    first_relative = str(first.relative_to(service.state_root))
    second_relative = str(second.relative_to(service.state_root))
    token = str(service.cleanup(first_relative, apply=False)["preview_token"])

    with pytest.raises(ValueError, match="preview_token"):
        service.cleanup(first_relative, apply=True, idempotency_key="forged", preview_token=token + "x")
    with pytest.raises(ValueError, match="does not match"):
        service.cleanup(second_relative, apply=True, idempotency_key="cross-target", preview_token=token)

    assert first.exists() and second.exists()
    assert service.quarantine.list_records() == []
    assert not service.idempotency.binding_path("forged").exists()
    assert not service.idempotency.binding_path("cross-target").exists()


def test_project_admission_guard_serializes_competing_instances(tmp_path: Path) -> None:
    service = _service(tmp_path)
    guard_type = type(service.admission_guard)
    contender = guard_type(
        state_root=service.state_root,
        project_roots={"kis-mcp": service.project_boundary / "kis-mcp"},
    )
    attempted = threading.Event()
    acquired = threading.Event()

    def compete() -> None:
        attempted.set()
        with contender.hold("kis-mcp"):
            acquired.set()

    with service.admission_guard.hold("kis-mcp"):
        worker = threading.Thread(target=compete)
        worker.start()
        assert attempted.wait(1)
        assert not acquired.wait(0.05)
    assert acquired.wait(1)
    worker.join(timeout=1)
    assert not worker.is_alive()


def test_idempotency_reservation_recovers_after_flush_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _service(tmp_path).idempotency
    real_fsync = os.fsync
    monkeypatch.setattr(
        "kis_mcp.state.cleanup_coordination.os.fsync",
        lambda fd: (_ for _ in ()).throw(KeyboardInterrupt("flush interruption")),
    )
    with pytest.raises(KeyboardInterrupt, match="flush interruption"):
        store.reserve("cleanup-flush", "target", "20260828T210000000000Z-111111111111")
    assert not store.binding_path("cleanup-flush").exists()

    monkeypatch.setattr("kis_mcp.state.cleanup_coordination.os.fsync", real_fsync)
    created, binding = store.reserve(
        "cleanup-flush", "target", "20260828T210000000000Z-111111111111"
    )
    assert created is True
    assert store.read("cleanup-flush") == binding


def test_idempotency_completion_remains_readable_after_post_replace_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _service(tmp_path).idempotency
    operation_id = "20260828T210000000000Z-222222222222"
    store.reserve("cleanup-complete", "target", operation_id)
    real_replace = store._replace_write_through

    def replace_then_interrupt(source: Path, destination: Path, *, replace: bool = True) -> None:
        real_replace(source, destination, replace=replace)
        raise KeyboardInterrupt("post-replace interruption")

    monkeypatch.setattr(store, "_replace_write_through", replace_then_interrupt)
    result = {"quarantine_operation_id": operation_id, "action": "quarantined"}
    with pytest.raises(KeyboardInterrupt, match="post-replace interruption"):
        store.complete("cleanup-complete", "target", result)

    persisted = store.read("cleanup-complete")
    assert persisted["quarantine_operation_id"] == operation_id
    assert persisted["result"] == result


def test_cleanup_rejects_preview_token_after_path_identity_changes(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.state_root / "projects" / "kis-mcp" / "sources" / "change-122-identity" / "reconstructible" / "cache"
    candidate.mkdir(parents=True)
    relative = str(candidate.relative_to(service.state_root))
    token = str(service.cleanup(relative, apply=False)["preview_token"])
    replaced = candidate.with_name("cache-old")
    candidate.rename(replaced)
    candidate.mkdir()

    with pytest.raises(ValueError, match="does not match"):
        service.cleanup(relative, apply=True, idempotency_key="identity-change", preview_token=token)

    assert candidate.exists() and replaced.exists()
    assert service.quarantine.list_records() == []
    assert not service.idempotency.binding_path("identity-change").exists()


def test_project_admission_lock_is_cross_process_and_recovers_after_holder_exit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    project_root = service.project_boundary / "kis-mcp"
    script = (
        "import sys,time; from pathlib import Path; "
        "from kis_mcp.state.cleanup_coordination import StateCleanupAdmissionGuard as G; "
        "g=G(state_root=Path(sys.argv[1]),project_roots={'kis-mcp':Path(sys.argv[2])}); "
        "ctx=g.hold('kis-mcp'); ctx.__enter__(); print('held',flush=True); time.sleep(30)"
    )
    holder = subprocess.Popen(
        [sys.executable, "-c", script, str(service.state_root), str(project_root)],
        stdout=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert holder.stdout is not None and holder.stdout.readline().strip() == "held"
    acquired = threading.Event()

    def contend() -> None:
        with service.admission_guard.hold("kis-mcp"):
            acquired.set()

    worker = threading.Thread(target=contend)
    worker.start()
    assert not acquired.wait(0.05)
    holder.terminate()
    holder.wait(timeout=5)
    assert acquired.wait(1)
    worker.join(timeout=1)
    assert not worker.is_alive()


def test_idempotency_reservation_survives_post_publish_interruption_and_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    store = service.idempotency
    operation_id = "20260828T210000000000Z-333333333333"
    real_replace = store._replace_write_through

    def replace_then_interrupt(source: Path, destination: Path, *, replace: bool = True) -> None:
        real_replace(source, destination, replace=replace)
        raise KeyboardInterrupt("reservation published")

    monkeypatch.setattr(store, "_replace_write_through", replace_then_interrupt)
    with pytest.raises(KeyboardInterrupt, match="reservation published"):
        store.reserve("cleanup-published", "target", operation_id)

    restarted = type(store)(state_root=service.state_root)
    persisted = restarted.read("cleanup-published")
    assert persisted["quarantine_operation_id"] == operation_id
    assert persisted["result"] is None
    created, replay = restarted.reserve("cleanup-published", "target", operation_id)
    assert created is False
    assert replay == persisted
