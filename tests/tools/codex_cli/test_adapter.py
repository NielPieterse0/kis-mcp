from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from kis_mcp.tools import ToolBoundary, ToolKind, ToolRegistry, ToolState
from kis_mcp.tools.codex_cli import (
    CodexCliAdapter,
    CodexCliError,
    CodexSettings,
    codex_tool_descriptor,
    register_codex_tool,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _settings() -> CodexSettings:
    return CodexSettings(
        enabled=True,
        script_path=REPOSITORY_ROOT / "scripts" / "invoke-codex-agent.ps1",
        executable=r"C:\Projects\.kis-mcp\tools\codex\0.147.0\node_modules\.bin\codex.cmd",
        home_path=Path(r"C:\Projects\.kis-mcp\agent-hosts\codex-reviewer"),
        expected_version="0.147.0",
        timeout_seconds=60,
        max_output_chars=30000,
    )


def test_codex_adapter_invokes_fixed_script_and_extracts_agent_message(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def run(args, **kwargs):
        calls.append({"args": args, **kwargs})
        stdout = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "t1"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "review result"},
                    }
                ),
            ]
        )
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    adapter = CodexCliAdapter(_settings(), runner=run, pwsh_executable="pwsh")

    result = adapter.review(tmp_path, "inspect the change")

    call = calls[0]
    assert call["args"] == [
        "pwsh",
        "-NoProfile",
        "-File",
        str(_settings().script_path),
        "-CodexExecutable",
        _settings().executable,
        "-ProjectPath",
        str(tmp_path.resolve()),
        "-CodexHome",
        str(_settings().home_path),
    ]
    assert call["input"] == "inspect the change"
    assert call["timeout"] == 60
    assert call["capture_output"] is True
    assert call["text"] is True
    assert result == "review result"


def test_codex_adapter_reports_process_failure_without_raw_prompt(tmp_path: Path) -> None:
    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 7, stdout="", stderr="auth required")

    adapter = CodexCliAdapter(_settings(), runner=run, pwsh_executable="pwsh")

    with pytest.raises(CodexCliError) as exc_info:
        adapter.review(tmp_path, "sensitive prompt text")

    assert exc_info.value.code == "CODEX_CLI_PROCESS_FAILED"
    assert exc_info.value.details == {"returncode": 7}
    assert "sensitive prompt text" not in str(exc_info.value)
    assert "auth required" not in str(exc_info.value)


def test_codex_adapter_reports_detected_repository_mutation(tmp_path: Path) -> None:
    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 86, stdout="", stderr="mutation detected")

    adapter = CodexCliAdapter(_settings(), runner=run, pwsh_executable="pwsh")

    with pytest.raises(CodexCliError) as exc_info:
        adapter.review(tmp_path, "prompt")

    assert exc_info.value.code == "CODEX_CLI_MUTATION_DETECTED"
    assert exc_info.value.details == {}
    assert "mutation detected" not in str(exc_info.value)


def test_codex_adapter_reports_missing_agent_message(tmp_path: Path) -> None:
    def run(args, **kwargs):
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps({"type": "turn.completed", "usage": {}}),
            stderr="",
        )

    adapter = CodexCliAdapter(_settings(), runner=run, pwsh_executable="pwsh")

    with pytest.raises(CodexCliError, match="agent message") as exc_info:
        adapter.review(tmp_path, "prompt")

    assert exc_info.value.code == "CODEX_CLI_RESPONSE_INVALID"


def test_codex_script_enforces_ephemeral_read_only_json_execution() -> None:
    script = (REPOSITORY_ROOT / "scripts" / "invoke-codex-agent.ps1").read_text(
        encoding="utf-8"
    )

    required_fragments = [
        "exec",
        "--ephemeral",
        "--json",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "-C",
        "$ProjectPath",
        "-",
    ]
    for fragment in required_fragments:
        assert fragment in script
    assert "danger-full-access" not in script
    assert "workspace-write" not in script
    assert "Get-RepositoryStateFingerprint" in script
    assert "$env:CODEX_HOME = $ResolvedCodexHome" in script
    assert "CODEX_CLI_HOME_REPARSE_POINT" in script
    assert "CODEX_CLI_MUTATION_DETECTED" in script
    assert "exit 86" in script


def test_codex_tool_descriptor_uses_generic_tools_registry() -> None:
    def ready_run(args, **kwargs):
        stdout = "codex-cli 0.147.0\n" if args[-1] == "--version" else "Logged in using ChatGPT\n"
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    descriptor = codex_tool_descriptor(
        _settings(),
        which=lambda name: f"C:/Tools/{name}.exe",
        runner=ready_run,
    )

    assert descriptor.tool_id == "codex-cli"
    assert descriptor.tool_kind is ToolKind.LOCAL_EXECUTABLE
    assert descriptor.boundary is ToolBoundary.LOCAL_PROCESS
    assert descriptor.readiness_probe().state is ToolState.READY
    assert [item.capability_id for item in descriptor.capabilities] == [
        "code.review.codex-cli"
    ]

    registry = ToolRegistry()
    registered = register_codex_tool(
        registry,
        settings=_settings(),
        which=lambda name: f"C:/Tools/{name}.exe",
        runner=ready_run,
    )
    assert registry.get("codex-cli") is registered


def test_codex_tool_readiness_verifies_exact_version_and_chatgpt_auth() -> None:
    calls: list[list[str]] = []

    def run(args, **kwargs):
        calls.append(list(args))
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.147.0\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="Logged in using ChatGPT\n", stderr="")

    descriptor = codex_tool_descriptor(
        _settings(),
        which=lambda name: name,
        runner=run,
    )

    readiness = descriptor.readiness_probe()

    assert readiness.state is ToolState.READY
    assert readiness.details == {"version": "0.147.0", "authentication": "chatgpt"}
    assert calls == [
        [_settings().executable, "--version"],
        [_settings().executable, "login", "status"],
    ]


def test_codex_tool_readiness_accepts_chatgpt_status_from_stderr() -> None:
    def run(args, **kwargs):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.147.0\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="Logged in using ChatGPT\n")

    descriptor = codex_tool_descriptor(
        _settings(),
        which=lambda name: name,
        runner=run,
    )

    readiness = descriptor.readiness_probe()

    assert readiness.state is ToolState.READY
    assert readiness.details == {"version": "0.147.0", "authentication": "chatgpt"}


def test_codex_tool_readiness_reports_missing_executable_without_building() -> None:
    descriptor = codex_tool_descriptor(
        _settings(),
        which=lambda name: "C:/Tools/pwsh.exe" if name == "pwsh" else None,
    )

    readiness = descriptor.readiness_probe()

    assert readiness.state is ToolState.DEGRADED
    assert readiness.details == {"executable": _settings().executable}


def _initialize_git_repository(root: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Codex Wrapper Tests"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "codex-wrapper@example.invalid"],
        cwd=root,
        check=True,
    )
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)


def test_codex_wrapper_executes_fake_cli_and_preserves_repository(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell is unavailable")
    _initialize_git_repository(tmp_path)
    fake_codex = tmp_path / "fake-codex.cmd"
    fake_codex.write_text(
        '@echo off\r\necho {"type":"item.completed","item":{"type":"agent_message","text":"review output"}}\r\nexit /b 0\r\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-File",
            str(_settings().script_path),
            "-CodexExecutable",
            str(fake_codex),
            "-ProjectPath",
            str(tmp_path),
            "-CodexHome",
            str(tmp_path / "codex-home"),
        ],
        input="review prompt",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert '"text":"review output"' in completed.stdout
    assert (tmp_path / "tracked.txt").read_text(encoding="utf-8") == "baseline\n"


def test_codex_wrapper_detects_fake_cli_repository_mutation(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell is unavailable")
    _initialize_git_repository(tmp_path)
    fake_codex = tmp_path / "mutating-codex.cmd"
    fake_codex.write_text(
        '@echo off\r\necho changed>>"%~dp0tracked.txt"\r\necho {"type":"item.completed","item":{"type":"agent_message","text":"review output"}}\r\nexit /b 0\r\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-File",
            str(_settings().script_path),
            "-CodexExecutable",
            str(fake_codex),
            "-ProjectPath",
            str(tmp_path),
            "-CodexHome",
            str(tmp_path / "codex-home"),
        ],
        input="review prompt",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 86
    assert "CODEX_CLI_MUTATION_DETECTED" in completed.stderr
