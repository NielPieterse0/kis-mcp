# SEP-2640 Skills Extension Implementation Plan

**Goal:** Implement #569 over the existing immutable KIS Skills catalogue with no duplicate authority or execution path.

**Architecture:** Register one FastMCP `ServerExtension` for SEP-2640 methods and one read-only direct-resource provider backed by `SkillCatalogue`. Keep validation, snapshot identity, mutation routing, and telemetry in their existing owners.

**Tech stack:** Python, FastMCP 4, MCP 2026-07-28 extension API, pytest, repository governance scripts.

## Constraints

- Stay inside `scope.json`; do not touch `once_through/**`.
- Preserve HR-001/HR-002/HR-003 semantics and existing Skills mutation paths.
- Treat the upstream SEP as a draft external contract and isolate compatibility code.
- Prefer focused verification locally; exact-head canonical verification belongs to GitHub Actions.

## Tasks

1. Add failing contract tests for extension advertisement, list/get, direct resources, directory reads, negotiation, and snapshot drift.
2. Implement `skills.sep2640` using FastMCP's native extension API.
3. Add complete file digests/sizes and host-side content-bound verification/reapproval helpers.
4. Integrate registration through `skills.platform` and update architecture dependency expectations.
5. Reconcile the durable Skills module product specification and governed change records.
6. Run focused Skills tests, scope check, specialist review, then prepare the exact review head for provider-native verification and landing.
