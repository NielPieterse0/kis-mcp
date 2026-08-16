# GitHub Projects Commissioning

## Registered target

The shared Work Management portfolio uses GitHub user Project `NielPieterse0/#1`, titled `KIS Work Management`.

- managed project IDs: `kis-mcp`, `chatgpt-skill`, `commodity`, `college`, `import-isolate`
- repositories: `NielPieterse0/kis-mcp`, `NielPieterse0/chatgpt-skill`, `NielPieterse0/commodity`, `NielPieterse0/college`, `NielPieterse0/import-isolate`
- Work Management binding: `github-default`
- Project coordinate owner: `kis-mcp` registry entry with binding ID `work-management`
- Project owner type: `user`
- Project number: `1`

The Project coordinate is registered once because the central registry requires GitHub Project coordinates to be unique. Each managed repository retains its own repository identity and maps to the shared backend through Work Management settings. Repository engineering artifacts remain authoritative; Project #1 is the operational projection and KIS performs bounded reconciliation.

## Desired schema

`settings/work-management/github-project-schema.json` is the current repository-owned desired projection. It contains **25 managed fields and 12 saved views**. Work command state is held in `Status`; implementation progress is separate in `Delivery Stage`; exact verification evidence is separate in `Verification`. The canonical `Status` options are:

`Inbox`, `Triage`, `Proposed`, `Approved`, `Ready`, `Active`, `Blocked`, `On Hold`, `Deferred`, `Rejected`, `Superseded`, and `Done`.

Each saved view now carries executable semantics in the manifest: layout, filter, visible-field order, sort/group configuration, and board vertical grouping. A view name or layout alone is insufficient readiness evidence. `project_management_schema_status(project_id)` compares live fields/options and the full observable view semantics against the manifest; semantic mismatches make `views_ready=false`. `project_management_schema_plan(project_id)` reports missing or mismatched elements and must be empty after successful commissioning.

## Bounded schema and view commissioning

The normal official GitHub MCP surface continues to own Project/item reads and bounded item-field mutation. Schema/view provisioning is isolated to the approval-gated registered-Project commissioner. That operation resolves only the central-registry Project binding and checked-in manifest, preserves existing single-select option IDs, creates only missing manifest fields/views, updates existing view filter/visible-field configuration in place where GitHub exposes a safe mutation, refuses incompatible field/layout or unsupported saved-view semantic drift, and re-reads the Project before success.

The commissioner exposes no caller-supplied GraphQL/REST path, query, token, schema definition, delete operation, or destructive type conversion. Missing views are created through a fixed current GitHub Project-view endpoint with manifest-owned semantics; existing views are never deleted/recreated to force a match. Live readiness is not frozen in this document: use the runtime `project_management_schema_status` and schema plan as current evidence, with dated acceptance retained in the closing issue/change record.

## Supervised operating mode

`features.reconciliation` is `enabled`; `intake` and `review_import` remain `read_only`; `programme_status` remains `enabled`; every custom/native automation flag remains `false`. Those feature choices are intentional and separate from schema/view readiness.

Remote item mutation remains explicit: `project_management_reconcile` requires preview review, `apply=true`, and a non-empty idempotency key. No delete/archive operation or unrestricted API surface is added. Actionable task/specification intake classifies documentation impact; pre-merge readiness and post-merge documentation reconciliation continue through their bounded Work Management operations.

## Historical commissioning evidence

The sections below preserve earlier commissioning milestones. They are historical evidence only and do not override the current 25-field / semantic-12-view contract above.

## Earlier 085 write evidence

GitHub issue `#102` (`085: Commission GitHub Projects writes`) remains the first tracked write-commissioning item. It established that Project #1 was open, issue #102 could be added once, numeric Project item IDs were required for follow-up writes, and the item reached `Status=In Progress`.

That evidence proves bounded item mutation compatibility only. It does not prove the richer 18-field/12-view schema is provisioned.

## Change 113 backfill evidence

On 2026-08-13, bounded reconciliation added the recent governed slices and residual work to Project #1: change 113 issue #138 (`In Progress`), change 110 issue #139 (`Done`), change 111 issue #140 (`Done`), and existing audit change 112 issue #141 (`In Progress`). Separate `Todo` records track rich Project commissioning (#142), provider commissioning-status persistence (#143), Docker Hub search compatibility (#144), and the pinned dependency advisory risk (#145). A fresh bounded inventory returned all eight records.

At that 2026-08-13 checkpoint, the rich fields were not yet provisioned, so record type/change ID/authority metadata remained in source records and repository change artifacts rather than being falsely represented as live Project fields.

## Change 115 multi-repository onboarding

On 2026-08-13, change 115 extended the shared `github-default` Work Management backend to `chatgpt-skill`, `commodity`, and `college` while retaining `kis-mcp`. The central Project coordinate remains registered once under `kis-mcp`; duplicating that coordinate across registry entries is intentionally invalid. No new Project, backend binding, automation, or schema variant was introduced.

## Change 117 classification projection

At the change 117 checkpoint, the repository-owned target expanded from 18 to 20 fields by adding `Complexity` and `Risk Triggers`; `SPEC-117` / issue #157 was then held `In Progress`. The provider at that time could update the existing `Status` field but could not provision those generic custom fields. This limitation was later superseded by changes 152/155 and the 25-field commissioned contract.

## Historical change 113 gap plan — superseded

Change 113 originally required a supervised GitHub UI procedure because the then-approved connector could not provision the target fields/views. Changes 152/155 replaced that gap with the bounded registered-Project commissioner, and change 157 adds semantic saved-view readiness. This old UI plan is retained only as historical evidence; current commissioning uses the checked-in manifest plus the bounded commissioner and runtime schema status/plan.
