from __future__ import annotations

from subprocess import CompletedProcess
from typing import Any

from kis_mcp.providers.github.auth import resolve_github_shared_auth
from kis_mcp.providers.github.settings import GitHubProviderSettings


TOKEN = "gho_test-token-never-log"
CONFIG_DIR = r"C:\Projects\.mcp-external-state\gh-config"


def _settings() -> GitHubProviderSettings:
    return GitHubProviderSettings(
        schema_version=3,
        provider_id="github-mcp",
        authoritative_source="https://github.com/github/github-mcp-server",
        release_tag="v1.8.0",
        source_revision="ca8ab52dcc45b86fae190398178fd22edb7b1362",
        transport="stdio",
        executable=r"C:\Projects\.kis-mcp\github-mcp\github-mcp-server.exe",
        auth_mode="oauth",
        pat_env="GITHUB_PERSONAL_ACCESS_TOKEN",
        toolsets=("all",),
    )


def test_reuses_valid_github_cli_keyring_auth_without_exposing_token() -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def runner(command: list[str], **kwargs: Any) -> CompletedProcess[str]:
        calls.append((command, kwargs["env"]))
        if command[1:3] == ["auth", "status"]:
            return CompletedProcess(command, 0, stdout="", stderr="")
        return CompletedProcess(command, 0, stdout=TOKEN + "\n", stderr="")

    resolved = resolve_github_shared_auth(
        _settings(),
        github_cli_config_dir=CONFIG_DIR,
        environ={"PATH": "bin", "SYSTEMROOT": r"C:\Windows"},
        runner=runner,
    )

    assert resolved.decision.source == "github_cli_keyring"
    assert resolved.decision.state == "shared_auth_reused"
    assert resolved.decision.reason == "github_cli_active_auth_valid"
    assert resolved.child_environment == {
        "PATH": "bin",
        "SYSTEMROOT": r"C:\Windows",
        "GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN,
    }
    assert [call[0] for call in calls] == [
        ["gh", "auth", "status", "--active", "--hostname", "github.com"],
        ["gh", "auth", "token", "--hostname", "github.com"],
    ]
    assert all(call[1]["GH_CONFIG_DIR"] == CONFIG_DIR for call in calls)
    assert all(call[1]["GH_PROMPT_DISABLED"] == "1" for call in calls)
    assert TOKEN not in repr(resolved)
    assert TOKEN not in repr(resolved.decision)


def test_missing_or_invalid_cli_auth_falls_back_to_interactive_oauth() -> None:
    def runner(command: list[str], **_: Any) -> CompletedProcess[str]:
        return CompletedProcess(command, 1, stdout="", stderr="not authenticated")

    resolved = resolve_github_shared_auth(
        _settings(),
        github_cli_config_dir=CONFIG_DIR,
        environ={"PATH": "bin"},
        runner=runner,
    )

    assert resolved.decision.source == "interactive_oauth"
    assert resolved.decision.state == "interactive_auth_required"
    assert resolved.decision.reason == "github_cli_auth_invalid_or_missing"
    assert resolved.child_environment == {"PATH": "bin"}


def test_token_lookup_failure_falls_back_without_forwarding_partial_state() -> None:
    def runner(command: list[str], **_: Any) -> CompletedProcess[str]:
        if command[1:3] == ["auth", "status"]:
            return CompletedProcess(command, 0, stdout="", stderr="")
        return CompletedProcess(command, 1, stdout="", stderr="token unavailable")

    resolved = resolve_github_shared_auth(
        _settings(),
        github_cli_config_dir=CONFIG_DIR,
        environ={"PATH": "bin"},
        runner=runner,
    )

    assert resolved.decision.state == "interactive_auth_required"
    assert resolved.decision.reason == "github_cli_token_unavailable"
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" not in resolved.child_environment


def test_ambient_pat_remains_a_conflict_and_is_never_reused() -> None:
    called = False

    def runner(*_: Any, **__: Any) -> CompletedProcess[str]:
        nonlocal called
        called = True
        raise AssertionError("gh must not run while ambient PAT conflict exists")

    resolved = resolve_github_shared_auth(
        _settings(),
        github_cli_config_dir=CONFIG_DIR,
        environ={"PATH": "bin", "GITHUB_PERSONAL_ACCESS_TOKEN": TOKEN},
        runner=runner,
    )

    assert called is False
    assert resolved.decision.source == "ambient_environment"
    assert resolved.decision.state == "configuration_conflict"
    assert resolved.decision.reason == "ambient_pat_override_present"
    assert resolved.child_environment == {"PATH": "bin"}
    assert TOKEN not in repr(resolved)
