# ADR-001: Provider-Neutral Work Management Domain

- Status: Accepted for P0
- Date: 2026-08-06
- Owner: Repository operator
- Scope: Work-management programme

## Context

The capability must coordinate several managed repositories. GitHub is the first operational backend, but backend-specific identities and response layouts must not define the project, record, lifecycle, review, or documentation contracts.

The active 047 architecture introduces explicit domain platform entry points and workflow composition. Its Providers and Workflows packages already carry material fan-in and should not own persistent work-management domain state.

## Decision

Create `src/kis_mcp/work_management` as a provider-neutral domain package.

P0 owns immutable project identity, record types, lifecycle state, documentation milestones, transition validation, and next-work selection. It imports no FastMCP, provider, workflow, gateway, or GitHub adapter module.

A later GitHub adapter translates official GitHub MCP operations to these contracts. Workflow and gateway registration wait for change 047 to merge.

## Consequences

- Multiple repositories and future approved backends can use the same domain contracts.
- GitHub-specific pagination, OAuth scopes, node IDs, and errors remain isolated.
- P0 introduces a new top-level package and requires architecture tests before public integration.
- The domain package must resist catch-all growth; adapter, workflow, automation, and evidence persistence remain separate change reasons.

## Recovery

Before public integration, revert the P0 package and tests without migration. No remote records or persistent user data are created by P0.
