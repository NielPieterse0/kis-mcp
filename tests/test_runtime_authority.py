from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings" / "runtime-authority.settings.json"
SCRIPTS = ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_runtime_authority_declares_shared_signed_hosts_and_separate_native_helpers() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["python"]["ownership"] == "shared_system"
    assert data["python"]["authenticode_status"] == "Valid"
    assert data["python"]["publisher_subject_contains"] == "Python Software Foundation"
    assert data["python"]["uv_managed_python"] == "disabled"
    assert data["uv"]["acquisition_policy"] == "authoritative_source_required"
    assert data["node"]["ownership"] == "shared_system"
    assert data["node"]["native_helpers_policy"] == "separate_artifact_verification"


def test_bootstrap_forbids_uv_managed_python_and_quarantines_incompatible_env() -> None:
    content = _script("bootstrap-python.ps1")

    assert "Resolve-KisMcpSystemPython" in content
    assert "$env:UV_PYTHON_PREFERENCE" not in content
    assert "$env:UV_NO_MANAGED_PYTHON = '1'" in content
    assert "--no-managed-python" in content
    assert "--python $PythonRuntime.executable" in content
    assert "Move-Item -LiteralPath $PythonEnvironmentRoot" in content
    assert '"quarantine\\$OperationId"' in content


def test_serena_builds_venv_from_verified_system_python_and_records_provenance() -> None:
    content = _script("install-serena.ps1")

    assert "Resolve-KisMcpSystemPython" in content
    assert "& $PythonRuntime.executable -m pip download" in content
    assert "& $PythonRuntime.executable -m venv $CandidateVenv" in content
    assert "$PythonLauncher.Source -3.11" not in content
    assert content.count("host_python = [ordered]@{") == 2


def test_runtime_authority_resolves_current_signed_python_and_node() -> None:
    script = (SCRIPTS / "runtime-authority.ps1").as_posix()
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f". '{script}'; $a=Get-KisMcpRuntimeAuthority; $p=Resolve-KisMcpSystemPython $a; $n=Resolve-KisMcpNodeRuntime $a; Write-Output \"$($p.signature_status)|$($p.version)|$($n.signature_status)\""],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Valid|3.11|Valid"
