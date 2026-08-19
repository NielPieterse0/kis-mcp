# Change Specification: GitHub Shared Auth Reuse

- **Change ID**: `209-github-shared-auth-reuse`
- **Status**: Active
- **Development level**: Complex — authentication/secrets boundary; repository governance complexity remains `medium`.

## Outcome

Reuse valid GitHub CLI OAuth credentials for each fresh GitHub MCP child without persisting a new secret. If reusable CLI auth is absent or invalid, leave the child token-free so the pinned provider can use interactive OAuth. Emit only a redacted auth-source decision.

## Authority and scope

- Authorities: `AGENTS.md`, applicable `SPEC.md` GitHub-provider sections, `docs/operations/providers.md`, provider settings/schema/source/tests, and issue #228.
- Owned paths: exactly those declared in `scope.json`.
- Excluded: #397, Work Management repair/reconciliation, #391/private-repository Actions behavior.
- Base: `00996bebba601c819018f438b19aad58e18520ee`.

## Requirements

- **REQ-001**: Resolve the configured non-secret GitHub CLI config directory and verify active `github.com` authentication non-interactively.
- **REQ-002**: Obtain the CLI-managed token only in process memory and pass it only to the GitHub MCP child through the configured token environment variable.
- **REQ-003**: Never persist or log token content; redacted health/startup evidence may report only source, state, and reason.
- **REQ-004**: When CLI auth/token lookup is unavailable or invalid, start token-free and preserve interactive OAuth fallback.
- **REQ-005**: Preserve the existing ambient PAT conflict behavior; do not silently adopt arbitrary caller-provided PAT state.
- **REQ-006**: Startup/operator guidance must describe shared-auth reuse first and interactive OAuth only as fallback.

## Acceptance

1. Valid CLI keyring auth produces `shared_auth_reused`, injects the token only into the child environment, and exposes no token in repr/log/status output.
2. Missing/invalid CLI auth or token lookup produces `interactive_auth_required` and forwards no credential.
3. Ambient PAT state remains a redacted configuration conflict and is not reused.
4. Focused GitHub-provider checks, governance check, required specialist reviews, and exact-head GitHub Actions pass before merge.

## Risks and recovery

- Risk: accidental credential disclosure or stale/incorrect credential reuse. Mitigation: no persistence, minimal child environment, redacted decision objects/logging, explicit active-host validation, tests for fallback/conflict paths.
- Recovery: remove the shared-auth resolver integration to return to provider-native interactive OAuth; no credential migration or persisted KIS secret state requires rollback.
