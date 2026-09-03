from __future__ import annotations

import json
import os
import subprocess
import time
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
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "[IO.File]::WriteAllText($env:KIS_RECOVERY_MARKER,\"$Instance|$ExpectedRunId\")\n",
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
    assert marker.read_text(encoding="utf-8") == "kis-op|run-a"


def test_guard_does_not_recover_before_configured_failure_grace(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    marker = tmp_path / "recovered-after-grace.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "[IO.File]::WriteAllText($env:KIS_RECOVERY_MARKER,\"$Instance|$ExpectedRunId\")\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_RECOVERY_MARKER"] = str(marker)
    process = subprocess.Popen([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "run-a", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "2",
    ], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(1.0)
    assert not marker.exists()
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr or stdout
    assert marker.read_text(encoding="utf-8") == "kis-op|run-a"


def test_guard_recovers_same_stopped_generation(tmp_path: Path) -> None:
    root, state = _fixture(tmp_path)
    current_path = state / "tunnel-client" / "runtime" / "operation" / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["lifecycle"] = "stopped"
    current_path.write_text(json.dumps(current), encoding="utf-8")
    marker = tmp_path / "recovered-stopped.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "[IO.File]::WriteAllText($env:KIS_RECOVERY_MARKER,\"$Instance|$ExpectedRunId\")\n",
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
    assert marker.read_text(encoding="utf-8") == "kis-op|run-a"


def test_duplicate_guards_for_same_generation_recover_once(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    marker = tmp_path / "recoveries.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "[IO.File]::AppendAllText($env:KIS_RECOVERY_MARKER,\"$PID|$ExpectedRunId`n\")\n"
        "Start-Sleep -Seconds 2\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_RECOVERY_MARKER"] = str(marker)
    command = [
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "run-a", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "1", "-MaxRecoveryAttempts", "1",
    ]
    first = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    second = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    first_out, first_err = first.communicate(timeout=10)
    second_out, second_err = second.communicate(timeout=10)
    assert first.returncode == 0, first_err or first_out
    assert second.returncode == 0, second_err or second_out
    assert marker.read_text(encoding="utf-8").splitlines() == [marker.read_text(encoding="utf-8").splitlines()[0]]
    assert marker.read_text(encoding="utf-8").splitlines()[0].endswith("|run-a")


def test_guard_retries_transient_recovery_failure_with_backoff(tmp_path: Path) -> None:
    root, _ = _fixture(tmp_path)
    marker = tmp_path / "attempts.txt"
    (root / "scripts" / "recover-chatgpt.ps1").write_text(
        "param([string]$Instance,[string]$RepositoryRoot,[string]$ExpectedRunId)\n"
        "$path=$env:KIS_RECOVERY_MARKER\n"
        "$count=if(Test-Path $path){[int](Get-Content $path -Raw)}else{0}\n"
        "$count += 1; [IO.File]::WriteAllText($path,[string]$count)\n"
        "[IO.File]::AppendAllText($env:KIS_RUN_MARKER,\"$ExpectedRunId`n\")\n"
        "if($count -eq 1){throw 'transient restart failure'}\n",
        encoding="utf-8",
    )
    run_marker = tmp_path / "run-ids.txt"
    env = dict(os.environ)
    env["KIS_RECOVERY_MARKER"] = str(marker)
    env["KIS_RUN_MARKER"] = str(run_marker)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "runtime-health-guard.ps1"),
        "-Instance", "kis-op", "-RunId", "run-a", "-RepositoryRoot", str(root),
        "-PollSeconds", "1", "-FailureGraceSeconds", "1", "-MaxRecoveryAttempts", "2",
        "-RecoveryBackoffSeconds", "1", "-MaxRecoveryBackoffSeconds", "1",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=12, check=False)
    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8") == "2"
    assert run_marker.read_text(encoding="utf-8").splitlines() == ["run-a", "run-a"]
    assert "KIS_MCP_HEALTH_RECOVERY_FAILED" in result.stdout


def test_launcher_installs_generation_scoped_health_guard() -> None:
    start = (Path(__file__).parents[1] / "scripts" / "start-chatgpt.ps1").read_text(encoding="utf-8")
    assert "runtime-health-guard.ps1" in start
    assert "-RunId" in start
    assert "-FailureGraceSeconds 60" in start
    assert "KIS_MCP_HEALTH_GUARD_START_FAILED" in start


def test_guard_default_failure_grace_is_sixty_seconds() -> None:
    guard = (Path(__file__).parents[1] / "scripts" / "runtime-health-guard.ps1").read_text(encoding="utf-8")
    assert "[ValidateRange(1,60)][int]$FailureGraceSeconds = 60" in guard
    assert "[ValidateRange(1,300)][int]$RecoveryBackoffSeconds = 60" in guard
    assert "[ValidateRange(1,300)][int]$MaxRecoveryBackoffSeconds = 60" in guard


def test_launcher_preserves_failed_ready_generation_for_health_recovery() -> None:
    start = (Path(__file__).parents[1] / "scripts" / "start-chatgpt.ps1").read_text(encoding="utf-8")
    assert "$PreserveCurrentForHealthRecovery = $true" in start
    assert "if ($CurrentStateWritten -and -not $PreserveCurrentForHealthRecovery)" in start


def test_health_checks_use_canonical_server_listener_pid() -> None:
    root = Path(__file__).parents[1]
    guard = (root / "scripts" / "runtime-health-guard.ps1").read_text(encoding="utf-8")
    recovery = (root / "scripts" / "recover-chatgpt.ps1").read_text(encoding="utf-8")
    assert "$ServerListenerPid = [int]$Current.PSObject.Properties['server_listener_pid'].Value" in guard
    assert "OwningProcess -eq $ServerListenerPid" in guard
    assert "$ServerListenerPid = [int]$Current.PSObject.Properties['server_listener_pid'].Value" in recovery
    assert "OwningProcess -eq $ServerListenerPid" in recovery
