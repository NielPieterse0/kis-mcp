# Change: Supabase Registered Read Commissioning

- **Change ID**: `142-supabase-registered-read-commissioning`
- **Risk Profile**: lean

## Outcome

Make Supabase current-runtime commissioning recognize successful reads through the live upstream get_project id contract only when the referenced project is registered, while preserving process-local reset semantics.

## Scope and acceptance

- Recognize the live upstream `get_project` schema, where the project reference is supplied as `id` rather than `project_id`.
- Mark commissioning only after a successful read whose resolved project reference is registered.
- Do not mark failed reads, wrong/unregistered project references, account-level discovery, or mutations.
- Preserve process-local commissioning state so restart continues to reset live verification.
- Do not widen Supabase routing or authorization.

## Implementation and verification

- Implementation: added a tool-specific project-reference mapping for `get_project(id=...)`; existing `project_id` behavior is unchanged.
- Focused checks: routing/operational-status tests pass; Ruff passes on all changed Python files; governed scope check passes.
- Review: required `api-contracts` review was attempted on the actual diff. The fast reviewer raised one high finding claiming `authorize()` changed, but the diff proves `authorize()` is untouched; the finding was rejected as non-evidence-backed. A focused re-review then failed with `AGENT_BACKEND_FAILED:NvidiaNimError`. Manual exact-diff review found no blocking correctness, authorization-boundary, or test gaps.
- Repository verification: `scripts/verify.ps1 -SkipDependencySync` passed in full; pytest reached 100%, and configuration, interpreter, dependency, syntax, change-governance, and verification checks were all green.
- Residual risk: live `kis-op` commissioning still must be demonstrated after the change lands and the runtime is restarted.
- Closeout state: implementation and repository verification complete; landing/live commissioning pending.
