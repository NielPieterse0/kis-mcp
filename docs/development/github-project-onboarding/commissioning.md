# GitHub Projects Commissioning

## Registered target

The shared Work Management portfolio uses GitHub user Project `NielPieterse0/#1`, titled `KIS Work Management`.

- managed project IDs: `kis-mcp`, `chatgpt-skill`, `commodity`, `college`
- repositories: `NielPieterse0/kis-mcp`, `NielPieterse0/chatgpt-skill`, `NielPieterse0/commodity`, `NielPieterse0/college`
- Work Management binding: `github-default`
- Project coordinate owner: `kis-mcp` registry entry with binding ID `work-management`
- Project owner type: `user`
- Project number: `1`

The Project coordinate is registered once because the central registry requires GitHub Project coordinates to be unique. Each managed repository retains its own repository identity and maps to the shared backend through Work Management settings. Repository engineering artifacts remain authoritative; Project #1 is the operational projection and KIS performs bounded reconciliation.

## Desired schema

`settings/work-management/github-project-schema.json` is the current repository-owned desired projection. It contains the 18 approved core fields and 12 approved saved views from the Work Management programme.

The desired `Status` options are:

`Inbox`, `Triage`, `Proposed`, `Approved`, `Active`, `Review`, `Verification`, `Documentation`, `Done`, `Blocked`, `On Hold`, `Deferred`, `Rejected`, and `Superseded`.

`project_management_schema_status(project_id)` compares live field inventory against that manifest. Saved-view observability is reported separately because the approved connector does not expose saved-view inventory.

## Live state checked 2026-08-13

Project #1 is reachable. Its live field inventory contains GitHub built-ins plus `Status`; the live `Status` options remain `Todo`, `In Progress`, and `Done`. The current schema check reports 16 custom fields not yet provisioned and 12 views not yet verified.

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

## Change 113 backfill evidence

On 2026-08-13, bounded reconciliation added the recent governed slices and residual work to Project #1: change 113 issue #138 (`In Progress`), change 110 issue #139 (`Done`), change 111 issue #140 (`Done`), and existing audit change 112 issue #141 (`In Progress`). Separate `Todo` records track rich Project commissioning (#142), provider commissioning-status persistence (#143), Docker Hub search compatibility (#144), and the pinned dependency advisory risk (#145). A fresh bounded inventory returned all eight records.

Because the rich fields are not yet provisioned, record type/change ID/authority metadata is carried by the source records and repository change artifacts rather than falsely represented as live Project fields.

## Change 115 multi-repository onboarding

On 2026-08-13, change 115 extended the shared `github-default` Work Management backend to `chatgpt-skill`, `commodity`, and `college` while retaining `kis-mcp`. The central Project coordinate remains registered once under `kis-mcp`; duplicating that coordinate across registry entries is intentionally invalid. No new Project, backend binding, automation, or schema variant was introduced.

## Close the remaining external gap

Change 113 has operator approval for a supervised GitHub UI commissioning procedure because the bounded connector still lacks these schema/view mutations:

1. provision the missing fields and exact Status options from the manifest;
2. create the 12 named views from the programme specification;
3. leave all automation disabled unless each rule is separately commissioned;
4. re-run `project_management_schema_status` and retain the exact result;
5. update current operations/specification evidence only after live drift is zero and view configuration is independently verified.
