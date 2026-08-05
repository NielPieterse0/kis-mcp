# Discover Impact Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task-by-task. Keep `tasks.md` current and review after every task.

**Goal:** Extend bounded local Discover impact analysis with the remaining deterministic architecture, dependency, and change-impact value from the pinned donor branch.

**Architecture:** Add a focused `discover.analyzers` package containing immutable analysis context/output contracts, a deterministic registry, an ordered pipeline, and separate repository-map, architecture, dependency, and impact analyzers. `ImpactGraphService` remains the coordinator and converts analyzer output into the existing provider-neutral impact response.

**Tech Stack:** Python 3.11+, standard library only, existing Discover scanner/read authority/Python AST index/verification contracts, pytest.

## Global constraints

- Write only inside `C:\Projects\kis-mcp\.work\worktrees\032-discover-impact-parity`.
- Use no network, subprocess, repository import, target-code execution, donor runtime dependency, new package dependency, or policy change.
- Preserve deterministic ordering, configured Discover budgets, explicit diagnostics/unknowns/truncation, and existing response identity.
- Add failing tests before each behavior change and run the exact external project interpreter through repository scripts.

---

### Task 1: Analyzer contracts, registry, and ordered pipeline

**Files:**
- Create: `src/kis_mcp/discover/analyzers/__init__.py`
- Create: `src/kis_mcp/discover/analyzers/contracts.py`
- Create: `src/kis_mcp/discover/analyzers/registry.py`
- Create: `src/kis_mcp/discover/analyzers/pipeline.py`
- Test: `tests/discover/impact_parity/test_analyzer_pipeline.py`

**Interfaces:**
- Consumes: existing repository snapshot, read authority, Python index result, verification declarations, changed paths, and bounded analyzer options.
- Produces: `AnalysisContext`, `AnalyzerOutput`, `AnalyzerRegistry`, `PipelineResult`, and `run_pipeline(ids, context, registry)`.

- [ ] Write tests proving deterministic registration, duplicate/unknown rejection, immutable prior outputs, output identity checking, deduplicated unknowns, and aggregate truncation.
- [ ] Run the focused test file and confirm the new package is missing.
- [ ] Implement the minimal contracts, registry, and pipeline.
- [ ] Run the focused test file and confirm it passes.

### Task 2: Repository-map and architecture-component analyzers

**Files:**
- Create: `src/kis_mcp/discover/analyzers/repository_map.py`
- Create: `src/kis_mcp/discover/analyzers/architecture.py`
- Test: `tests/discover/impact_parity/test_architecture_analyzer.py`

**Interfaces:**
- Consumes: `AnalysisContext.snapshot` and prior `repository.map` output.
- Produces: deterministic file/category facts and bounded component records `{id, path, kind, files}`.

- [ ] Write fixture tests for root files, `src/<unit>`, `packages/<unit>`, `services/<unit>`, and deterministic truncation.
- [ ] Run the focused tests and confirm analyzer resolution fails.
- [ ] Implement repository map and architecture grouping with explicit prerequisite validation.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Python and JavaScript/TypeScript dependency analyzer

**Files:**
- Create: `src/kis_mcp/discover/analyzers/dependencies.py`
- Test: `tests/discover/impact_parity/test_dependency_analyzer.py`

**Interfaces:**
- Consumes: safe `ReadAuthority.read_relative_text`, repository snapshot, Python index imports/modules, architecture output, configured edge/read limits.
- Produces: deterministic local dependency records `{source, target, kind, line}`, diagnostics, unknowns, and truncation.

- [ ] Write tests for Python imports, JS/TS relative imports, extension and `index` resolution, `require`, export-from, dynamic imports, unresolved/external targets, malformed Python evidence, and max-edge truncation.
- [ ] Run the focused tests and confirm the analyzer is absent.
- [ ] Implement static parsing only; do not execute or import target code.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Change-impact analyzer and service integration

**Files:**
- Create: `src/kis_mcp/discover/analyzers/change_impact.py`
- Modify: `src/kis_mcp/discover/impact_graph.py`
- Modify only if required without changing response identity: `src/kis_mcp/discover/impact_contracts.py`
- Test: `tests/discover/impact_parity/test_change_impact_parity.py`
- Test: `tests/discover/test_impact_graph.py`
- Test: `tests/discover/test_impact_determinism.py`

**Interfaces:**
- Consumes: repository-map, architecture, dependency, Python symbol/call/inheritance, changed-path, and verification evidence.
- Produces: direct and bounded transitive reverse dependants, affected components/tests, category impact, explicit uncertainty, and existing `InspectImpactResponse` records.

- [ ] Write tests for direct and transitive dependency impact, JS/TS dependants, component impact, contract/configuration/documentation/test categories, unknown task-token impact, and deterministic bounds.
- [ ] Run the focused tests and confirm they fail on current Python-only behavior.
- [ ] Implement the analyzer and integrate it into `ImpactGraphService` while preserving current Python evidence and fingerprints.
- [ ] Run all impact tests and confirm they pass.

### Task 5: Donor traceability and slice verification

**Files:**
- Modify: `docs/development/discover-foundation/source-harvest.md`
- Modify: `.work/changes/032-discover-impact-parity/tasks.md`
- Modify: `.work/changes/032-discover-impact-parity/closeout.md`

- [ ] Replace unsupported `ee18566` references with recoverable pinned evidence and add the `a6af216` change-impact harvest matrix.
- [ ] Search the worktree for stale donor revision and runtime-coupling claims.
- [ ] Run `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check`.
- [ ] Run focused Discover tests, then `pwsh -NoProfile -File .\scripts\verify.ps1` with no concurrent verification.
- [ ] Review the full diff for scope, modularity, security, simplicity, deterministic behavior, and donor independence.
- [ ] Record exact evidence and commit the slice.
