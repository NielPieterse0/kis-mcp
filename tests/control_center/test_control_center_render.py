from __future__ import annotations

from kis_mcp.control_center.contracts import ControlCenterSnapshot
from kis_mcp.control_center.render import render_control_center


def test_renderer_escapes_runtime_text_and_preserves_section_order(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)

    assert "kis-mcp &lt;operator&gt;" in html
    assert "main&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Sample &lt;b&gt;diagnostic&lt;/b&gt;" in html
    assert "<script>" not in html.lower()

    headings = [
        "Runtime",
        "Project",
        "Policy",
        "Providers",
        "Quarantine",
        "Verification",
        "Diagnostics",
    ]
    positions = [html.index(f"<h2>{heading}</h2>") for heading in headings]
    assert positions == sorted(positions)


def test_renderer_is_self_contained_and_uses_host_theme_fallbacks(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)
    lowered = html.lower()

    assert html.startswith("<!doctype html>")
    assert "var(--color-background-primary" in html
    assert "var(--color-text-primary" in html
    assert "<style>" in lowered
    assert "<script" not in lowered
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert " src=" not in lowered
    assert " href=" not in lowered
    assert "url(" not in lowered


def test_renderer_shows_configuration_as_unverified_not_ready(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)

    assert html.count("Runtime check required") == 2
    assert "Not recorded" in html
    assert "Configured does not mean authenticated or live" in html
