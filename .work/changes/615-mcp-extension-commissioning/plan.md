# MCP Extension Commissioning Implementation Plan

**Goal:** Deliver issue #621 without touching #620's generic post-merge observer paths.

**Architecture:** Add a small generic `mcp_extensions` commissioning core that creates a real in-process FastMCP client with explicit extension negotiation, dispatches profile-defined MCP requests, produces identity-bound receipts, and retains only bounded in-memory last-receipt readiness. Implement SEP-2640 profile logic in Skills, and extend the existing Skills middleware/SQLite event model additively for extension-method and commissioning correlation.

**Tech stack:** Python 3.11, FastMCP 4.0.0b3, MCP 2026 protocol types, Pydantic, SQLite, pytest.

## Global constraints

- Stay inside `scope.json`; do not modify `commissioning/**` or `commissioning_runtime/**`.
- Use `Client(server, extensions=...)`; no HTTP, localhost, subprocess transport, or direct extension handler calls.
- Add failing focused tests before each behavior slice.
- Preserve observed/reported telemetry separation and existing native telemetry compatibility.
- Keep telemetry writes fail-open relative to successful protocol requests.

### Task 1: Generic in-process commissioning core

- Add typed runtime identity, step evidence, receipt, freshness/matching, profile protocol, registry/readiness, and public tool registration.
- Test real initialize/extension negotiation, dispatcher execution, bounded failure evidence, and identity drift.

### Task 2: SEP-2640 Skills commissioning profile

- Exercise advertised capability/settings, `skills/list`, `skills/get`, SKILL.md resource read, optional directory read, manifest/frontmatter verification, and unnegotiated negative control.
- Select a deterministic canonical returned skill and keep evidence content-free.
### Task 3: Skills telemetry hardening

- Observe negotiated `skills/list`, `skills/get`, and `resources/directory/read` independently from resource loading.
- Add stable server/runtime fingerprint, protocol version, extension settings fingerprint, canonical skill URI/resource-set fingerprint, commissioning receipt ID, and integrity provenance fields.
- Migrate SQLite additively and retain existing rows/defaults.
- Extend delivery reports with exact commissioned/uncommissioned reasons and bounded protocol observation counts.

### Task 4: Readiness and integration

- Register the generic commissioning tool through Skills platform composition without modifying generic post-merge observer code.
- Expose bounded registration/last-matching evidence through the commissioning response/readiness contract.
- Update the existing Skills product specification only.

### Task 5: Verification, review, and closeout

- Run focused protocol, telemetry, migration, privacy, and platform tests.
- Run `pwsh -File scripts/change-workflow.ps1 check` and governed change execution/reviews.
- Prepare the exact PR, verify exact-head GitHub Actions, pass Work Management merge readiness, merge the approved head, reconcile documentation/Work state, and clean the worktree.
- On the landed current `kis-dev` runtime, run live SEP-2640 commissioning and attach retrospective PASS evidence to #569 without reopening it.
