# Change Specification: Python Quality Tooling Evidence

- **Change ID**: `096-python-quality-tooling-evidence`
- **Status**: Approved by operator continuation request
- **Development level**: Small — additive read-only Discover evidence only
- **Risk Profile**: lean

## Outcome

Add deterministic Discover evidence for declared Python quality tooling (Ruff, coverage.py/pytest-cov, Vulture, LibCST, and type checking) and safe non-executing verification declarations without installing or executing project tooling.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, and the approved continuation boundary recorded by change 093.
- Owned paths: exactly those recorded in `scope.json`.
- Shared paths: none.
- Excluded paths: all active 095-owned paths and any policy/runtime-execution surface not explicitly owned here.
- Dependencies: none; Python 3.11 `tomllib` only.
- Integration owner: none; this slice must merge and clean independently.

## Requirements

- **REQ-001 Standard declaration parsing:** read `pyproject.toml` with stdlib TOML parsing and normalize Python package names from project dependencies, optional dependencies, and dependency groups without executing repository code.
- **REQ-002 Quality-tool evidence:** report deterministic evidence for declared/configured Ruff, coverage.py or pytest-cov, Vulture, LibCST, and supported type checkers with explicit role, declaration source, confidence, and optional verification ID.
- **REQ-003 Stable verification handoffs:** emit discovered-only verification declarations only where a stable non-shell command exists: Ruff lint, coverage/pytest-cov test coverage, Vulture dead-code analysis, and mypy/pyright type checking.
- **REQ-004 LibCST boundary:** represent LibCST as concrete-syntax/refactor capability evidence but do not invent an executable verification command or import/execute LibCST.
- **REQ-005 Determinism and compatibility:** identical repository evidence yields stable ordering and IDs; existing verification declarations and public response behavior remain additive and backward compatible.
- **REQ-006 Failure isolation:** malformed `pyproject.toml` produces a bounded Discover diagnostic and does not prevent unrelated PowerShell/Node/CI workflow discovery.
- **REQ-007 Authority:** Discover does not install packages, execute tools, widen Work authority, or add policy decisions.

## Acceptance

1. A project declaring Ruff, coverage.py/pytest-cov, Vulture, LibCST, and a type checker returns normalized quality-tool evidence in stable order.
2. Ruff, coverage, Vulture, and type-checker declarations produce fixed discovered-only verification handoffs with `execution_available=false`.
3. LibCST evidence has no verification ID and cannot become executable through this slice.
4. Config-only declarations are distinguishable from dependency-backed declarations and use lower confidence where appropriate.
5. Invalid TOML yields `WORKFLOW_PYPROJECT_INVALID` while unrelated workflow discovery continues.
6. Existing verification-discovery tests, change scope validation, and canonical repository verification pass.

## Risks and recovery

- Risk: loose text matching could generate false tool evidence. Mitigation: parse TOML structurally and normalize only recognized package/config keys.
- Risk: a declared dependency may not be installed locally. Mitigation: all declarations remain `discovered_only`; availability/execution belongs to later Work slices.
- Recovery: revert the slice merge; no generated-state or dependency migration is introduced.

## Out of scope

- Installing or locking Ruff, coverage.py, Vulture, LibCST, mypy, pyright, or any other package.
- Executing quality tools, choosing which quality checks apply to a change, or enforcing pass/fail policy (later verification-selection/workflow slices).
- agnix integration, workflow orchestration, closeout automation, or policy changes.
