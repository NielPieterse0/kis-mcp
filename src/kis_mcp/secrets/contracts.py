from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"KIS_MCP_SECRET_CONTRACT_INVALID: {label}")


@dataclass(frozen=True, slots=True)
class KdfParameters:
    iterations: int = 3
    memory_cost_kib: int = 65536
    lanes: int = 4
    length: int = 32

    def __post_init__(self) -> None:
        if not 1 <= self.iterations <= 10:
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID")
        if not 8192 <= self.memory_cost_kib <= 1048576:
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID")
        if not 1 <= self.lanes <= 16:
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID")
        if self.length != 32:
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID")

    def to_dict(self) -> dict[str, int]:
        return {
            "iterations": self.iterations,
            "memory_cost_kib": self.memory_cost_kib,
            "lanes": self.lanes,
            "length": self.length,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KdfParameters":
        _exact_keys(
            value,
            {"iterations", "memory_cost_kib", "lanes", "length"},
            "kdf_parameters",
        )
        fields = ("iterations", "memory_cost_kib", "lanes", "length")
        if any(type(value[field]) is not int for field in fields):
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID")
        try:
            return cls(
                iterations=value["iterations"],
                memory_cost_kib=value["memory_cost_kib"],
                lanes=value["lanes"],
                length=value["length"],
            )
        except ValueError as exc:
            raise ValueError("KIS_MCP_SECRET_KDF_PARAMETERS_INVALID") from exc


@dataclass(frozen=True, slots=True)
class VaultEnvelope:
    version: int
    cipher: str
    kdf: str
    kdf_parameters: KdfParameters
    salt: str
    nonce: str
    ciphertext: str

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError("KIS_MCP_SECRET_ENVELOPE_VERSION_UNSUPPORTED")
        if self.cipher != "AES-256-GCM":
            raise ValueError("KIS_MCP_SECRET_CIPHER_UNSUPPORTED")
        if self.kdf != "argon2id":
            raise ValueError("KIS_MCP_SECRET_KDF_UNSUPPORTED")
        if not all(isinstance(value, str) and value for value in (self.salt, self.nonce, self.ciphertext)):
            raise ValueError("KIS_MCP_SECRET_ENVELOPE_INVALID")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "cipher": self.cipher,
            "kdf": self.kdf,
            "kdf_parameters": self.kdf_parameters.to_dict(),
            "salt": self.salt,
            "nonce": self.nonce,
            "ciphertext": self.ciphertext,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VaultEnvelope":
        _exact_keys(
            value,
            {"version", "cipher", "kdf", "kdf_parameters", "salt", "nonce", "ciphertext"},
            "vault_envelope",
        )
        parameters = value["kdf_parameters"]
        if not isinstance(parameters, Mapping):
            raise ValueError("KIS_MCP_SECRET_ENVELOPE_INVALID")
        try:
            return cls(
                version=int(value["version"]),
                cipher=str(value["cipher"]),
                kdf=str(value["kdf"]),
                kdf_parameters=KdfParameters.from_dict(parameters),
                salt=str(value["salt"]),
                nonce=str(value["nonce"]),
                ciphertext=str(value["ciphertext"]),
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc).startswith("KIS_MCP_SECRET_"):
                raise
            raise ValueError("KIS_MCP_SECRET_ENVELOPE_INVALID") from exc


@dataclass(frozen=True, slots=True)
class SecretReferenceRecord:
    reference: str
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return {"reference": self.reference, "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecretReferenceRecord":
        _exact_keys(value, {"reference", "updated_at"}, "secret_reference_record")
        return cls(reference=str(value["reference"]), updated_at=str(value["updated_at"]))


@dataclass(frozen=True, slots=True)
class VaultMetadata:
    schema_version: int
    generation: int
    created_at: str
    updated_at: str
    references: tuple[SecretReferenceRecord, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.generation < 1:
            raise ValueError("KIS_MCP_SECRET_METADATA_INVALID")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generation": self.generation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "references": [record.to_dict() for record in self.references],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VaultMetadata":
        _exact_keys(
            value,
            {"schema_version", "generation", "created_at", "updated_at", "references"},
            "vault_metadata",
        )
        references = value["references"]
        if not isinstance(references, list) or any(not isinstance(item, Mapping) for item in references):
            raise ValueError("KIS_MCP_SECRET_METADATA_INVALID")
        return cls(
            schema_version=int(value["schema_version"]),
            generation=int(value["generation"]),
            created_at=str(value["created_at"]),
            updated_at=str(value["updated_at"]),
            references=tuple(SecretReferenceRecord.from_dict(item) for item in references),
        )


@dataclass(frozen=True, slots=True)
class SecretsStatus:
    initialized: bool
    unlocked: bool
    version: int | None
    cipher: str | None
    kdf: str | None
    generation: int
    reference_count: int
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "initialized": self.initialized,
            "unlocked": self.unlocked,
            "version": self.version,
            "cipher": self.cipher,
            "kdf": self.kdf,
            "generation": self.generation,
            "reference_count": self.reference_count,
        }
