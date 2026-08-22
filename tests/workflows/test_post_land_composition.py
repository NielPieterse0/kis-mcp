from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from kis_mcp.workflows import post_land as post_land_module
from kis_mcp.workflows import registered_github as registered_github_module

SHA = "a" * 40


def test_post_land_builder_injects_validated_state_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        post_land_module,
        "dispatch_kis_dev_post_land_restart",
        lambda *args, **kwargs: calls.append((*args, kwargs)),
    )
    runtime = SimpleNamespace(state_root=str(tmp_path / "state"))

    dispatcher = post_land_module.build_kis_post_land_dispatcher(runtime)
    dispatcher("kis-mcp", tmp_path / "repo", "main", SHA)

    assert calls == [(
        "kis-mcp", tmp_path / "repo", "main", SHA,
        {"state_root": tmp_path / "state"},
    )]


def test_post_land_failure_recorder_injects_validated_state_root(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        post_land_module,
        "record_kis_dev_post_land_restart_exception",
        lambda *args, **kwargs: calls.append((*args, kwargs)),
    )
    runtime = SimpleNamespace(state_root=str(tmp_path / "state"))
    hooks = post_land_module.build_kis_post_land_hooks(runtime)
    error = RuntimeError("boom")

    hooks.failure_recorder("kis-mcp", tmp_path / "repo", "main", SHA, error)

    assert calls == [(
        "kis-mcp", tmp_path / "repo", "main", SHA, error,
        {"state_root": tmp_path / "state"},
    )]


def test_direct_runtime_wrapper_injects_shared_hooks(monkeypatch, tmp_path: Path) -> None:
    hooks = object()
    captured: dict[str, object] = {}
    runtime = SimpleNamespace(
        project_boundary=str(tmp_path),
        github_cli_config_dir=str(tmp_path / "gh"),
    )
    monkeypatch.setattr(registered_github_module, "load_runtime_config", lambda: runtime)
    monkeypatch.setattr(
        registered_github_module, "load_project_registry_settings", lambda **kwargs: object()
    )
    monkeypatch.setattr(
        registered_github_module, "build_kis_post_land_hooks", lambda value: hooks
    )

    def execute(operation, arguments, *, operations):
        captured["operation"] = operation
        captured["arguments"] = dict(arguments)
        captured["operations"] = operations
        return {"state": "ok"}

    monkeypatch.setattr(registered_github_module, "execute_registered_github_operation", execute)
    result = registered_github_module.execute_runtime_registered_github_operation("example", {"x": 1})

    assert result == {"state": "ok"}
    service = captured["operations"]
    assert service.post_land_hooks is hooks
    assert service.gh_config_dir == tmp_path / "gh"



def test_queue_runtime_wrapper_injects_shared_hooks(monkeypatch, tmp_path: Path) -> None:
    import kis_mcp.capabilities  # establishes the repository's supported import order

    merge_queue_module = importlib.import_module("kis_mcp.workflows.merge_queue")
    hooks = object()
    projects = object()
    service = object()
    captured: dict[str, object] = {}
    runtime = SimpleNamespace(
        project_boundary=str(tmp_path),
        github_cli_config_dir=str(tmp_path / "gh"),
    )
    monkeypatch.setattr(merge_queue_module, "load_runtime_config", lambda: runtime)
    monkeypatch.setattr(
        merge_queue_module,
        "load_project_registry_settings",
        lambda **kwargs: projects,
    )
    monkeypatch.setattr(
        merge_queue_module,
        "build_kis_post_land_hooks",
        lambda value: hooks,
    )
    def build_service(projects_arg: object, **kwargs: object) -> object:
        assert projects_arg is projects
        captured["service_kwargs"] = kwargs
        return service

    monkeypatch.setattr(
        merge_queue_module,
        "RegisteredGitHubMergeQueueOperations",
        build_service,
    )

    def execute(operation, arguments, *, operations):
        captured["execute"] = (operation, dict(arguments), operations)
        return {"state": "ok"}

    monkeypatch.setattr(
        merge_queue_module,
        "execute_registered_github_merge_queue_operation",
        execute,
    )
    result = merge_queue_module.execute_governed_github_merge_queue_operation(
        "example", {"project_id": "kis-mcp"}
    )
    assert result == {"state": "ok"}
    assert captured["execute"] == (
        "example",
        {"project_id": "kis-mcp"},
        service,
    )
    kwargs = captured["service_kwargs"]
    assert kwargs["post_land_hooks"] is hooks
    assert kwargs["governance_validator"] is merge_queue_module._governance_receipt
    assert kwargs["gh_config_dir"] == tmp_path / "gh"
