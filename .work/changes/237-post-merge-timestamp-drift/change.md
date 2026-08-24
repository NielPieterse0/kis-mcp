# Change 237 — Post-merge timestamp drift

Issue: #482

## What changes

- Accept provider/Git merge timestamp drift under 60 seconds.
- Reject drift of 60 seconds or more.
- Keep all existing PR/head/source-SHA/`web-flow`/scope/Work identity checks unchanged.
- Update the matching product and operator wording.

## Why

Live acceptance of Change 236 found a legitimate merge where GitHub PR `merged_at` was `23:09:53Z` and the matching GitHub `web-flow` merge commit was `23:09:52Z`. Exact-second equality incorrectly rejected it.

## Verification

- Tests cover accepted sub-minute drift and exact 60-second rejection in both directions.
- Run the post-merge commissioning suite, Ruff, diff check, and change-governance checks before publication.
- After landing, verify the live `kis-op` observer no longer wedges on this timestamp difference.
