# Discover Final Integration Implementation Plan

**Goal:** Complete the approved four-workflow public Discover runtime, close the bounded donor change-impact gaps, and prove the integrated result end-to-end without modifying policy/settings authority or installing Tool or Provider packages.

**Architecture:** Keep the existing top-level server registration seams. `InspectProjectService` remains the façade for project inspection and code context. `InspectChangeService` composes the hardened local Git reader with `ImpactGraphService`, allowing `register_change_tools` to expose both `inspect_change` and the unified `analyze_change` workflow. Caller-supplied change and GitHub metadata are normalized locally; no connector or network execution occurs. Existing request defaults and task-term-free serialization remain compatible.

## Tasks

### Task 1: Public integration baseline
- Add red registration and composition tests for `get_code_context` and all existing `inspect_change` source/ref shapes.
- Preserve `inspect_project` and one-argument `inspect_change(path)` behavior.
- Normalize structural failures and Discover errors without adding `HR-*` codes.

### Task 2: Context façade and bounded change targets
- Add `InspectProjectService.get_code_context(request)` delegating to `ContextBrokerService` with the same boundary and settings.
- Register `get_code_context` with explicit project, task, and complete context budgets.
- Expose working-tree, staged, commit, range, and branch target arguments through the existing strict `InspectChangeRequest` contract.

### Task 3: Unified change-analysis contracts
- Add `SuppliedChange`, `GitHubChangeContext`, `AnalyzeChangeRequest`, `NormalizedChange`, and `AnalyzeChangeResponse` contracts.
- Normalize repository-relative paths, statuses, GitHub repository identity, and lowercase 40-character SHAs.
- Add configured maximum supplied/local changed-path counts and task-term counts.
- Add checked-in `analyze-change-request` and `analyze-change-response` schemas and schema tests.

### Task 4: Impact graph completion
- Pass normalized task terms into `InspectImpactRequest` and `ImpactGraphService`.
- Add contract, configuration, and task-term relationship records with explicit heuristic provenance and confidence.
- Make dependency and relationship evidence share the explicit `max_dependants` budget and report omissions/truncation deterministically.
- Add evidence-backed implementation steps derived from changed paths, relationships, affected tests, and verification handoffs.
- Preserve the existing task-term-free `InspectImpactRequest` serialized wire shape.

### Task 5: Public `analyze_change` workflow
- Compose local change inventory and impact analysis inside `InspectChangeService` using the Git reader’s public authority/settings properties.
- Register `analyze_change` through the existing change registration seam only when the service supports analysis.
- Accept local Git targets or bounded supplied changes and caller-supplied GitHub PR metadata.
- Keep raw `inspect_impact`, provider admission, and project catalog internal.

### Task 6: Documentation and traceability
- Update `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` to record the four-workflow local v1 surface and supplied-context boundary.
- Update the dedicated final-integration record with implemented capabilities, exclusions, review findings, and verification evidence.
- Reconcile change `spec.md`, `plan.md`, `tasks.md`, and `closeout.md` with the final approved scope.

### Task 7: Review, verification, and integration
- Run focused TDD cycles and the full Discover regression.
- Review security, boundedness, normalization, compatibility, modularity, annotations, schemas, and public/internal boundaries.
- Fix all critical and important findings.
- Integrate current `origin/main` and run `scripts/change-workflow.ps1 check` plus `scripts/verify.ps1` on the exact integrated tree.
- Commit, push, create and review the PR, merge safely, verify `main`, and run governed cleanup without disturbing other active worktrees.
