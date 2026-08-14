# Change Specification: Skill Capability Refresh

- **Change ID**: `142-skill-capability-refresh`
- **Status**: Approved for implementation
- **Risk Profile**: standard (`public_contract`)

## Outcome

Reconcile skill-derived capability contributions with the active immutable Skills snapshot after `refresh_skills`, without rebuilding the gateway or changing unrelated capability authority.

## Authority and scope

- Authoritative sources: `AGENTS.md`, issue `NielPieterse0/kis-mcp#183`, active Skills snapshot, capability metadata settings.
- Owned paths: capability runtime refresh, gateway composition, Skills capability composition, focused regression tests, this change record.
- Shared paths: none.
- Excluded paths: capability execution/surface code owned by change 140; Skills catalogue contents; capability metadata settings.
- Dependencies: none.
- Integration owner: this change.

## Requirements

- **REQ-001**: Capability reads must derive skill contributions from the current active Skills snapshot, not only gateway-startup cards.
- **REQ-002**: Removing or renaming a skill then refreshing must not leave its contribution advertised as ready.
- **REQ-003**: Adding a classified active skill then refreshing must make its configured contribution discoverable without gateway rebuild.
- **REQ-004**: Valid unclassified skills remain listable/loadable and produce no private capability contribution.
- **REQ-005**: Provider, tool, Discover, Project and capability-control contributions remain unchanged by Skills refresh.
- **REQ-006**: Invalid Skills refresh keeps the previous valid snapshot and therefore the previous valid capability projection.

## Acceptance

1. **Given** a runtime catalogue backed by a mutable contribution source, **when** that source changes, **then** subsequent capability reads use the new contribution set without rebuilding the runtime object.
2. **Given** a classified skill present at gateway composition, **when** its source is removed and Skills are refreshed, **then** `search_capabilities` cannot report its skill contribution as ready.
3. **Given** a classified skill added to the canonical Skills root, **when** Skills are refreshed, **then** its configured skill contribution becomes discoverable.
4. **Given** a valid unclassified skill, **when** Skills are refreshed, **then** Skills search/load continues to work while no skill capability contribution is created.
5. Existing capability/runtime and Skills regression suites pass.

## Risks and recovery

- Risk: rebuilding the contribution catalogue on capability reads can introduce inconsistent snapshots if the source is not deterministic.
- Mitigation: the Skills catalogue already exposes immutable snapshot semantics; the callback reads only the active snapshot and static settings.
- Recovery: remove the dynamic contribution source and fall back to the existing immutable startup catalogue; no persistent data migration is involved.

## Out of scope

- Changing skill packages or capability metadata settings.
- Altering provider runtime-tool refresh behavior or direct-exposure policy.
- Restarting the connected ChatGPT runtime as part of implementation.
