# Change: Housekeeping Provider Content

- **Change ID**: `207-housekeeping-provider-content`
- **Risk Profile**: lean

## Outcome

Make the internal housekeeping invoker consume successful text-only FastMCP tool results without bypassing capability dispatch, so live GitHub source evidence reaches both runners while preserving fail-closed result handling.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Preserve generic capability-dispatch effect, eligibility, and approval enforcement as the execution boundary.
- Accept one successful FastMCP text-only result as bounded content without replaying the underlying operation.
- Preserve structured-content behavior unchanged.
- Reject ambiguous/multi-content text results and provider errors fail closed.
- After merge, both live scheduled runners must complete with zero source-evidence failures before natural commissioning proof is accepted.

## Implementation and verification

- Implementation notes: `FastMCPInvoker` now normalizes exactly one text content item to the existing `{text: ...}` provider envelope when `structured_content` is absent; no operation is replayed.
- Live root-cause evidence: loopback `execute_external_action -> github_issue_read` returned one successful text content item with no `structuredContent`; the old invoker rejected that result before the provider payload decoder could run.
- TDD evidence: the text-only external-result regression failed before implementation and passed afterward; ambiguous two-item text content remains rejected.
- Focused checks: full `tests/housekeeping` + `tests/housekeeping_runtime` green; Ruff green; `git diff --check` green.
- Review findings: pending final exact-range review.
- Residual risk: unsupported provider content shapes still fail closed; mutation operations are never replayed by this normalization.
- Closeout state: implementation complete locally; scope check, review, publication, merge, and live commissioning pending.
