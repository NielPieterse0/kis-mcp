# Closeout: Discover Scan Evidence Priority

## Status

Active. Governance artifacts registered before implementation edits.

## Baseline evidence

- Live bounded Discover inspection starved `src` behind auxiliary/hidden trees.
- Current scanner consumes `max_files` and `max_total_bytes` during alphabetical DFS traversal.
- Modularity assessment supports separating traversal safety from evidence selection as independently testable change reasons.

## Verification

- RED: `test_narrow_file_budget_prioritizes_manifest_and_application_source` failed because the old alphabetical DFS returned `.agents/skills/helper.py` and `.archive/legacy.py` instead of `pyproject.toml` and `src/app.py`; `pytest_exit=1`.
- GREEN: the same regression passed after evidence-priority traversal was introduced.
- Focused scanner/priority tests passed.
- Full `tests/discover` plus `tests/architecture/test_modularity_boundaries.py` and `tests/architecture/test_capability_composition_boundaries.py` passed with one existing skip; `pytest_exit=0`.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with all changed paths inside the declared claim.
- `git diff --check`: passed.
- Static Python project review returned zero findings on the final implementation state.
- Simplicity/efficiency review rejected an earlier post-traversal candidate-selection design because it weakened the practical early-stop value of `max_files`; the final design keeps every existing resource bound during traversal and changes only deterministic visitation priority.
- Review also caught and fixed a priority-precedence defect that would have promoted auxiliary `.agents/.../SKILL.md` files as generic Markdown; an explicit regression now preserves auxiliary paths at the lowest tier.
- Exact-head local repository verification initially exposed an unrelated overbroad Skills-root guard: both `scripts/verify.ps1` and `tests/test_repository_scope.py` treated any `.agents` path label as a runtime Skills-root reference. RED evidence reproduced both failures; the guard now targets `.agents\\skills` references only while retaining canonical-root validation.
- Fresh final `scripts/verify.ps1` passed on the amended worktree: configuration, line endings, interpreter, dependencies, Python syntax, change governance, full pytest, and verification all green.

## Landing

Pending amended commit publication, exact-head remote Work Management verification, merge, and governed closeout.
