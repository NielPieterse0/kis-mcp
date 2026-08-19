# Change: Github Closing Keyword Guard

- **Change ID**: `203-github-closing-keyword-guard`
- **Risk Profile**: lean

## Outcome

Reject GitHub issue-closing keyword references in registered pull-request bodies and commit messages before merge execution while preserving normal issue references and Work Management terminal authority.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- At the registered merge boundary, reject issue-closing references in PR bodies and commit messages before `gh pr merge` can execute.
- Cover `close/closes/closed`, `fix/fixes/fixed`, and `resolve/resolves/resolved`, case-insensitively, for both `#N` and `owner/repo#N` references.
- Preserve ordinary non-closing issue references and all existing approval, exact-head, state, and merge-method gates.
- Work Management remains the sole terminal-completion authority; this change must not close #364 or #379.
- Keep #379 open through implementation and commissioning. After Change 203 lands, a fresh governed merge must prove its source issue remains open before the premature-close defect can be treated as resolved.
- Defense-in-depth follow-up only: consider the repository-level GitHub setting that disables automatic closing of linked issues. Change 203 does not depend on that setting.

## Implementation and verification

- Implementation notes: merge-time PR inspection now includes commit metadata and rejects detected closing references after existing exact-head/open/non-draft gates and before merge execution.
- Focused checks: 103 tests passed in `tests/workflows/test_registered_commit_publication.py`; Ruff, diff hygiene, and governed scope checks are clean. Coverage includes all registered keyword/reference/case combinations, whitespace separators, normal-reference negatives, merge-boundary rejection, and malformed PR-view payloads.
- Specialist review: code-quality and required API-contract review are clean on the final implementation/test content. Test-quality review has no blocking findings; its remaining `body=None` / `commits=None` suggestions are low-severity edge-case coverage only. An additional NVIDIA security review was attempted but the provider failed/timed out and is not a configured Change 203 gate.
- Residual risk: GitHub may introduce additional closing syntax in the future; this guard intentionally implements only the registered Change 203 pattern families and reference forms.
- Closeout state: final immutable-head publication, exact-head GitHub Actions, landing, and post-landing fresh governed merge commissioning proof remain required; #379 remains open.
