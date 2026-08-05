from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.secrets.contracts import (
    KdfParameters,
    SecretReferenceRecord,
    VaultEnvelope,
    VaultMetadata,
)
from kis_mcp.secrets.errors import (
    VaultAlreadyInitializedError,
    VaultIntegrityError,
    VaultNotInitializedError,
)
from kis_mcp.secrets.vault import VaultStore


def _envelope(marker: str = "Y2lwaGVydGV4dA==") -> VaultEnvelope:
    return VaultEnvelope(
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        kdf_parameters=KdfParameters(),
        salt="MDEyMzQ1Njc4OWFiY2RlZg==",
        nonce="MDEyMzQ1Njc4OWFi",
        ciphertext=marker,
    )


def _metadata(generation: int = 1) -> VaultMetadata:
    return VaultMetadata(
        schema_version=1,
        generation=generation,
        created_at="2026-08-05T01:00:00Z",
        updated_at=f"2026-08-05T0{generation}:00:00Z",
        references=(
            SecretReferenceRecord(
                reference="secret://providers/nvidia/api-key",
                updated_at=f"2026-08-05T0{generation}:00:00Z",
            ),
        ),
    )


def test_vault_store_requires_absolute_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="KIS_MCP_SECRET_ROOT_INVALID"):
        VaultStore(Path("relative/secrets"))

    assert VaultStore(tmp_path).root == tmp_path.resolve()


def test_initialize_creates_encrypted_state_and_metadata(tmp_path: Path) -> None:
    store = VaultStore(tmp_path / "secrets")

    store.initialize(_envelope(), _metadata())

    assert store.paths.vault.is_file()
    assert store.paths.metadata.is_file()
    assert store.paths.backups.is_dir()
    assert store.load_envelope() == _envelope()
    assert store.load_metadata() == _metadata()
    combined = store.paths.vault.read_text("utf-8") + store.paths.metadata.read_text("utf-8")
    assert "plaintext-secret-marker" not in combined
    assert not list(store.root.glob("*.tmp"))


def test_initialize_refuses_to_replace_existing_vault(tmp_path: Path) -> None:
    store = VaultStore(tmp_path / "secrets")
    store.initialize(_envelope(), _metadata())

    with pytest.raises(VaultAlreadyInitializedError, match="KIS_MCP_SECRET_VAULT_ALREADY_INITIALIZED"):
        store.initialize(_envelope("bmV3"), _metadata(2))


def test_uninitialized_load_fails_with_bounded_error(tmp_path: Path) -> None:
    store = VaultStore(tmp_path / "secrets")

    with pytest.raises(VaultNotInitializedError, match="KIS_MCP_SECRET_VAULT_NOT_INITIALIZED"):
        store.load_envelope()


def test_malformed_or_unknown_envelope_fails_closed(tmp_path: Path) -> None:
    store = VaultStore(tmp_path / "secrets")
    store.root.mkdir(parents=True)
    store.paths.vault.write_text('{"version": 99}', encoding="utf-8")
    store.paths.metadata.write_text(json.dumps(_metadata().to_dict()), encoding="utf-8")

    with pytest.raises(VaultIntegrityError, match="KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"):
        store.load_envelope()


def test_replace_preserves_prior_encrypted_vault_backup(tmp_path: Path) -> None:
    store = VaultStore(tmp_path / "secrets")
    original = _envelope()
    replacement = _envelope("cmVwbGFjZW1lbnQ=")
    store.initialize(original, _metadata())

    backup = store.replace(replacement, _metadata(2))

    assert store.load_envelope() == replacement
    assert store.load_metadata().generation == 2
    assert backup.parent == store.paths.backups
    assert VaultEnvelope.from_dict(json.loads(backup.read_text("utf-8"))) == original
    assert backup.is_file()
