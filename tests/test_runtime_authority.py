from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings" / "runtime-authority.settings.json"
SCRIPTS = ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_runtime_authority_pins_signed_python_inside_project_boundary() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert data["schema_version"] == 2
    assert data["project_boundary"] == r"C:\Projects"
    assert data["python"]["ownership"] == "project_managed"
    assert data["python"]["executable"] == r"C:\Projects\.tools\python\3.11.9\python.exe"
    assert data["python"]["version"] == "3.11.9"
    assert data["python"]["authenticode_status"] == "Valid"
    assert data["python"]["publisher_subject_contains"] == "Python Software Foundation"
    assert data["python"]["uv_managed_python"] == "disabled"
    assert data["uv"]["acquisition_policy"] == "authoritative_source_required"
    assert data["node"]["ownership"] == "shared_system"
    assert data["node"]["native_helpers_policy"] == "separate_artifact_verification"


def test_project_python_installer_is_pinned_signed_and_project_local() -> None:
    content = _script("install-project-python.ps1")

    assert "Authority.python.executable" in content
    assert "python.org/ftp/python/$Version/python-$Version-amd64.exe" in content
    assert "Get-AuthenticodeSignature" in content
    assert "publisher_subject_contains" in content
    assert "TargetDir=$PythonRoot" in content
    assert "Resolve-KisMcpProjectPython" in content


def test_bootstrap_forbids_uv_managed_python_and_quarantines_incompatible_env() -> None:
    content = _script("bootstrap-python.ps1")

    assert "Resolve-KisMcpProjectPython" in content
    assert "Assert-KisMcpProjectVenv" in content
    assert "$env:UV_PYTHON_PREFERENCE" not in content
    assert "$env:UV_NO_MANAGED_PYTHON = '1'" in content
    assert "--no-managed-python" in content
    assert "--python $PythonRuntime.executable" in content
    assert "Move-Item -LiteralPath $PythonEnvironmentRoot" in content
    assert '"quarantine\\$OperationId"' in content


def test_serena_builds_venv_from_verified_project_python_and_records_provenance() -> None:
    content = _script("install-serena.ps1")

    assert "Resolve-KisMcpProjectPython" in content
    assert content.count("Assert-KisMcpProjectVenv") >= 2
    assert "& $PythonRuntime.executable -m pip download" in content
    assert "& $PythonRuntime.executable -m venv $CandidateVenv" in content
    assert "$PythonLauncher.Source -3.11" not in content
    assert content.count("host_python = [ordered]@{") == 2


def test_runtime_authority_boundary_helper_rejects_user_profile_paths() -> None:
    script = (SCRIPTS / "runtime-authority.ps1").as_posix()
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f". '{script}'; Write-Output (Test-KisMcpPathWithinBoundary 'C:\\Projects\\.tools\\python\\3.11.9\\python.exe' 'C:\\Projects'); Write-Output (Test-KisMcpPathWithinBoundary 'C:\\Users\\operator\\Python\\python.exe' 'C:\\Projects')"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["True", "False"]


def test_runtime_authority_resolves_current_signed_project_python_and_node() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    if not Path(data["python"]["executable"]).is_file():
        pytest.skip("Pinned project Python is installed by the supervised operator bootstrap.")
    script = (SCRIPTS / "runtime-authority.ps1").as_posix()
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", f". '{script}'; $a=Get-KisMcpRuntimeAuthority; $p=Resolve-KisMcpProjectPython $a; $n=Resolve-KisMcpNodeRuntime $a; Write-Output \"$($p.signature_status)|$($p.full_version)|$($p.base_prefix)|$($n.signature_status)\""],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    fields = result.stdout.strip().split("|")
    assert fields[0] == "Valid"
    assert fields[1] == "3.11.9"
    assert fields[2].lower().startswith("c:\\projects\\")
    assert fields[3] == "Valid"
