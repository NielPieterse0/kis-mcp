# Context7 and Serena Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate independent pinned Context7 and Serena adapters through the existing Tools foundation while activating only the operator-approved, evidence-complete HR mappings.

**Architecture:** Context7 is an approved external read-only evidence adapter. Serena is a local stdio MCP adapter whose provider-managed state is contained through settings and readiness invariants, while invocation-controlled mutations, shell effects, and whole-memory deletion are resolved through narrow adapters into the existing HR-001/002/003 enforcement path. The approved shared resolver corrections required by Serena shell activation are implemented in the same isolated slice with dedicated tests and no broader policy expansion.

**Tech Stack:** Python 3.11 stdlib, FastMCP, JSON Schema, PowerShell installers, pytest.

## Global Constraints

- Work only in `.work/worktrees/040-context7-serena-adapters` on `change/040-context7-serena-adapters`.
- Preserve exactly HR-001, HR-002, and HR-003.
- Use `docs/HARD-BLOCK-APPROVAL-REGISTER.md` as the only hard-block approval register.
- Do not create a second policy engine or provider-native restriction layer.
- Implement only the approved shared resolver corrections required by HR2-06; do not broaden command policy beyond the recorded exact contracts.
- Context7 normal lookups use `ToolBoundary.APPROVED_EXTERNAL_SERVICE`, not the local Work command path.
- Provider-managed Serena cache, index, log, temporary, configuration, language-server, and runtime-state roots are installation/readiness invariants, not per-invocation hard blocks.
- HR1-07 is approved and activates only after exact per-operation effect tests pass.
- HR2-06 remains inactive until the corrected shared command resolver is present and its activation tests pass.
- HR3-07 remains inactive until pinned-contract evidence proves the complete deleted artifact set and consistency behavior.

---

### Task 1: Finalize approval-state documentation

**Files:**
- Modify: `docs/HARD-BLOCK-APPROVAL-REGISTER.md`
- Modify: `.work/changes/040-context7-serena-adapters/spec.md`
- Modify: `.work/changes/040-context7-serena-adapters/tasks.md`

**Interfaces:**
- Consumes: operator review decision for HR1-07, HR2-06, HR3-07.
- Produces: one auditable activation state for each mapping.

- [x] Record HR1-07 as `Revise` and narrow it to invocation-controlled file and entry mutations.
- [x] Record HR2-06 as approved with corrected-resolver and semantic-preservation conditions.
- [x] Record HR3-07 as approved with pinned-contract completeness and consistency conditions.
- [x] Record the operator's 2026-08-06 approval of the revised HR1-07 wording.
- [ ] Commit the approval-state revision separately from production implementation.

### Task 2: Freeze pinned upstream contracts

**Files:**
- Create: `contracts/tools/context7/upstream-tools.json`
- Create: `contracts/tools/context7/settings.schema.json`
- Create: `contracts/tools/serena/upstream-tools.json`
- Create: `contracts/tools/serena/settings.schema.json`
- Test: `tests/tools/test_context7_tool.py`
- Test: `tests/tools/test_serena_tool.py`

**Interfaces:**
- Produces: immutable tool schemas and source revisions consumed by descriptors, adapters, effect mapping, and installers.

- [ ] Capture only Context7 `resolve-library-id` and `query-docs` from the pinned distribution.
- [ ] Capture every enabled Serena operation with exact argument names, precedence, path semantics, shell representation, and mutation classification.
- [ ] Inspect pinned Serena source for `delete_memory` and enumerate every deleted or modified artifact.
- [ ] Write failing fixture tests that reject schema drift, unknown enabled mutations, ambiguous aliases, and incomplete `delete_memory` artifact evidence.
- [ ] Run `pytest tests/tools/test_context7_tool.py tests/tools/test_serena_tool.py -v` and confirm the fixture tests fail before implementation.
- [ ] Commit the pinned contracts and failing tests.

### Task 3: Implement independent Context7 adapter

**Files:**
- Create: `src/kis_mcp/tools/context7/settings.py`
- Create: `src/kis_mcp/tools/context7/adapter.py`
- Create: `src/kis_mcp/tools/context7/tool.py`
- Create: `src/kis_mcp/tools/context7/__init__.py`
- Create: `settings/tools/context7.tool.json`
- Create: `scripts/install-context7.ps1`
- Modify: `tests/tools/test_context7_tool.py`

**Interfaces:**
- Produces: `Context7Settings`, `Context7Adapter`, `build_context7_descriptor()`.

- [ ] Add tests for fixed provider identity, pinned source revision, settings validation, bounded outputs, redacted credentials, readiness containment, and exact two-operation exposure.
- [ ] Implement the minimal adapter and descriptor using `ToolBoundary.APPROVED_EXTERNAL_SERVICE`.
- [ ] Keep installation/package state beneath `C:\Projects\.kis-mcp\context7`.
- [ ] Verify arbitrary endpoint mutation, arbitrary provider passthrough, and local Work command routing are absent.
- [ ] Run `pytest tests/tools/test_context7_tool.py -v` and confirm pass.
- [ ] Commit Context7 independently.

### Task 4: Implement Serena bootstrap and provider-managed storage invariants

**Files:**
- Create: `src/kis_mcp/tools/serena/settings.py`
- Create: `src/kis_mcp/tools/serena/adapter.py`
- Create: `src/kis_mcp/tools/serena/tool.py`
- Create: `src/kis_mcp/tools/serena/__init__.py`
- Create: `settings/tools/serena.tool.json`
- Create: `scripts/install-serena.ps1`
- Modify: `tests/tools/test_serena_tool.py`

**Interfaces:**
- Produces: `SerenaSettings`, `SerenaAdapter`, `build_serena_descriptor()`.

- [ ] Add failing tests requiring Serena home, project data, cache, index, log, temporary, language-server, configuration, and memory roots beneath `C:\Projects`.
- [ ] Implement installation and readiness checks that fail Serena readiness without creating per-invocation HR decisions.
- [ ] Launch the pinned provider over stdio and preserve upstream operation schemas.
- [ ] Confirm provider absence or readiness failure does not prevent Context7 or wider runtime startup.
- [ ] Run the Serena readiness and storage tests and confirm pass.
- [ ] Commit bootstrap and readiness independently.

### Task 5: Implement narrowed HR1-07 invocation effect mapping

**Files:**
- Create: `src/kis_mcp/tools/serena/effects.py`
- Modify: `src/kis_mcp/tools/serena/adapter.py`
- Modify: `tests/tools/test_serena_tool.py`

**Interfaces:**
- Produces: `resolve_serena_effects(operation: str, arguments: Mapping[str, object], settings: SerenaSettings) -> InvocationEffects`.

- [x] Confirm the revised HR1-07 wording is explicitly approved in the existing register.
- [ ] Add failing tests for explicit file paths, project-relative symbol edits, exact memory paths, move source/destination, explicit outputs, argument precedence, traversal, links, junctions, and prefix collisions.
- [ ] Add counterexamples proving provider-managed state roots, reads, unknown effect coverage, and valid in-boundary edits do not create HR-001 blocks.
- [ ] Implement exact per-operation contracts; do not infer destinations generically from all path-like arguments.
- [ ] Run `pytest tests/tools/test_serena_tool.py -k "effect or mutation or boundary" -v` and confirm pass.
- [ ] Commit HR1-07 mapping independently.

### Task 6: Integrate HR2-06 through the corrected shared resolver
**Files:**
- Modify: `src/kis_mcp/command_intent.py`
- Modify: `src/kis_mcp/shell_parser.py`
- Modify: `tests/test_desktop_commander.py`
- Modify: `tests/test_shell_parser.py`
- Modify: `src/kis_mcp/tools/serena/effects.py`
- Modify: `tests/tools/test_serena_tool.py`

**Interfaces:**
- Produces: corrected shared `resolve_command_effects(...)` behavior and unchanged-semantic Serena delegation.

- [ ] Add failing shared-resolver tests for proxy, connection-routing, DNS override, jump-host, case-sensitive short options, quoted/escaped redirection, and exact command operand contracts.
- [ ] Run the focused shared-resolver tests and confirm they fail for the approved missing behavior.
- [ ] Implement the minimal shared resolver corrections without changing unknown-command or URL-as-data behavior.
- [ ] Run the focused shared-resolver tests and existing command-intent suite and confirm pass.
- [ ] Add Serena tests preserving command text or argument vector, shell type, working directory, quoting, argument boundaries, and explicitly represented environment target data.
- [ ] Add Serena proxy, connection-routing, DNS override, jump-host, package-source, Git-remote, localhost, URL-as-data, unknown-command, composed-command, and dry-run-network cases.
- [ ] Delegate to the corrected shared resolver without reconstructing command semantics.
- [ ] Run `pytest tests/test_desktop_commander.py tests/test_shell_parser.py tests/tools/test_serena_tool.py -k "network or shell or redirect or command" -v` and confirm pass.
- [ ] Commit shared resolver and HR2-06 integration independently.

### Task 7: Implement HR3-07 complete-artifact quarantine

**Files:**
- Create: `src/kis_mcp/tools/serena/memory.py`
- Modify: `src/kis_mcp/tools/serena/adapter.py`
- Modify: `tests/tools/test_serena_tool.py`

**Interfaces:**
- Produces: exact `delete_memory` artifact resolution and one quarantine request; never calls provider deletion after successful quarantine.

- [ ] Keep activation blocked until the pinned-contract audit proves the complete artifact set.
- [ ] Add failing tests for memory file, metadata, catalogue, index, and any other proven related artifacts.
- [ ] Add tests rejecting wildcard, traversal, ambiguous aliases, outside global memory, unknown artifact sets, and quarantine failure.
- [ ] Add assertions that the provider delete operation is not called after quarantine.
- [ ] Add restore and subsequent Serena readiness tests for stale, regenerated, or repaired metadata.
- [ ] Call the existing transactional `QuarantineService.quarantine_many(...)` batch for the complete proven artifact set and verify rollback on partial failure.
- [ ] Run `pytest tests/tools/test_serena_tool.py -k memory -v` and confirm pass.
- [ ] Commit HR3-07 independently.

### Task 8: Register, document, and verify

**Files:**
- Modify: `src/kis_mcp/tools/__init__.py`
- Create: `src/kis_mcp/tools/platform.py`
- Modify: `src/kis_mcp/server.py`
- Create: `tests/tools/test_context7_serena_registration.py`
- Modify: `tests/architecture/test_modularity_boundaries.py`
- Create: `docs/development/tools/context7-serena.md`
- Modify: `.work/changes/040-context7-serena-adapters/closeout.md`

**Interfaces:**
- Consumes: independent Context7 and Serena descriptors.
- Produces: optional runtime registration with contained failure domains.

- [ ] Add one Tools-module platform registration entry point that owns Context7/Serena construction and mounting; `server.py` calls that entry point without importing adapter internals, and neither adapter constructs or requires the other.
- [ ] Ensure conditionally inactive Serena capabilities remain explicitly inactive rather than broadly disabling Serena.
- [ ] Run `pytest tests/tools/test_context7_tool.py tests/tools/test_serena_tool.py tests/tools/test_context7_serena_registration.py -v`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and `check`.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` serially.
- [ ] Review the full diff against AGENTS.md, the trust model, and every activation condition.
- [ ] Reconcile the register with the operator-edited primary-worktree version without losing existing decisions.
- [ ] Commit, push, raise a PR, review the exact head, merge only if all activation conditions and verification pass, then clean the worktree without force.
