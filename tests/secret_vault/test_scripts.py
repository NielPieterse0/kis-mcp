from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_secret_settings_define_only_metadata_and_approved_modes() -> None:
    settings = json.loads(
        (ROOT / "settings" / "secrets.settings.json").read_text(encoding="utf-8")
    )

    assert settings["root"] == r"C:\Projects\.kis-mcp\secrets"
    assert settings["bootstrap_environment"] == "KIS_MCP_VAULT_KEY"
    assert settings["interactive_unlock"] is True
    assert settings["self_unlocking_key_file"] is False
    assert settings["runtime_unlock"]["mode"] == "windows-credential"
    assert settings["runtime_unlock"]["target"] == "kis-mcp/secrets/runtime-unlock"
    assert settings["cipher"] == "AES-256-GCM"
    assert settings["kdf"] == "argon2id"
    serialized = json.dumps(settings).casefold()
    assert "passphrase" not in serialized
    assert "secret://" not in serialized
    assert "master.key" not in serialized


def test_common_script_transfers_sensitive_payload_only_over_standard_input() -> None:
    content = _script("secret-vault.ps1")

    assert "Read-Host" in content
    assert "-AsSecureString" in content
    assert "RedirectStandardInput" in content
    assert "AnonymousPipeServerStream" in content
    assert "ConvertTo-Json" in content
    assert "ZeroFreeBSTR" in content
    assert "bootstrap_environment" in content
    assert "KIS_MCP_SECRET_INPUT_PIPE_HANDLE" in content
    assert "ArgumentList" in content
    assert "$Process.Kill()" in content
    assert "--passphrase" not in content
    assert "--secret" not in content
    assert "master.key" not in content


def test_operator_scripts_use_common_secure_boundary() -> None:
    for name in (
        "initialize-secret-vault.ps1",
        "set-secret.ps1",
        "rotate-secret.ps1",
        "unlock-secrets.ps1",
    ):
        content = _script(name)
        assert "secret-vault.ps1" in content
        assert "Invoke-KisMcpSecretCommand" in content

    for name in ("set-secret.ps1", "unlock-secrets.ps1"):
        content = _script(name)
        assert "windows-credential.ps1" not in content
        assert "Set-KisMcpWindowsCredential" not in content
        assert "Get-KisMcpWindowsCredential" not in content

    for name in ("initialize-secret-vault.ps1", "rotate-secret.ps1"):
        content = _script(name)
        assert "windows-credential.ps1" in content
        assert "Set-KisMcpWindowsCredential" in content

    assert "-AsSecureString" in _script("set-secret.ps1")
    assert "-AsSecureString" in _script("rotate-secret.ps1")
    assert "resolve-internal" not in _script("unlock-secrets.ps1")


def test_runtime_unlock_migration_verifies_before_windows_credential_write() -> None:
    content = _script("configure-secret-runtime-unlock.ps1")

    verify = content.index("@('verify-unlock')")
    credential_write = content.index("Set-KisMcpWindowsCredential")
    assert "Get-KisMcpUnlockPayload" in content
    assert "Get-KisMcpRuntimeUnlockCredentialTarget" in content
    assert verify < credential_write


def test_vault_rotation_updates_runtime_unlock_only_after_success() -> None:
    content = _script("rotate-secret.ps1")

    rotation = content.index("@('rotate')")
    credential_write = content.index("Set-KisMcpWindowsCredential")
    assert rotation < credential_write
    assert "-Secret $NewUnlock" in content


def test_post_rotation_credential_failure_reports_recovery_path() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        return
    command = (
        f". '{SCRIPTS / 'secret-vault.ps1'}'; "
        "Invoke-KisMcpPostRotationRuntimeCredentialUpdate -Action { throw 'simulated' }"
    )

    completed = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "KIS_MCP_ROTATION_RUNTIME_CREDENTIAL_UPDATE_FAILED" in completed.stderr
    assert "configure-secret-runtime-unlock.ps1" in completed.stderr
    assert "simulated" not in completed.stderr


def test_local_launcher_does_not_unlock_or_launch_through_secret_vault() -> None:
    content = _script("start.ps1")

    assert "kis_mcp.server" in content
    assert "kis_mcp.secrets.launcher" not in content
    assert "KIS_MCP_SECRET_INPUT_PIPE_HANDLE" not in content
    assert "Start-KisMcpSecretAwareProcess" not in content
    assert "Read-Host 'Unlock kis-mcp secrets'" not in content
    assert "KIS_MCP_VAULT_PASSPHRASE" not in content
    assert "--passphrase" not in content


def test_local_launcher_validates_before_direct_runtime_start() -> None:
    content = _script("start.ps1")

    validation = content.index("load_runtime_config(Path.cwd())")
    process_start = content.index("$Process = [System.Diagnostics.Process]::new()")

    assert validation < process_start
