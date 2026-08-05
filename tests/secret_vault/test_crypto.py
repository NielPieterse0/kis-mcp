from __future__ import annotations

import base64

import pytest

from kis_mcp.secrets.contracts import KdfParameters, VaultEnvelope
from kis_mcp.secrets.crypto import (
    decode_bootstrap_key,
    derive_key,
    derive_key_from_envelope,
    encrypt_payload,
    decrypt_payload,
)
from kis_mcp.secrets.errors import VaultIntegrityError


PASSPHRASE = b"correct horse battery staple"


def _encrypted(plaintext: bytes = b'{"secrets":{}}') -> tuple[VaultEnvelope, bytes]:
    salt = b"0123456789abcdef"
    key = derive_key(PASSPHRASE, salt, KdfParameters())
    return encrypt_payload(plaintext, key, salt=salt, parameters=KdfParameters()), key


def test_argon2id_derives_stable_256_bit_key() -> None:
    salt = b"0123456789abcdef"

    first = derive_key(PASSPHRASE, salt, KdfParameters())
    second = derive_key(PASSPHRASE, salt, KdfParameters())

    assert first == second
    assert len(first) == 32
    assert first != derive_key(PASSPHRASE, b"fedcba9876543210", KdfParameters())


def test_encrypt_decrypt_round_trip() -> None:
    envelope, key = _encrypted(b"sensitive payload")

    assert decrypt_payload(envelope, key) == b"sensitive payload"
    assert derive_key_from_envelope(PASSPHRASE, envelope) == key


def test_encryption_uses_fresh_nonce() -> None:
    first, key = _encrypted(b"same")
    second = encrypt_payload(
        b"same",
        key,
        salt=base64.b64decode(first.salt),
        parameters=first.kdf_parameters,
    )

    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize("key", [b"", b"short", b"x" * 31, b"x" * 33])
def test_encryption_rejects_non_256_bit_keys(key: bytes) -> None:
    with pytest.raises(ValueError, match="KIS_MCP_SECRET_KEY_INVALID"):
        encrypt_payload(b"payload", key, salt=b"0123456789abcdef", parameters=KdfParameters())


def test_wrong_key_fails_closed_without_plaintext() -> None:
    envelope, _ = _encrypted(b"top-secret-marker")

    with pytest.raises(VaultIntegrityError) as failure:
        decrypt_payload(envelope, b"z" * 32)

    assert "top-secret-marker" not in str(failure.value)


def test_tampered_ciphertext_fails_closed() -> None:
    envelope, key = _encrypted()
    tampered = VaultEnvelope.from_dict(
        {**envelope.to_dict(), "ciphertext": base64.b64encode(b"tampered").decode("ascii")}
    )

    with pytest.raises(VaultIntegrityError, match="KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"):
        decrypt_payload(tampered, key)


def test_authenticated_header_tampering_fails_closed() -> None:
    envelope, key = _encrypted()
    parameters = envelope.kdf_parameters.to_dict()
    parameters["iterations"] += 1
    tampered = VaultEnvelope.from_dict(
        {**envelope.to_dict(), "kdf_parameters": parameters}
    )

    with pytest.raises(VaultIntegrityError, match="KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"):
        decrypt_payload(tampered, key)


def test_bootstrap_key_requires_canonical_base64_32_bytes() -> None:
    encoded = base64.b64encode(b"k" * 32).decode("ascii")

    assert decode_bootstrap_key(encoded) == b"k" * 32
    for invalid in ("", "not-base64", base64.b64encode(b"short").decode("ascii")):
        with pytest.raises(ValueError, match="KIS_MCP_SECRET_BOOTSTRAP_KEY_INVALID"):
            decode_bootstrap_key(invalid)
