# MCP 2026 Workflow Prompts Implementation Plan

**Goal:** Complete #589 with thin prompts, deterministic discovery identity, and evidence-backed cache/header decisions.

**Architecture:** Register four FastMCP prompts and one pure discovery-order transform at the existing gateway boundary. Preserve Work as sole workflow authority. Do not add transport routing or persistent cache state.

**Tech stack:** Python 3.13, FastMCP 4.0.0b3, MCP 2026-07-28, pytest, Ruff, KIS change governance.

## Constraints

- Stay inside `scope.json`.
- Do not edit `mcp2026.py` or `SPEC.md` while #628 claims them.
- Do not create a second workflow, policy rule, cache store, or HTTP router.
- Positive cache hints require stale-safe invalidation evidence.

## Tasks

1. Add failing MCP prompt/discovery contract tests.
2. Register thin workflow prompts with explicit Work-authority wording.
3. Add deterministic sorting for tools, prompts, resources, and resource templates.
4. Record cache and header-routing architecture decisions from the pinned runtime.
5. Run focused tests, Ruff, diff/scope checks, KIS verification, and specialist reviews.
6. Commit, prepare exact PR head, require GitHub Actions, merge, reconcile Work/source issue, and clean the worktree.
