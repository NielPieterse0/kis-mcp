from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION = ROOT / "src" / "kis_mcp" / "gateway" / "composition.py"
FOUNDATION = ROOT / "src" / "kis_mcp" / "gateway" / "foundation.py"


def test_gateway_composes_post_merge_commissioning_before_capability_snapshot() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")

    compose_call = source.index("compose_post_merge_commissioning_runtime(")
    runtime_snapshot = source.index("static_runtime_tools = tuple(")

    assert compose_call < runtime_snapshot
    assert "post_merge_commissioning_capability_contribution()" in source


def test_runtime_generation_tracks_post_merge_commissioning_policy() -> None:
    source = FOUNDATION.read_text(encoding="utf-8")

    assert '"settings/post-merge-commissioning.settings.json"' in source
