# Change Specification: Register Commodity Project

- **Change ID**: `102-register-commodity-project`
- **Status**: Closed
- **Risk Profile**: lean

## Outcome

Register `commodity` as a KIS managed project with local root `C:\Projects\commodity` and GitHub repository `NielPieterse0/commodity`.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/OPERATIONS.md`, `settings/projects.settings.json`.
- Owned paths: `settings/projects.settings.json`, four project/repository registry contract tests under `tests/projects/` and `tests/repositories/`, and this change record.
- Excluded paths: `policy/**`.
- Dependencies: none.

## Requirements

- **REQ-001**: Add stable project ID `commodity` with the exact absolute local root and GitHub repository binding.
- **REQ-002**: Do not add GitHub Project or Supabase bindings that were not requested.
- **REQ-003**: Preserve all existing project registrations and the default project.

## Acceptance

1. The checked-in registry parses and validates against its schema.
2. The registry loader resolves `commodity` to `C:\Projects\commodity` and `nielpieterse0/commodity`.
3. Existing `college`, `gpt-os`, and `kis-mcp` bindings remain unchanged.
4. Full repository verification passes.

## Risks and recovery

- Risk: an incorrect coordinate could authorize the wrong provider target. Recovery: revert the bounded registry/test commit; no project files are modified.

## Out of scope

- Configuring a GitHub Project, Supabase project, or changing the local commodity repository's Git remote/history.
