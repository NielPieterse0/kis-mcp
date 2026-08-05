from __future__ import annotations

from kis_mcp.control_center.contracts import ControlCenterSnapshot
from kis_mcp.control_center.render import render_control_center


def test_renderer_escapes_runtime_text_and_preserves_operational_section_order(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)

    assert "kis-mcp &lt;operator&gt;" in html
    assert "main&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Sample &lt;b&gt;diagnostic&lt;/b&gt;" in html
    assert "Sample finding &lt;unsafe&gt;" in html
    assert "Authenticate &lt;unsafe&gt; before live operations." in html
    assert "<script>" not in html.lower()
    assert "Authenticate <unsafe>" not in html

    headings = [
        "Overview",
        "Project &amp; Discover",
        "Policy &amp; Approvals",
        "Providers",
        "Processes &amp; Searches",
        "Recent Calls",
        "Quarantine",
        "Verification",
        "Diagnostics",
    ]
    positions = [html.index(f"<h2>{heading}</h2>") for heading in headings]
    assert positions == sorted(positions)


def test_renderer_is_self_contained_responsive_and_host_theme_aware(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)
    lowered = html.lower()

    assert html.startswith("<!doctype html>")
    assert "var(--color-background-primary" in html
    assert "var(--color-text-primary" in html
    assert "var(--font-sans" in html
    assert "@media" in html
    assert '<nav aria-label="Control Center sections">' in html
    assert "<style>" in lowered
    assert "<script" not in lowered
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert " src=" not in lowered
    assert " href=" not in lowered
    assert "url(" not in lowered


def test_renderer_shows_truthful_status_and_available_action_names(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)

    assert html.count("Runtime check required") == 2
    assert "Not recorded" in html
    assert "Configured does not mean authenticated or live" in html
    assert "Authentication required" in html
    assert "Pending approvals" in html
    assert "inspect_project" in html
    assert "kis_list_quarantine" in html
    assert "kis_restore_quarantine" in html
    assert "Actions are executed through the supervised kis-mcp tool surface" in html


def test_renderer_exposes_runtime_observability_without_argument_values(
    sample_snapshot: ControlCenterSnapshot,
) -> None:
    html = render_control_center(sample_snapshot)

    assert "PID 42" in html
    assert "search-1" in html
    assert "read_file" in html
    assert "execute_command" in html
    assert "path" in html
    assert "command" in html
    assert "result body" not in html
