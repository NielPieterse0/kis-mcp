from __future__ import annotations

import base64
import io
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from kis_mcp.secrets.cli import main


REFERENCE = "secret://providers/nvidia/api-key"
SECRET = "cli-secret-marker"
PASSPHRASE = "cli-master-passphrase"


@pytest.fixture
def cli_environment() -> dict[str, str]:
    root = Path.cwd() / ".work" / "runtime-tests" / f"secrets-{uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield {"KIS_MCP_SECRETS_ROOT": str(root)}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run(
    args: list[str],
    payload: dict[str, str],
    environment: dict[str, str],
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        args,
        stdin=io.StringIO(json.dumps(payload)),
        stdout=stdout,
        stderr=stderr,
        environ=environment,
    )
    return code, stdout.getvalue(), stderr.getvalue()


def test_initialize_and_status_emit_metadata_only(cli_environment: dict[str, str]) -> None:
    code, output, error = _run(
        ["initialize"],
        {"unlock": PASSPHRASE},
        cli_environment,
    )

    assert code == 0 and error == ""
    initialized = json.loads(output)
    assert initialized["initialized"] is True
    assert initialized["unlocked"] is True
    combined = output + Path(cli_environment["KIS_MCP_SECRETS_ROOT"], "vault.json").read_text("utf-8")
    assert PASSPHRASE not in combined

    code, output, error = _run(["status"], {}, cli_environment)
    assert code == 0 and error == ""
    assert json.loads(output)["unlocked"] is False


def test_set_list_and_internal_resolve_use_stdin_for_sensitive_values(
    cli_environment: dict[str, str],
) -> None:
    assert _run(["initialize"], {"unlock": PASSPHRASE}, cli_environment)[0] == 0

    code, output, error = _run(
        ["set", "--reference", REFERENCE],
        {"unlock": PASSPHRASE, "value": SECRET},
        cli_environment,
    )
    assert code == 0 and error == ""
    assert SECRET not in output

    code, output, error = _run(["list"], {}, cli_environment)
    assert code == 0 and error == ""
    assert json.loads(output)["references"][0]["reference"] == REFERENCE
    assert SECRET not in output

    code, output, error = _run(
        ["resolve-internal", "--reference", REFERENCE],
        {"unlock": PASSPHRASE},
        cli_environment,
    )
    assert code == 0 and error == ""
    assert output == SECRET


def test_wrong_unlock_fails_without_echoing_sensitive_input(
    cli_environment: dict[str, str],
) -> None:
    _run(["initialize"], {"unlock": PASSPHRASE}, cli_environment)

    code, output, error = _run(
        ["verify-unlock"],
        {"unlock": "wrong-unlock-marker"},
        cli_environment,
    )

    assert code == 2
    assert output == ""
    assert "wrong-unlock-marker" not in error
    assert PASSPHRASE not in error


def test_bootstrap_environment_key_never_appears_in_output(
    cli_environment: dict[str, str],
) -> None:
    encoded = base64.b64encode(b"b" * 32).decode("ascii")
    environment = {**cli_environment, "KIS_MCP_VAULT_KEY": encoded}

    code, output, error = _run(["initialize"], {}, environment)
    assert code == 0 and error == ""
    assert encoded not in output

    code, output, error = _run(["verify-unlock"], {}, environment)
    assert code == 0 and error == ""
    assert encoded not in output + error


def test_rotate_changes_passphrase_and_preserves_secret(
    cli_environment: dict[str, str],
) -> None:
    _run(["initialize"], {"unlock": PASSPHRASE}, cli_environment)
    _run(
        ["set", "--reference", REFERENCE],
        {"unlock": PASSPHRASE, "value": SECRET},
        cli_environment,
    )

    code, output, error = _run(
        ["rotate"],
        {"unlock": PASSPHRASE, "new_unlock": "rotated-passphrase"},
        cli_environment,
    )
    assert code == 0 and error == ""
    assert SECRET not in output

    assert _run(
        ["verify-unlock"], {"unlock": PASSPHRASE}, cli_environment
    )[0] == 2
    code, output, error = _run(
        ["resolve-internal", "--reference", REFERENCE],
        {"unlock": "rotated-passphrase"},
        cli_environment,
    )
    assert code == 0 and error == "" and output == SECRET
