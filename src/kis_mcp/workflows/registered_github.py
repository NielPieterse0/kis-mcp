"""Runtime composition for registered GitHub operations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..config import load_runtime_config
from ..projects.github_exact import RegisteredGitHubOperations, execute_registered_github_operation
from ..projects.settings import load_project_registry_settings
from .post_land import build_kis_post_land_hooks


def execute_runtime_registered_github_operation(
    operation: str,
    arguments: Mapping[str, Any],
) -> dict[str, object]:
    runtime = load_runtime_config()
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    service = RegisteredGitHubOperations(
        projects,
        gh_config_dir=Path(runtime.github_cli_config_dir),
        post_land_hooks=build_kis_post_land_hooks(runtime),
    )
    return execute_registered_github_operation(
        operation,
        arguments,
        operations=service,
    )


__all__ = ["execute_runtime_registered_github_operation"]
