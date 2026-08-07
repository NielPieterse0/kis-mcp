# GitHub Tools Experience Implementation Plan

> **For agentic workers:** Execute task-by-task in the single governed worktree and preserve exact-head evidence for each PR batch.

**Goal:** Improve GitHub and GitHub Projects progressive discovery and long-tail usability while retaining current OAuth, routing, approval, safety, and direct-exposure boundaries.

**Architecture:** Keep GitHub-specific semantic declarations inside the GitHub provider. Extend provider-neutral operation metadata only with bounded invocation schema. Runtime augmentation enriches registered/dynamic operations from the authoritative MCP tool snapshot. Capability search/description becomes exact-first and compact. Workflow recommendation follows the 047 hard-eligibility contract. A later isolated budgeter bounds oversized generic provider results without altering direct provider contracts.

**Tech Stack:** Python 3.13 runtime / FastMCP 3.4.4 / pytest / Git / GitHub Actions / governed PowerShell workflow.

## Global constraints

- Stay inside `scope.json`; update claims before touching any additional path.
- TDD: add failing regression tests before behavior changes.
- Do not change `policy/**`, GitHub OAuth settings, Project commissioning settings, or active Discover paths.
- Do not hard-code the full GitHub MCP catalogue.
- Keep the full GitHub long tail discoverable rather than directly exposed.
- Merge/reconcile after every PR batch before starting the next batch.

---

### Batch 1 / PR 1: Self-describing progressive discovery

**Implementation:** `capabilities/contracts.py`, `capabilities/surface.py`, `capabilities/tools.py`, `providers/platform.py`.

- [ ] RED: runtime provider projection must preserve MCP input schema.
- [ ] RED: exact operation description must return bounded exact metadata with schema.
- [ ] RED: exact/name/capability searches must rank before generic token matches.
- [ ] GREEN: add provider-neutral schema metadata and runtime enrichment.
- [ ] GREEN: implement exact-first description and deterministic search ranking.
- [ ] Run focused capability/provider tests, governance check, diff check, full verifier.
- [ ] Review findings-first, commit, push, exact-head CI, PR merge.
- [ ] Fetch and reconcile merged `main` into this same worktree.

### Batch 2 / PR 2: GitHub semantic composition and workflow contract

**Implementation:** `providers/github/server.py`, `capabilities/resolver.py`, targeted workflow tests/descriptors only if evidence requires.

- [ ] RED: runtime GitHub review/merge/create operations satisfy reviewed semantic capability aliases without a full static catalogue.
- [ ] RED: GitHub Projects read/write operations retain the existing project-management semantics.
- [ ] RED: ineligible workflows are not returned as recommendations.
- [ ] GREEN: add small GitHub provider semantic capability declarations.
- [ ] GREEN: hard-filter workflow recommendations before scoring/return.
- [ ] Verify no change to OAuth lifecycle, repository scope, approval routing, or Project adapter safety.
- [ ] Run focused tests, governance check, diff check, full verifier, review, exact-head CI, PR merge.
- [ ] Fetch and reconcile merged `main` into this same worktree.

### Batch 3 / PR 3: Bounded GitHub result usability and Projects regression audit

**Implementation:** `capabilities/execution.py` and only the minimum GitHub/Project paths proven necessary by tests.

- [ ] Characterize actual FastMCP result shapes for small and oversized provider responses.
- [ ] RED: oversized generic GitHub list/search result exceeds the approved long-tail budget.
- [ ] RED: small response must remain semantically unchanged.
- [ ] GREEN: implement deterministic explicit result budgeting without changing authorization.
- [ ] Run all GitHub Projects inventory/reconciliation regressions and capability UX tests.
- [ ] Re-run user-style audit queries for GitHub, pull requests, Actions, Projects, exact description, and safe-closeout recommendation.
- [ ] Run governance check, diff check, full verifier, review, exact-head CI, PR merge.

### Final closeout

- [ ] Reconcile final `main` and confirm the worktree is clean.
- [ ] Record which attached audit findings are closed, improved, deferred, or outside this programme.
- [ ] Mark change 063 closed only after final merge evidence is recorded.
- [ ] Run post-merge verification and governed cleanup last; no force deletion.
