# Closeout: Project Registry Routing

## Status

**Closed.** Implementation landed through PR #98 after exact-head Work Management #35 passed. This metadata-only closeout releases change 078's remaining claims after it lands on `main`.

## Implemented scope

- Added strict central project registry, read-only project catalogue tools, and gateway-owned registry composition.
- Changed GitHub routing to authorize the registered repository/Project union while retaining legacy repository-settings compatibility.
- Converted Supabase to schema v3, unscoped account OAuth, persistent runtime client reuse, and fail-closed registered per-call project routing.
- Added registry-backed Work Management identity/Project-coordinate compatibility without changing feature, gate, evidence, service, or policy behavior.
- Updated GitHub/Supabase commissioning scripts and current product/operations documentation.

## Validation evidence

- Focused TDD: Task 1-2 `13/13`; post-main reconciliation `17/17`; Supabase `63/63`; Work Management bridge `5/5`; script/artifact `9/9`.
- Final local `scripts/verify.ps1` passed: pytest exit `0`, 229 Python files syntax-valid, configuration/interpreter/dependencies/change-governance and exact three-rule verification green.
- Exact PR head `ba9ec4a0d6efe3fe99ee99c7eaac4175d1d24935` passed Work Management #35 (`31271763489`), including settings, governance, focused P5 tests, and canonical repository verification.
- JSON contracts/settings and governed scope validation passed; excluded policy/provider-platform/GitHub-server/Work-service/Work-settings paths remained unchanged.
- Modularity Mode A evidence supports the retained seams; RFC clustering and AGT read/edit ratio remained unmeasured, so `MAS = n/a`.

## Review

- Manual full-diff review found one material edge: ambiguous multiple GitHub Project coordinates could preserve stale Work Management coordinates. Fixed to fail closed and regression-tested.
- NVIDIA advisory review completed with generic observations and no reproducible blocker. Codex advisory backend returned `AGENT_BACKEND_UNAVAILABLE`; no Codex review pass is claimed.

## Git and merge

- Branch/worktree: `change/078-project-registry-routing` / `.work/worktrees/078-project-registry-routing`.
- Registry/Gateway slice: `194c925`.
- Final implementation head: `ba9ec4a0d6efe3fe99ee99c7eaac4175d1d24935`.
- PR #98; Work Management #35 (`31271763489`) passed on that exact head; merge commit `37adc01daf6703d164cd7b719872ffbfb55ed1c9`.
- Primary `main` was fast-forwarded to the merge before this closeout was recorded.
- Cleanup remains deferred only until this metadata-only closeout lands on `main`.

## Residual items

- No remaining 078 implementation scope. Governed branch/worktree cleanup is the final lifecycle action.
- Live Supabase account OAuth and explicit registered-project commissioning remain supervised deployment evidence, not inferred from implementation tests.
