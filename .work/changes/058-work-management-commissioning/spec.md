# Change Specification: Work Management Commissioning

- **Change ID**: `058-work-management-commissioning`
- **Status**: Active
- **Development level**: Complex — live provider integration and configured mutation-boundary behavior are involved.

## Outcome

Commission the existing P0-P5 work-management implementation against `NielPieterse0` user Project `#1` (`KIS Work Management`) and expose only read-only commissioned behavior until a separate mutation-enablement decision is made.

## Authority and scope

- Repository authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Work-management authority: `.work/programmes/work-management/target-spec.md`.
- The GitHub provider remains pinned to official GitHub MCP `v1.8.0`; provider authentication configuration is out of scope.
- The current runtime already proves OAuth, private repository access, and Project `#1` routing.

## Requirements

- **R1 — Project identity**: Bind `settings/work-management/github-projects.settings.json` to user Project `#1` and enable work-management composition only after read-only live existence, field, and item checks succeed.
- **R2 — Live response compatibility**: The GitHub Project inventory adapter MUST accept the pinned provider's observed REST-shaped numeric IDs, prefer stable `node_id` values when present, and normalize structured option names such as `{ "raw": "Todo" }` without leaking provider layout into provider-neutral contracts.
- **R3 — Read-only feature enforcement**: `features.reconciliation = "read_only"` MUST allow preview and MUST reject `apply=true` before any backend mutation. `features.review_import = "read_only"` MUST reject review-evidence persistence before any filesystem write.
- **R4 — No automation or remote mutation**: All automation flags remain `false`. This change MUST NOT add Project items, update Project fields, provision views/workflows, delete records, or exercise `projects_write`.
- **R5 — Commissioning evidence**: Settings validation, focused tests, scope check, repository verification, and post-merge live `kis-op` inventory must prove the enabled read-only configuration.
- **R6 — Status reconciliation**: Update the work-management programme commissioning statement and change closeout from fresh evidence only.

## Acceptance

1. **Given** the authenticated `kis-op` runtime, **when** Project `#1` is read, **then** it resolves to private Project `KIS Work Management`, its fields include `Status` with `Todo`, `In Progress`, and `Done`, and item pagination is complete.
2. **Given** a live-shaped field payload with numeric `id`, string `node_id`, and structured option names, **when** the inventory adapter normalizes it, **then** the provider-neutral field identity and option names are valid strings and no exception is raised.
3. **Given** reconciliation mode `read_only`, **when** preview runs, **then** it remains available; **when** apply is requested, **then** it fails before `apply_reconciliation` is invoked.
4. **Given** review-import mode `read_only`, **when** persistence is requested, **then** it fails before an evidence store is created or written.
5. **Given** the commissioned settings, **when** configuration is loaded, **then** `enabled` is `true`, the binding is Project `#1`, and every automation flag remains `false`.
6. **Given** the merged exact head and a restarted authenticated `kis-op`, **when** `project_management_inventory(project_id="kis-mcp", field_names=["Status"])` runs, **then** it returns the Project inventory without remote mutation.

## Risks and recovery

- Live provider response layouts may change despite the version pin; retain tolerant normalization only for shapes observed or documented by the pinned tool contract and keep contract tests.
- Enabling composition increases the visible workflow surface; feature-mode guards are therefore required before `enabled=true` is committed.
- Recovery is a normal Git revert or setting `enabled=false`; no GitHub data is mutated by this slice.

## Out of scope

- Project schema/view/bootstrap creation or repair.
- Adding, updating, archiving, or deleting GitHub Project items.
- Enabling reconciliation apply, review-evidence writes, intake mutation, built-in automation, or scheduled automation.
- Changing OAuth/provider lifecycle, provider authentication settings, repository routing, HR-001/HR-002/HR-003, or GitHub MCP version.
- Adapting numeric write-side `item_id` calls; that is required before a later mutation-enablement slice.
