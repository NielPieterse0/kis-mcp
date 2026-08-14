# Canonical Skills Module Only Implementation Plan

**Goal:** Remove repository-local skill packages and make the KIS Skills module the sole supported agent-facing skill access path.

**Architecture:** Keep the existing shared Skills runtime unchanged. Change only repository authority, current documentation, CI preparation, verification guards, fixtures, and the tracked local copies. Historical change evidence remains historical.

**Tech Stack:** Markdown authority, PowerShell verification/CI, Python pytest, Git change governance, KIS Skills module.

## Requirements mapping

- REQ-001 → recoverably remove tracked local skill packages; verify Git index after staging/commit.
- REQ-002/003 → update `AGENTS.md`, README, current Skills/product/operations documentation.
- REQ-004 → remove CI copy-from-checkout behavior; keep CI canonical fixture provision in verification.
- REQ-005 → add repository-scope and verifier guards; neutralize test fixtures that imply a local catalogue.
- REQ-006 → no runtime policy or Skills service behavior change.

## Tasks

1. Add a failing repository-scope test proving local skill packages are still tracked.
2. Reconcile already-merged change 120's stale lifecycle claim so formerly-owned current files can be changed safely.
3. Move the repository-local skill tree intact to quarantine so Git records recoverable deletions.
4. Replace current direct-path skill guidance with canonical Skills-module operations and canonical skill IDs.
5. Remove CI dependence on copying repository-local skill content and add verification guards against reintroduction.
6. Update affected fixtures without changing Discover priority semantics or Skills root validation behavior.
7. Run focused tests, scope/governance checks, specialist review, and the repository verification path appropriate to the PR lifecycle.

## Recovery

Restore the quarantined tree only if rollback is required before merge. After merge, Git history remains the authoritative recovery source for removed tracked content.
