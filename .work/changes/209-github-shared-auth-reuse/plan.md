# GitHub Shared Auth Reuse Implementation Plan

**Goal:** Reuse the existing authenticated GitHub CLI credential for the fresh GitHub MCP child, while retaining interactive provider OAuth fallback and never persisting or logging the token.

**Architecture:** Add one provider-local auth resolver. It checks configured `gh` auth using an isolated process environment, obtains the CLI-managed token only after active-host validation, and returns a redacted decision plus a repr-hidden child environment. Server construction consumes that result once per provider child. Existing persistent-client lifecycle remains unchanged.

**Tech Stack:** Python, FastMCP stdio transport, GitHub CLI, PowerShell operator helper, pytest.

## Constraints

- Stay inside `scope.json`; no #397/Work Management repair or #391 work.
- Treat GitHub CLI credential storage as external existing state; KIS stores no new credential.
- Never print token values or credential-store contents.
- Preserve provider-native interactive OAuth when reuse cannot be proven valid.

## Tasks

1. Add resolver tests for valid reuse, invalid/missing auth, token lookup failure, ambient PAT conflict, and redaction.
2. Implement the smallest resolver and integrate it once into GitHub provider construction.
3. Update readiness/operator language and supervised auth helper to describe reuse-first behavior.
4. Update current-product specification only where restart/auth behavior changed.
5. Run focused provider tests, Ruff for affected Python, and `change-workflow.ps1 check`.
6. Review full base-to-head diff for code quality, security, architecture, tests, and documentation as required by risk triggers.
7. Resolve blocking findings, freeze one final head, publish PR, and require canonical GitHub Actions success on that exact head.
8. Merge exact approved head, complete Work Management #228, refresh `main`, and run governed cleanup.
