# Work Management and Discover

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Current module architecture belongs to [SPEC.md](../../SPEC.md); schema values, managed-project membership, operation surfaces, bindings, and field contracts belong to settings/manifests/source/tests and live status.

## Configure work management

Use these canonical configuration owners:

- [`../../settings/projects.settings.json`](../../settings/projects.settings.json) for registered project identity/routing;
- [`../../settings/work-management/contracts/`](../../settings/work-management/contracts/) for canonical Work item/vocabulary/applicability, lifecycle/operation, and selection semantics;
- [`../../settings/work-management/github-projects.settings.json`](../../settings/work-management/github-projects.settings.json) for Work Management feature/gate/evidence modes and backend bindings;
- [`../../settings/work-management/command-plane.settings.json`](../../settings/work-management/command-plane.settings.json) for the compatibility/runtime projection validated against canonical Work semantics;
- [`../../settings/work-management/github-project-schema.json`](../../settings/work-management/github-project-schema.json) for the desired GitHub Project schema/view projection validated against canonical field/type/option semantics;
- [`../../settings/housekeeping.settings.json`](../../settings/housekeeping.settings.json) for the `kis-op` housekeeping host, runner cadence, freshness, retention, and bounded execution limits.

Before changing or adding a managed project, register the intended identity/routing, keep stable bindings stable unless an explicit migration is approved, authenticate the runtime provider, and inspect current schema/status before apply.

Useful fixed-shape CLI reads/previews include:

```powershell
pwsh -NoProfile -File .\scripts\project-workflow.ps1 settings --settings settings\work-management\github-projects.settings.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 schema-manifest --manifest settings\work-management\github-project-schema.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 status --settings settings\work-management\github-projects.settings.json --records .\records.json
pwsh -NoProfile -File .\scripts\project-workflow.ps1 reconcile --desired .\desired.json --observed .\observed.json --supported-field Status
pwsh -NoProfile -File .\scripts\project-workflow.ps1 verify-traceability --trace .\trace.json --stage active
pwsh -NoProfile -File .\scripts\project-workflow.ps1 merge-readiness --record .\record.json --trace .\trace.json --pull-request-number 123
```

Standalone reconciliation is preview-only. Use `project_management_contract` for the current canonical machine-readable Work semantics and fingerprints, and use the current KIS Work Management operation schemas for live reconciliation/apply, idempotency, merge-readiness, documentation reconciliation, and traceability effects.

Before schema-dependent mutation, run the current schema-status operation. If it reports the registered Project is not ready, invoke the bounded registered-project commissioner with the intended registered project/binding and explicit approval, then rerun schema status. Use the manifest itself for current field/view counts, types, option values, and layout semantics.

Do not treat historical commissioning records, issue/change numbers, or copied managed-repository lists as current authority. Inspect the registry, manifest, runtime status, and exact Git/GitHub evidence instead.

## Operate unattended housekeeping

The scheduler authority is the long-lived `kis-op` runtime (`operation` remote instance). Work Management exposes no generic automation-switch object; `kis-dev`, stdio, and GitHub Actions do not run the timer.

After deploying a housekeeping change, restart `kis-op` from the merged revision and complete its normal GitHub OAuth bootstrap. Use `execute_read_action` for `kis_housekeeping_status`. Commissioning requires `active=true`, one active target for each configured runner, and a concrete `next_due_at` for each target.

Scheduled runs are always preview-only. After each configured initial delay/cadence, read `kis_housekeeping_status` again through `execute_read_action`. For both `work_management_reconciliation` and `backlog_readiness`, require a `last_success_receipt_id` and `freshness=fresh`. Use `execute_read_action` for `kis_housekeeping_receipt` with that ID to inspect the persisted bounded receipt. `failed`, `stale`, or `never` is not commissioned evidence.

Apply is never timer-driven. To apply an intended preview, use approval-gated `execute_external_action` for `kis_housekeeping_apply_receipt` with its receipt ID. The runtime rejects stale, incomplete, conflicting, unsafe, or changed plans, reruns preview against current authority, and derives a stable idempotency key from the unchanged actionable-plan fingerprint.

If housekeeping must be stopped, set `enabled=false` in `settings/housekeeping.settings.json`, deliver that governed change, and restart `kis-op`. Persisted receipts remain under the configured KIS state root for diagnosis and bounded retention. Do not redirect housekeeping into GitHub Actions or revive the retired local execution/landing architecture.

## Use Discover

Inspect one local project with bounded current evidence:

```json
{
  "path": "C:\\Projects\\example",
  "limits": {
    "max_files": 500,
    "max_output_chars": 200000
  }
}
```

Request limits are optional and may only narrow configured maxima. For exact current Discover limits, persistent-state behavior, provider inclusion, and result contracts, use settings/source/contracts/tests rather than this runbook.

Inspect the current working-tree change:

```json
{
  "path": "C:\\Projects\\example"
}
```

For an immutable commit, use the operation's explicit source selector:

```json
{
  "path": "C:\\Projects\\example",
  "source": "commit",
  "commit_ref": "HEAD"
}
```

Use the current `inspect_change` schema for staged/range/branch selectors. Treat `DISCOVER_*` failures as structural/diagnostic errors to correct at the reported input/state boundary; they do not create or modify HR policy.