# Implementation Plan: Discover Scan Evidence Priority

## Goal

Separate safe candidate traversal from deterministic evidence-budget selection so constrained scans keep manifests and application source without weakening repository safety.

## Architecture

`RepositoryScanner` remains the filesystem authority and keeps applying file/byte budgets during traversal. A new pure `scan_selection.py` provides deterministic generic path-priority ordering so the scanner visits root project markers and conventional application source before auxiliary trees. Scanner retains its existing early-stop resource semantics and returns files in the existing lexical output order.

## Tasks

### T1 — RED integration regression
- Add a scanner test with hidden auxiliary files before `pyproject.toml` and `src/app.py` alphabetically.
- Constrain `max_files=2`.
- Verify current scanner selects auxiliary files and the new expected high-value set fails.

### T2 — Pure evidence-priority seam
- Add deterministic `evidence_path_priority(label)` with small conventional path tiers.
- Priority: root project markers/instructions; conventional application source roots; tests/contracts/configuration; docs; ordinary project files; hidden/archive/auxiliary paths.
- Tie-break by case-folded label.
- Unit-test ranking, stable ties, and `.github` configuration treatment independently of filesystem traversal.

### T3 — Integrate priority into scanner traversal
- Use the pure priority key when sorting each bounded `os.scandir` batch.
- Preserve existing per-file, file-count, total-byte, depth, directory, visited-entry, and timeout enforcement during traversal.
- Preserve lexical final output ordering and directory/exclusion behavior.
- Record the review correction that rejected post-traversal candidate selection because it would weaken the efficiency value of `max_files`.

### T4 — Review and verify
- Run focused selector/scanner tests.
- Run full Discover + architecture-boundary suites.
- Repair the repository Skills-root verifier if generic `.agents` evidence triggers its guard; keep the guard specific to `.agents\\skills` root references and add regressions.
- Run governed scope check and `git diff --check`.
- Static/code/simplicity review final diff.
- Commit, push, PR, exact-head Work Management full verification, merge, governed closeout.

## Recovery

One bounded revert removes the selector seam and restores traversal-time budgeting. No config, schema, or state migration.
