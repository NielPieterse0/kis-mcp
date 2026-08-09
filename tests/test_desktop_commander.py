from __future__ import annotations

from pathlib import Path

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.runtime_observability import RuntimeObservability


RESOLVER = DesktopCommanderEffectResolver(
    project_boundary=r"C:\Projects",
    provider_state_file=r"C:\Projects\.kis-mcp\.claude-server-commander\config.json",
)


def _write_git_remote(repository: Path, url: str) -> None:
    git_dir = repository / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "config").write_text(
        (
            '[remote "origin"]\n'
            f"    url = {url}\n"
            '[branch "main"]\n'
            "    remote = origin\n"
        ),
        encoding="utf-8",
    )


def test_direct_write_tool_reports_path() -> None:
    effects = RESOLVER.resolve("write_file", {"path": r"C:\Projects\kis-mcp\x.txt"})
    assert effects.write_paths == (r"C:\Projects\kis-mcp\x.txt",)


def test_write_pdf_reports_only_the_effective_output_path() -> None:
    separate_output = RESOLVER.resolve(
        "write_pdf",
        {
            "path": r"C:\Windows\Temp\source.pdf",
            "outputPath": r"C:\Projects\kis-mcp\output.pdf",
        },
    )
    in_place = RESOLVER.resolve(
        "write_pdf",
        {"path": r"C:\Projects\kis-mcp\source.pdf"},
    )

    assert separate_output.write_paths == (r"C:\Projects\kis-mcp\output.pdf",)
    assert in_place.write_paths == (r"C:\Projects\kis-mcp\source.pdf",)


def test_move_reports_entry_mutations() -> None:
    effects = RESOLVER.resolve(
        "move_file",
        {
            "source": r"C:\Projects\kis-mcp\a.txt",
            "destination": r"C:\Projects\kis-mcp\b.txt",
        },
    )
    assert effects.write_paths == ()
    assert effects.entry_paths == (
        r"C:\Projects\kis-mcp\a.txt",
        r"C:\Projects\kis-mcp\b.txt",
    )


def test_unexposed_url_mode_has_no_redundant_policy_mapping() -> None:
    for path in ("https://example.com/data", "http://localhost:3000/data"):
        effects = RESOLVER.resolve("read_file", {"path": path, "isUrl": True})
        assert effects.external_network is False


def test_url_text_without_provider_url_mode_is_local_input() -> None:
    effects = RESOLVER.resolve(
        "read_file", {"path": "https://example.com/data", "isUrl": False}
    )
    assert effects.external_network is False


def test_read_multiple_files_has_no_url_mode() -> None:
    effects = RESOLVER.resolve(
        "read_multiple_files", {"paths": ["https://example.com/data"]}
    )
    assert effects.external_network is False


def test_unexposed_feedback_tool_has_no_redundant_policy_mapping() -> None:
    effects = RESOLVER.resolve("give_feedback_to_desktop_commander", {})
    assert effects.external_network is False


def test_normal_terminal_command_remains_available() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": "pytest -q", "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.write_paths == ()
    assert effects.entry_paths == ()
    assert effects.delete_paths == ()
    assert effects.external_network is False


def test_terminal_network_command_is_detected() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": "curl https://example.com", "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.external_network is True


def test_url_text_is_not_network_intent_without_a_consumer() -> None:
    for command in (
        'Write-Output "https://example.com"',
        'Select-String "https://example.com" README.md',
        'python generate_docs.py --example-url https://example.com',
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is False


def test_network_client_option_values_are_not_mistaken_for_targets() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": 'curl -H "Referer: https://example.com" http://localhost:3000',
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.external_network is False


def test_network_bearing_client_options_are_consuming_targets() -> None:
    for command in (
        "curl --proxy https://proxy.example http://localhost:3000",
        "curl -x https://proxy.example http://localhost:3000",
        "curl --connect-to example.com:443:route.example:443 https://localhost",
        "curl --resolve example.com:443:203.0.113.10 https://localhost",
        "ssh -J jump.example localhost",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is True, command


def test_curl_short_options_preserve_case_sensitive_semantics() -> None:
    method_data = RESOLVER.resolve(
        "start_process",
        {
            "command": "curl -X https://example.com http://localhost:3000",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    local_proxy = RESOLVER.resolve(
        "start_process",
        {
            "command": "curl -x http://localhost:8080 http://localhost:3000",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert method_data.external_network is False
    assert local_proxy.external_network is False


def test_network_client_positional_host_is_detected() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": "ssh example.com", "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.external_network is True


def test_scp_requires_an_explicit_remote_operand() -> None:
    local_only = RESOLVER.resolve(
        "start_process",
        {
            "command": r"scp missing.txt C:\Projects\kis-mcp\copy.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    remote = RESOLVER.resolve(
        "start_process",
        {
            "command": "scp local.txt user@example.com:/tmp/remote.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )

    assert local_only.external_network is False
    assert remote.external_network is True


def test_localhost_network_client_is_allowed() -> None:
    for command in (
        "curl http://localhost:3000/health",
        "ssh localhost",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is False


def test_local_git_clone_is_allowed() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"git clone C:\Projects\source C:\Projects\clone",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.external_network is False


def test_read_only_git_forms_do_not_claim_a_write_target() -> None:
    for command in (
        "git status",
        "git log",
        "git branch",
        "git branch --all",
        "git branch --list",
        "git tag",
        "git tag --list",
        "git stash list",
        "git stash show",
        "git rebase --show-current-patch",
        "git am --show-current-patch",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Windows\Temp"},
        )
        assert effects.write_paths == ()


def test_mutating_git_forms_report_the_working_directory() -> None:
    for command in (
        "git branch feature",
        "git tag v1.0.0",
        "git stash push",
        "git reset --hard",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.write_paths
        assert effects.write_paths[0] == r"C:\Projects\kis-mcp"
        assert all(
            path == r"C:\Projects\kis-mcp"
            or path.startswith("C:\\Projects\\kis-mcp\\")
            for path in effects.write_paths
        )


def test_local_package_install_is_allowed() -> None:
    for command in (
        r"pip install C:\Projects\packages\local.whl",
        r"npm install C:\Projects\packages\local-package",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is False


def test_ambiguous_package_operations_are_not_blocked_by_category() -> None:
    for command in (
        "npm install",
        "pip install example-package",
        "uv sync",
        "uv lock",
        "uv pip install example-package",
        "winget search example-package",
        "winget search --source winget example-package",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is False


def test_explicit_offline_package_operations_are_allowed() -> None:
    for command in (
        "npm install --offline",
        "uv sync --offline",
        "uv lock --offline",
        "uv pip install --offline example-package",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is False


def test_explicit_remote_git_and_package_targets_are_blocked() -> None:
    for command in (
        "git clone https://example.com/repository.git",
        "pip install https://example.com/package.whl",
        "npm install git+https://example.com/package.git",
        "pip install --index-url https://packages.example.com/simple example-package",
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.external_network is True


def test_git_pull_without_resolved_remote_is_not_blocked_by_category(
    tmp_path: Path,
) -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": "git pull", "cwd": str(tmp_path)},
    )
    assert effects.external_network is False


def test_git_named_remote_is_resolved_from_local_config(tmp_path: Path) -> None:
    _write_git_remote(tmp_path, "https://example.com/repository.git")
    for command in ("git pull", "git fetch origin", "git push origin main"):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": str(tmp_path)},
        )
        assert effects.external_network is True


def test_git_local_remote_is_allowed(tmp_path: Path) -> None:
    local_remote = tmp_path.parent / "source-repository"
    local_remote.mkdir()
    _write_git_remote(tmp_path, str(local_remote))
    effects = RESOLVER.resolve(
        "start_process",
        {"command": "git pull", "cwd": str(tmp_path)},
    )
    assert effects.external_network is False


def test_chained_command_resolves_each_explicit_operation() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": (
                r"echo ok && curl https://example.com/data; "
                r"Remove-Item C:\Projects\kis-mcp\old.txt"
            ),
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.external_network is True
    assert effects.delete_paths == (r"C:\Projects\kis-mcp\old.txt",)


def test_shell_wrappers_resolve_nested_explicit_operations() -> None:
    for command in (
        r'cmd /c "del C:\Projects\kis-mcp\old.txt"',
        r'pwsh -Command "Remove-Item C:\Projects\kis-mcp\old.txt"',
    ):
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.delete_paths == (r"C:\Projects\kis-mcp\old.txt",)


def test_quoted_shell_separator_is_not_treated_as_a_chain() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": 'echo "safe; literal"', "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.external_network is False
    assert effects.delete_paths == ()


def test_terminal_delete_command_is_detected() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"Remove-Item -LiteralPath C:\Projects\kis-mcp\old.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.delete_paths == (r"C:\Projects\kis-mcp\old.txt",)


def test_terminal_move_reports_entry_paths() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"move C:\Projects\kis-mcp\a.txt C:\Projects\kis-mcp\b.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.entry_paths == (
        r"C:\Projects\kis-mcp\a.txt",
        r"C:\Projects\kis-mcp\b.txt",
    )


def test_terminal_redirection_outside_boundary_is_detected() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"echo test > C:\Windows\temp\ki-test.txt",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.write_paths == (r"C:\Windows\temp\ki-test.txt",)


def test_quoted_redirection_text_is_not_a_write_target() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": 'Write-Output "literal > C:\\Windows\\Temp\\not-a-target.txt"',
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.write_paths == ()


def test_exact_write_command_operand_contracts_skip_option_values() -> None:
    cases = (
        (
            r"New-Item -ItemType File C:\Windows\Temp\new.txt",
            (r"C:\Windows\Temp\new.txt",),
        ),
        (
            r'touch -d "2026-01-01" C:\Windows\Temp\stamp.txt',
            (r"C:\Windows\Temp\stamp.txt",),
        ),
        (
            r"Set-Content -Encoding utf8 C:\Windows\Temp\content.txt value",
            (r"C:\Windows\Temp\content.txt",),
        ),
    )
    for command, expected in cases:
        effects = RESOLVER.resolve(
            "start_process",
            {"command": command, "cwd": r"C:\Projects\kis-mcp"},
        )
        assert effects.write_paths == expected, command


def test_positional_powershell_write_path_is_detected() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"Set-Content C:\Windows\Temp\kis.txt value",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.write_paths == (r"C:\Windows\Temp\kis.txt",)


def test_relative_redirection_uses_command_working_directory() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {"command": r"echo test > .\output.txt", "cwd": r"C:\Projects\kis-mcp"},
    )
    assert effects.write_paths == (r"C:\Projects\kis-mcp\output.txt",)


def test_generic_dash_o_is_not_assumed_to_be_an_output_path() -> None:
    effects = RESOLVER.resolve(
        "start_process",
        {
            "command": r"custom-tool -o C:\Windows\Temp\value",
            "cwd": r"C:\Projects\kis-mcp",
        },
    )
    assert effects.write_paths == ()


def test_git_clean_and_reset_are_classified_by_exact_effect() -> None:
    dry_run = RESOLVER.resolve(
        "start_process",
        {"command": "git clean --dry-run -d", "cwd": r"C:\Projects\kis-mcp"},
    )
    destructive = RESOLVER.resolve(
        "start_process",
        {"command": "git clean -fd", "cwd": r"C:\Projects\kis-mcp"},
    )
    reset = RESOLVER.resolve(
        "start_process",
        {"command": "git reset --hard", "cwd": r"C:\Projects\kis-mcp"},
    )

    assert dry_run.delete_paths == ()
    assert dry_run.unresolved_delete is False
    assert destructive.delete_paths == ()
    assert destructive.unresolved_delete is True
    assert reset.delete_paths == ()
    assert reset.unresolved_delete is False


def test_enabling_telemetry_is_network_intent() -> None:
    for value in (True, "true", None, "unexpected"):
        effects = RESOLVER.resolve(
            "set_config_value", {"key": "telemetryEnabled", "value": value}
        )
        assert effects.external_network is True
        assert effects.write_paths == (
            r"C:\Projects\.kis-mcp\.claude-server-commander\config.json",
        )


def test_disabling_telemetry_is_not_network_intent() -> None:
    for value in (False, "false", " FALSE "):
        effects = RESOLVER.resolve(
            "set_config_value", {"key": "telemetryEnabled", "value": value}
        )
        assert effects.external_network is False


def test_unknown_tool_is_allowed_without_invented_restriction() -> None:
    effects = RESOLVER.resolve("future_local_tool", {"value": "anything"})
    assert effects.write_paths == ()
    assert effects.entry_paths == ()
    assert effects.delete_paths == ()
    assert effects.external_network is False


def test_search_success_observer_tracks_and_stops_active_searches() -> None:
    observability = RuntimeObservability(max_recent_calls=5, max_policy_decisions=5)
    resolver = DesktopCommanderEffectResolver(
        project_boundary=r"C:\Projects",
        provider_state_file=r"C:\Projects\.kis-mcp\desktop-commander\config.json",
        observability=observability,
    )

    resolver.observe_success(
        "start_search",
        {"path": r"C:\Projects\secret-project", "query": "private query"},
        "Search started. Search ID: search-abc-123",
    )
    resolver.observe_success(
        "get_more_search_results",
        {"search_id": "search-abc-123", "offset": 10},
        "private result body",
    )

    active = observability.snapshot().active_searches
    assert [(item.search_id, item.tool_name) for item in active] == [
        ("search-abc-123", "start_search")
    ]
    rendered = str(observability.snapshot().to_dict())
    assert "private query" not in rendered
    assert "private result body" not in rendered

    resolver.observe_success(
        "stop_search",
        {"search_id": "search-abc-123"},
        "stopped",
    )
    assert observability.snapshot().active_searches == ()
