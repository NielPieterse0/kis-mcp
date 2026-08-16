# Work Management and Discover

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Current module architecture belongs to [SPEC.md](../../SPEC.md); schema values, managed-project membership, operation surfaces, bindings, and field contracts belong to settings/manifests/source/tests and live status.

## Configure work management

Use these canonical configuration owners:

- [`../../settings/projects.settings.json`](../../settings/projects.settings.json) for registered project identity/routing;
- [`../../settings/work-management/github-projects.settings.json`](../../settings/work-management/github-projects.settings.json) for Work Management modes/bindings;
- [`../../settings/work-management/github-project-schema.json`](../../settings/work-management/github-project-schema.json) for the desired GitHub Project schema/view projection.

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

Standalone reconciliation is preview-only. Use the current KIS Work Management operation schemas for live reconciliation/apply, idempotency, merge-readiness, documentation reconciliation, and traceability semantics.

Before schema-dependent mutation, run the current schema-status operation. If it reports the registered Project is not ready, invoke the bounded registered-project commissioner with the intended registered project/binding and explicit approval, then rerun schema status. Use the manifest itself for current field/view counts, types, option values, and layout semantics.

Do not treat historical commissioning records, issue/change numbers, or copied managed-repository lists as current authority. Inspect the registry, manifest, runtime status, and exact Git/GitHub evidence instead.

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