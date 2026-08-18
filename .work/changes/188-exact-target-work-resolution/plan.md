# Exact Target Work Resolution Plan

1. Port only the proven historical service/test behavior from `af501c9` onto fresh reconstructed `main`.
2. Run focused Work Management tests and Ruff for the touched files.
3. Run `change-workflow.ps1 check`.
4. Freeze one commit, run required review, publish PR, and use GitHub Actions as the single canonical repository verification gate.
5. Merge exact head, align `main`, close issue #358, clean branch/worktree, then activate Change 189.