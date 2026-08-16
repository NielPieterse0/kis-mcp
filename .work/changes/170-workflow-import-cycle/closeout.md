# Closeout: Workflow Import Cycle

## Implemented scope

- Replaced eager `kis_mcp.workflows` platform composition with a PEP 562 lazy `workflow_descriptors` export.
- Preserved `from kis_mcp.workflows import workflow_descriptors` while allowing workflow submodules to load without importing `workflows.platform` as a package side effect.
- Added clean-process regression coverage for tools-first, workflows-first, direct public export, and tools-first public-export access.

## Validation evidence

- RED evidence: the initial clean-process regression produced exactly one failure (`import kis_mcp.tools; import kis_mcp.workflows`) with the #271 partial-`tools.platform` circular-import traceback; the other two initial cases passed.
- GREEN evidence: final import-order regression matrix **4/4 passed**.
- Affected suites: `uv run pytest tests/workflows tests/capabilities -q` passed.
- Ruff: `uv run ruff check src/kis_mcp/workflows/__init__.py tests/workflows/test_import_order.py` passed.
- Compile: `uv run python -m compileall -q src/kis_mcp/workflows tests/workflows/test_import_order.py` passed.
- Repository verification: the canonical offline `scripts/verify.py` payload used by `scripts/verify.ps1` ran against `C:\Projects\.kis-mcp\python-env` on the pre-rebase candidate and passed with exit code 0, including line endings, configuration, dependencies, Python syntax, change governance, and the full pytest suite. Direct synchronous wrapper launches returned KIS connector 502s rather than repository failures; duplicate verifier trees from those launches were stopped, and one clean canonical payload run was retained through completion. Because `main` advanced afterwards, exact-head GitHub Actions remains the canonical post-rebase full-suite gate.
- Rebase verification: after rebasing cleanly onto `origin/main` `f917101db714f0f158774659e00bbe8b6d0d4d3e`, the clean-process import regression plus capability suite passed, and Ruff remained clean.
- Diff scope check: passed on the original candidate. After rebase, local `main` was independently divergent from verified `origin/main`, so the change record was corrected to use `origin/main` as its governance base before the final scope check.

## Review

- Codex code-quality review completed with full evidence and **no findings** on the bounded change.
- Reviewer unknowns were limited to non-required introspection/repeated-access cases and lack of supplied execution evidence; execution evidence was subsequently produced, and an additional tools-first public-export regression was added.

## Git and merge

- Branch: `change/170-workflow-import-cycle`
- Worktree: `.work/worktrees/170-workflow-import-cycle`
- Intake base: exact verified `main` `06095474723757657a0bb2a980b8ced31e8b50cf`.
- Publication base after clean rebase: verified `origin/main` `f917101db714f0f158774659e00bbe8b6d0d4d3e`.
- Commit: this reviewed local change is committed after the closeout record; the exact SHA is Git evidence rather than self-referential document content.
- Pull request or merge: not performed.
- Cleanup: pending merge.

## Residual items

- Publication, exact-head GitHub Actions verification, merge, issue #271 closure, and post-merge cleanup remain separate delivery gates.
