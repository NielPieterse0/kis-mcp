# GitHub Projects Commissioning

## Registered target

`kis-mcp` uses GitHub user Project `NielPieterse0/#1`, titled `KIS Work Management`.

- project ID: `kis-mcp`
- repository: `NielPieterse0/kis-mcp`
- Work Management binding: `github-default`
- Project owner type: `user`
- Project number: `1`

Repository engineering artifacts remain authoritative. Project #1 is the operational projection; KIS performs bounded reconciliation.

## Desired schema

`settings/work-management/github-project-schema.json` is the current repository-owned desired projection. It contains the 18 approved core fields and 12 approved saved views from the Work Management programme.

The desired `Status` options are:

`Inbox`, `Triage`, `Proposed`, `Approved`, `Active`, `Review`, `Verification`, `Documentation`, `Done`, `Blocked`, `On Hold`, `Deferred`, `Rejected`, and `Superseded`.

`project_management_schema_status(project_id)` compares live field inventory against that manifest. Saved-view observability is reported separately because the approved connector does not expose saved-view inventory.

## Live state checked 2026-08-12

Project #1 is reachable. Its live field inventory contains GitHub built-ins plus `Status`; the live `Status` options are still `Todo`, `In Progress`, and `Done`.

The approved GitHub MCP Project write surface can add/update Project items and create an iteration field. It does **not** expose bounded operations for generic custom-field creation, single-select option-schema changes, saved-view creation, or native Project-workflow configuration.

No direct GitHub GraphQL/network fallback is used. The iteration-field primitive is also left unused because the approved programme makes iteration cadence optional, no cadence is configured, and the current bounded provider surface exposes no delete-field recovery operation.

Therefore change 110 commissions the complete repository-side schema/drift and lifecycle integration while recording the remaining live schema/view provisioning as an explicit provider/UI gap. The exact evidence is retained in `.work/changes/110-work-management-documentation-completion/commissioning.json`.

## Supervised operating mode

`features.reconciliation` is `enabled`; `intake` and `review_import` remain `read_only`; `programme_status` remains `enabled`; every custom/native automation flag remains `false`.

Remote item mutation remains explicit: `project_management_reconcile` requires preview review, `apply=true`, and a non-empty idempotency key. No delete/archive operation or unrestricted GraphQL surface is added.

Actionable task/specification intake must classify documentation impact. Before merge use `project_management_merge_readiness`. After an exact merged PR, use `project_management_documentation_reconcile` to create `documentation_reconciliation_due`; keep required work in `Documentation` until the same operation records `post_merge_complete` at an exact completion revision.

## Earlier 085 write evidence

GitHub issue `#102` (`085: Commission GitHub Projects writes`) remains the first tracked write-commissioning item. It established that Project #1 was open, issue #102 could be added once, numeric Project item IDs were required for follow-up writes, and the item reached `Status=In Progress`.

That evidence proves bounded item mutation compatibility only. It does not prove the richer 18-field/12-view schema is provisioned.

## Close the remaining external gap

When the approved connector gains bounded schema/view configuration, or a separate supervised GitHub UI procedure is approved:

1. provision the missing fields and exact Status options from the manifest;
2. create the 12 named views from the programme specification;
3. leave all automation disabled unless each rule is separately commissioned;
4. re-run `project_management_schema_status` and retain the exact result;
5. update current operations/specification evidence only after live drift is zero and view configuration is independently verified.
