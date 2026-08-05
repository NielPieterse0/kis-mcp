from __future__ import annotations

from html import escape

from .contracts import ControlCenterSnapshot


def render_control_center(snapshot: ControlCenterSnapshot) -> str:
    """Render a deterministic, self-contained, read-only MCP App document."""

    runtime_items = [
        _metric("Product", snapshot.runtime.product),
        _metric("Server", snapshot.runtime.server),
        _metric("Runtime status", _label(snapshot.runtime.status)),
        _metric(
            "Desktop Commander",
            (
                f"{snapshot.runtime.desktop_commander_version} · "
                f"{_installed_label(snapshot.runtime.desktop_commander_installed)}"
            ),
        ),
    ]
    implementation = "".join(
        _row(key, value)
        for key, value in snapshot.runtime.implementation_status
    ) or _empty("No implementation-status records were available.")

    project_items = [
        _metric("Path", snapshot.project.path),
        _metric("Path state", "Available" if snapshot.project.exists else "Unavailable"),
        _metric("Git status", _label(snapshot.project.git.status)),
        _metric("Branch", snapshot.project.git.branch or "Unknown"),
        _metric("Working tree", _working_tree_label(snapshot)),
    ]

    policy_rows = "".join(
        _policy_row(
            rule.rule_id,
            rule.name,
            rule.prohibited_outcome,
            rule.decision,
        )
        for rule in snapshot.policy.rules
    ) or _empty("Policy rules were unavailable.")

    provider_rows = "".join(
        _provider_row(
            provider.provider_id,
            provider.namespace,
            provider.enabled,
            provider.readiness,
            provider.action,
        )
        for provider in snapshot.providers
    ) or _empty("Provider settings were unavailable.")

    quarantine_items = [
        _metric("Root", snapshot.quarantine.root),
        _metric("Status", _label(snapshot.quarantine.status)),
        _metric("Total", str(snapshot.quarantine.total_records)),
        _metric("Active", str(snapshot.quarantine.active_records)),
        _metric("Restored", str(snapshot.quarantine.restored_records)),
        _metric("Invalid", str(snapshot.quarantine.invalid_records)),
    ]

    diagnostic_rows = "".join(
        _diagnostic(diagnostic.code, diagnostic.message)
        for diagnostic in snapshot.diagnostics
    ) or _empty("No Control Center diagnostics.")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KIS Control Center</title>
<style>
:root {{
  color-scheme: light dark;
  --kis-bg: var(--color-background-primary, #f5f6f8);
  --kis-surface: var(--color-background-secondary, #ffffff);
  --kis-text: var(--color-text-primary, #16181d);
  --kis-muted: var(--color-text-secondary, #626975);
  --kis-border: var(--color-border-primary, #d8dce3);
  --kis-accent: var(--color-accent-primary, #405cf5);
  --kis-positive: var(--color-text-success, #177245);
  --kis-warning: var(--color-text-warning, #8b5a00);
  --kis-danger: var(--color-text-danger, #a12c2c);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--kis-bg);
  color: var(--kis-text);
  font: 14px/1.45 var(--font-sans, system-ui, -apple-system, "Segoe UI", sans-serif);
}}
main {{ max-width: 1180px; margin: 0 auto; padding: 18px; }}
header {{ display: flex; gap: 14px; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }}
h1 {{ font-size: 22px; line-height: 1.2; margin: 0 0 5px; }}
h2 {{ font-size: 15px; margin: 0 0 12px; }}
p {{ margin: 0; color: var(--kis-muted); }}
.timestamp {{ white-space: nowrap; font-size: 12px; color: var(--kis-muted); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 12px; }}
.card {{ background: var(--kis-surface); border: 1px solid var(--kis-border); border-radius: 12px; padding: 15px; min-width: 0; }}
.card.wide {{ grid-column: 1 / -1; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 9px; }}
.metric {{ border: 1px solid var(--kis-border); border-radius: 9px; padding: 10px; min-width: 0; }}
.metric dt {{ color: var(--kis-muted); font-size: 11px; margin-bottom: 4px; }}
.metric dd {{ margin: 0; overflow-wrap: anywhere; font-weight: 600; }}
.rows {{ border-top: 1px solid var(--kis-border); margin-top: 12px; }}
.row {{ display: grid; grid-template-columns: minmax(110px, .7fr) minmax(160px, 1.3fr); gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--kis-border); }}
.row-key {{ color: var(--kis-muted); overflow-wrap: anywhere; }}
.row-value {{ overflow-wrap: anywhere; }}
.entry {{ padding: 11px 0; border-bottom: 1px solid var(--kis-border); }}
.entry:last-child {{ border-bottom: 0; padding-bottom: 0; }}
.entry-title {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-weight: 650; }}
.entry-detail {{ color: var(--kis-muted); margin-top: 5px; overflow-wrap: anywhere; }}
.badge {{ display: inline-flex; align-items: center; border: 1px solid var(--kis-border); border-radius: 999px; padding: 2px 7px; font-size: 11px; font-weight: 650; }}
.badge.good {{ color: var(--kis-positive); }}
.badge.warn {{ color: var(--kis-warning); }}
.badge.bad {{ color: var(--kis-danger); }}
.notice {{ margin-top: 10px; border-left: 3px solid var(--kis-accent); padding: 8px 10px; background: var(--kis-bg); color: var(--kis-muted); }}
.command {{ margin-top: 9px; padding: 9px; border: 1px solid var(--kis-border); border-radius: 8px; overflow-wrap: anywhere; font-family: var(--font-mono, ui-monospace, "Cascadia Code", monospace); }}
.empty {{ color: var(--kis-muted); padding: 8px 0; }}
@media (max-width: 620px) {{
  main {{ padding: 12px; }}
  header {{ display: block; }}
  .timestamp {{ margin-top: 7px; }}
  .row {{ grid-template-columns: 1fr; gap: 3px; }}
}}
</style>
</head>
<body>
<main>
<header>
  <div><h1>KIS Control Center</h1><p>Read-only local operational evidence. Desktop Commander remains separate and unchanged.</p></div>
  <div class="timestamp">Snapshot: {_text(snapshot.generated_at)}</div>
</header>
<div class="grid">
<section class="card"><h2>Runtime</h2><dl class="metrics">{''.join(runtime_items)}</dl><div class="rows">{implementation}</div></section>
<section class="card"><h2>Project</h2><dl class="metrics">{''.join(project_items)}</dl><div class="notice">{_text(snapshot.project.git.detail)}</div></section>
<section class="card wide"><h2>Policy</h2><div class="entry-title">Closed three-rule set {_badge('Confirmed' if snapshot.policy.closed_rule_set else 'Mismatch', 'good' if snapshot.policy.closed_rule_set else 'bad')}</div><div>{policy_rows}</div></section>
<section class="card wide"><h2>Providers</h2><p>Configured does not mean authenticated or live. Current provider evidence remains available through <strong>kis_provider_status</strong>.</p><div>{provider_rows}</div></section>
<section class="card"><h2>Quarantine</h2><dl class="metrics">{''.join(quarantine_items)}</dl>{'<div class="notice">Record list is bounded.</div>' if snapshot.quarantine.truncated else ''}</section>
<section class="card"><h2>Verification</h2><div class="entry-title">{_badge(_label(snapshot.verification.status), 'warn')}</div><div class="command">{_text(' '.join(snapshot.verification.command))}</div><div class="notice">{_text(snapshot.verification.detail)}</div></section>
<section class="card wide"><h2>Diagnostics</h2><div>{diagnostic_rows}</div></section>
</div>
</main>
</body>
</html>"""


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _label(value: str) -> str:
    normalized = value.replace("_", " ").strip()
    return normalized[:1].upper() + normalized[1:]


def _installed_label(value: bool | None) -> str:
    if value is True:
        return "Installed"
    if value is False:
        return "Not installed"
    return "Unknown"


def _working_tree_label(snapshot: ControlCenterSnapshot) -> str:
    git = snapshot.project.git
    if git.dirty is True:
        return f"Dirty · {git.changed_files or 0} changed"
    if git.dirty is False:
        return "Clean"
    return "Unknown"


def _metric(label: str, value: object) -> str:
    return f'<div class="metric"><dt>{_text(label)}</dt><dd>{_text(value)}</dd></div>'


def _row(key: str, value: str) -> str:
    return f'<div class="row"><div class="row-key">{_text(key)}</div><div class="row-value">{_text(value)}</div></div>'


def _policy_row(
    rule_id: str, name: str, prohibited_outcome: str, decision: str
) -> str:
    return (
        '<div class="entry">'
        f'<div class="entry-title">{_text(rule_id)} · {_text(name)} {_badge(_label(decision), "warn")}</div>'
        f'<div class="entry-detail">{_text(prohibited_outcome)}</div>'
        '</div>'
    )


def _provider_row(
    provider_id: str,
    namespace: str,
    enabled: bool,
    readiness: str,
    action: str,
) -> str:
    enabled_badge = _badge("Enabled" if enabled else "Disabled", "good" if enabled else "warn")
    readiness_badge = _badge(_label(readiness), "warn")
    return (
        '<div class="entry">'
        f'<div class="entry-title">{_text(provider_id)} · {_text(namespace)} {enabled_badge} {readiness_badge}</div>'
        f'<div class="entry-detail">{_text(action)}</div>'
        '</div>'
    )


def _diagnostic(code: str, message: str) -> str:
    return (
        '<div class="entry">'
        f'<div class="entry-title">{_text(code)}</div>'
        f'<div class="entry-detail">{_text(message)}</div>'
        '</div>'
    )


def _badge(label: str, tone: str) -> str:
    return f'<span class="badge {_text(tone)}">{_text(label)}</span>'


def _empty(message: str) -> str:
    return f'<div class="empty">{_text(message)}</div>'
