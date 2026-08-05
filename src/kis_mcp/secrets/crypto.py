from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from .contracts import KdfParameters, VaultEnvelope
from .errors import VaultIntegrityError


_SALT_BYTES = 16
_NONCE_BYTES = 12
_KEY_BYTES = 32


def _require_key(key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) != _KEY_BYTES:
        raise ValueError("KIS_MCP_SECRET_KEY_INVALID")
    return key


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode(value: str, *, expected_length: int | None = None) -> bytes:
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED") from exc
    if expected_length is not None and len(decoded) != expected_length:
        raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
    return decoded


def _associated_data(
    *,
    version: int,
    cipher: str,
    kdf: str,
    parameters: KdfParameters,
    salt: str,
    nonce: str,
) -> bytes:
    header: dict[str, Any] = {
        "version": version,
        "cipher": cipher,
        "kdf": kdf,
        "kdf_parameters": parameters.to_dict(),
        "salt": salt,
        "nonce": nonce,
    }
    return json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")


def derive_key(passphrase: bytes, salt: bytes, parameters: KdfParameters) -> bytes:
    if not isinstance(passphrase, bytes) or not passphrase:
        raise ValueError("KIS_MCP_SECRET_PASSPHRASE_INVALID")
    if not isinstance(salt, bytes) or len(salt) != _SALT_BYTES:
        raise ValueError("KIS_MCP_SECRET_SALT_INVALID")
    return Argon2id(
        salt=salt,
        length=parameters.length,
        iterations=parameters.iterations,
        lanes=parameters.lanes,
        memory_cost=parameters.memory_cost_kib,
    ).derive(passphrase)


def derive_key_from_envelope(passphrase: bytes, envelope: VaultEnvelope) -> bytes:
    salt = _decode(envelope.salt, expected_length=_SALT_BYTES)
    return derive_key(passphrase, salt, envelope.kdf_parameters)


def encrypt_payload(
    plaintext: bytes,
    key: bytes,
    *,
    salt: bytes,
    parameters: KdfParameters,
) -> VaultEnvelope:
    key = _require_key(key)
    if not isinstance(plaintext, bytes):
        raise TypeError("KIS_MCP_SECRET_PLAINTEXT_INVALID")
    if not isinstance(salt, bytes) or len(salt) != _SALT_BYTES:
        raise ValueError("KIS_MCP_SECRET_SALT_INVALID")

    nonce_bytes = os.urandom(_NONCE_BYTES)
    salt_text = _encode(salt)
    nonce_text = _encode(nonce_bytes)
    associated_data = _associated_data(
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        parameters=parameters,
        salt=salt_text,
        nonce=nonce_text,
    )
    ciphertext = AESGCM(key).encrypt(nonce_bytes, plaintext, associated_data)
    return VaultEnvelope(
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        kdf_parameters=parameters,
        salt=salt_text,
        nonce=nonce_text,
        ciphertext=_encode(ciphertext),
    )


def decrypt_payload(envelope: VaultEnvelope, key: bytes) -> bytes:
    key = _require_key(key)
    nonce = _decode(envelope.nonce, expected_length=_NONCE_BYTES)
    _decode(envelope.salt, expected_length=_SALT_BYTES)
    ciphertext = _decode(envelope.ciphertext)
    if len(ciphertext) < 16:
        raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
    associated_data = _associated_data(
        version=envelope.version,
        cipher=envelope.cipher,
        kdf=envelope.kdf,
        parameters=envelope.kdf_parameters,
        salt=envelope.salt,
        nonce=envelope.nonce,
    )
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, associated_data)
    except (InvalidTag, ValueError) as exc:
        raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED") from exc


def decode_bootstrap_key(value: str) -> bytes:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("KIS_MCP_SECRET_BOOTSTRAP_KEY_INVALID")
    try:
        decoded = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ValueError("KIS_MCP_SECRET_BOOTSTRAP_KEY_INVALID") from exc
    if len(decoded) != _KEY_BYTES or _encode(decoded) != value:
        raise ValueError("KIS_MCP_SECRET_BOOTSTRAP_KEY_INVALID")
    return decoded
