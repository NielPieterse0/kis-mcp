from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    scripts = root / "scripts"
    settings = root / "settings"
    state = tmp_path / "state"
    scripts.mkdir(parents=True)
    settings.mkdir()
    state.mkdir()
    source = Path(__file__).parents[1] / "scripts" / "recover-chatgpt.ps1"
    (scripts / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (settings / "kis-mcp.settings.json").write_text(json.dumps({
        "paths": {"state_root": str(state)},
        "remote_mcp": {
            "host": "127.0.0.1", "path": "/mcp", "active_instance": "operation",
            "instances": {
                "operation": {"port": 18010, "app_name": "kis-op"},
                "development": {"port": 18011, "app_name": "kis-dev"},
            },
        },
    }), encoding="utf-8")
    return root, state


def test_recovery_selects_only_requested_instance(tmp_path: Path) -> None:
    root, state = _repo(tmp_path)
    target = tmp_path / "target.txt"
    (root / "scripts" / "start-chatgpt.ps1").write_text(
        "param([string]$Instance)\n[IO.File]::WriteAllText($env:KIS_TEST_TARGET,$Instance)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_TEST_TARGET"] = str(target)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
        "-Instance", "kis-op", "-Foreground", "-WaitSeconds", "0",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "kis-op"
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["instance"] == "operation"
    assert payload["app"] == "kis-op"
    assert not (state / "runtime" / "kis-dev" / "state" / "recovery").exists()


def test_compatibility_wrappers_delegate_to_general_recovery() -> None:
    scripts = Path(__file__).parents[1] / "scripts"
    dev = (scripts / "recover-kis-dev.ps1").read_text(encoding="utf-8")
    op = (scripts / "recover-kis-op.ps1").read_text(encoding="utf-8")
    recovery = (scripts / "recover-chatgpt.ps1").read_text(encoding="utf-8")
    assert "recover-chatgpt.ps1" in dev
    assert "Instance = 'kis-dev'" in dev
    assert "recover-chatgpt.ps1" in op
    assert "Instance = 'kis-op'" in op
    assert '-NoProfile -WindowStyle Hidden -File' in recovery


def test_health_recovery_suppresses_replacement_when_local_server_is_responsive(tmp_path: Path) -> None:
    root, state = _repo(tmp_path)
    marker = tmp_path / "launched.txt"
    server_script = tmp_path / "mcp_server.py"
    server_script.write_text(
        "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
        "import json, os\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        "    def do_POST(self):\n"
        "        length = int(self.headers.get('Content-Length', '0'))\n"
        "        self.rfile.read(length)\n"
        "        body = json.dumps({'jsonrpc':'2.0','id':1,'result':{'serverInfo':{'name':'test','version':'1'}}}).encode()\n"
        "        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)\n"
        "    def log_message(self, format, *args): pass\n"
        "HTTPServer(('127.0.0.1', int(os.environ['KIS_TEST_PORT'])), Handler).serve_forever()\n",
        encoding="utf-8",
    )
    port = 18010
    env = dict(os.environ)
    env["KIS_TEST_PORT"] = str(port)
    server = subprocess.Popen([sys.executable, str(server_script)], env=env)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
        runtime = state / "tunnel-client" / "runtime" / "operation"
        runtime.mkdir(parents=True)
        (runtime / "current.json").write_text(json.dumps({
            "lifecycle": "ready", "run_id": "run-a", "instance": "operation", "app": "kis-op",
            "endpoint": f"http://127.0.0.1:{port}/mcp", "launcher_pid": server.pid,
            "server_pid": server.pid, "server_listener_pid": server.pid, "tunnel_pid": 999993,
        }), encoding="utf-8")
        (root / "scripts" / "start-chatgpt.ps1").write_text(
            "param([string]$Instance)\n[IO.File]::WriteAllText($env:KIS_TEST_TARGET,$Instance)\n",
            encoding="utf-8",
        )
        env["KIS_TEST_TARGET"] = str(marker)
        result = subprocess.run([
            "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
            "-Instance", "kis-op", "-ExpectedRunId", "run-a", "-WaitSeconds", "0",
        ], cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False)
        assert result.returncode == 0, result.stderr
        assert not marker.exists()
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["state"] == "degraded"
        assert "replacement suppressed" in payload["detail"]
    finally:
        server.terminate()
        server.wait(timeout=10)


def test_recovery_read_is_bounded_and_does_not_launch(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    marker = root / "AGENTS.md"
    marker.write_text("authority", encoding="utf-8")
    (root / "scripts" / "start-chatgpt.ps1").write_text("throw 'must not launch'", encoding="utf-8")
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
        "-Instance", "kis-dev", "-ReadPath", "AGENTS.md",
    ], cwd=root, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["state"] == "read"
    assert payload["app"] == "kis-dev"
    assert payload["content"] == "authority"


def test_invalid_instance_fails_without_peer_fallback(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
        "-Instance", "other", "-WaitSeconds", "0",
    ], cwd=root, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode != 0
    assert "KIS_MCP_RECOVERY_INSTANCE_INVALID" in result.stderr


def test_malformed_current_pid_is_treated_as_unhealthy(tmp_path: Path) -> None:
    root, state = _repo(tmp_path)
    runtime = state / "tunnel-client" / "runtime" / "operation"
    runtime.mkdir(parents=True)
    (runtime / "current.json").write_text(json.dumps({
        "lifecycle": "ready", "run_id": "bad-run", "instance": "operation",
        "app": "kis-op", "endpoint": "http://127.0.0.1:18010/mcp",
        "launcher_pid": "not-a-pid", "server_pid": 1, "tunnel_pid": 1,
    }), encoding="utf-8")
    target = tmp_path / "target.txt"
    (root / "scripts" / "start-chatgpt.ps1").write_text(
        "param([string]$Instance)\n[IO.File]::WriteAllText($env:KIS_TEST_TARGET,$Instance)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_TEST_TARGET"] = str(target)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
        "-Instance", "kis-op", "-Foreground", "-WaitSeconds", "0",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "kis-op"


@pytest.mark.parametrize("missing", ["lifecycle", "instance", "app", "endpoint", "run_id"])
def test_missing_current_identity_is_treated_as_unhealthy(tmp_path: Path, missing: str) -> None:
    root, state = _repo(tmp_path)
    runtime = state / "tunnel-client" / "runtime" / "operation"
    runtime.mkdir(parents=True)
    current = {
        "lifecycle": "ready", "run_id": "run-a", "instance": "operation", "app": "kis-op",
        "endpoint": "http://127.0.0.1:18010/mcp", "launcher_pid": 1, "server_pid": 1, "tunnel_pid": 1,
    }
    current.pop(missing)
    (runtime / "current.json").write_text(json.dumps(current), encoding="utf-8")
    target = tmp_path / "target.txt"
    (root / "scripts" / "start-chatgpt.ps1").write_text(
        "param([string]$Instance)\n[IO.File]::WriteAllText($env:KIS_TEST_TARGET,$Instance)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["KIS_TEST_TARGET"] = str(target)
    result = subprocess.run([
        "pwsh.exe", "-NoProfile", "-File", str(root / "scripts" / "recover-chatgpt.ps1"),
        "-Instance", "kis-op", "-Foreground", "-WaitSeconds", "0",
    ], cwd=root, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") == "kis-op"
