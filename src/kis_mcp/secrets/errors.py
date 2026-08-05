from __future__ import annotations


class SecretsError(RuntimeError):
    """Base error for bounded Secrets module failures."""


class InvalidSecretReferenceError(SecretsError):
    """Raised when a secret URI is not canonical or exceeds bounds."""


class VaultNotInitializedError(SecretsError):
    """Raised when an operation requires an initialized vault."""


class VaultAlreadyInitializedError(SecretsError):
    """Raised when initialization would replace an existing vault."""


class VaultLockedError(SecretsError):
    """Raised when plaintext access is attempted while locked."""


class VaultIntegrityError(SecretsError):
    """Raised when encrypted state cannot be authenticated or decoded."""


class SecretNotFoundError(SecretsError):
    """Raised when a canonical reference is absent from the unlocked vault."""
