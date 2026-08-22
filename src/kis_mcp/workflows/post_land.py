"""Runtime composition for KIS post-land behavior."""

from __future__ import annotations

from pathlib import Path

from ..config import RuntimeConfig
from ..projects.post_land import PostLandDispatcher, PostLandFailureRecorder, PostLandHooks
from ..post_land_restart import (
    dispatch_kis_dev_post_land_restart,
    record_kis_dev_post_land_restart_exception,
)


def build_kis_post_land_dispatcher(runtime: RuntimeConfig) -> PostLandDispatcher:
    """Bind validated runtime state ownership to the KIS restart dispatcher."""
    state_root = Path(runtime.state_root)

    def dispatch(
        project_id: str,
        local_root: Path,
        target_branch: str,
        landed_sha: str | None,
    ) -> None:
        dispatch_kis_dev_post_land_restart(
            project_id,
            local_root,
            target_branch,
            landed_sha,
            state_root=state_root,
        )

    return dispatch


def build_kis_post_land_failure_recorder(
    runtime: RuntimeConfig,
) -> PostLandFailureRecorder:
    state_root = Path(runtime.state_root)

    def record(
        project_id: str,
        local_root: Path,
        target_branch: str,
        landed_sha: str | None,
        exc: BaseException,
    ) -> None:
        record_kis_dev_post_land_restart_exception(
            project_id,
            local_root,
            target_branch,
            landed_sha,
            exc,
            state_root=state_root,
        )

    return record


def build_kis_post_land_hooks(runtime: RuntimeConfig) -> PostLandHooks:
    return PostLandHooks(
        dispatcher=build_kis_post_land_dispatcher(runtime),
        failure_recorder=build_kis_post_land_failure_recorder(runtime),
    )


__all__ = [
    "build_kis_post_land_dispatcher",
    "build_kis_post_land_failure_recorder",
    "build_kis_post_land_hooks",
]
