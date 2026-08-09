# Registered GitHub Exact Operations Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Add KIS-native exact publication, approval-gated merge, and remote branch cleanup for centrally registered GitHub repositories.

**Architecture:** Add one focused exact-GitHub service in `src/kis_mcp/projects/github_exact.py`. It resolves `project_id` from the immutable project registry, uses local Git only for immutable object/ref evidence, and uses a narrowly fixed `git`/`gh` command set for approved external mutations. The three KIS-owned `kis_github_*` operations are virtual descriptors in the existing capability-control contribution and execute through the already-direct `execute_external_action` router; the read-only `projects` contribution remains unchanged and `workflows/platform.py` only advertises publication/closeout workflows. No generic shell/network passthrough or extra public FastMCP tool is added.

**Tech Stack:** Python 3.13, FastMCP 3.4.4, local `git`, GitHub CLI `gh`, pytest, repository change-workflow scripts.

## Global constraints

- Stay inside `scope.json`; `policy/**` remains excluded.
- Add tests before behavior changes.
- Resolve repository coordinates only from `settings/projects.settings.json` and the non-secret GitHub CLI configuration directory only from canonical JSON.
- Do not use `mcp-tool-1` at runtime, shared skill files, `gh auth setup-git`, `gh auth token`, `--admin`, or unrestricted `gh api`.
- Preserve exactly HR-001, HR-002, and HR-003.

---

### Task 1: Contract and command safety

**Requirements:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-007

**Files:**
- Create: `tests/workflows/test_registered_commit_publication.py`
- Create: `src/kis_mcp/projects/github_exact.py`

- [ ] Write failing tests for registry resolution, approval refusal, immutable commit resolution, stale remote-base rejection, non-ancestor rejection, exact publication command, exact post-verification, default-branch refusal, stale branch-delete refusal, and exact branch deletion.
- [ ] Run the focused test file and confirm RED because the module/API does not yet exist.
- [ ] Implement a fixed command runner, safe ref/SHA validation, per-process `gh auth git-credential` Git configuration, registry resolution, publication, and deletion.
- [ ] Run the focused test file and confirm GREEN.

### Task 2: Approval-gated exact PR merge

**Requirements:** REQ-004, REQ-007

**Files:**
- Modify: `tests/workflows/test_registered_commit_publication.py`
- Modify: `src/kis_mcp/projects/github_exact.py`

- [ ] Add failing tests proving approval is mandatory, `--match-head-commit` is always present, merge method is explicit, `--admin` is impossible, stale/non-merged post-state fails, and the authorized head is verified after merge.
- [ ] Run the merge-focused tests and confirm RED.
- [ ] Implement the smallest `gh pr view` / `gh pr merge` / post-view sequence with JSON parsing and exact-head checks.
- [ ] Run focused tests and confirm GREEN.

### Task 3: KIS registration and discoverability

**Requirements:** REQ-006

**Files:**
- Create: `tests/capabilities/test_registered_commit_workflow.py`
- Modify: `src/kis_mcp/workflows/platform.py`
- Modify: `src/kis_mcp/projects/github_exact.py`

- [ ] Add failing tests proving the three exact operations are discoverable virtual descriptors, do not expand the 24-operation direct profile, do not add local FastMCP tools, and are routed by publication/closeout workflows.
- [ ] Confirm RED.
- [ ] Add strict virtual descriptors to the existing capability-control contribution, dispatch only `virtual + registered-github` operations through `execute_external_action`, preserve generic approval gating, and add/adjust workflow descriptors.
- [ ] Confirm focused registration/capability tests GREEN.

### Task 4: Review, scope, and canonical verification

**Requirements:** REQ-001 through REQ-008

**Files:**
- Modify: `.work/changes/087-registered-commit-publication/tasks.md`
- Modify: `.work/changes/087-registered-commit-publication/closeout.md`

- [ ] Run focused workflow/capability tests.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and require zero scope violations.
- [ ] Review the final diff for credentials, external-target bounding, exact-SHA semantics, command injection, force/history rewrite, default-branch deletion, and parallel-claim conflicts.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` on the exact 087 head.
- [ ] Record exact commands/results and residual constraints in closeout evidence.
