# Discover Final Integration Implementation Plan

**Goal:** Complete the approved three-tool public Discover runtime through existing registration seams and prove it end-to-end without modifying active shared-file ownership.

**Architecture:** Keep `InspectProjectService` as the server-created façade. Add a narrow `get_code_context` delegation method using `ContextBrokerService`. Extend `register_discover_tools` to bind both project inspection and context retrieval. Extend `register_change_tools` to expose the complete existing change-target contract. Preserve all version-1 response contracts and top-level server composition.

## Tasks

### Task 1: Red public-registration tests
- Update the Discover registration test to require `inspect_project` and `get_code_context`, exact annotations, exact request delegation, and normalized structural errors.
- Update change registration tests for all supported source/ref shapes and backward-compatible defaults.
- Add a public integration test proving the top-level server contains the three Discover operations and no provider-admission/project-catalog public tools.
- Run focused tests and confirm failures against the current runtime.

### Task 2: Context façade and tool binding
- Add `InspectProjectService.get_code_context(request)` delegating to `ContextBrokerService` with the same boundary/settings.
- Add narrow context port typing and `get_code_context` registration.
- Construct `CodeContextBudget` and `GetCodeContextRequest` from explicit tool arguments.
- Normalize `ValueError` and `DiscoverError` into deterministic JSON `ToolError` payloads.
- Run focused registration/context tests to green.

### Task 3: Complete change target binding
- Extend `inspect_change` tool parameters with optional `source`, `commit_ref`, `base_ref`, and `head_ref`.
- Delegate to the existing strict `InspectChangeRequest`; preserve default `working_tree` behavior.
- Normalize all structural validation errors consistently.
- Run focused change registration and service tests to green.

### Task 4: Product status and integration documentation
- Update `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` implementation status and public/internal capability boundaries.
- Add `docs/development/discover-final-integration/README.md` with exact tool surface, runtime composition, internal services, limits, and shared-file ownership note.
- Do not edit active 035-owned shared files.

### Task 5: Verification and integration
- Run focused tests, full Discover suite, scope/whitespace checks, and serialized full repository verification.
- Review security, compatibility, modularity, tool annotations, error contracts, and public-surface minimality.
- Integrate current `origin/main`, rerun exact-head verification, commit, PR, merge, close governance, and clean safely.
