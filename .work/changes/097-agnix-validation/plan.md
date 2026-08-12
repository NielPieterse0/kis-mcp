# Agnix Validation Implementation Plan

**Goal:** expose pinned agnix as one bounded validation workflow without adding mutation or provider authority.

**Architecture:** reuse workflow registration and nested Work middleware. Load all limits/paths from `settings/bootstrap/agnix.install.json`; construct one fixed native validation command; return a versioned bounded result contract. Keep general agnix/MCP exposure disabled.

**Development level:** Medium — new executable workflow and integration contract, but no policy or provider-boundary change.

## Tasks

1. Reconcile the operator-approved repo-local agnix runtime path and smoke the native/wrapper commands.
2. Add settings/result/service/tool/platform modules under `workflows/agent_validation`.
3. Register `validate_agent_configuration` and a discoverable executable workflow descriptor.
4. Add unit, tool-surface, workflow, bootstrap, and exact local-tool registration tests.
5. Reconcile `AGENTS.md`, `SPEC.md`, `OPERATIONS.md`, and current agnix bootstrap guidance.
6. Run focused tests, scope check, full `scripts/verify.ps1`, review, exact-head delivery, and cleanup.

## Constraints

- No `--fix`, `--fix-safe`, `--fix-unsafe`, watch, init, telemetry mutation, schema, tools, or arbitrary agnix arguments.
- No new HR rule, provider mount, network authority, or deletion.
- Preserve prior runtime recoverably in quarantine.
- Do not overlap active change 096.
