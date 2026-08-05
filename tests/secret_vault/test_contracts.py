from __future__ import annotations

from kis_mcp.secrets.contracts import (
    KdfParameters,
    SecretReferenceRecord,
    SecretsStatus,
    VaultEnvelope,
    VaultMetadata,
)


def test_kdf_parameters_use_bounded_argon2id_defaults() -> None:
    parameters = KdfParameters()

    assert parameters.iterations == 3
    assert parameters.memory_cost_kib == 65536
    assert parameters.lanes == 4
    assert parameters.length == 32
    assert parameters.to_dict() == {
        "iterations": 3,
        "memory_cost_kib": 65536,
        "lanes": 4,
        "length": 32,
    }


def test_kdf_parameters_reject_boolean_or_coerced_types() -> None:
    valid = KdfParameters().to_dict()
    for field in valid:
        candidate = dict(valid)
        candidate[field] = True
        try:
            KdfParameters.from_dict(candidate)
        except ValueError as exc:
            assert "KIS_MCP_SECRET_KDF_PARAMETERS_INVALID" in str(exc)
        else:
            raise AssertionError(f"boolean accepted for {field}")


def test_vault_envelope_round_trips_strict_mapping() -> None:
    envelope = VaultEnvelope(
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        kdf_parameters=KdfParameters(),
        salt="c2FsdA==",
        nonce="bm9uY2U=",
        ciphertext="Y2lwaGVydGV4dA==",
    )

    restored = VaultEnvelope.from_dict(envelope.to_dict())

    assert restored == envelope


def test_envelope_and_metadata_reject_coerced_json_types() -> None:
    envelope = VaultEnvelope(
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        kdf_parameters=KdfParameters(),
        salt="c2FsdA==",
        nonce="bm9uY2U=",
        ciphertext="Y2lwaGVydGV4dA==",
    ).to_dict()
    for field, invalid in (
        ("version", True),
        ("cipher", 1),
        ("kdf", 1),
        ("salt", 1),
        ("nonce", 1),
        ("ciphertext", 1),
    ):
        candidate = dict(envelope)
        candidate[field] = invalid
        try:
            VaultEnvelope.from_dict(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError(f"coerced envelope field accepted: {field}")

    record = {
        "reference": "secret://providers/nvidia/api-key",
        "updated_at": "2026-08-05T02:00:00Z",
    }
    metadata = {
        "schema_version": 1,
        "generation": 2,
        "created_at": "2026-08-05T01:00:00Z",
        "updated_at": "2026-08-05T02:00:00Z",
        "references": [record],
    }
    for field, invalid in (
        ("schema_version", True),
        ("generation", True),
        ("created_at", 1),
        ("updated_at", 1),
    ):
        candidate = dict(metadata)
        candidate[field] = invalid
        try:
            VaultMetadata.from_dict(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError(f"coerced metadata field accepted: {field}")

    for field in ("reference", "updated_at"):
        invalid_record = dict(record)
        invalid_record[field] = 1
        candidate = dict(metadata)
        candidate["references"] = [invalid_record]
        try:
            VaultMetadata.from_dict(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError(f"coerced reference field accepted: {field}")


def test_metadata_and_status_are_plaintext_safe() -> None:
    record = SecretReferenceRecord(
        reference="secret://providers/nvidia/api-key",
        updated_at="2026-08-05T02:00:00Z",
    )
    metadata = VaultMetadata(
        schema_version=1,
        generation=2,
        created_at="2026-08-05T01:00:00Z",
        updated_at="2026-08-05T02:00:00Z",
        references=(record,),
    )
    status = SecretsStatus(
        initialized=True,
        unlocked=False,
        version=1,
        cipher="AES-256-GCM",
        kdf="argon2id",
        generation=2,
        reference_count=1,
    )

    assert metadata.to_dict()["references"] == [record.to_dict()]
    assert status.to_dict() == {
        "schema_version": 1,
        "initialized": True,
        "unlocked": False,
        "version": 1,
        "cipher": "AES-256-GCM",
        "kdf": "argon2id",
        "generation": 2,
        "reference_count": 1,
    }
    serialized = repr(metadata.to_dict()) + repr(status.to_dict())
    assert "secret-value" not in serialized
