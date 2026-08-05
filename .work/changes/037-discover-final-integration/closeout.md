# Closeout: Discover Final Integration

## Implemented scope

- Completed the fixed bounded local Discover v1 public surface: `inspect_project`, `inspect_change`, and `get_code_context`.
- Added `InspectProjectService.get_code_context()` as a narrow façade over `ContextBrokerService` using the same configured boundary and Discover settings.
- Registered `get_code_context` with explicit project, task, and complete code-context budgets.
- Extended the public `inspect_change` binding to all existing supported targets: working tree, staged, commit, range, and branch, while preserving the one-argument working-tree default.
- Normalized structural request failures and Discover retrieval failures into deterministic JSON `ToolError` payloads without new hard-rule codes.
- Preserved read-only, non-destructive, idempotent, and closed-world annotations for all three public operations.
- Proved top-level server composition through the existing unchanged registration seams and kept provider admission and project catalog services internal.
- Updated the Discover product specification with the bounded local v1 completion checkpoint, public/internal boundary, staged provider expansion, and revised definition of done.
- Added dedicated final-integration documentation, including active shared-file ownership and later synchronization requirements.

## Validation evidence

- Focused public registration and composition suite: 15 tests passed.
- Full Discover suite: 202 tests passed, 1 expected skip.
- Registered change scope check: passed and reported only declared 037 paths.
- Full repository verification: passed; complete pytest suite passed with 2 expected skips, 112 Python files passed syntax validation, and configuration, dependency, governance, whitespace, line-ending, interpreter, and exact HR-001/HR-002/HR-003 checks passed.
- Full verification used the 037 worktree package in the serialized shared Python environment.

## Review

- Security: no network, subprocess, provider execution, credentials, policy mutation, settings mutation, or new server authority was introduced.
- Compatibility: existing `inspect_project` and one-argument `inspect_change(path)` calls remain valid; response schema identities are unchanged.
- Public surface: exactly three Discover operations are exposed. Internal provider-admission and project-catalog service names are absent from the public tool list.
- Modularity: context composition remains behind the existing project-service façade; change registration uses the existing strict request contract and service.
- Error contract: a review regression found that `DiscoverError` inherits `ValueError`; handlers were reordered so specific retrieval errors retain their structured codes instead of being flattened into generic request errors.
- Simplicity: one shared read-only annotation constant and two narrow error helpers replace duplicated registration logic.
- Ownership: active change `035-llm-capability` owns `src/kis_mcp/server.py`, `SPEC.md`, and `docs/OPERATIONS.md`; this slice did not edit or bypass those files.
- Findings: no critical or important defects remain.

## Git and merge

- Branch: `change/037-discover-final-integration`
- Worktree: `.work/worktrees/037-discover-final-integration`
- Implementation commit: pending
- Pull request and merge: pending
- Cleanup: pending

## Residual items

- Shared `SPEC.md` and `docs/OPERATIONS.md` synchronization remains with the active 035 shared-file owner or a later non-overlapping documentation change. This is documentation alignment, not a Discover runtime blocker.
- Optional semantic providers, remote forge evidence, provider registries, background indexes, process-backed analyzers, and additional contract formats remain separately governed expansion work and are explicitly staged rather than represented as installed.
