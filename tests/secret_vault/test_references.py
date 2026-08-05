from __future__ import annotations

import pytest

from kis_mcp.secrets.errors import InvalidSecretReferenceError
from kis_mcp.secrets.references import SecretReference


@pytest.mark.parametrize(
    ("value", "path"),
    [
        ("secret://providers/nvidia/api-key", "providers/nvidia/api-key"),
        ("secret://tunnel/operation/authentication-token", "tunnel/operation/authentication-token"),
        ("secret://a/b-2/c_3/d.4", "a/b-2/c_3/d.4"),
    ],
)
def test_secret_reference_parses_and_round_trips(value: str, path: str) -> None:
    reference = SecretReference.parse(value)

    assert reference.path == path
    assert reference.uri == value
    assert str(reference) == value


@pytest.mark.parametrize(
    "value",
    [
        "providers/nvidia/api-key",
        "SECRET://providers/nvidia/api-key",
        "secret:/providers/nvidia/api-key",
        "secret://",
        "secret:///providers/nvidia/api-key",
        "secret://providers//api-key",
        "secret://providers/../api-key",
        "secret://providers/./api-key",
        "secret://providers\\nvidia\\api-key",
        "secret://providers/nvidia/api-key?version=1",
        "secret://providers/nvidia/api-key#fragment",
        "secret://providers/nvidia/api key",
        "secret://providers/%2e%2e/api-key",
    ],
)
def test_secret_reference_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(InvalidSecretReferenceError, match="KIS_MCP_SECRET_REFERENCE_INVALID"):
        SecretReference.parse(value)


def test_secret_reference_rejects_excessive_length() -> None:
    value = "secret://" + "/".join(["segment"] * 40)

    with pytest.raises(InvalidSecretReferenceError, match="KIS_MCP_SECRET_REFERENCE_INVALID"):
        SecretReference.parse(value)
