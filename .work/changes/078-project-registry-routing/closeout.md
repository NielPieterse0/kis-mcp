# Closeout: Project Registry Routing

## Implemented scope

- Added strict central project registry, read-only project catalogue tools, and gateway-owned registry composition.
- Changed GitHub routing to authorize the registered repository/Project union while retaining legacy repository-settings compatibility.
- Converted Supabase to schema v3, unscoped account OAuth, persistent runtime client reuse, and fail-closed registered per-call project routing.
- Added registry-backed Work Management identity/Project-coordinate compatibility without changing feature, gate, evidence, service, or policy behavior.
- Updated GitHub/Supabase commissioning scripts and current product/operations documentation.

## Validation evidence

- Focused TDD: Task 1-2 `13/13`; post-main reconciliation `17/17`; Supabase `63/63`; Work Management bridge `5/5`; script/artifact `9/9`.
- Full suite: canonical `scripts/verify.ps1` passed on the final candidate; pytest exit code `0`, Python syntax `229` files, configuration/interpreter/dependencies/change-governance all OK.
- JSON: project registry/schema, Supabase provider/schema, capabilities, and change scope validated.
- Diff scope: `change-workflow.ps1 check` and `validate` passed; excluded policy/provider-platform/GitHub-server/Work-service/Work-settings paths are unchanged versus `main`.
- Modularity: Mode A, 90-day collector on six affected units; measured LOC/fan evidence supports current seams. RFC clustering and AGT read/edit ratio remain unmeasured, so `MAS = n/a` rather than inferred.

## Review

- Manual full-diff review found one material edge: ambiguous multiple GitHub Project coordinates could preserve stale Work Management coordinates. Fixed to fail closed and regression-tested.
- NVIDIA advisory review completed but returned only generic observations; no reproducible blocker. Codex advisory backend returned `AGENT_BACKEND_UNAVAILABLE`.

## Git and merge

- Branch: `change/078-project-registry-routing`
- Worktree: `.work/worktrees/078-project-registry-routing`
- Implementation commits: `194c925` plus pending final implementation commit.
- Pull request or merge: pending.
- Cleanup: pending post-merge governed cleanup.

## Residual items

- Live Supabase account OAuth and explicit registered-project commissioning remain supervised deployment evidence, not inferred from implementation tests.
