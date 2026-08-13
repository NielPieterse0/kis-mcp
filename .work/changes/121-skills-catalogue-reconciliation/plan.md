# Skills Catalogue Reconciliation Implementation Plan

**Goal:** Decouple shared Skill discovery from private KIS capability classification while requiring canonical `kis-mcp`.

## Constraints

- Use only `C:\Projects\.agents\skills` for runtime Skills discovery.
- Do not modify shared skill packages.
- Do not add static capability metadata merely to mirror catalogue membership.
- Do not edit paths owned by active changes 117/120.
- Preserve HR-001 / HR-002 / HR-003.

## Tasks

1. Add RED tests for an unclassified valid Skill and required canonical `kis-mcp`.
2. Add strict JSON/schema support for `required_skills = ["kis-mcp"]` and validate required IDs after each scan.
3. Skip enhanced capability contribution generation when explicit KIS metadata is absent.
4. Preserve a recovery copy and remove the repository-local `.agents/skills/kis-mcp` duplicate.
5. Remove brittle tests that equate private capability metadata cardinality with shared catalogue membership.
6. Add a RED→GREEN CI bootstrap regression and CI-only canonical fixture provisioning in `scripts/verify.ps1`.
7. Run focused verification, PR-context governance, exact-head CI, merge, refresh tracking state, commission `kis-op`, and reconcile Work Management.
