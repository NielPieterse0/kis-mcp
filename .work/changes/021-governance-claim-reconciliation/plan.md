# Plan

1. Confirm every active/ready claim in the current checkout against `origin/main` merge ancestry.
2. Close only records whose branch heads are already merged.
3. Make the current checkout authoritative and load only each linked worktree's own claim when absent.
4. Preserve explicit underscore-template exclusion with focused regression tests.
5. Run focused tests, governance validation, scope enforcement, syntax, JSON, and whitespace checks.
6. Review and publish the point-3-only diff.
