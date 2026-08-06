# GitHub Project Inventory Implementation Plan

**Goal:** Add bounded read-only GitHub Project inventory behind provider-neutral contracts.

**Architecture:** A small `work_management.backend` contract defines normalized inventory. A GitHub-specific adapter invokes an injected async tool caller using only `projects_get` and `projects_list`. Provider metadata advertises exact read operations. Public composition remains deferred.

**Tech stack:** Python 3.11+, dataclasses, enums, protocols, pytest, pinned official GitHub MCP contracts.

## Global constraints

- Stay inside `scope.json`.
- Use failing tests before production changes.
- Perform no live mutation.
- Add no dependency or settings change.
- Keep domain contracts independent of FastMCP and Providers.
- Bound pagination, output, and error evidence.

## Task 1: Provider-neutral inventory contracts

- Write failing tests for Project binding, fields, options, items, pages, inventory, and backend protocol.
- Implement `backend.py` and shared package exports.
- Extend the P0 architecture test without weakening its original boundary.
- Run focused tests and repository verification.

## Task 2: GitHub read adapter

- Write failing adapter tests using representative pinned response fixtures.
- Implement exact `projects_get` and `projects_list` calls.
- Implement bounded pagination, normalization, truncation, and redacted errors.
- Prove the adapter imports domain contracts but the domain imports no provider code.
- Run focused tests and repository verification.

## Task 3: Provider capability metadata

- Write failing descriptor tests for a separate read-only Project capability.
- Add exact tool names `projects_get` and `projects_list` without removing repository capability.
- Prove capability composition namespaces both operations and classifies them read-only/external.
- Run focused tests and full repository verification.

## Task 4: Review and programme reconciliation

- Run findings-first review of contracts, pagination, response ambiguity, and capability effects.
- Fix blocking findings with regression tests.
- Update shared programme phase and closeout evidence.
- Keep P2 and all remote mutations explicitly deferred.
