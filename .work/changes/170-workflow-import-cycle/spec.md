# Change Specification: Workflow Import Cycle

- **Change ID**: `170-workflow-import-cycle`
- **Status**: Active
- **Risk Profile**: standard

## Outcome

Eliminate the deterministic tools-first circular import in the workflow package while preserving the public `workflow_descriptors` export and existing runtime contracts.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, GitHub issue #271.
- Owned paths: `src/kis_mcp/workflows/__init__.py`, `tests/workflows/test_import_order.py`, this change directory.
- Shared paths: none.
- Excluded paths: all active change lanes and unrelated package refactors.
- Dependencies: none.
- Integration owner: this isolated change.

## Requirements

- **REQ-001**: A clean Python process must import `kis_mcp.tools` followed by `kis_mcp.workflows` without a circular import.
- **REQ-002**: The reverse import order must remain valid.
- **REQ-003**: `from kis_mcp.workflows import workflow_descriptors` must remain a supported public import.
- **REQ-004**: Avoid broad dependency movement; remove the package-initialization edge that eagerly imports workflow platform composition when only a workflow submodule is requested.

## Acceptance

1. **Given** a clean Python process, **When** tools are imported before workflows, **Then** both imports succeed.
2. **Given** a clean Python process, **When** workflows are imported before tools, **Then** both imports succeed.
3. **Given** the public workflow package, **When** `workflow_descriptors` is imported from it, **Then** the callable resolves successfully.
4. Focused import-order and affected workflow/capability tests pass on the final tree.

## Risks and recovery

- Risk: lazy package export changes import semantics for callers that inspect module globals before attribute access.
- Recovery: revert this isolated change; no persistent state or external schema changes are introduced.

## Out of scope

- Refactoring `capabilities.execution`, `tools.platform`, workflow composition, or unrelated import topology.
- Changing runtime behavior beyond removing the import-order failure.
