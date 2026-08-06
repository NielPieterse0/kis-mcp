# Change Specification: GitHub Project Inventory

- **Change ID**: `051-github-project-inventory`
- **Status**: Active
- **Risk Profile**: standard
- **Development level**: Standard

## Outcome

Add a read-only GitHub Projects backend that inventories one configured Project through the pinned official GitHub MCP provider and normalizes the result into provider-neutral work-management contracts.

P1 performs no remote mutation and exposes no public workflow or gateway tool.

## Authority and scope

- Parent programme: `.work/programmes/work-management/target-spec.md`.
- Foundation dependency: change `049-github-project-management-spec`.
- Verified upstream surface: pinned GitHub MCP `v1.8.0` tools `projects_get` and `projects_list`.
- Owned domain contract: `src/kis_mcp/work_management/backend.py`.
- Owned adapter: `src/kis_mcp/providers/github/projects/**`.
- Exact provider metadata change: `src/kis_mcp/providers/github/server.py`.

## Requirements

- **REQ-001**: Define immutable, JSON-safe provider-neutral Project binding, field, option, item, page, and inventory contracts.
- **REQ-002**: Define an asynchronous read-only backend protocol without importing FastMCP or provider modules.
- **REQ-003**: The GitHub adapter MUST invoke only verified `projects_get` and `projects_list` operations.
- **REQ-004**: The adapter MUST use fixed method shapes for project, fields, and items.
- **REQ-005**: The adapter MUST follow bounded cursor pagination and report truncation explicitly.
- **REQ-006**: The adapter MUST normalize GitHub response wrappers and reject malformed or ambiguous results.
- **REQ-007**: Requested field names MUST be passed explicitly when item field values are needed.
- **REQ-008**: Project owner, owner type, Project number, repository identity, and managed project ID MUST remain distinct.
- **REQ-009**: GitHub provider metadata MUST advertise read-only Project operations with exact tool names.
- **REQ-010**: P1 MUST create no GitHub project, issue, item, field, label, status update, or other remote mutation.

## Acceptance

1. **Given** representative pinned Project responses, **when** inventory runs, **then** project metadata, fields, options, items, and requested field values are normalized deterministically.
2. **Given** more items than the configured limit, **when** pagination reaches the limit, **then** inventory returns bounded items with `truncated=true` and the next cursor.
3. **Given** a malformed response, **when** normalization runs, **then** a bounded adapter error identifies the failed operation without exposing credentials.
4. **Given** the provider descriptor, **when** capability contributions are built, **then** namespaced `github_projects_get` and `github_projects_list` operations are discoverable and read-only.
5. **Given** P1 source and tests, **when** architecture checks run, **then** no `projects_write`, issue write, gateway, workflow, settings, or policy change exists.

## Risks and recovery

- Risk: inferred response shapes drift from the pinned provider.
- Mitigation: isolate normalization, accept only documented wrappers, add fixtures, and require later live read commissioning.
- Risk: pagination produces excessive context.
- Mitigation: strict item/page limits and explicit truncation.
- Risk: read capability is accidentally classified as write-capable.
- Mitigation: exact provider capability metadata and contribution tests.
- Recovery: revert the additive adapter and metadata commits. P1 creates no remote state.

## Out of scope

- Project creation or schema mutation.
- Issue, item, field, label, or status mutation.
- Persistent settings and multi-binding configuration.
- Public work-management tools or workflows.
- Live authenticated Project reads as completion evidence.
- Reader-facing repository documentation changes.
