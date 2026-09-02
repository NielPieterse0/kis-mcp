from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError
from kis_mcp.post_land_restart import (
    dispatch_kis_dev_post_land_restart,
    record_kis_dev_post_land_restart_failure,
    schedule_kis_dev_post_land_restart,
)

SHA = "a" * 40
REMOTE_AFTER = "b" * 40


def test_other_projects_and_branches_do_not_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr("kis_mcp.post_land_restart.subprocess.run", lambda *a, **k: calls.append((a, k)))

    state_root = Path("C:/Projects/.kis-mcp")
    assert schedule_kis_dev_post_land_restart(
        "college", Path("C:/Projects/college"), "main", SHA, state_root=state_root
    )["state"] == "not_applicable"
    assert schedule_kis_dev_post_land_restart(
        "kis-mcp", Path("C:/Projects/kis-mcp"), "release", SHA, state_root=state_root
    )["state"] == "not_applicable"
    assert calls == []


def test_kis_mcp_main_schedules_detached_worker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "restart-kis-dev-after-land.ps1").write_text("test", encoding="utf-8")
    calls: list[tuple[object, object]] = []

    def fake_run(command: object, **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":1234}\n', stderr="")

    state_root = tmp_path / "state"
    monkeypatch.setattr("kis_mcp.post_land_restart.subprocess.run", fake_run)
    result = schedule_kis_dev_post_land_restart(
        "kis-mcp", tmp_path, "main", SHA, state_root=state_root
    )

    assert result == {"state": "scheduled", "pid": 1234}
    command = calls[0][0]
    assert command[-6:] == [
        "-ExpectedLandedSha", SHA,
        "-RepositoryRoot", str(tmp_path),
        "-StateRoot", str(state_root),
    ]
    assert "restart-kis-dev-after-land.ps1" in str(command)


def test_first_landing_uses_executing_source_worker_when_primary_lacks_script(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[object, object]] = []

    def fake_run(command: object, **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":4321}\n', stderr="")

    state_root = tmp_path / "state"
    monkeypatch.setattr("kis_mcp.post_land_restart.subprocess.run", fake_run)
    result = schedule_kis_dev_post_land_restart(
        "kis-mcp", tmp_path, "main", SHA, state_root=state_root
    )

    assert result == {"state": "scheduled", "pid": 4321}
    command = calls[0][0]
    source_script = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    assert Path(command[3]).resolve() == source_script.resolve()
    assert "-RepositoryRoot" in command
    assert str(tmp_path) in command


def test_detached_scheduler_propagates_requested_delay(tmp_path: Path) -> None:
    root = tmp_path / "detached-delay"
    scripts = root / "scripts"
    settings = root / "settings"
    state_root = root / "state"
    for path in (scripts, settings, state_root):
        path.mkdir(parents=True)
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text("{}", encoding="utf-8")
    command_log = root / "detached-command.txt"
    wrapper = root / "invoke.ps1"
    wrapper.write_text(
        "function Invoke-CimMethod { param([string]$ClassName,[string]$MethodName,[hashtable]$Arguments) "
        "[IO.File]::WriteAllText($env:KIS_TEST_COMMAND,[string]$Arguments.CommandLine); "
        "[pscustomobject]@{ReturnValue=0;ProcessId=321} }\n"
        f"& '{worker_script}' -ExpectedLandedSha '{SHA}' -RepositoryRoot '{root}' "
        f"-StateRoot '{state_root}' -DelaySeconds 0\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_TEST_COMMAND"] = str(command_log)
    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(wrapper)], cwd=root, env=env,
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '-DelaySeconds "0" -Worker' in command_log.read_text(encoding="utf-8")


def test_scheduler_receipt_replace_is_windows_powershell_compatible(tmp_path: Path) -> None:
    root = tmp_path / "windows-powershell-receipt"
    scripts = root / "scripts"
    state_root = root / "state"
    scripts.mkdir(parents=True)
    state_root.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"state": "launching", "landed_sha": SHA}), encoding="utf-8")
    previous_receipt = receipt.parent / "latest.json.previous"
    previous_receipt.write_text(json.dumps({"state": "older"}), encoding="utf-8")
    wrapper = root / "invoke-windows-powershell.ps1"
    wrapper.write_text(
        "function Invoke-CimMethod { param([string]$ClassName,[string]$MethodName,[hashtable]$Arguments) "
        "[pscustomobject]@{ReturnValue=0;ProcessId=654} }\n"
        f"& '{worker_script}' -ExpectedLandedSha '{SHA}' -RepositoryRoot '{root}' "
        f"-StateRoot '{state_root}' -DelaySeconds 0\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    assert evidence["state"] == "scheduled"
    assert evidence["landed_sha"] == SHA
    assert evidence["worker_pid"] == 654
    previous = json.loads((receipt.parent / "latest.json.previous").read_text(encoding="utf-8"))
    assert previous == {"state": "launching", "landed_sha": SHA}


def test_scheduler_reuses_live_same_sha_worker_without_detaching_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "live-worker-reuse"
    scripts = root / "scripts"
    state_root = root / "state"
    scripts.mkdir(parents=True)
    state_root.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    receipt.parent.mkdir(parents=True)
    wrapper = root / "invoke-live-worker-reuse.ps1"
    wrapper.write_text(
        "$receipt = @{schema_version=1;state='launching';landed_sha='" + SHA + "';launched_sha='" + SHA + "';worker_pid=$PID;detail='live';updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json\n"
        f"[IO.File]::WriteAllText('{receipt}', $receipt)\n"
        "function Invoke-CimMethod { throw 'duplicate detach must not happen' }\n"
        f"& '{worker_script}' -ExpectedLandedSha '{SHA}' -RepositoryRoot '{root}' "
        f"-StateRoot '{state_root}' -DelaySeconds 0\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(wrapper)],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout.strip().splitlines()[-1])
    assert output["state"] == "scheduled"
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    assert evidence["state"] == "launching"
    assert evidence["detail"] == "live"


def test_windows_powershell_detach_failure_does_not_claim_scheduled(tmp_path: Path) -> None:
    root = tmp_path / "windows-powershell-detach-failure"
    scripts = root / "scripts"
    state_root = root / "state"
    scripts.mkdir(parents=True)
    state_root.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    receipt.parent.mkdir(parents=True)
    existing = {"state": "launching", "landed_sha": SHA}
    receipt.write_text(json.dumps(existing), encoding="utf-8")
    wrapper = root / "invoke-detach-failure.ps1"
    wrapper.write_text(
        "function Invoke-CimMethod { param([string]$ClassName,[string]$MethodName,[hashtable]$Arguments) "
        "[pscustomobject]@{ReturnValue=1;ProcessId=0} }\n"
        f"& '{worker_script}' -ExpectedLandedSha '{SHA}' -RepositoryRoot '{root}' "
        f"-StateRoot '{state_root}' -DelaySeconds 0\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode != 0
    assert "POST_LAND_RESTART_DETACH_FAILED" in result.stderr
    assert json.loads(receipt.read_text(encoding="utf-8")) == existing


@pytest.mark.parametrize(
    ("current_landed_sha", "current_worker_pid"),
    [(REMOTE_AFTER, 999998), (SHA, 999999)],
    ids=["different-sha", "same-sha-different-worker"],
)
def test_stale_worker_cannot_overwrite_newer_receipt_generation(
    tmp_path: Path, current_landed_sha: str, current_worker_pid: int
) -> None:
    root = tmp_path / f"stale-worker-{current_landed_sha[0]}-{current_worker_pid}"
    scripts = root / "scripts"
    state_root = root / "state"
    scripts.mkdir(parents=True)
    state_root.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    receipt.parent.mkdir(parents=True)
    newer = {
        "schema_version": 1,
        "state": "launching",
        "landed_sha": current_landed_sha,
        "launched_sha": current_landed_sha,
        "worker_pid": 999999,
        "detail": "newer generation",
        "updated_utc": "2026-08-23T09:00:00Z",
    }
    receipt.write_text(json.dumps(newer), encoding="utf-8")

    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(worker_script),
         "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
         "-StateRoot", str(state_root), "-Worker", "-DelaySeconds", "0"],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(receipt.read_text(encoding="utf-8")) == newer
    assert not (receipt.parent / "latest.json.previous").exists()


@pytest.mark.parametrize(
    "error",
    [
        subprocess.TimeoutExpired(["pwsh.exe"], 15),
        FileNotFoundError("pwsh.exe"),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    ],
)
def test_scheduler_normalizes_process_launch_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, error: BaseException
) -> None:
    scripts = tmp_path / "scripts"
    settings = tmp_path / "settings"
    state_root = tmp_path / "state"
    for path in (scripts, settings, state_root):
        path.mkdir()
    (scripts / "restart-kis-dev-after-land.ps1").write_text("test", encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text(
        json.dumps({"paths": {"state_root": str(state_root)}}), encoding="utf-8"
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr("kis_mcp.post_land_restart.subprocess.run", fail)
    with pytest.raises(ToolError, match="POST_LAND_RESTART_SCHEDULE_FAILED"):
        schedule_kis_dev_post_land_restart(
            "kis-mcp", tmp_path, "main", SHA, state_root=state_root
        )
    receipt_path = (
        state_root / "runtime" / "kis-dev" / "state" /
        "post-land-restart" / "latest.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == SHA


@pytest.mark.parametrize(
    ("process_result", "error_code"),
    [
        (SimpleNamespace(returncode=9, stdout="", stderr="boom"), "POST_LAND_RESTART_SCHEDULE_FAILED"),
        (SimpleNamespace(returncode=0, stdout="{", stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout="[]", stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='"scheduled"', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"unexpected"}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled"}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":true}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":"123"}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":0}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":-1}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
        (SimpleNamespace(returncode=0, stdout='{"state":"scheduled","pid":123,"extra":1}', stderr=""), "POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE"),
    ],
)
def test_scheduler_rejects_unverified_process_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    process_result: SimpleNamespace,
    error_code: str,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "restart-kis-dev-after-land.ps1").write_text("test", encoding="utf-8")
    state_root = tmp_path / "state"
    monkeypatch.setattr(
        "kis_mcp.post_land_restart.subprocess.run",
        lambda *args, **kwargs: process_result,
    )
    with pytest.raises(ToolError, match=error_code):
        schedule_kis_dev_post_land_restart(
            "kis-mcp", tmp_path, "main", SHA, state_root=state_root
        )
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == SHA
    assert error_code in receipt["detail"]


def test_scheduler_rejects_invalid_sha_before_process_launch(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="POST_LAND_RESTART_SHA_INVALID"):
        schedule_kis_dev_post_land_restart(
            "kis-mcp", tmp_path, "main", "bad", state_root=tmp_path / "state"
        )


@pytest.mark.parametrize("settings_text", [None, "{"])
def test_worker_settings_failure_replaces_scheduled_receipt(
    tmp_path: Path, settings_text: str | None
) -> None:
    root = tmp_path / "worker-settings-failure"
    scripts = root / "scripts"
    settings = root / "settings"
    state_root = root / "state"
    scripts.mkdir(parents=True)
    settings.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    if settings_text is not None:
        (settings / "kis-mcp.settings.json").write_text(settings_text, encoding="utf-8")
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"state": "scheduled", "landed_sha": SHA}), encoding="utf-8")

    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(worker_script),
         "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
         "-StateRoot", str(state_root), "-Worker", "-DelaySeconds", "0"],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode != 0
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    assert evidence["state"] == "failed"
    assert evidence["landed_sha"] == SHA
    assert evidence["launched_sha"] == ""
    assert evidence["detail"]


def test_worker_is_hardwired_to_kis_dev_only() -> None:
    script = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    content = script.read_text(encoding="utf-8")
    assert "(Join-Path $RepositoryRoot 'scripts\\recover-kis-dev.ps1')" in content
    assert "recover-kis-op.ps1" not in content
    assert "-Instance 'kis-op'" not in content
    assert "Invoke-CimMethod" in content
    assert "git merge --ff-only" in content


@pytest.mark.parametrize(
    "status_line",
    [None, "?? .work/programmes/verification-review-evidence/run.json"],
)
def test_worker_behavior_invokes_only_kis_dev(
    tmp_path: Path, status_line: str | None
) -> None:
    root = tmp_path / "worker"
    scripts = root / "scripts"
    settings = root / "settings"
    fake_bin = root / "bin"
    state_root = root / "state"
    for path in (scripts, settings, fake_bin, state_root):
        path.mkdir(parents=True, exist_ok=True)

    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    (scripts / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    target_log = root / "restart-target.txt"
    (scripts / "recover-kis-dev.ps1").write_text(
        "param([string]$RepositoryRoot,[int]$WaitSeconds)\n"
        "[IO.File]::WriteAllText($env:KIS_TEST_TARGET, 'kis-dev')\n",
        encoding="utf-8",
    )
    (settings / "kis-mcp.settings.json").write_text(
        json.dumps({
            "paths": {"state_root": str(state_root)},
            "github_cli": {"config_dir": str(root / "gh")},
        }),
        encoding="utf-8",
    )
    git_log = root / "git-commands.txt"
    gh_log = root / "gh-commands.txt"
    merge_flag = root / "merged.flag"
    git_fake = fake_bin / "git_fake.py"
    git_fake.write_text(
        "import os, sys\nfrom pathlib import Path\n"
        f"SHA = {SHA!r}\nREMOTE = {REMOTE_AFTER!r}\n"
        "args = sys.argv[1:]\n"
        "with Path(os.environ['KIS_TEST_GIT_LOG']).open('a', encoding='utf-8') as handle:\n"
        "    handle.write('|'.join(args) + '\\n')\n"
        "flag = Path(os.environ['KIS_TEST_MERGE_FLAG'])\n"
        "fetch = ['-c','credential.https://github.com.helper=','-c','credential.https://github.com.helper=!gh auth git-credential','fetch','--no-tags','--no-recurse-submodules','--no-write-fetch-head','origin','refs/heads/main:refs/remotes/origin/main']\n"
        "if args == ['symbolic-ref','--quiet','--short','HEAD']:\n    print('main')\n"
        "elif args == ['status','--porcelain=v1','--untracked-files=all']:\n"
        "    status = os.environ.get('KIS_TEST_STATUS_LINE')\n"
        "    if status:\n        print(status)\n"
        "elif args == fetch:\n    pass\n"
        "elif args == ['rev-parse','--verify','HEAD']:\n    print(REMOTE if flag.exists() else SHA)\n"
        "elif args == ['rev-parse','--verify','refs/remotes/origin/main']:\n    print(REMOTE)\n"
        "elif args == ['merge-base','--is-ancestor',SHA,REMOTE]:\n    pass\n"
        "elif args == ['merge','--ff-only','refs/remotes/origin/main']:\n    flag.write_text('merged', encoding='utf-8')\n"
        "else:\n    print('unexpected git command: ' + repr(args), file=sys.stderr)\n    raise SystemExit(99)\n",
        encoding="utf-8",
    )
    (fake_bin / "git.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0git_fake.py" %*\nexit /b %ERRORLEVEL%\n',
        encoding="utf-8",
    )
    gh_fake = fake_bin / "gh_fake.py"
    gh_fake.write_text(
        "import os, sys\nfrom pathlib import Path\nargs = sys.argv[1:]\n"
        "with Path(os.environ['KIS_TEST_GH_LOG']).open('a', encoding='utf-8') as handle:\n"
        "    handle.write('|'.join(args) + '\\n')\n"
        "expected = ['auth','status','--active','--hostname','github.com']\n"
        "if args != expected:\n    print('unexpected gh command: ' + repr(args), file=sys.stderr)\n    raise SystemExit(99)\n",
        encoding="utf-8",
    )
    (fake_bin / "gh.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0gh_fake.py" %*\nexit /b %ERRORLEVEL%\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    env["KIS_TEST_TARGET"] = str(target_log)
    env["KIS_TEST_GIT_LOG"] = str(git_log)
    env["KIS_TEST_GH_LOG"] = str(gh_log)
    env["KIS_TEST_MERGE_FLAG"] = str(merge_flag)
    if status_line is not None:
        env["KIS_TEST_STATUS_LINE"] = status_line
    result = subprocess.run(
        [
            "pwsh.exe", "-NoProfile", "-File", str(scripts / source.name),
            "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
            "-StateRoot", str(state_root), "-Worker", "-DelaySeconds", "0",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert target_log.read_text(encoding="utf-8") == "kis-dev"
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "ready"
    assert receipt["landed_sha"] == SHA
    assert receipt["launched_sha"] == REMOTE_AFTER
    assert gh_log.read_text(encoding="utf-8").splitlines() == [
        "auth|status|--active|--hostname|github.com"
    ]
    assert git_log.read_text(encoding="utf-8").splitlines() == [
        "symbolic-ref|--quiet|--short|HEAD",
        "status|--porcelain=v1|--untracked-files=all",
        "-c|credential.https://github.com.helper=|-c|credential.https://github.com.helper=!gh auth git-credential|fetch|--no-tags|--no-recurse-submodules|--no-write-fetch-head|origin|refs/heads/main:refs/remotes/origin/main",
        "rev-parse|--verify|HEAD",
        "rev-parse|--verify|refs/remotes/origin/main",
        f"merge-base|--is-ancestor|{SHA}|{REMOTE_AFTER}",
        "merge|--ff-only|refs/remotes/origin/main",
        "rev-parse|--verify|HEAD",
        f"merge-base|--is-ancestor|{SHA}|{REMOTE_AFTER}",
    ]


def test_worker_retries_transient_kis_dev_launch_failure_then_succeeds(tmp_path: Path) -> None:
    root = tmp_path / "worker-recovery"
    scripts = root / "scripts"
    settings = root / "settings"
    fake_bin = root / "bin"
    state_root = root / "state"
    for path in (scripts, settings, fake_bin, state_root):
        path.mkdir(parents=True, exist_ok=True)

    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    (scripts / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    attempts = root / "launch-attempts.txt"
    (scripts / "recover-kis-dev.ps1").write_text(
        "param([string]$RepositoryRoot,[int]$WaitSeconds)\n"
        "$count = if (Test-Path $env:KIS_TEST_ATTEMPTS) { [int](Get-Content $env:KIS_TEST_ATTEMPTS -Raw) } else { 0 }\n"
        "$count += 1\n"
        "[IO.File]::WriteAllText($env:KIS_TEST_ATTEMPTS, [string]$count)\n"
        "if ($count -eq 1) { throw 'transient launch failure' }\n",
        encoding="utf-8",
    )
    (settings / "kis-mcp.settings.json").write_text(
        json.dumps({
            "paths": {"state_root": str(state_root)},
            "github_cli": {"config_dir": str(root / "gh")},
        }),
        encoding="utf-8",
    )
    git_log = root / "git-commands.txt"
    gh_log = root / "gh-commands.txt"
    git_fake = fake_bin / "git_fake.py"
    git_fake.write_text(
        "import os, sys\nfrom pathlib import Path\n"
        f"SHA = {SHA!r}\n"
        "args = sys.argv[1:]\n"
        "with Path(os.environ['KIS_TEST_GIT_LOG']).open('a', encoding='utf-8') as handle:\n"
        "    handle.write('|'.join(args) + '\\n')\n"
        "fetch = ['-c','credential.https://github.com.helper=','-c','credential.https://github.com.helper=!gh auth git-credential','fetch','--no-tags','--no-recurse-submodules','--no-write-fetch-head','origin','refs/heads/main:refs/remotes/origin/main']\n"
        "if args == ['symbolic-ref','--quiet','--short','HEAD']:\n    print('main')\n"
        "elif args == ['status','--porcelain=v1','--untracked-files=all']:\n    pass\n"
        "elif args == fetch:\n    pass\n"
        "elif args == ['rev-parse','--verify','HEAD']:\n    print(SHA)\n"
        "elif args == ['rev-parse','--verify','refs/remotes/origin/main']:\n    print(SHA)\n"
        "elif args == ['merge-base','--is-ancestor',SHA,SHA]:\n    pass\n"
        "elif args == ['merge','--ff-only','refs/remotes/origin/main']:\n    pass\n"
        "else:\n    print('unexpected git command: ' + repr(args), file=sys.stderr); raise SystemExit(99)\n",
        encoding="utf-8",
    )
    (fake_bin / "git.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0git_fake.py" %*\nexit /b %ERRORLEVEL%\n',
        encoding="utf-8",
    )
    gh_fake = fake_bin / "gh_fake.py"
    gh_fake.write_text(
        "import os, sys\nfrom pathlib import Path\nargs = sys.argv[1:]\n"
        "with Path(os.environ['KIS_TEST_GH_LOG']).open('a', encoding='utf-8') as handle:\n"
        "    handle.write('|'.join(args) + '\\n')\n"
        "expected = ['auth','status','--active','--hostname','github.com']\n"
        "if args != expected:\n    print('unexpected gh command: ' + repr(args), file=sys.stderr); raise SystemExit(99)\n",
        encoding="utf-8",
    )
    (fake_bin / "gh.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0gh_fake.py" %*\nexit /b %ERRORLEVEL%\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    env["KIS_TEST_ATTEMPTS"] = str(attempts)
    env["KIS_TEST_GIT_LOG"] = str(git_log)
    env["KIS_TEST_GH_LOG"] = str(gh_log)

    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(scripts / source.name),
         "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
         "-StateRoot", str(state_root), "-Worker", "-DelaySeconds", "0"],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert attempts.read_text(encoding="utf-8") == "2"
    receipt = state_root / "runtime" / "kis-dev" / "state" / "post-land-restart" / "latest.json"
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    assert evidence["state"] == "ready"
    assert evidence["landed_sha"] == SHA
    assert evidence["launched_sha"] == SHA


def test_worker_still_rejects_governed_primary_dirt(tmp_path: Path) -> None:
    root = tmp_path / "governed-dirty"
    scripts = root / "scripts"
    settings = root / "settings"
    fake_bin = root / "bin"
    state_root = root / "state"
    for path in (scripts, settings, fake_bin, state_root):
        path.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    (scripts / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text(
        json.dumps({"github_cli": {"config_dir": str(root / "gh")}}), encoding="utf-8"
    )
    git_fake = fake_bin / "git_fake.py"
    git_fake.write_text(
        "import sys\nargs = sys.argv[1:]\n"
        "if args == ['symbolic-ref','--quiet','--short','HEAD']:\n    print('main')\n"
        "elif args == ['status','--porcelain=v1','--untracked-files=all']:\n    print('?? governed-source.txt')\n"
        "else:\n    raise SystemExit(99)\n",
        encoding="utf-8",
    )
    (fake_bin / "git.cmd").write_text(
        f'@echo off\n"{sys.executable}" "%~dp0git_fake.py" %*\nexit /b %ERRORLEVEL%\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(scripts / source.name),
         "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
         "-StateRoot", str(state_root), "-Worker", "-DelaySeconds", "0"],
        cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode != 0
    assert "POST_LAND_RESTART_PRIMARY_DIRTY" in result.stderr
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "failed"
    assert receipt["detail"] == "POST_LAND_RESTART_PRIMARY_DIRTY"


def test_unexpected_hook_failure_recorder_retains_bounded_evidence(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_root.mkdir()

    record_kis_dev_post_land_restart_failure(
        state_root, SHA, "unexpected hook failure"
    )

    receipt_path = (
        state_root / "runtime" / "kis-dev" / "state" /
        "post-land-restart" / "latest.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == SHA
    assert receipt["detail"] == "unexpected hook failure"


def test_failure_recorder_logs_fallback_when_receipt_storage_is_unavailable(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    blocked_state_root = tmp_path / "blocked-state-root"
    blocked_state_root.write_text("not a directory", encoding="utf-8")
    record_kis_dev_post_land_restart_failure(
        blocked_state_root, SHA, "storage unavailable"
    )

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "post-land restart failure evidence fallback" in message
        and SHA in message
        and "storage unavailable" in message
        for message in messages
    )


def test_worker_receipt_failure_uses_repo_recovery_fallback(tmp_path: Path) -> None:
    root = tmp_path / "worker-receipt-failure"
    scripts = root / "scripts"
    settings = root / "settings"
    scripts.mkdir(parents=True)
    settings.mkdir()
    source = Path(__file__).parents[2] / "scripts" / "restart-kis-dev-after-land.ps1"
    worker_script = scripts / source.name
    worker_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    blocked_state_root = root / "blocked-state-root"
    blocked_state_root.write_text("not a directory", encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text(
        json.dumps({"paths": {"state_root": str(blocked_state_root)}}), encoding="utf-8"
    )
    fallback = root / ".temp" / "kis" / "post-land-restart-fallback.json"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("x" * 100_000, encoding="utf-8")

    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-File", str(worker_script),
         "-ExpectedLandedSha", SHA, "-RepositoryRoot", str(root),
         "-StateRoot", str(blocked_state_root), "-Worker", "-DelaySeconds", "0"],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )

    assert result.returncode != 0
    evidence = json.loads(fallback.read_text(encoding="utf-8"))
    assert evidence["state"] == "synchronizing"
    assert evidence["landed_sha"] == SHA
    assert evidence["launched_sha"] == ""
    assert evidence["receipt_error"]
    assert fallback.stat().st_size < 10_000


def test_dispatcher_records_missing_landed_identity(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    dispatch_kis_dev_post_land_restart(
        "kis-mcp", tmp_path, "main", None, state_root=state_root
    )
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == "unknown"
    assert receipt["detail"] == "POST_LAND_LANDED_IDENTITY_UNVERIFIABLE"


def test_dispatcher_contains_scheduler_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "state"
    monkeypatch.setattr(
        "kis_mcp.post_land_restart.schedule_kis_dev_post_land_restart",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    dispatch_kis_dev_post_land_restart(
        "kis-mcp", tmp_path, "main", SHA, state_root=state_root
    )
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == SHA
    assert "POST_LAND_HOOK_UNEXPECTED: RuntimeError: boom" in receipt["detail"]


def test_dispatcher_preserves_specific_scheduler_failure_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "restart-kis-dev-after-land.ps1").write_text("test", encoding="utf-8")
    state_root = tmp_path / "state"
    monkeypatch.setattr(
        "kis_mcp.post_land_restart.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=7, stdout="", stderr="specific scheduler stderr"
        ),
    )

    dispatch_kis_dev_post_land_restart(
        "kis-mcp", tmp_path, "main", SHA, state_root=state_root
    )
    receipt = json.loads(
        (state_root / "runtime" / "kis-dev" / "state" /
         "post-land-restart" / "latest.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "failed"
    assert receipt["landed_sha"] == SHA
    assert receipt["detail"] == (
        "POST_LAND_RESTART_SCHEDULE_FAILED: specific scheduler stderr"
    )
    assert "POST_LAND_HOOK_UNEXPECTED" not in receipt["detail"]


def test_legacy_restart_receipt_is_retained_but_not_current(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    legacy = (
        state_root
        / "tunnel-client"
        / "runtime"
        / "development"
        / "post-land-restart"
        / "latest.json"
    )
    legacy.parent.mkdir(parents=True)
    legacy_payload = {"state": "legacy", "landed_sha": REMOTE_AFTER}
    legacy.write_text(json.dumps(legacy_payload), encoding="utf-8")

    record_kis_dev_post_land_restart_failure(state_root, SHA, "canonical failure")

    assert json.loads(legacy.read_text(encoding="utf-8")) == legacy_payload
    canonical = (
        state_root
        / "runtime"
        / "kis-dev"
        / "state"
        / "post-land-restart"
        / "latest.json"
    )
    evidence = json.loads(canonical.read_text(encoding="utf-8"))
    assert evidence["landed_sha"] == SHA
    assert evidence["detail"] == "canonical failure"


def test_restart_receipt_ownership_is_fixed_to_kis_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_root = tmp_path / "state"
    monkeypatch.setenv("KIS_MCP_RUNTIME_INSTANCE", "kis-op")

    record_kis_dev_post_land_restart_failure(state_root, SHA, "owned by kis-dev")

    canonical = (
        state_root
        / "runtime"
        / "kis-dev"
        / "state"
        / "post-land-restart"
        / "latest.json"
    )
    assert canonical.exists()
    assert not (state_root / "runtime" / "kis-op" / "state" / "post-land-restart").exists()


def test_repeated_restart_failure_recording_replaces_current_evidence(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    record_kis_dev_post_land_restart_failure(state_root, SHA, "first failure")
    record_kis_dev_post_land_restart_failure(state_root, REMOTE_AFTER, "second failure")

    receipt = json.loads(
        (
            state_root
            / "runtime"
            / "kis-dev"
            / "state"
            / "post-land-restart"
            / "latest.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["landed_sha"] == REMOTE_AFTER
    assert receipt["detail"] == "second failure"
