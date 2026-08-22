"""Provider-neutral post-land dispatch contract."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

PostLandDispatcher = Callable[[str, Path, str, str | None], None]
PostLandFailureRecorder = Callable[
    [str, Path, str, str | None, BaseException], None
]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostLandHooks:
    dispatcher: PostLandDispatcher
    failure_recorder: PostLandFailureRecorder


def dispatch_post_land_non_interfering(
    hooks: PostLandHooks | None,
    project_id: str,
    local_root: Path,
    target_branch: str,
    landed_sha: str | None,
) -> None:
    """Invoke post-land work without replacing authoritative landing truth."""
    if hooks is None:
        return
    try:
        hooks.dispatcher(project_id, local_root, target_branch, landed_sha)
    except Exception as exc:
        try:
            hooks.failure_recorder(project_id, local_root, target_branch, landed_sha, exc)
        except Exception:
            _LOGGER.exception("post-land failure recorder failed after authoritative landing")


__all__ = [
    "PostLandDispatcher",
    "PostLandFailureRecorder",
    "PostLandHooks",
    "dispatch_post_land_non_interfering",
]
