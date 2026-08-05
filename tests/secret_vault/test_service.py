from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from kis_mcp.secrets.contracts import KdfParameters
from kis_mcp.secrets.crypto import encrypt_payload
from kis_mcp.secrets.errors import (
    SecretNotFoundError,
    VaultIntegrityError,
    VaultLockedError,
)
from kis_mcp.secrets.service import SecretsService
from kis_mcp.secrets.vault import VaultStore


FAST_KDF = KdfParameters(iterations=1, memory_cost_kib=8192, lanes=1)
PASSPHRASE = "correct horse battery staple"
REFERENCE = "secret://providers/nvidia/api-key"
SECRET = "nvidia-secret-marker"


def _service(tmp_path: Path) -> SecretsService:
    return SecretsService(VaultStore(tmp_path / "secrets"), kdf_parameters=FAST_KDF)


def test_initialize_and_resolve_without_retaining_plaintext_payload(tmp_path: Path) -> None:
    service = _service(tmp_path)

    service.initialize(PASSPHRASE, {REFERENCE: SECRET})

    assert service.resolve(REFERENCE) == SECRET
    assert service.status().unlocked is True
    assert set(vars(service)) == {"_store", "_kdf_parameters", "_session_key", "_lock"}
    assert SECRET not in repr(vars(service))


def test_lock_zeroes_session_key_and_blocks_resolution(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    key_buffer = service._session_key
    assert key_buffer is not None and any(key_buffer)

    service.lock()

    assert service.status().unlocked is False
    assert bytes(key_buffer) == b"\x00" * 32
    with pytest.raises(VaultLockedError, match="KIS_MCP_SECRET_VAULT_LOCKED"):
        service.resolve(REFERENCE)


def test_unlock_rejects_wrong_passphrase_without_leaking_values(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    service.lock()

    with pytest.raises(VaultIntegrityError) as failure:
        service.unlock("wrong-passphrase-marker")

    text = str(failure.value)
    assert SECRET not in text
    assert "wrong-passphrase-marker" not in text
    assert service.status().unlocked is False


def test_unlock_restores_internal_resolution(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    service.lock()

    service.unlock(PASSPHRASE)

    assert service.resolve(REFERENCE) == SECRET


def test_metadata_references_are_available_while_locked(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    service.lock()

    records = service.list_references()

    assert [record.reference for record in records] == [REFERENCE]
    assert SECRET not in repr([record.to_dict() for record in records])


def test_missing_reference_raises_bounded_error(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})

    with pytest.raises(SecretNotFoundError, match="KIS_MCP_SECRET_NOT_FOUND") as failure:
        service.resolve("secret://providers/openai/api-key")

    assert SECRET not in str(failure.value)


def test_set_secret_reencrypts_and_preserves_backup(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    previous_vault = service._store.paths.vault.read_bytes()

    service.set_secret(REFERENCE, "replacement-secret-marker")

    assert service.resolve(REFERENCE) == "replacement-secret-marker"
    assert service.status().generation == 2
    backups = list(service._store.paths.backups.glob("vault-*.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == previous_vault
    assert "replacement-secret-marker" not in service._store.paths.vault.read_text("utf-8")
    assert "replacement-secret-marker" not in service._store.paths.metadata.read_text("utf-8")


def test_rotate_master_key_invalidates_old_passphrase(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})

    service.rotate_master_key("new-master-passphrase")
    service.lock()

    with pytest.raises(VaultIntegrityError):
        service.unlock(PASSPHRASE)
    service.unlock("new-master-passphrase")
    assert service.resolve(REFERENCE) == SECRET
    assert service.status().generation == 2


def test_bootstrap_key_can_initialize_and_unlock(tmp_path: Path) -> None:
    bootstrap_key = b"k" * 32
    service = _service(tmp_path)

    service.initialize_with_key(bootstrap_key, {REFERENCE: SECRET})
    service.lock()
    service.unlock_with_key(bootstrap_key)

    assert service.resolve(REFERENCE) == SECRET


def test_initialize_rejects_invalid_reference_before_writing(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(Exception, match="KIS_MCP_SECRET_REFERENCE_INVALID"):
        service.initialize(PASSPHRASE, {"../bad": SECRET})

    assert not service._store.paths.vault.exists()


def test_partial_vault_state_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service._store.root.mkdir(parents=True)
    service._store.paths.vault.write_text("{}", encoding="utf-8")

    with pytest.raises(
        VaultIntegrityError,
        match="KIS_MCP_SECRET_VAULT_STATE_INCOMPLETE",
    ):
        service.status()


def test_tampered_metadata_reference_fails_as_integrity_error(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    metadata = service._store.load_metadata().to_dict()
    metadata["references"][0]["reference"] = "../bad"
    service._store.paths.metadata.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(
        VaultIntegrityError,
        match="KIS_MCP_SECRET_METADATA_INTEGRITY_FAILED",
    ):
        service.list_references()


def test_tampered_decrypted_reference_fails_as_integrity_error(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize(PASSPHRASE, {REFERENCE: SECRET})
    envelope = service._store.load_envelope()
    salt = base64.b64decode(envelope.salt)
    tampered = encrypt_payload(
        json.dumps(
            {"version": 1, "secrets": {"../bad": SECRET}},
            separators=(",", ":"),
        ).encode("utf-8"),
        service._session_key_bytes(),
        salt=salt,
        parameters=envelope.kdf_parameters,
    )
    service._store.replace(tampered, service._store.load_metadata())

    with pytest.raises(
        VaultIntegrityError,
        match="KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED",
    ):
        service.resolve(REFERENCE)
