# Providers and Workflows

## Load when

Read this reference for provider readiness/authentication, GitHub or Supabase
operations, Control Center status, advisory review, workflow recommendation, or
work-management behavior.

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

A missing optional backend can permit fallback when the workflow contract says
so. Do not claim a backend is live merely because its adapter is registered.

## Workflow recommendation

Use `recommend_workflow(task)` when the request describes an end-to-end outcome
rather than one known operation. Recommendations are explainable routing
evidence, not automatic execution or authorization.

Before executing a recommendation:

1. inspect required steps/capabilities;
2. confirm current readiness/eligibility;
3. use the exact operation schemas for executable steps;
4. preserve any explicit approval/idempotency requirements.

## Change planning and verification transition

When advertised by the running catalogue, prefer the bounded workflow bridge:

- `plan_change` for read-only authority/change/impact/test/verification planning;
- `run_verification(project, verification_id)` for executing a previously
  discovered approved verification declaration.

These operations are designed to avoid arbitrary command text. If they are not
present in an older instance, use the target repository's existing development
workflow and direct tools under its authority.

## Work management

Work-management operations are conditional on strict settings and provider
bindings. Disabled configuration is a valid state and must not be interpreted as
provider failure.

When enabled, expect bounded inventory, preview/reconciliation, portfolio
status, review-evidence persistence, and traceability verification workflows.
Apply paths retain revision/idempotency controls; no unrestricted GitHub Project
GraphQL or delete operation is implied by provider availability.
