# Change Specification: Skills Module

- **Change ID**: `012-skills-module`
- **Status**: Approved for implementation
- **Risk Profile**: standard
- **Development level**: Medium — new public MCP surface, filesystem catalogue, external shared skills root, and mutation routing through the existing Work boundary.

## Outcome

Add a focused Skills module that resolves the operator-approved shared catalogue at `C:\Projects\.agents\skills`, exposes the same practical read/create/update capability family used by the existing Work tool, and keeps every mutation behind the existing kis-mcp FastMCP middleware and Desktop Commander provider.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, operator approval in this conversation.
- Owned paths: `src/kis_mcp/skills/**`, `tests/skills/**`, `contracts/skills/**`, module JSON settings and documentation.
- Shared paths: composition root and current-state authority documents only.
- Excluded paths: Discover, Providers, Work effect resolution, policy, quarantine implementation, and remote commissioning.
- Dependencies: existing FastMCP proxy, `ThreeRuleMiddleware`, and authoritative Desktop Commander provider contracts.
- Integration owner: `012-skills-module`.

## Requirements

- **REQ-001**: Resolve skills only from the JSON-configured root `C:\Projects\.agents\skills`.
- **REQ-002**: Expose `list_skills`, `search_skills`, `load_skill`, `search_skill_files`, `read_skill_file`, `refresh_skills`, `evaluate_skill`, `create_skill`, and `improve_skill`.
- **REQ-003**: Catalogue reads must be deterministic, bounded, UTF-8 aware, traversal-safe, and reject configured link/reparse/hard-link cases as structural `SKILLS_*` failures rather than HR policy decisions.
- **REQ-004**: Skill identity comes from required `name` and `description` frontmatter in `SKILL.md`; canonical IDs are lowercase hyphenated names.
- **REQ-005**: Create and improve mutations must call Desktop Commander operations through `FastMCP.call_tool(..., run_middleware=True)` so the normal Work middleware evaluates the concrete writes.
- **REQ-006**: `create_skill` validates content before publication, stages beneath the configured kis-mcp temp root, and publishes with Desktop Commander `move_file`.
- **REQ-007**: `improve_skill` requires the active file SHA-256, validates the complete proposed skill before mutation, and uses Desktop Commander `edit_block` with exactly one expected replacement.
- **REQ-008**: No new hard rule, command allowlist/denylist, provider fork, runtime dependency, external network call, or permanent-delete operation may be added.
- **REQ-009**: Public responses and settings must have versioned bounded JSON contracts.
- **REQ-010**: Current-state authority documents must stop claiming that a runtime Skills catalogue is absent.

## Acceptance

1. **Given** a valid skill under the configured root, **When** catalogue tools are invoked, **Then** bounded cards, entrypoint content, file evidence, and a deterministic snapshot ID are returned.
2. **Given** an unsafe path, malformed skill, stale cursor, or stale expected hash, **When** a Skills operation runs, **Then** it fails with a corrective `SKILLS_*` structural error and does not mutate state.
3. **Given** a valid create request, **When** `create_skill` runs, **Then** the backend call sequence is `create_directory`, `write_file`, and `move_file`, each through the server middleware.
4. **Given** a valid update request, **When** `improve_skill` runs, **Then** it uses `edit_block` with the current complete content and `expected_replacements=1`.
5. **Given** the final server, **When** tools are listed, **Then** all nine Skills operations are present alongside the ordinary Desktop Commander and gateway tools.
6. **Given** repository verification, **When** the full check runs, **Then** policy remains exactly HR-001, HR-002, and HR-003.

## Risks and recovery

- Risk: concurrent external edits can invalidate an active snapshot. Mitigation: snapshot refresh and SHA-256 preconditions; callers retry after refresh.
- Risk: create publication can leave staged residue if Desktop Commander fails before move. Recovery: staged data remains under the configured kis-mcp temp root and is recoverable; no permanent cleanup is attempted.
- Risk: shared composition/docs may conflict with active branches. Recovery: keep changes narrowly scoped and integrate current `main` before landing.
- Recovery: close the PR and abandon the isolated branch; created runtime skills are not produced by repository tests and no data migration is required.

## Out of scope

- Executing arbitrary skill instructions inside the server.
- Installing, downloading, syncing, publishing, or remotely discovering skills.
- A custom filesystem, terminal, policy rule, approval tier, or duplicate Desktop Commander implementation.
- Editing repository-local `.agents/skills`; the runtime root is the shared `C:\Projects\.agents\skills` location.
