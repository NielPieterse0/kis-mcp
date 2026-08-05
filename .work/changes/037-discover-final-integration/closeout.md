# Closeout: Discover Final Integration

## Implemented scope

- Completed the bounded local Discover public surface: `inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change`.
- Added `InspectProjectService.get_code_context()` as a narrow façade over `ContextBrokerService` using the configured Discover boundary and settings.
- Extended public `inspect_change` to working tree, staged, commit, range, and branch targets while preserving the one-argument working-tree default.
- Added `analyze_change` to normalize local Git targets, caller-supplied change records, and caller-supplied GitHub pull-request metadata without executing a connector or using external network access.
- Integrated task terms into `ImpactGraphService` rather than returning `TASK_TOKEN_IMPACT_UNAVAILABLE` when terms are supplied.
- Added bounded contract, configuration, and task-term relationship evidence with explicit provenance and confidence.
- Added evidence-backed implementation steps, affected-test selection, and non-executable verification handoffs.
- Added configured input bounds for supplied changes and task terms, and made dependency and relationship evidence share the existing dependant budget.
- Added `analyze-change-request`, `analyze-change-response`, and extended `inspect-impact` schemas.
- Preserved backward-compatible serialization for legacy `InspectImpactRequest` calls without task terms.
- Normalized supplied GitHub repository names and SHAs before serialization.
- Exposed GitReader authority and settings through public read-only properties rather than private-attribute coupling.
- Updated the Discover product specification and dedicated final-integration documentation.
- Installed no Tool or Provider packages.

## Validation evidence

- Focused final review regression: 31 tests passed.
- Full Discover regression before final integration: 204 tests passed with 1 expected skip.
- Registered change scope check on the integrated head: passed and reported only declared `037` paths.
- Integrated full repository verification on commit `2b0fa9d` passed:
  - complete pytest suite passed with 2 expected skips;
  - 138 Python files passed syntax validation;
  - line-ending, whitespace, configuration, locked dependency, interpreter, change-governance, and exact HR-001/HR-002/HR-003 checks passed.
- Full verification used the `037` worktree package in the serialized shared Python environment.

## Review

- Security: no external network call, connector execution, repository-code execution, credential access, policy mutation, package installation, or additional hard-rule decision was introduced.
- Boundedness: review found and fixed unbounded supplied-change, task-term, and relationship output paths. Runtime limits now come from `settings.discover.limits` and relationship evidence shares the existing dependant budget.
- Normalization: review found and fixed preservation of whitespace and uppercase GitHub identifiers in normalized output.
- Compatibility: existing `inspect_project`, `inspect_change(path)`, and task-term-free `InspectImpactRequest` serialization remain valid.
- Modularity: public workflow registration remains under Discover; the top-level server composition file was not modified. GitReader now exposes narrow public properties required by the composition service.
- Error contract: structural request failures and Discover retrieval failures remain deterministic JSON `ToolError` payloads without new `HR-*` codes.
- Public surface: raw `inspect_impact`, provider admission, and project-catalog operations remain internal.
- Findings: no critical or important defects remain after the final review fixes.

## Git and merge

- Branch: `change/037-discover-final-integration`
- Worktree: `.work/worktrees/037-discover-final-integration`
- Checkpoint commit: `4f47053`
- Main implementation commit: `cd7b843`
- Latest-main integration commit: `2b0fa9d`
- Pull request and merge: pending
- Cleanup: pending

## Residual boundaries

- Discover accepts GitHub context supplied by the caller; it does not execute the GitHub connector or infer missing remote evidence.
- Dynamic JavaScript imports, alias/package resolution, external module resolution, background indexing, implicit project-root scans, and verification execution remain explicitly outside this bounded local slice.
- Optional semantic providers and additional contract formats remain separately governed expansion work and are not represented as installed.
