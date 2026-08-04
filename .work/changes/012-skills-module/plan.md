# Skills Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven development for every behavior change and verification-before-completion before delivery.

**Goal:** Add a versioned Skills MCP surface rooted at `C:\Projects\.agents\skills`, with deterministic bounded reads and Desktop Commander-backed create/update operations.

**Architecture:** `SkillCatalogue` owns immutable snapshots and validation. `SkillsWorkBackend` is a narrow mutation protocol; `FastMcpWorkBackend` re-enters the existing server with middleware enabled. `SkillsService` composes catalogue and backend, while `register_skills_tools` provides the thin public FastMCP layer.

**Tech Stack:** Python 3.11, FastMCP 3.4.4, dataclasses/Pydantic schema generation, pytest, JSON settings and JSON Schema.

## Global Constraints

- Preserve exactly HR-001, HR-002, and HR-003.
- Add no runtime dependency or external network behavior.
- Keep every mutation inside `C:\Projects` and route it through the server middleware.
- Treat catalogue validation failures as structural `SKILLS_*` errors, not policy decisions.
- Do not modify Discover, Providers, effect resolution, policy, quarantine, or remote commissioning internals.

---

### Task 1: Contracts and configuration

**Files:**
- Create: `settings/skills.settings.json`
- Create: `contracts/skills/settings.schema.json`
- Create: `src/kis_mcp/skills/config.py`
- Create: `src/kis_mcp/skills/models.py`
- Test: `tests/skills/test_config.py`
- Test: `tests/skills/test_models.py`

**Produces:** `SkillsConfig`, versioned public response dataclasses, and validated configured paths/limits.

- [ ] Write failing tests for the exact shared root, staging root, limits, suffixes, and response schema fields.
- [ ] Run focused tests and confirm failure because the module does not exist.
- [ ] Implement strict JSON loading and path validation beneath `C:\Projects`.
- [ ] Implement explicit versioned response records.
- [ ] Run focused tests and confirm pass.

### Task 2: Deterministic catalogue

**Files:**
- Create: `src/kis_mcp/skills/errors.py`
- Create: `src/kis_mcp/skills/catalogue.py`
- Test: `tests/skills/test_catalogue.py`

**Consumes:** `SkillsConfig`.
**Produces:** `SkillCatalogue.refresh/list/search/load/search_files/read_file/evaluate/validate_create/validate_replacement`.

- [ ] Write failing tests for valid snapshots, frontmatter identity, pagination, search, file reads, evaluation, traversal rejection, stale cursors, size limits, and invalid proposed replacements.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement immutable snapshot collection and bounded validation without mutation.
- [ ] Run focused tests and confirm pass.

### Task 3: Work backend and mutations

**Files:**
- Create: `src/kis_mcp/skills/backend.py`
- Create: `src/kis_mcp/skills/service.py`
- Test: `tests/skills/test_service.py`
- Test: `tests/skills/test_architecture.py`

**Consumes:** `SkillCatalogue`, `FastMCP.call_tool`.
**Produces:** `SkillsWorkBackend`, `FastMcpWorkBackend`, and `SkillsService`.

- [ ] Write failing tests proving create uses `create_directory`, `write_file`, and `move_file`; improve uses `edit_block`; stale hashes do not call the backend; and mutation code performs no direct filesystem write.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the backend protocol and middleware-reentering adapter.
- [ ] Implement create/update orchestration with prevalidation and refresh.
- [ ] Run focused tests and confirm pass.

### Task 4: Public MCP composition

**Files:**
- Create: `src/kis_mcp/skills/tools.py`
- Create: `src/kis_mcp/skills/__init__.py`
- Modify: `src/kis_mcp/server.py`
- Test: `tests/skills/test_tools.py`
- Modify: `tests/test_public_contracts.py`

**Consumes:** `SkillsService`.
**Produces:** nine public Skills tools registered on the existing server.

- [ ] Write failing tests for the exact operation names, signatures, and response schemas.
- [ ] Run focused tests and confirm failure.
- [ ] Register thin async tool handlers and compose the service in `build_server()`.
- [ ] Run focused tests and confirm pass.

### Task 5: Authority, modularity, and delivery evidence

**Files:**
- Create: `docs/SKILLS-MODULE-PRODUCT-SPEC.md`
- Create: `docs/development/skills-module/README.md`
- Modify: `AGENTS.md`
- Modify: `SPEC.md`
- Modify: `docs/PLATFORM-CONCEPT.md`
- Update: `.work/changes/012-skills-module/tasks.md`
- Update: `.work/changes/012-skills-module/closeout.md`

- [ ] Record the architecture, capability surface, backend boundary, structural limits, and non-goals.
- [ ] Run the modularity assessment against the final units and fix justified boundary defects.
- [ ] Run `scripts/change-workflow.ps1 check`, focused tests, full `scripts/verify.ps1`, and `git diff --check` on the exact final state.
- [ ] Review the diff for scope, policy, secrets, recovery, and unnecessary complexity.
- [ ] Commit, push, and open a draft PR with exact verification evidence.
