from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .contracts import (
    KdfParameters,
    SecretReferenceRecord,
    SecretsStatus,
    VaultMetadata,
)
from .crypto import decrypt_payload, derive_key, derive_key_from_envelope, encrypt_payload
from .errors import (
    InvalidSecretReferenceError,
    SecretNotFoundError,
    VaultIntegrityError,
    VaultLockedError,
)
from .references import SecretReference
from .status import build_status
from .vault import VaultStore


_MAX_SECRET_VALUE_BYTES = 1024 * 1024


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _passphrase_bytes(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("KIS_MCP_SECRET_PASSPHRASE_INVALID")
    encoded = value.encode("utf-8")
    if len(encoded) > 16 * 1024:
        raise ValueError("KIS_MCP_SECRET_PASSPHRASE_INVALID")
    return encoded


def _bootstrap_bytes(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("KIS_MCP_SECRET_BOOTSTRAP_KEY_INVALID")
    return value


class SecretsService:
    def __init__(
        self,
        store: VaultStore,
        *,
        kdf_parameters: KdfParameters | None = None,
    ) -> None:
        self._store = store
        self._kdf_parameters = kdf_parameters or KdfParameters()
        self._session_key: bytearray | None = None
        self._lock = RLock()

    def initialize(
        self,
        passphrase: str,
        initial_secrets: Mapping[str, str] | None = None,
    ) -> None:
        material = _passphrase_bytes(passphrase)
        self._initialize(material, initial_secrets)

    def initialize_with_key(
        self,
        bootstrap_key: bytes,
        initial_secrets: Mapping[str, str] | None = None,
    ) -> None:
        self._initialize(_bootstrap_bytes(bootstrap_key), initial_secrets)

    def _initialize(
        self,
        unlock_material: bytes,
        initial_secrets: Mapping[str, str] | None,
    ) -> None:
        with self._lock:
            secrets = self._validated_secrets(initial_secrets or {})
            salt = os.urandom(16)
            key = derive_key(unlock_material, salt, self._kdf_parameters)
            now = _timestamp()
            metadata = VaultMetadata(
                schema_version=1,
                generation=1,
                created_at=now,
                updated_at=now,
                references=tuple(
                    SecretReferenceRecord(reference=uri, updated_at=now)
                    for uri in sorted(secrets)
                ),
            )
            envelope = encrypt_payload(
                self._serialize_payload(secrets),
                key,
                salt=salt,
                parameters=self._kdf_parameters,
            )
            self._store.initialize(envelope, metadata)
            self._replace_session_key(key)

    def unlock(self, passphrase: str) -> None:
        material = _passphrase_bytes(passphrase)
        self._unlock(material)

    def unlock_with_key(self, bootstrap_key: bytes) -> None:
        self._unlock(_bootstrap_bytes(bootstrap_key))

    def _unlock(self, unlock_material: bytes) -> None:
        with self._lock:
            self.lock()
            envelope = self._store.load_envelope()
            key = derive_key_from_envelope(unlock_material, envelope)
            self._decrypt_secrets_with_key(key, envelope=envelope)
            self._replace_session_key(key)

    def lock(self) -> None:
        with self._lock:
            if self._session_key is not None:
                for index in range(len(self._session_key)):
                    self._session_key[index] = 0
                self._session_key = None

    def status(self) -> SecretsStatus:
        with self._lock:
            if self._store.state_incomplete:
                raise VaultIntegrityError(
                    "KIS_MCP_SECRET_VAULT_STATE_INCOMPLETE"
                )
            if not self._store.initialized:
                return build_status(envelope=None, metadata=None, unlocked=False)
            envelope = self._store.load_envelope()
            metadata = self._store.load_metadata()
            return build_status(
                envelope=envelope,
                metadata=metadata,
                unlocked=self._session_key is not None,
            )

    def list_references(self) -> tuple[SecretReferenceRecord, ...]:
        with self._lock:
            metadata = self._store.load_metadata()
            try:
                for record in metadata.references:
                    SecretReference.parse(record.reference)
            except InvalidSecretReferenceError as exc:
                raise VaultIntegrityError(
                    "KIS_MCP_SECRET_METADATA_INTEGRITY_FAILED"
                ) from exc
            return metadata.references

    def resolve(self, reference: str) -> str:
        parsed = SecretReference.parse(reference)
        with self._lock:
            secrets = self._decrypt_secrets()
            try:
                return secrets[parsed.uri]
            except KeyError as exc:
                raise SecretNotFoundError(
                    f"KIS_MCP_SECRET_NOT_FOUND: {parsed.uri}"
                ) from exc

    def set_secret(self, reference: str, value: str) -> None:
        parsed = SecretReference.parse(reference)
        self._validate_secret_value(value)
        with self._lock:
            secrets = self._decrypt_secrets()
            metadata = self._store.load_metadata()
            envelope = self._store.load_envelope()
            secrets[parsed.uri] = value
            now = _timestamp()
            updated_by_reference = {
                record.reference: record.updated_at for record in metadata.references
            }
            updated_by_reference[parsed.uri] = now
            replacement_metadata = VaultMetadata(
                schema_version=1,
                generation=metadata.generation + 1,
                created_at=metadata.created_at,
                updated_at=now,
                references=tuple(
                    SecretReferenceRecord(
                        reference=uri,
                        updated_at=updated_by_reference[uri],
                    )
                    for uri in sorted(secrets)
                ),
            )
            salt = self._envelope_salt(envelope.salt)
            replacement = encrypt_payload(
                self._serialize_payload(secrets),
                self._session_key_bytes(),
                salt=salt,
                parameters=envelope.kdf_parameters,
            )
            self._store.replace(replacement, replacement_metadata)

    def rotate_master_key(self, new_passphrase: str) -> None:
        material = _passphrase_bytes(new_passphrase)
        with self._lock:
            secrets = self._decrypt_secrets()
            metadata = self._store.load_metadata()
            salt = os.urandom(16)
            key = derive_key(material, salt, self._kdf_parameters)
            now = _timestamp()
            replacement_metadata = VaultMetadata(
                schema_version=1,
                generation=metadata.generation + 1,
                created_at=metadata.created_at,
                updated_at=now,
                references=metadata.references,
            )
            replacement = encrypt_payload(
                self._serialize_payload(secrets),
                key,
                salt=salt,
                parameters=self._kdf_parameters,
            )
            self._store.replace(replacement, replacement_metadata)
            self._replace_session_key(key)

    def _validated_secrets(self, values: Mapping[str, str]) -> dict[str, str]:
        if not isinstance(values, Mapping):
            raise TypeError("KIS_MCP_SECRET_VALUES_INVALID")
        result: dict[str, str] = {}
        for raw_reference, value in values.items():
            reference = SecretReference.parse(raw_reference)
            self._validate_secret_value(value)
            result[reference.uri] = value
        return result

    @staticmethod
    def _validate_secret_value(value: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError("KIS_MCP_SECRET_VALUE_INVALID")
        if len(value.encode("utf-8")) > _MAX_SECRET_VALUE_BYTES:
            raise ValueError("KIS_MCP_SECRET_VALUE_INVALID")

    @staticmethod
    def _serialize_payload(secrets: Mapping[str, str]) -> bytes:
        return json.dumps(
            {"version": 1, "secrets": dict(secrets)},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    def _decrypt_secrets(self) -> dict[str, str]:
        return self._decrypt_secrets_with_key(
            self._session_key_bytes(), envelope=self._store.load_envelope()
        )

    def _decrypt_secrets_with_key(self, key: bytes, *, envelope) -> dict[str, str]:
        plaintext = bytearray(decrypt_payload(envelope, key))
        try:
            try:
                value: Any = json.loads(plaintext.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise VaultIntegrityError(
                    "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
                ) from exc
            if not isinstance(value, dict) or set(value) != {"version", "secrets"}:
                raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
            if value["version"] != 1 or not isinstance(value["secrets"], dict):
                raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
            secrets: dict[str, str] = {}
            for raw_reference, secret_value in value["secrets"].items():
                if not isinstance(raw_reference, str) or not isinstance(secret_value, str):
                    raise VaultIntegrityError(
                        "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
                    )
                reference = SecretReference.parse(raw_reference)
                self._validate_secret_value(secret_value)
                secrets[reference.uri] = secret_value
            return secrets
        except (InvalidSecretReferenceError, ValueError) as exc:
            raise VaultIntegrityError(
                "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
            ) from exc
        finally:
            for index in range(len(plaintext)):
                plaintext[index] = 0

    def _session_key_bytes(self) -> bytes:
        if self._session_key is None:
            raise VaultLockedError("KIS_MCP_SECRET_VAULT_LOCKED")
        return bytes(self._session_key)

    def _replace_session_key(self, key: bytes) -> None:
        if self._session_key is not None:
            for index in range(len(self._session_key)):
                self._session_key[index] = 0
        self._session_key = bytearray(key)

    @staticmethod
    def _envelope_salt(value: str) -> bytes:
        try:
            salt = base64.b64decode(value.encode("ascii"), validate=True)
        except Exception as exc:
            raise VaultIntegrityError(
                "KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED"
            ) from exc
        if len(salt) != 16:
            raise VaultIntegrityError("KIS_MCP_SECRET_VAULT_INTEGRITY_FAILED")
        return salt
