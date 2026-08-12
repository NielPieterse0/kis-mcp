# Providers and Workflows

## Load when

Read this reference for provider readiness/authentication, DBHub, Docker Hub,
GitHub or Supabase operations, Control Center status, advisory review, workflow
recommendation, or work-management behavior.

## Provider status layers

`kis_provider_status` intentionally separates:

- registration;
- runtime enablement;
- local readiness;
- build and mount state;
- bounded user status / next action;
- commissioning stages such as authentication, upstream connection, tool
  discovery, and live verification.

Do not collapse these into one `ready=true/false` interpretation.

A mounted provider can still require authentication. A locally ready provider
can still lack live commissioning evidence. Expected onboarding is not the same
as a degraded or failed provider.

## Discover provider operations

Provider long tails are namespaced and progressively exposed. Search by task or
semantic capability rather than trying to memorize upstream tool names:

```text
search_capabilities("review pull request")
search_capabilities("GitHub Actions failures")
search_capabilities("Supabase schema read")
```

Then inspect the exact result with `describe_capability` before dispatching a
long-tail operation.

## DBHub

DBHub is a source-aware database connector. Resolve the stable KIS project and
binding before execution; do not infer a database from the current directory.
Public KIS tool names are stable:

```text
db_<project>_<binding>_search_objects
db_<project>_<binding>_execute_sql
```

Local SQLite bindings are read-only and use `execute_read_action`. External
bindings are also read-only but retain an external effect, so dispatch them with
`execute_external_action`. Search schema objects before free-form SQL when the
schema is unknown. KIS starts one isolated DBHub process per registered binding,
so adding another binding must not rename an existing public operation.

## Docker Hub

Docker Hub is an approved external registry connector, not local Docker Engine
control. Discover `dockerhub.*` capability metadata and dispatch eligible calls
with `execute_external_action`. Public mode needs no PAT; PAT mode requires the
configured runtime secret reference and username. Project namespace routing is
optional and must come from the central project registry rather than prompt
assumptions.

## GitHub

GitHub uses an approved external MCP provider boundary. In the runtime-scoped
OAuth model, one authenticated upstream provider process is reused for the
parent kis-mcp runtime and is recreated when that runtime restarts.

Practical rules:

- use explicit repository arguments from the discovered schema;
- treat repository/Project routing separately from OAuth identity;
- use `github_*` operations only when readiness/eligibility says they are
  available;
- do not add a PAT to compensate for an OAuth problem unless current provider
  authority explicitly changes that design;
- merge/review or other approval-sensitive actions may require their original
  workflow and cannot always be sent through generic dispatch.

Recent/concurrent GitHub-tool experience work improves runtime schema
preservation, exact description, semantic ranking, workflow eligibility, and
bounded provider results. Use the live runtime evidence rather than freezing a
copied catalogue or assuming every improvement is present in an older instance.

## Supabase

Supabase is an approved external connector, not a local Work network command.
Use current provider status and discovered operation schemas. In project-neutral
runtimes, account authentication and project routing are separate; project
operations use explicit registered targets.

If the live runtime still reports project-initialization requirements from an
older provider revision, follow that runtime's corrective status rather than
assuming the newer routing model is already deployed.

## Control Center

The Control Center is read-only local status/diagnostic UI. It reports bounded
runtime, project, policy, provider, quarantine, and verification guidance; it
does not authorize Work mutations.

When the mounted provider is present, treat it as a local read-only component.
It should not require external-provider commissioning. Older instances may show
stale commissioning metadata; prefer the current provider/user-status evidence.

## Advisory code review

`review_change_with_agent` is an advisory workflow. It collects bounded local
change evidence and may use configured NVIDIA NIM or Codex CLI backends. It does
not grant mutation or nested-agent authority.

The fixed review purposes are:

- `code-quality`;
- `safety-security`;
- `architecture`;
- `performance`;
- `test-quality`;
- `documentation`;
- `api-contracts`.

Changing purpose changes the review rubric only. A missing optional backend can
permit fallback when the workflow contract says so. Do not claim a backend is
live merely because its adapter is registered.

## Workflow recommendation

Use `recommend_workflow(task)` when the request describes an end-to-end outcome
rather than one known operation. Recommendations are explainable routing
evidence, not automatic execution or authorization.

Before executing a recommendation:

1. inspect required steps/capabilities;
2. confirm current readiness/eligibility;
3. use the exact operation schemas for executable steps;
4. preserve any explicit approval/idempotency requirements.

## Change analysis, verification, and execution

Use the change workflow stack progressively rather than jumping to arbitrary
process commands:

- `inspect_change` and `analyze_change` establish bounded change/impact evidence;
- `plan_change` produces read-only authority, impact, test, and verification planning;
- `select_change_verification` reconciles impact handoffs against current declared
  executable profiles without running them;
- `run_verification(project, verification_id)` executes one approved declaration;
- `execute_change_workflow`, when present, composes selection, selected
  verification execution, and bounded specialist reviews for one change.

Python project discovery recognizes Ruff, coverage.py/pytest-cov, Vulture,
LibCST, mypy, and Pyright declarations. Discovery is evidence only: it does not
install tooling or turn non-executable declarations into runnable checks.

If `execute_change_workflow` is absent from the running instance, use the
individual operations above. Do not infer absence from repository source alone;
check the live catalogue because a running kis-op/kis-dev process may lag the
checkout.

## Agent configuration validation

Use the discoverable `validate-agent-configuration` workflow or
`validate_agent_configuration` operation for bounded agnix validation. The
managed path uses pinned agnix `0.45.0` with fixed JSON-validation arguments.
It does not expose fix, watch, init, telemetry, arbitrary command execution, or
a general agnix MCP/provider passthrough.

Treat its findings as validation evidence. Do not interpret the presence of the
managed binary as authority to invoke other agnix modes through a local shell.

## Govern advisory evidence

The repository contains a deterministic advisory Govern core for authority and
documentation drift. Its rules evaluate evidence; they do not add Work policy or
mutation authority. Public composition can lag source implementation, so use
live capability discovery before invoking Govern operations and do not treat a
target architecture document as proof that a Govern tool is exposed.

## Safe delivery and closeout

Use exact registered-GitHub operations for repository publication/merge/branch
cleanup when their current schemas and approval preconditions match the task.
The established surface includes immutable commit publication, exact-head PR
merge, and exact-head non-default branch deletion.

Slice 6 also implements a bounded tree-equivalent reconciliation publication
path for divergent local history. Its delivery can lag the checkout; use
`kis_github_reconcile_registered_commit` only when the running catalogue
advertises it. It is for a verified non-default review branch and is not a
force-push or default-branch rewrite primitive.

`prepare_reviewable_pull_request` is implemented as a bounded coordinator when
the live catalogue advertises it. It accepts an immutable local commit plus
exact review/default-branch expectations, runs the existing bounded verification
and specialist-review workflow, reconciles a tree-equivalent review branch, and
creates/post-verifies one open non-draft PR. It deliberately stops before merge,
branch deletion, worktree cleanup, auto-merge, release, or default-branch
mutation. If a running instance lacks it or a required reviewer backend fails,
compose the existing exact verification/publication/PR operations explicitly and
retain every exact-head, approval, idempotency, and recovery precondition.

## Work management

Work-management operations are conditional on strict settings and provider
bindings. Disabled configuration is a valid state and must not be interpreted as
provider failure.

When enabled, expect bounded inventory, preview/reconciliation, Project schema
status, merge readiness, documentation reconciliation, portfolio status,
review-evidence persistence, and traceability verification operations. The
repository-owned desired Project projection is
`settings/work-management/github-project-schema.json`.

For managed tasks/specification slices, documentation impact is part of intake.
Use the `complete-work-managed-pull-request` workflow for closeout: it requires
`project_management_merge_readiness` before the exact-head registered merge and
then `project_management_documentation_reconcile` after confirmed merge evidence.
Required work remains in `Documentation` until `post_merge_complete` is recorded
at an exact revision.

Apply paths retain revision/idempotency controls. The approved GitHub MCP surface
currently cannot provision generic Project fields, Status option schemas, saved
views, or native Project workflows, so `project_management_schema_status`
reports those gaps rather than bypassing the provider with unrestricted GraphQL.
All custom/native automation remains disabled until separately commissioned.
