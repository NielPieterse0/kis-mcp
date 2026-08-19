from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kis_mcp.config import load_runtime_config

from .settings import GitHubProviderSettings


_BASIC_ENVIRONMENT_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
_GITHUB_HOST = "github.com"


@dataclass(frozen=True, slots=True)
class GitHubAuthDecision:
    source: str
    state: str
    reason: str

    @property
    def shared_auth_reused(self) -> bool:
        return self.state == "shared_auth_reused"


@dataclass(frozen=True, slots=True)
class GitHubResolvedAuth:
    decision: GitHubAuthDecision
    child_environment: Mapping[str, str] = field(repr=False)


CommandRunner = Callable[..., Any]


def _base_environment(
    environ: Mapping[str, str] | None,
    *,
    github_cli_config_dir: str,
) -> dict[str, str]:
    source = os.environ if environ is None else environ
    environment = {
        key: str(source[key])
        for key in _BASIC_ENVIRONMENT_KEYS
        if str(source.get(key, "")).strip()
    }
    environment["GH_CONFIG_DIR"] = github_cli_config_dir
    environment["GH_PROMPT_DISABLED"] = "1"
    return environment


def _run_gh(
    arguments: Sequence[str],
    *,
    environment: Mapping[str, str],
    runner: CommandRunner,
) -> Any:
    return runner(
        ["gh", *arguments],
        env=dict(environment),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def resolve_github_shared_auth(
    settings: GitHubProviderSettings,
    *,
    repository_root: Path | None = None,
    github_cli_config_dir: str | None = None,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = subprocess.run,
) -> GitHubResolvedAuth:
    """Resolve reusable GitHub CLI OAuth without persisting or reporting the token."""

    source = os.environ if environ is None else environ
    ambient_pat = str(source.get(settings.pat_env, "")).strip()
    config_dir = github_cli_config_dir
    if config_dir is None:
        config_dir = load_runtime_config(repository_root).github_cli_config_dir
    cli_environment = _base_environment(source, github_cli_config_dir=config_dir)
    child_environment = {
        key: value
        for key, value in cli_environment.items()
        if key not in {"GH_CONFIG_DIR", "GH_PROMPT_DISABLED"}
    }

    if ambient_pat:
        return GitHubResolvedAuth(
            decision=GitHubAuthDecision(
                source="ambient_environment",
                state="configuration_conflict",
                reason="ambient_pat_override_present",
            ),
            child_environment=child_environment,
        )

    try:
        status = _run_gh(
            ("auth", "status", "--active", "--hostname", _GITHUB_HOST),
            environment=cli_environment,
            runner=runner,
        )
    except (OSError, subprocess.SubprocessError):
        return GitHubResolvedAuth(
            decision=GitHubAuthDecision(
                source="interactive_oauth",
                state="interactive_auth_required",
                reason="github_cli_unavailable",
            ),
            child_environment=child_environment,
        )
    if int(getattr(status, "returncode", 1)) != 0:
        return GitHubResolvedAuth(
            decision=GitHubAuthDecision(
                source="interactive_oauth",
                state="interactive_auth_required",
                reason="github_cli_auth_invalid_or_missing",
            ),
            child_environment=child_environment,
        )

    try:
        token_result = _run_gh(
            ("auth", "token", "--hostname", _GITHUB_HOST),
            environment=cli_environment,
            runner=runner,
        )
    except (OSError, subprocess.SubprocessError):
        return GitHubResolvedAuth(
            decision=GitHubAuthDecision(
                source="interactive_oauth",
                state="interactive_auth_required",
                reason="github_cli_token_unavailable",
            ),
            child_environment=child_environment,
        )
    token = str(getattr(token_result, "stdout", "")).strip()
    if int(getattr(token_result, "returncode", 1)) != 0 or not token:
        return GitHubResolvedAuth(
            decision=GitHubAuthDecision(
                source="interactive_oauth",
                state="interactive_auth_required",
                reason="github_cli_token_unavailable",
            ),
            child_environment=child_environment,
        )

    child_environment[settings.pat_env] = token
    token = ""
    return GitHubResolvedAuth(
        decision=GitHubAuthDecision(
            source="github_cli_keyring",
            state="shared_auth_reused",
            reason="github_cli_active_auth_valid",
        ),
        child_environment=child_environment,
    )


__all__ = [
    "GitHubAuthDecision",
    "GitHubResolvedAuth",
    "resolve_github_shared_auth",
]
