from __future__ import annotations

from html import escape
from typing import Iterable

from .contracts import ControlCenterSnapshot


def render_control_center(snapshot: ControlCenterSnapshot) -> str:
    """Render a deterministic, self-contained, read-only MCP App document."""

    sections = "".join(
        (
            _overview_section(snapshot),
            _project_section(snapshot),
            _policy_section(snapshot),
            _providers_section(snapshot),
            _runtime_activity_section(snapshot),
            _recent_calls_section(snapshot),
            _quarantine_section(snapshot),
            _verification_section(snapshot),
            _diagnostics_section(snapshot),
        )
    )
    nav_labels = (
        "Overview",
        "Project & Discover",
        "Policy & Approvals",
        "Providers",
        "Processes & Searches",
        "Recent Calls",
        "Quarantine",
        "Verification",
        "Diagnostics",
    )
    navigation = "".join(f"<span>{_text(label)}</span>" for label in nav_labels)

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
  --kis-surface-alt: var(--color-background-tertiary, #eef1f5);
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
main {{ max-width: 1280px; margin: 0 auto; padding: 18px; }}
header {{ display: flex; gap: 18px; align-items: flex-start; justify-content: space-between; margin-bottom: 12px; }}
h1 {{ font-size: 24px; line-height: 1.2; margin: 0 0 5px; }}
h2 {{ font-size: 16px; margin: 0 0 12px; }}
h3 {{ font-size: 13px; margin: 14px 0 7px; }}
p {{ margin: 0; color: var(--kis-muted); }}
nav {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  position: sticky;
  top: 0;
  z-index: 2;
  margin: 0 0 12px;
  padding: 9px;
  background: var(--kis-bg);
  border: 1px solid var(--kis-border);
  border-radius: 11px;
}}
nav span {{ padding: 4px 8px; border-radius: 999px; background: var(--kis-surface); color: var(--kis-muted); font-size: 11px; }}
.timestamp {{ white-space: nowrap; font-size: 12px; color: var(--kis-muted); }}
.grid {{ display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 12px; }}
.card {{ grid-column: span 6; background: var(--kis-surface); border: 1px solid var(--kis-border); border-radius: 12px; padding: 15px; min-width: 0; }}
.card.wide {{ grid-column: 1 / -1; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 9px; margin: 0; }}
.metric {{ border: 1px solid var(--kis-border); border-radius: 9px; padding: 10px; min-width: 0; background: var(--kis-surface-alt); }}
.metric dt {{ color: var(--kis-muted); font-size: 11px; margin-bottom: 4px; }}
.metric dd {{ margin: 0; overflow-wrap: anywhere; font-weight: 650; }}
.entries {{ margin-top: 10px; }}
.entry {{ padding: 10px 0; border-bottom: 1px solid var(--kis-border); }}
.entry:last-child {{ border-bottom: 0; padding-bottom: 0; }}
.entry-title {{ display: flex; flex-wrap: wrap; align-items: center; gap: 7px; font-weight: 650; overflow-wrap: anywhere; }}
.entry-detail {{ color: var(--kis-muted); margin-top: 4px; overflow-wrap: anywhere; }}
.row {{ display: grid; grid-template-columns: minmax(120px, .7fr) minmax(170px, 1.3fr); gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--kis-border); }}
.row:last-child {{ border-bottom: 0; }}
.row-key {{ color: var(--kis-muted); overflow-wrap: anywhere; }}
.row-value {{ overflow-wrap: anywhere; }}
.badge {{ display: inline-flex; align-items: center; border: 1px solid var(--kis-border); border-radius: 999px; padding: 2px 7px; font-size: 11px; font-weight: 650; }}
.badge.good {{ color: var(--kis-positive); }}
.badge.warn {{ color: var(--kis-warning); }}
.badge.bad {{ color: var(--kis-danger); }}
.notice {{ margin-top: 9px; border-left: 3px solid var(--kis-accent); padding: 8px 10px; background: var(--kis-surface-alt); color: var(--kis-muted); overflow-wrap: anywhere; }}
.command {{ margin-top: 9px; padding: 9px; border: 1px solid var(--kis-border); border-radius: 8px; overflow-wrap: anywhere; font-family: var(--font-mono, ui-monospace, "Cascadia Code", monospace); }}
.empty {{ color: var(--kis-muted); padding: 7px 0; }}
.action-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; margin-top: 10px; }}
.action {{ border: 1px solid var(--kis-border); border-radius: 9px; padding: 9px; }}
.action code {{ display: block; margin-top: 4px; overflow-wrap: anywhere; }}
@media (max-width: 820px) {{
  .card {{ grid-column: 1 / -1; }}
  .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  header {{ display: block; }}
  .timestamp {{ margin-top: 7px; }}
}}
@media (max-width: 560px) {{
  main {{ padding: 10px; }}
  nav {{ position: static; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  nav span {{ text-align: center; overflow-wrap: anywhere; }}
  .metrics {{ grid-template-columns: 1fr; }}
  .timestamp {{ white-space: normal; }}
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
<nav aria-label="Control Center sections">{navigation}</nav>
<div class="grid">{sections}</div>
</main>
</body>
</html>"""


def _overview_section(snapshot: ControlCenterSnapshot) -> str:
    process_count = len(snapshot.observability.active_processes)
    search_count = len(snapshot.observability.active_searches)
    mounted_provider_value: object = (
        sum(item.mounted for item in snapshot.provider_runtime)
        if snapshot.provider_runtime
        else "Unavailable"
    )
    metrics = (
        _metric("Product", snapshot.runtime.product),
        _metric("Runtime", _label(snapshot.runtime.status)),
        _metric("Project", snapshot.project.path),
        _metric("Git branch", snapshot.project.git.branch or "Unknown"),
        _metric("Pending approvals", len(snapshot.approvals)),
        _metric("Mounted providers", mounted_provider_value),
        _metric("Active processes", process_count),
        _metric("Active searches", search_count),
    )
    implementation = "".join(
        _row(key, value) for key, value in snapshot.runtime.implementation_status
    ) or _empty("No implementation-status records were available.")
    return _section(
        "Overview",
        f'<dl class="metrics">{"".join(metrics)}</dl><div class="entries">{implementation}</div>',
    )


def _project_section(snapshot: ControlCenterSnapshot) -> str:
    project_metrics = (
        _metric("Path state", "Available" if snapshot.project.exists else "Unavailable"),
        _metric("Git status", _label(snapshot.project.git.status)),
        _metric("Working tree", _working_tree_label(snapshot)),
        _metric("Discover", _label(snapshot.discover.status)),
        _metric("Confidence", _label(snapshot.discover.confidence)),
        _metric("Modules", snapshot.discover.module_count),
        _metric("Findings", snapshot.discover.finding_count),
    )
    technologies = "".join(
        (
            _row("Languages", ", ".join(snapshot.discover.languages) or "Unknown"),
            _row("Frameworks", ", ".join(snapshot.discover.frameworks) or "Unknown"),
            _row("Project ID", snapshot.discover.project_id or "Unknown"),
        )
    )
    findings = "".join(_entry(item, "Discover finding") for item in snapshot.discover.findings)
    if not findings:
        findings = _empty("No bounded Discover findings were returned.")
    body = (
        f'<dl class="metrics">{"".join(project_metrics)}</dl>'
        f'<div class="notice">{_text(snapshot.project.git.detail)}</div>'
        f'<div class="entries">{technologies}</div>'
        f'<h3>Discover findings</h3><div class="entries">{findings}</div>'
        f'<div class="notice">{_text(snapshot.discover.detail)}</div>'
    )
    return _section("Project &amp; Discover", body, wide=True)


def _policy_section(snapshot: ControlCenterSnapshot) -> str:
    rules = "".join(
        _entry(
            f"{rule.rule_id} &middot; {rule.name}",
            rule.prohibited_outcome,
            badges=((_label(rule.decision), "warn"),),
        )
        for rule in snapshot.policy.rules
    ) or _empty("Policy rules were unavailable.")
    approvals = "".join(
        _entry(
            f"{item.approval_id} &middot; {item.title}",
            item.detail,
            badges=((_label(item.status), "warn"),),
        )
        for item in snapshot.approvals
    ) or _empty("No pending operator approvals were detected.")
    status = _badge(
        "Confirmed" if snapshot.policy.closed_rule_set else "Mismatch",
        "good" if snapshot.policy.closed_rule_set else "bad",
    )
    return _section(
        "Policy &amp; Approvals",
        (
            f'<div class="entry-title">Closed three-rule set {status}</div>'
            f'<h3>Policy declarations</h3><div class="entries">{rules}</div>'
            f'<h3>Pending approvals</h3><div class="entries">{approvals}</div>'
        ),
        wide=True,
    )


def _providers_section(snapshot: ControlCenterSnapshot) -> str:
    configured = "".join(
        _entry(
            f"{item.provider_id} &middot; {item.namespace}",
            item.action,
            badges=(
                ("Enabled" if item.enabled else "Disabled", "good" if item.enabled else "warn"),
                (_label(item.readiness), "warn"),
            ),
        )
        for item in snapshot.providers
    ) or _empty("Provider configuration was unavailable.")
    runtime = "".join(_provider_runtime_entry(item) for item in snapshot.provider_runtime)
    if not runtime:
        runtime = _empty("No provider mount evidence has been published in this gateway process.")
    return _section(
        "Providers",
        (
            "<p>Configured does not mean authenticated or live. Current provider evidence is reported separately from settings.</p>"
            f'<h3>Configured providers</h3><div class="entries">{configured}</div>'
            f'<h3>Runtime providers</h3><div class="entries">{runtime}</div>'
        ),
        wide=True,
    )


def _provider_runtime_entry(item: object) -> str:
    provider = item
    commissioning = dict(provider.commissioning)
    local_only = bool(commissioning) and all(
        value == "not_applicable" for value in commissioning.values()
    )
    extra_badges: list[tuple[str, str]] = [
        (_label(provider.state), "good" if provider.mounted else "bad"),
        (_label(provider.readiness), "good" if provider.readiness == "ready" else "warn"),
    ]
    if local_only:
        extra_badges.append(("Local read-only", "good"))
    elif commissioning.get("authenticated") == "required":
        extra_badges.append(("Authentication required", "warn"))
    detail = _text(provider.action)
    if local_only:
        detail += '<div class="notice">No commissioning required for this local provider.</div>'
    else:
        detail_rows = "".join(_row(key, value) for key, value in provider.commissioning)
        if detail_rows:
            detail += f'<div class="entries">{detail_rows}</div>'
    return _entry(
        f"{provider.provider_id} &middot; {provider.namespace}",
        detail,
        badges=tuple(extra_badges),
        detail_is_html=True,
    )


def _runtime_activity_section(snapshot: ControlCenterSnapshot) -> str:
    processes = "".join(
        _entry(
            f"PID {item.pid} &middot; {item.shell}",
            f"{item.cwd} &middot; interactions {item.interaction_count} &middot; last seen {item.last_seen_at}",
            badges=(("Active", "good"),),
        )
        for item in snapshot.observability.active_processes
    ) or _empty("No managed processes are active in this gateway process.")
    searches = "".join(
        _entry(
            item.search_id,
            f"{item.tool_name} &middot; last seen {item.last_seen_at}",
            badges=(("Active", "good"),),
        )
        for item in snapshot.observability.active_searches
    ) or _empty("No managed searches are active in this gateway process.")
    return _section(
        "Processes &amp; Searches",
        (
            f'<h3>Managed processes</h3><div class="entries">{processes}</div>'
            f'<h3>Managed searches</h3><div class="entries">{searches}</div>'
        ),
    )


def _recent_calls_section(snapshot: ControlCenterSnapshot) -> str:
    boundary = "".join(
        _boundary_entry(item) for item in snapshot.observability.recent_boundary_requests
    )
    if not boundary:
        boundary = _empty("No recent MCP boundary requests are recorded in this gateway process.")
    calls = "".join(_call_entry(item) for item in snapshot.observability.recent_calls)
    if not calls:
        calls = _empty("No recent calls are recorded in this gateway process.")
    policy = "".join(
        _call_entry(item) for item in snapshot.observability.recent_policy_decisions
    )
    if not policy:
        policy = _empty("No recent block or quarantine decisions are recorded.")
    return _section(
        "Recent Calls",
        (
            "<p>Only protocol methods, tool names, argument key names, decisions, outcomes, and bounded correlation IDs are retained. Argument values and result bodies are excluded.</p>"
            f'<h3>MCP boundary requests</h3><div class="entries">{boundary}</div>'
            f'<h3>Recent tool calls</h3><div class="entries">{calls}</div>'
            f'<h3>Recent policy decisions</h3><div class="entries">{policy}</div>'
        ),
    )


def _boundary_entry(item: object) -> str:
    title = item.method if not item.tool_name else f"{item.method}: {item.tool_name}"
    badges: list[tuple[object, str]] = [
        (item.request_id, "neutral"),
        (_label(item.outcome), "good" if item.outcome == "success" else "warn"),
    ]
    if item.error_type:
        badges.append((item.error_type, "warn"))
    return _entry(title, item.timestamp, badges=tuple(badges))


def _call_entry(item: object) -> str:
    keys = ", ".join(item.argument_keys) or "no arguments"
    badges: list[tuple[object, str]] = [
        (_label(item.decision), _decision_tone(item.decision)),
        (_label(item.outcome), "good" if item.outcome == "success" else "warn"),
    ]
    if item.code:
        badges.append((item.code, "warn"))
    return _entry(
        item.tool_name,
        f"{item.call_id} | Arguments: {keys} | {item.timestamp}",
        badges=tuple(badges),
    )


def _quarantine_section(snapshot: ControlCenterSnapshot) -> str:
    metrics = (
        _metric("Status", _label(snapshot.quarantine.status)),
        _metric("Total", snapshot.quarantine.total_records),
        _metric("Active", snapshot.quarantine.active_records),
        _metric("Restored", snapshot.quarantine.restored_records),
        _metric("Invalid", snapshot.quarantine.invalid_records),
    )
    records = "".join(
        _entry(
            item.operation_id,
            f"{item.original_path} &middot; {item.item_type}",
            badges=(("Restored" if item.restored else "Recoverable", "good"),),
        )
        for item in snapshot.quarantine_records
    ) or _empty("No bounded quarantine records are available.")
    actions = "".join(_action(item) for item in snapshot.actions)
    return _section(
        "Quarantine",
        (
            f'<dl class="metrics">{"".join(metrics)}</dl>'
            f'<div class="notice">{_text(snapshot.quarantine.root)}</div>'
            f'<h3>Recent records</h3><div class="entries">{records}</div>'
            '<h3>Available supervised actions</h3>'
            f'<div class="action-grid">{actions}</div>'
            '<div class="notice">Actions are executed through the supervised kis-mcp tool surface; this dashboard does not execute mutations directly.</div>'
        ),
        wide=True,
    )


def _verification_section(snapshot: ControlCenterSnapshot) -> str:
    return _section(
        "Verification",
        (
            f'<div class="entry-title">{_badge(_label(snapshot.verification.status), "warn")}</div>'
            f'<div class="command">{_text(" ".join(snapshot.verification.command))}</div>'
            f'<div class="notice">{_text(snapshot.verification.detail)}</div>'
        ),
    )


def _diagnostics_section(snapshot: ControlCenterSnapshot) -> str:
    diagnostics = "".join(
        _entry(item.code, item.message, badges=(("Diagnostic", "warn"),))
        for item in snapshot.diagnostics
    ) or _empty("No Control Center diagnostics.")
    return _section("Diagnostics", f'<div class="entries">{diagnostics}</div>')


def _section(title: str, body: str, *, wide: bool = False) -> str:
    class_name = "card wide" if wide else "card"
    return f'<section class="{class_name}"><h2>{title}</h2>{body}</section>'


def _action(item: object) -> str:
    return (
        '<div class="action">'
        f'<div class="entry-title">{_text(item.label)} {_badge(_label(item.kind), "warn")}</div>'
        f'<code>{_text(item.tool_name)}</code>'
        "</div>"
    )


def _entry(
    title: object,
    detail: object,
    *,
    badges: Iterable[tuple[object, str]] = (),
    detail_is_html: bool = False,
) -> str:
    rendered_badges = "".join(_badge(label, tone) for label, tone in badges)
    rendered_detail = str(detail) if detail_is_html else _text(detail)
    return (
        '<div class="entry">'
        f'<div class="entry-title">{_text(title)}{rendered_badges}</div>'
        f'<div class="entry-detail">{rendered_detail}</div>'
        "</div>"
    )


def _metric(label: object, value: object) -> str:
    return f'<div class="metric"><dt>{_text(label)}</dt><dd>{_text(value)}</dd></div>'


def _row(key: object, value: object) -> str:
    return f'<div class="row"><div class="row-key">{_text(key)}</div><div class="row-value">{_text(value)}</div></div>'


def _badge(label: object, tone: str) -> str:
    return f'<span class="badge {_text(tone)}">{_text(label)}</span>'


def _empty(message: object) -> str:
    return f'<div class="empty">{_text(message)}</div>'


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _label(value: object) -> str:
    normalized = str(value).replace("_", " ").strip()
    return normalized[:1].upper() + normalized[1:]


def _working_tree_label(snapshot: ControlCenterSnapshot) -> str:
    git = snapshot.project.git
    if git.dirty is True:
        return f"Dirty &middot; {git.changed_files or 0} changed"
    if git.dirty is False:
        return "Clean"
    return "Unknown"


def _decision_tone(value: str) -> str:
    if value == "allow":
        return "good"
    if value == "block":
        return "bad"
    return "warn"
