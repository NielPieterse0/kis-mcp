from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver


RESOLVER = DesktopCommanderEffectResolver(
    project_boundary=r"C:\Projects",
    provider_state_file=r"C:\Projects\.kis-mcp\desktop-commander.json",
)


def _write_repository_config(repository: Path, content: str) -> None:
    git_dir = repository / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "config").write_text(content, encoding="utf-8")


def test_git_global_c_option_selects_effective_write_and_delete_repository() -> None:
    write = RESOLVER.resolve(
        "start_process",
        {"command": r"git -C C:\Windows\Temp add .", "cwd": r"C:\Projects\kis-mcp"},
    )
    clean = RESOLVER.resolve(
        "start_process",
        {"command": r"git -C C:\Windows\Temp clean -fd", "cwd": r"C:\Projects\kis-mcp"},
    )

    assert r"C:\Windows\Temp" in write.write_paths
    assert clean.unresolved_delete is True


def test_git_global_metadata_options_report_actual_mutation_paths() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": (
                r"git --git-dir=C:\Windows\Temp\repo.git "
                r"--work-tree=C:\Windows\Temp\work reset --hard"
            ),
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert r"C:\Windows\Temp\repo.git" in effects.write_paths
    assert r"C:\Windows\Temp\work" in effects.write_paths


def test_repeated_git_c_options_are_resolved_sequentially() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"git -C C:\Windows -C Temp add .",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert r"C:\Windows\Temp" in effects.write_paths


@pytest.mark.parametrize(
    "command",
    [
        r'cmd /c "echo safe & del C:\Projects\kis-mcp\important.txt"',
        r'cmd /c "(del C:\Projects\kis-mcp\important.txt)"',
    ],
)
def test_cmd_single_ampersand_and_grouping_reveal_hidden_delete(command: str) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.delete_paths == (r"C:\Projects\kis-mcp\important.txt",)


@pytest.mark.parametrize(
    "command",
    [
        r'pwsh -Command "& Remove-Item C:\Projects\kis-mcp\important.txt"',
        r'pwsh -Command "& { Remove-Item C:\Projects\kis-mcp\important.txt }"',
    ],
)
def test_powershell_invocation_operator_and_script_block_reveal_delete(
    command: str,
) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.delete_paths == (r"C:\Projects\kis-mcp\important.txt",)


def test_escaped_shell_separators_remain_literal() -> None:
    cmd = RESOLVER.resolve(
        "start_process",
        {
            "command": r'cmd /c "echo safe ^& del C:\Projects\kis-mcp\important.txt"',
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    powershell = RESOLVER.resolve(
        "start_process",
        {
            "command": r'pwsh -Command "Write-Output safe `; Remove-Item C:\Projects\kis-mcp\important.txt"',
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert cmd.delete_paths == ()
    assert powershell.delete_paths == ()


def test_directory_change_updates_later_relative_write_path() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"cd C:\Windows\Temp && echo data > output.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert effects.write_paths == (r"C:\Windows\Temp\output.txt",)


def test_push_uses_pushurl_instead_of_fetch_url(tmp_path: Path) -> None:
    local_mirror = tmp_path / "mirror"
    local_mirror.mkdir()
    _write_repository_config(
        tmp_path,
        (
            '[remote "origin"]\n'
            f"    url = {local_mirror}\n"
            "    pushurl = https://example.com/external.git\n"
            '[branch "main"]\n'
            "    remote = origin\n"
        ),
    )

    effects = RESOLVER.resolve(
        "start_process",
        {"command": "git push origin main", "cwd": str(tmp_path)},
    )

    assert effects.external_network is True


def test_push_repo_option_is_the_effective_target(tmp_path: Path) -> None:
    _write_repository_config(
        tmp_path,
        '[remote "origin"]\n    url = C:\\Projects\\local-mirror\n',
    )

    for command in (
        "git push --repo=https://example.com/external.git main",
        "git push --repo https://example.com/external.git main",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": str(tmp_path)},
        )
        assert effects.external_network is True


def test_push_remote_configuration_from_local_include_is_loaded(tmp_path: Path) -> None:
    included = tmp_path / "included.gitconfig"
    included.write_text(
        '[remote "origin"]\n    pushurl = https://example.com/external.git\n',
        encoding="utf-8",
    )
    _write_repository_config(
        tmp_path,
        (
            '[include]\n'
            f"    path = {included}\n"
            '[remote "origin"]\n'
            "    url = C:\\Projects\\local-mirror\n"
            '[branch "main"]\n'
            "    remote = origin\n"
        ),
    )

    effects = RESOLVER.resolve(
        "start_process",
        {"command": "git push", "cwd": str(tmp_path)},
    )

    assert effects.external_network is True
