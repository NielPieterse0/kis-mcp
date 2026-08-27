# Merge Queue Concurrency Safe Implementation Plan

**Goal:** Make merge-queue state mutation concurrency-safe for Work #549 without reducing liveness for disjoint queue identities.

**Architecture:** Add a per-queue cross-process lock file derived from the queue state identity and hold it across each same-identity state mutation transaction. Preserve existing atomic `os.replace` publication and queue semantics.

**Tech Stack:** Python 3.13, `msvcrt` on Windows / `fcntl` on Unix, pytest, Ruff, KIS change governance.

## Constraints

- Stay inside `scope.json`.
- Test the race before implementation.
- Do not change Work, GitHub, or merge-policy authority.
- Do not serialize disjoint queue identities.

## Tasks

1. Reproduce concurrent enqueue corruption/collision with a deterministic regression.
2. Add per-identity cross-process mutation locking.
3. Apply the lock to enqueue, dequeue, reconcile, and landing mutations.
4. Prove disjoint identities remain concurrent.
5. Run focused tests, governance checks, specialist review, then exact-head PR verification.
