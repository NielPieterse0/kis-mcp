# Capability Composition and Tool Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use test-driven development for every behavior change and verification-before-completion before each commit or completion claim.

**Goal:** Build a modular capability composition and progressive tool-experience layer while preserving the exact three-rule Work boundary.

**Architecture:** Domain platform entry points emit normalized immutable contributions. A capability service composes catalogue, readiness, eligibility, scoring, workflow resolution, and exposure into instance-scoped runtime state. Gateway composition consumes only domain platform entry points and exposes a curated direct surface plus discovery operations.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, dataclasses, strict JSON settings/contracts, pytest, PowerShell verification.

## Global Constraints

- Write only beneath `C:\Projects`; no external network access through Work; no permanent deletion.
- Keep policy decisions limited to HR-001, HR-002, and HR-003.
- Preserve provider failure containment and current middleware order.
- Add no runtime dependency.
- Leave the deferred 040 worktree and Context7/Serena implementation untouched.
- Use versioned JSON for scoring and exposure configuration.
- Validate original operation schemas; never weaken adapter validation through generic parameters.

## Tasks

### Task 1: Characterization and governance repair
Create failing characterization tests for current tool contracts, annotations, middleware ordering, provider readiness semantics, and startup composition. Close stale merged claims 041/046 and validate the 047 worktree.

### Task 2: Capability contracts and settings
Add immutable domain, operation, dependency, readiness, exposure, quality, workflow, recommendation, and runtime-state contracts plus strict versioned JSON settings/schema and focused tests.

### Task 3: Catalogue, readiness, eligibility, and scoring
Implement deterministic composition, readiness normalization, hard eligibility filters, intrinsic quality, contextual suitability, and explainable reasons through TDD.

### Task 4: Domain platform entry points
Add/extend `providers/platform.py`, generic `tools/platform.py`, `discover/platform.py`, `skills/platform.py`, and `workflows/platform.py`. Enforce complete contribution metadata and capability-bearing Skills.

### Task 5: Workflow-first resolver and exposure planner
Implement capability search, description, workflow recommendation, curated direct exposure, long-tail suppression, unavailable-operation suppression, and explicit-request preservation.

### Task 6: Instance-scoped gateway composition
Move composition from `server.py` into `gateway/`, eliminate global latest-provider state, preserve middleware and failure containment, and expose discovery operations through FastMCP.

### Task 7: Architecture and regression enforcement
Add AST and behavior tests proving domain boundaries, platform-only gateway imports, no adapter-internal workflow dependencies, no policy override, metadata completeness, and direct-profile controls.

### Task 8: Documentation reconciliation and final verification
Update authoritative/current-state documentation without overstating implementation, run focused and full verification, review the complete diff, record closeout, commit, push, create PR, resolve findings, and prepare exact-head landing.
