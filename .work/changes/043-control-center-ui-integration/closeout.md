# Control Center UI Integration Closeout

- **Status**: Implementation complete; ready for integration
- **Change ID**: `043-control-center-ui-integration`
- **Development level**: Complex
- **Review**: No Critical or Important findings remain

## Implemented outcome

The KIS Control Center is now mounted through the normal provider runtime as a `LOCAL_READ_ONLY` platform provider. The existing kis-mcp connector exposes `controlcenter_open_kis_control_center` with MCP App resource `ui://controlcenter/kis-mcp/control-center.html`; no second manually started server is required. The standalone stdio entry point remains available for diagnostics and does not launch a window.

## Implemented scope

- Registered and enabled the `control-center` provider under namespace `controlcenter` without modifying `src/kis_mcp/server.py` or Desktop Commander assets.
- Corrected mounted MCP App metadata so the namespaced tool references the actual namespaced resource after FastMCP composition.
- Expanded the dashboard into nine responsive sections: overview, project/Discover, policy/approvals, providers, processes/searches, recent calls, quarantine, verification, and diagnostics.
- Added bounded process-local observability for tool names, argument key names, decisions, outcomes, active managed processes, and active searches.
- Added bounded local approval-register, Discover, provider-runtime, quarantine-record, Git, runtime, and verification evidence with section-level degradation.
- Extended strict Control Center and provider-runtime JSON settings/schema for the local provider and evidence limits.
- Updated operator documentation to distinguish normal mounted use from standalone stdio diagnostic mode.

## Safety and truthfulness

- Desktop Commander remains unchanged and authoritative for its file, editor, directory, preview, document, and settings widgets.
- The Control Center performs no filesystem mutation, restore, process termination, provider authentication, verification execution, settings change, or network request.
- Runtime observability excludes raw argument values and result bodies.
- The MCP App contains no external scripts, styles, fonts, images, frames, or requests and uses host theme/typography variables with safe local fallbacks.
- Runtime-derived text, including provider actions, is HTML-escaped.
- JSON and Markdown evidence inputs are byte-bounded; invalid or unavailable sections degrade independently.
- Provider configuration remains distinct from registration, mount, readiness, authentication, commissioning, and live verification evidence.
- Pending approvals are reported only when the operator-decision line is fully unchecked; approved, revised, or rejected entries are not presented as pending.

## Review findings resolved

- Fixed mounted-resource metadata after FastMCP namespaced the resource URI but did not rewrite tool MCP App metadata.
- Removed a convenience `providers.__init__` re-export that created a circular import; registration remains explicit in `providers/platform.py`.
- Escaped provider action text before composing generated HTML fragments.
- Applied the configured byte limit to the Markdown approval register and added UTF-8 validation.
- Tightened approval parsing so a checked Revise or Reject option cannot be misclassified as pending.

## Verification evidence

- Original Control Center baseline: **13 passed**.
- Final affected suite: **104 passed** across Control Center, provider composition, runtime observability, middleware, process state, and Desktop Commander.
- Primary-gateway integration test proves the normal `build_server()` surface exposes `controlcenter_open_kis_control_center` and `ui://controlcenter/kis-mcp/control-center.html` without a second process.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed and reported only declared paths.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/verify.ps1`: passed; repository tests completed with the existing two skips, 140 Python files compiled, 38 governance claims validated, and configuration, dependencies, line endings, and exact three-rule checks were green.

## Governance history

The primary worktree was clean and synchronized on `main`. The normal `scripts/change-workflow.ps1 new` path was attempted first. The command bridge returned an internal tool failure before exposing repository output when repeated path claims were supplied. Under the emergency exception documented in `AGENTS.md`, the native worktree tool created `.work/worktrees/043-control-center-ui-integration`; all five governance artifacts were registered before production edits, and subsequent validation/checks passed.

## Recovery

Revert the feature commits and remove the `control-center` entry from `settings/providers/platform-runtime.provider.json`. No migration, provider credential change, Desktop Commander change, external state mutation, or persistent telemetry store is introduced.

## Residual boundaries

- Observability is process-local and resets when the gateway restarts; it is labelled as current-process evidence rather than persisted history.
- UI rendering depends on host MCP App support. Hosts without MCP App rendering still receive the complete structured fallback result.
- Displayed action names are guidance only; actions remain subject to the ordinary supervised kis-mcp tool surface and three-rule policy.
