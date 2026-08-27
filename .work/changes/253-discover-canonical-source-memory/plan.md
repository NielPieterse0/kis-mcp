# Discover Canonical Source Memory Implementation Plan

**Goal:** Route Discover persisted generations through the canonical source-scoped KIS state namespace with identity-safe legacy compatibility.

**Architecture:** Keep Discover atlases reconstructible and repository/Git evidence authoritative. Resolve production persistence through `StateNamespaceResolver` using `reconstructible-cache`, registered `project_id`, canonical `source_id`, and one Discover state key. Retain the prior Discover namespace as compatibility-only evidence; migrate only a generation whose complete applicability fingerprint matches current project/source/Git/settings/provider identity.

**Tech Stack:** Python, shared `EvidenceStore`, canonical KIS state resolver, pytest, Ruff, governed change workflow.

## Global constraints
- Stay inside `scope.json`.
- Do not create a second production namespace model.
- Do not delete legacy state.
- Preserve existing applicability, corruption recovery, generation retention, and deterministic rebuild semantics.

## Tasks
- [x] Establish canonical source-scoped namespace resolution for Discover generations.
- [x] Preserve test injection without changing production authority.
- [x] Recover identity-safe legacy generations into the canonical namespace.
- [x] Retain mismatched or corrupt legacy state without trusting it.
- [x] Prove repository and linked-worktree isolation.
- [x] Reconcile current implementation truth in `SPEC.md`.
- [x] Run focused Discover/state verification and scope checks.
- [ ] Complete specialist review, publication, exact-head CI, merge, commissioning, and Work closeout.
