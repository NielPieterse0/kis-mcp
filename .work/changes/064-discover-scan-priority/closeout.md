# Closeout: Discover Scan Evidence Priority

## Status

Closed after exact-head verification and PR #81 merge.

## Baseline evidence

- Live bounded Discover inspection starved `src` behind auxiliary/hidden trees.
- The scanner consumed `max_files` and `max_total_bytes` during alphabetical DFS traversal.
- Modularity assessment supported separating traversal safety from evidence selection as independently testable change reasons.

## Verification

- RED: `test_narrow_file_budget_prioritizes_manifest_and_application_source` failed because the old alphabetical DFS returned `.agents/skills/helper.py` and `.archive/legacy.py` instead of `pyproject.toml` and `src/app.py`; `pytest_exit=1`.
- GREEN: the same regression passed after evidence-priority traversal was introduced.
- Focused scanner/priority tests passed.
- Full `tests/discover` plus `tests/architecture/test_modularity_boundaries.py` and `tests/architecture/test_capability_composition_boundaries.py` passed with one existing skip; `pytest_exit=0`.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with all changed paths inside the declared claim.
- `git diff --check`: passed.
- Static Python project review returned zero findings on the final implementation state.
- Simplicity/efficiency review rejected an earlier post-traversal candidate-selection design because it weakened the practical early-stop value of `max_files`; the final design keeps every existing resource bound during traversal and changes only deterministic visitation priority.
- Review caught and fixed a priority-precedence defect that would have promoted auxiliary `.agents/.../SKILL.md` files as generic Markdown; an explicit regression preserves auxiliary paths at the lowest tier.
- Exact-head local repository verification initially exposed an unrelated overbroad Skills-root guard in `scripts/verify.ps1` and `tests/test_repository_scope.py`; the guard was narrowed to `.agents\\skills` references and regression-tested.
- Final implementation head `1175e37c9a9e8e91273552443c224df13cbba626` passed Work Management run #18 with settings validation, governance validation, focused P5 tests, and canonical repository verification.
- This metadata-only closeout must pass a fresh exact-head Work Management run before merge; the run result belongs in PR/merge evidence so the verified tree is not edited afterward.

## Landing

- Pull request: #81, `Prioritize Discover scan evidence under tight budgets`.
- Exact tested implementation head: `1175e37c9a9e8e91273552443c224df13cbba626`.
- Exact-head Work Management run #18: success.
- GitHub merge commit: `2aa0717b8bec59d0509ad0ce6140cc5b631edcf6`.
- The implementation branch was fast-forwarded to the merged result before this metadata-only closeout; no history rewrite or forced ref update was used.
- Governed worktree cleanup becomes eligible after this closeout lands and local refs are synchronized.

## Recovery

- Revert PR #81 to restore the prior traversal order and verifier behavior; no settings, policy, schema, or state migration is involved.
- Reverting this closeout metadata does not change runtime behavior.

## Residual items

- Local worktree removal remains subject to the repository cleanup command proving a clean worktree, closed claim, and merged ancestry; no force deletion is authorized.
