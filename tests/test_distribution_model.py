from __future__ import annotations

import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_project_declares_source_checkout_only_deployment() -> None:
    project = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["tool"]["kis-mcp"] == {
        "deployment-model": "source-checkout-only",
        "configuration-root": ".",
    }
    hatch = project["tool"].get("hatch", {})
    assert "wheel" not in hatch.get("build", {}).get("targets", {})
