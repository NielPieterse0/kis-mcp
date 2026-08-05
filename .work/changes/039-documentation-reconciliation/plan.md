# Documentation Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit all tracked repository documentation and reconcile the owned current-state documents with the verified implementation, authority order, operational state, and writing standard.

**Architecture:** Treat `AGENTS.md` and the authority chain as the claim-control boundary. Build a source-to-document matrix from implementation, settings, tests, merged change records, and the operator audit; then make bounded edits only in owned documents. Preserve historical evidence and active external work through explicit status labels and exclusions.

**Tech Stack:** Markdown, JSON, Git, PowerShell repository workflows, Python/pytest verification already provided by the repository, GitHub CLI through approved MCP operations.

## Global constraints

- Work only in `.work/worktrees/039-documentation-reconciliation` on `change/039-documentation-reconciliation`.
- Do not modify any excluded path in `scope.json`.
- Preserve the three-rule trust model and the authority order in `AGENTS.md`.
- Treat public registration, internal implementation, configured readiness, target state, and historical evidence as distinct states.
- Do not rewrite historical `.work/changes/**` records.
- Do not claim external URL availability or Markdown anchor validation unless separately checked.
- Keep edits material and reviewable; do not reflow or restyle text without a coherence benefit.

---

### Task 1: Establish the audit baseline and source map

**Files:**
- Modify: `.work/changes/039-documentation-reconciliation/tasks.md`
- Modify: `.work/changes/039-documentation-reconciliation/closeout.md`

**Sources:** `AGENTS.md`, authority documents, all tracked Markdown paths, current source registration points, canonical settings, tests, recent merged change records, active change claims, and the operator audit.

**Produces:** A durable inventory of reviewed documents, implementation evidence, active conflicts, stale claim patterns, and checks to rerun.

- [ ] Enumerate every tracked Markdown file and classify it as authority, current guidance, module specification, historical development evidence, generated evidence, or local skill documentation.
- [ ] Run deterministic repository-relative link-target checks and record unsupported checks separately.
- [ ] Inspect public tool registration, provider composition, Discover internals, Skills operations, LLM capability registration, remote commissioning state, and operational scripts.
- [ ] Compare the source evidence with the operator audit and record which findings remain current, were already resolved, or are now superseded.
- [ ] Update `tasks.md` with the source-to-document mapping and material findings before editing reader-facing documents.

### Task 2: Reconcile the primary product and architecture authorities

**Files:**
- Modify: `README.md`
- Modify: `SPEC.md`
- Modify: `docs/PLATFORM-CONCEPT.md`

**Sources:** Task 1 evidence, `AGENTS.md`, `docs/TRUST-MODEL.md`, public runtime registration, provider composition, Discover implementation, Skills implementation, Tools/agent implementation, and remote runtime behavior.

**Produces:** A coherent top-level description of current product behavior and target evolution.

- [ ] Replace historical tool-count and inspect-project-only claims with stable capability descriptions.
- [ ] Add or update a public/internal/target capability matrix where status ambiguity exists.
- [ ] Align architecture diagrams and component descriptions with the current gateway, Discover, Skills, Providers, Tools, agent workflow, and remote surfaces.
- [ ] Remove duplicated policy prose when a link to the authoritative trust model is sufficient.
- [ ] Verify that target-state language remains explicitly prospective.
- [ ] Review the three documents together for terminology, heading hierarchy, duplicated claims, and contradictions.

### Task 3: Reconcile provider, operations, and lessons guidance

**Files:**
- Modify: `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `docs/LESSONS-APPLICABILITY.md`

**Sources:** Provider runtime composition, GitHub and Supabase commissioning behavior, NVIDIA NIM and Codex agent capability, AgentSys and agnix bootstrap contracts, startup scripts, current verification commands, and merged change records.

**Produces:** Current provider status, accurate operator actions, and an updated applicability map.

- [ ] Replace future-tense provider phases that are already implemented with current-state descriptions and remaining boundaries.
- [ ] Describe GitHub as ready when authenticated and Supabase as ready after project initialization rather than broken or uncommissioned.
- [ ] Describe NVIDIA NIM and Codex CLI as bounded agent backends with their credential and runtime prerequisites.
- [ ] Verify every documented command and path against current scripts and settings without exposing secrets.
- [ ] Reclassify lessons that moved from deferred to implemented or continuing evidence.
- [ ] Review the documents for consistent readiness vocabulary and explicit operator actions.

### Task 4: Preserve historical evidence while preventing current-guidance confusion

**Files:**
- Modify: `docs/development/provider-composition/README.md`
- Modify: `docs/development/skills-module/README.md`

**Sources:** Historical change evidence, current provider runtime composition, the repository writing standard, and Task 1 classification.

**Produces:** Clear historical status and one consistent H1 hierarchy in owned evidence files.

- [ ] Add a concise banner stating the provider-composition document records the state of its original slice and is superseded for current guidance.
- [ ] Link historical provider evidence to the current provider and product specifications.
- [ ] Normalize the Skills development-evidence heading hierarchy without rewriting its recorded evidence.
- [ ] Confirm no historical assertion is silently rewritten.
- [ ] Record the hard-block register as delegated to active change `040-context7-serena-adapters`; do not edit or claim it.

### Task 5: Review and verify the complete documentation set

**Files:**
- Modify: `.work/changes/039-documentation-reconciliation/tasks.md`
- Modify: `.work/changes/039-documentation-reconciliation/closeout.md`

**Sources:** Final branch diff, all authority documents, all owned documents, structural scans, and repository verification output.

**Produces:** Review findings, corrected documents, and current acceptance evidence.

- [ ] Re-run the full tracked-Markdown inventory and link-target scan.
- [ ] Search for stale phrases identified in Task 1 and verify each remaining occurrence is current, historical, or excluded.
- [ ] Review the final diff against `spec.md`, `scope.json`, the style guide, and active claims.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and `check` from the worktree.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` serially from the worktree.
- [ ] Run Git whitespace validation and confirm the worktree contains only owned paths.
- [ ] Resolve every blocking finding and rerun affected checks.

### Task 6: Deliver through PR and clean the worktree

**Files:**
- Modify: `.work/changes/039-documentation-reconciliation/tasks.md`
- Modify: `.work/changes/039-documentation-reconciliation/closeout.md`
- Modify: `.work/changes/039-documentation-reconciliation/scope.json`

**Sources:** Exact committed head, GitHub PR checks and mergeability, final verification output, and repository cleanup workflow.

**Produces:** Merged documentation reconciliation with no leftover `039` worktree or local branch.

- [ ] Mark all tasks complete and record exact verification evidence and residual exclusions.
- [ ] Set `scope.json` status to `closed` only after implementation and verification are complete.
- [ ] Commit the final branch and push without force.
- [ ] Open a PR with scope, evidence, exclusions, and recovery notes.
- [ ] Review the exact PR head, changed-file list, checks, and mergeability.
- [ ] Merge using a merge commit only when the exact head remains current and safe.
- [ ] Run the repository cleanup command from the clean primary worktree without modifying unrelated active worktrees.
- [ ] Confirm the `039` worktree and local branch are removed and the active `031`, `037`, and `040` worktrees remain intact.
