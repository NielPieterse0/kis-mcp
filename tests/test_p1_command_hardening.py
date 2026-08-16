from __future__ import annotations

from pathlib import Path

import pytest

from kis_mcp.command_intent import resolve_command_effects_with_state
from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.shell_parser import ShellState


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


@pytest.mark.parametrize(
    ("command", "field", "expected"),
    [
        (
            r'cmd /c "echo data > %USERPROFILE%\Desktop\out.txt"',
            "unresolved_write_paths",
            r"%USERPROFILE%\Desktop\out.txt",
        ),
        (
            r'cmd /c "echo data > %USERPROFILE:~0,3%\prefix.txt"',
            "unresolved_write_paths",
            r"%USERPROFILE:~0,3%\prefix.txt",
        ),
        (
            r'cmd /c "echo data > %ProgramFiles(x86)%\out.txt"',
            "unresolved_write_paths",
            r"%ProgramFiles(x86)%\out.txt",
        ),
        (
            r'cmd /V:ON /c "echo data > !USERPROFILE!\delayed.txt"',
            "unresolved_write_paths",
            r"!USERPROFILE!\delayed.txt",
        ),
        (
            r'cmd /V:ON /c "echo data > !ProgramFiles(x86)!\delayed.txt"',
            "unresolved_write_paths",
            r"!ProgramFiles(x86)!\delayed.txt",
        ),
        (
            r'cmd /V:ON /c "echo data > !FOO-BAR!\delayed.txt"',
            "unresolved_write_paths",
            r"!FOO-BAR!\delayed.txt",
        ),
        (
            r'pwsh -Command "Set-Content -Path $env:USERPROFILE\out.txt -Value data"',
            "unresolved_write_paths",
            r"$env:USERPROFILE\out.txt",
        ),
        (
            r'pwsh -Command "Set-Content -Path $ENV:USERPROFILE\mixed.txt -Value data"',
            "unresolved_write_paths",
            r"$ENV:USERPROFILE\mixed.txt",
        ),
        (
            r'pwsh -Command "Set-Content -Path $HOME\profile.txt -Value data"',
            "unresolved_write_paths",
            r"$HOME\profile.txt",
        ),
        (
            r'pwsh -Command "Remove-Item ${env:USERPROFILE}\old.txt"',
            "unresolved_delete_paths",
            r"${env:USERPROFILE}\old.txt",
        ),
        (
            r'cmd /c "move C:\Projects\kis-mcp\a.txt %USERPROFILE%\Desktop\b.txt"',
            "unresolved_entry_paths",
            r"%USERPROFILE%\Desktop\b.txt",
        ),
    ],
)
def test_shell_expanded_mutation_targets_are_preserved_as_unresolved_evidence(
    command: str,
    field: str,
    expected: str,
) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert expected in getattr(effects, field)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            r'cmd /c "echo data > C:\Projects\kis-mcp\100%.txt"',
            r"C:\Projects\kis-mcp\100%.txt",
        ),
        (
            r'cmd /V:OFF /c "echo data > C:\Projects\kis-mcp\!literal!.txt"',
            r"C:\Projects\kis-mcp\!literal!.txt",
        ),
    ],
)
def test_literal_cmd_markers_remain_resolvable(command: str, expected: str) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert effects.write_paths == (expected,)
    assert effects.unresolved_write_paths == ()


def test_nested_cmd_v_off_overrides_inherited_delayed_expansion() -> None:
    effects, _state = resolve_command_effects_with_state(
        r'cmd /V:OFF /c "echo data > C:\Projects\kis-mcp\!literal!.txt"',
        state=ShellState(
            cwd=r"C:\Projects\kis-mcp",
            shell="cmd",
            cmd_delayed_expansion=True,
        ),
        project_boundary=r"C:\Projects",
    )

    assert effects.write_paths == (r"C:\Projects\kis-mcp\!literal!.txt",)
    assert effects.unresolved_write_paths == ()


@pytest.mark.parametrize(
    ("command", "is_unresolved"),
    [
        (
            r'cmd /V:ON /V:OFF /c "echo data > C:\Projects\kis-mcp\!literal!.txt"',
            False,
        ),
        (
            r'cmd /V:OFF /V:ON /c "echo data > !USERPROFILE!\delayed.txt"',
            True,
        ),
    ],
)
def test_cmd_delayed_expansion_uses_last_switch(command: str, is_unresolved: bool) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert bool(effects.unresolved_write_paths) is is_unresolved


@pytest.mark.parametrize(
    ("command", "is_unresolved"),
    [
        (
            r'cmd /V:ON /c "echo /V:OFF > !USERPROFILE!\payload.txt"',
            True,
        ),
        (
            r'cmd /V:OFF /c "echo /V:ON > C:\Projects\kis-mcp\!literal!.txt"',
            False,
        ),
    ],
)
def test_cmd_payload_v_switch_text_does_not_change_wrapper_state(
    command: str,
    is_unresolved: bool,
) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert bool(effects.unresolved_write_paths) is is_unresolved


def test_nested_cmd_v_off_ignores_payload_v_on_text() -> None:
    effects, _state = resolve_command_effects_with_state(
        r'cmd /V:OFF /c "echo /V:ON > C:\Projects\kis-mcp\!literal!.txt"',
        state=ShellState(
            cwd=r"C:\Projects\kis-mcp",
            shell="cmd",
            cmd_delayed_expansion=True,
        ),
        project_boundary=r"C:\Projects",
    )

    assert effects.write_paths == (r"C:\Projects\kis-mcp\!literal!.txt",)
    assert effects.unresolved_write_paths == ()


@pytest.mark.parametrize("literal", [r"${literal}.txt", r"$(literal).txt"])
def test_single_quoted_powershell_markers_remain_literal_paths(literal: str) -> None:
    command = (
        'pwsh -Command "Set-Content -LiteralPath '
        f"'C:\\Projects\\kis-mcp\\{literal}' -Value data\""
    )
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert effects.write_paths == (rf"C:\Projects\kis-mcp\{literal}",)
    assert effects.unresolved_write_paths == ()


@pytest.mark.parametrize(
    "target",
    [
        "''" + "$env:USERPROFILE" + r"'\out.txt'",
        "'prefix'" + "$env:USERPROFILE" + "'suffix'",
    ],
)
def test_powershell_mixed_quote_write_target_is_unresolved(target: str) -> None:
    command = 'pwsh -Command "Set-Content -Path ' + target + ' -Value data"'
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert effects.unresolved_write_paths


@pytest.mark.parametrize(
    "target",
    [
        "''" + "$env:USERPROFILE" + r"'\out.txt'",
        "'prefix'" + "$env:USERPROFILE" + "'suffix'",
    ],
)
def test_powershell_mixed_quote_redirection_target_is_unresolved(target: str) -> None:
    command = 'pwsh -Command "echo data > ' + target + '"'
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert effects.unresolved_write_paths


def test_single_quoted_powershell_redirection_marker_remains_literal_path() -> None:
    command = r'''pwsh -Command "echo data > 'C:\\Projects\\kis-mcp\\$HOME.txt'"'''
    effects = RESOLVER.resolve(
        "start_process",
        {"command": command, "cwd": r"C:\Projects\kis-mcp"},
    )

    assert effects.write_paths == (r"C:\Projects\kis-mcp\$HOME.txt",)
    assert effects.unresolved_write_paths == ()


def test_powershell_subexpression_create_target_is_preserved_as_unresolved_evidence() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r'pwsh -Command "New-Item $(Join-Path $env:USERPROFILE out.txt)"',
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert effects.unresolved_write_paths
    assert any(value.startswith("$(") for value in effects.unresolved_write_paths)


def test_unknown_command_with_environment_syntax_does_not_create_mutation_evidence() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"unknown-tool %USERPROFILE% $env:USERPROFILE",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert effects.mutated_paths == ()
    assert effects.unresolved_write_paths == ()
    assert effects.unresolved_entry_paths == ()
    assert effects.unresolved_delete_paths == ()


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
