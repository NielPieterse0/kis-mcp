# Skills MCP Resources Implementation Plan

**Goal:** Deliver #313 as a native read-only MCP resource surface over the existing validated Skills snapshot.

**Architecture:** Add a thin `skills.resources` registration layer. It exposes an index plus two URI templates and obtains bytes through a new snapshot-verified catalogue read primitive. `skills.platform` registers the resources beside existing tools. No new catalogue or mutation service is introduced.

**Tech Stack:** Python 3.11, FastMCP resource APIs, pytest, existing KIS Skills catalogue.

## Global constraints
- Stay inside `scope.json` and revalidate any scope expansion first.
- Add failing behavior tests before implementation.
- Preserve exact HR-001/002/003 semantics and existing Skills mutation behavior.
- Treat scripts/assets as bytes only; never execute them.

### Task 1 — Resource contract and integrity [REQ-001..006]
- Add failing FastMCP tests for index, entrypoint, nested resource, binary bytes, traversal, and stale hash.
- Add snapshot-verified byte reads to `SkillCatalogue`.
- Implement and register the `skill:///` index and URI templates.
- Evidence: focused `tests/skills/test_resources.py` plus architecture tests.

### Task 2 — Compatibility and documentation [REQ-007..008]
- Prove existing Skills tools still compose unchanged.
- Update the durable Skills module spec with resource identities, progressive disclosure, and no-execution authority.
- Evidence: affected Skills/gateway tests and documentation/API review.

### Task 3 — Review and verification [REQ-001..008]
- Run `change-workflow.ps1 check`, focused tests, architecture and API-contract reviews.
- Resolve blocking findings and rerun affected checks before publication.