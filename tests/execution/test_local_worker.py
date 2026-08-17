from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from kis_mcp.execution.worker import WORKER_RESULT_NAME


def _process_alive(pid: int) -> bool:
    if sys.platform != "win32":
        return False
    synchronize = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        return False
    try:
        return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 0x00000102
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def test_worker_result_name_is_fixed() -> None:
    assert WORKER_RESULT_NAME == "worker-result.json"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object proof")
def test_worker_timeout_terminates_complete_spawned_process_tree(tmp_path: Path) -> None:
    state = tmp_path / "run"
    state.mkdir()
    pids = state / "pids.txt"
    worker = Path(__file__).resolve().parents[2] / "src" / "kis_mcp" / "execution" / "worker.py"
    child_code = (
        "import os,pathlib,subprocess,sys,time;"
        "g=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']);"
        f"pathlib.Path({str(pids)!r}).write_text(f'{{os.getpid()}} {{g.pid}}');"
        "time.sleep(30)"
    )
    completed = subprocess.run(
        [
            sys.executable, str(worker), "--state-dir", str(state),
            "--cwd", str(tmp_path), "--timeout-ms", "500",
            "--parent-pid", str(os.getpid()), "--",
            sys.executable, "-c", child_code,
        ],
        capture_output=True, text=True, timeout=10, check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads((state / WORKER_RESULT_NAME).read_text(encoding="utf-8"))
    assert result["status"] == "timeout"
    assert result["job_assigned"] is True
    child_pid, grandchild_pid = (int(value) for value in pids.read_text().split())
    time.sleep(0.2)
    assert not _process_alive(child_pid)
    assert not _process_alive(grandchild_pid)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object proof")
def test_worker_parent_loss_terminates_complete_spawned_process_tree(tmp_path: Path) -> None:
    state = tmp_path / "parent-loss"
    state.mkdir()
    pids = state / "pids.txt"
    worker = Path(__file__).resolve().parents[2] / "src" / "kis_mcp" / "execution" / "worker.py"
    child_code = (
        "import os,pathlib,subprocess,sys,time;"
        "g=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']);"
        f"pathlib.Path({str(pids)!r}).write_text(f'{{os.getpid()}} {{g.pid}}');"
        "time.sleep(30)"
    )
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
    try:
        completed = subprocess.run(
            [
                sys.executable, str(worker), "--state-dir", str(state),
                "--cwd", str(tmp_path), "--timeout-ms", "30000",
                "--parent-pid", str(parent.pid), "--",
                sys.executable, "-c", child_code,
            ],
            capture_output=True, text=True, timeout=10, check=False,
        )
    finally:
        parent.wait(timeout=5)

    assert completed.returncode == 0, completed.stderr
    result = json.loads((state / WORKER_RESULT_NAME).read_text(encoding="utf-8"))
    assert result["status"] == "parent_lost"
    child_pid, grandchild_pid = (int(value) for value in pids.read_text().split())
    time.sleep(0.2)
    assert not _process_alive(child_pid)
    assert not _process_alive(grandchild_pid)
