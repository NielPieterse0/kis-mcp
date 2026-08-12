# Closeout: Python Quality Tooling Evidence

## Implemented scope

- Added deterministic `pyproject.toml` parsing with stdlib `tomllib` for recognized Python quality tooling.
- Added normalized evidence for Ruff, coverage.py/pytest-cov, Vulture, LibCST, mypy, and Pyright with stable ordering, declaration source, role, confidence, and optional verification handoff.
- Added discovered-only Ruff, coverage, Vulture, mypy, and Pyright verification declarations with `execution_available=false`.
- Preserved LibCST as evidence-only with no executable verification declaration.
- Added malformed-TOML isolation so unrelated verification discovery continues with `WORKFLOW_PYPROJECT_INVALID`.

## Validation evidence

- Focused checks: `pytest -q tests/discover/test_verification_discovery.py` -> 7 passed.
- Scope: `scripts/change-workflow.ps1 check` passed for the seven registered 096 paths; `git diff --check` passed.
- Canonical verification: `scripts/verify.ps1` passed on the corrected exact worktree state; full pytest exit 0 with two expected skips, Python syntax/configuration/dependency/change-governance checks all green.

## Review

- Manual requirements/diff review found no blocking defect after the Pyright handoff correction; parsing remains structural/non-executing and additive.
- NVIDIA NIM `super` review was attempted and failed before findings with `AGENT_BACKEND_FAILED:NvidiaNimError`; no NVIDIA pass is claimed.
- Codex CLI review was attempted and failed before findings with `AGENT_BACKEND_FAILED:CodexCliError`; no Codex pass is claimed.
- Reviewer-runtime failures are recorded as an availability limitation, not represented as successful independent review.

## Git and merge

- Branch: `change/096-python-quality-tooling-evidence`.
- Worktree: `.work/worktrees/096-python-quality-tooling-evidence`.
- Implementation commit: `24cdd8a1db2b35bb28c1c935ef539080acd64093`.
- Implementation PR: #111, merged on 2026-08-12 at the exact approved head `24cdd8a1db2b35bb28c1c935ef539080acd64093`.
- The implementation remote branch was deleted only at that verified head, with recovery SHA retained by the registered GitHub operation.
- This closeout-only reconciliation records `status=closed`; its exact PR merge, final verifier, branch removal, and governed local cleanup are retained in the reconciliation PR timeline to avoid a recursive post-merge edit.

## Residual items

- This slice discovers declared tooling only; installation, executable availability, change-aware verification selection, workflow execution, and broader orchestration remain later slices.
- Parallel change worktrees were not modified by 096; at closeout time `098-specialist-review-purposes` is independently active.
