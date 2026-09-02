from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _fixture(tmp_path: Path, *, run_id: str = "run-a") -> tuple[Path, Path]:
    root = tmp_path / "repo"
    scripts = root / "scripts"
    settings = root / "settings"
    state = tmp_path / "state"
    scripts.mkdir(parents=True)
    settings.mkdir()
    state.mkdir()
    source = Path(__file__).parents[1] / "scripts" / "runtime-health-guard.ps1"
    (scripts / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text(json.dumps({
        "paths": {"state_root": str(state)},
        "remote_mcp": {"host": "127.0.0.1", "path": "/mcp", "instances": {
            "operation": {"port": 18010, "app_name": "kis-op"},
            "development": {"port": 18011, "app_name": "kis-dev"},
        }},
    }), encoding="utf-8")
    runtime = state / "tunnel-client" / "runtime" / "operation"
    runtime.mkdir(parents=True)
    (runtime / "current.json").write_text(json.dumps({
        "lifecycle": "ready", "run_id": run_id, "instance": "operation", "app": "kis-op",
        "launcher_pid": 999991, "server_pid": 999992, "tunnel_pid": 999993,
    }), encoding="utf-8")
    return root, state


def test_guard_exits_when_generation_is_no_longer_current(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path, run_id="new-run")
    (root / "scripts" / "recover-chatgpt.ps1").write_text("throw 'must not recover'", encoding="utf-8")
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "old-run", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "1",
    ], cwd=root, capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr


def test_guard_recovers_same_unhealthy_generation(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    marker = tmp_path / "recovered.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot)\n"
        "[IO.File]::WriteAllText($env:KIS_RECOVERY_MARKER,$Instance)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_RECOVERY_MARKER"] = str(marker)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "run-a", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "1",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8") == "kis-op"


def test_guard_retries_transient_recovery_failure_with_backoff(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    marker = tmp_path / "attempts.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "$path=$env:KIS_RECOVERY_MARKER\n"
        "$count=if(Test-Path $path){[int](Get-Content $path -Raw)}else{0}\n"
        "$count += 1; [IO.File]::WriteAllText($path,[string]$count)\n"
        "if($count -eq 1){throw 'transient restart failure'}\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_RECOVERY_MARKER"] = str(marker)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "run-a", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "1", "-MaxRecoveryAttempts", "2",
        "-RecoveryBackoffSeconds", "1", "-MaxRecoveryBackoffSeconds", "1",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=12, check=False)
    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8") == "2"
    assert "KIS_MCP_HEALTH_RECOVERY_FAILED" in result.stdout


def test_launcher_installs_generation_scoped_health_guard() -> None:
    start = (Path(__file__).parents[1] / "scripts" / "start-chatgpt.ps1").read_text(encoding="utf-8")
    assert "runtime-health-guard.ps1" in start
    assert "-RunId" in start
    assert "KIS_MCP_HEALTH_GUARD_START_FAILED" in start
