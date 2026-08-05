from __future__ import annotations

from .contracts import SecretsStatus, VaultEnvelope, VaultMetadata


def build_status(
    *,
    envelope: VaultEnvelope | None,
    metadata: VaultMetadata | None,
    unlocked: bool,
) -> SecretsStatus:
    return SecretsStatus(
        initialized=envelope is not None and metadata is not None,
        unlocked=unlocked,
        version=None if envelope is None else envelope.version,
        cipher=None if envelope is None else envelope.cipher,
        kdf=None if envelope is None else envelope.kdf,
        generation=0 if metadata is None else metadata.generation,
        reference_count=0 if metadata is None else len(metadata.references),
    )
