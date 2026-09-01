# Closeout: SEP-2640 Skills Extension

## Implemented scope

- Added a native FastMCP `io.modelcontextprotocol/skills` extension over the existing immutable KIS Skills catalogue.
- Added negotiated `skills/list`, URI-keyed `skills/get`, direct `skill:///` resource reads, and optional direct-child `resources/directory/read`.
- Added complete per-resource SHA-256/size manifests, snapshot-drift rejection, host-side manifest verification, and server+skill-URI+resource-set approval fingerprints.
- Pinned compatibility behavior to draft baseline `draft-v1-2026-08-25` and enforce the draft 512-resource / 16 MiB interoperability bounds without making one incompatible skill disable the wider Skills/gateway runtime.
- Reconciled the durable Skills module product specification and architecture dependency contract.
- No changes were made beneath `src/kis_mcp/workflows/once_through/**`.

## Validation evidence

- `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests\skills -q` — PASS, 91 tests.
- `pwsh -NoProfile -File scripts\change-workflow.ps1 check` — PASS; all changed paths are governed.
- Focused SEP-2640 + architecture suite — PASS, 15 tests after current-draft reconciliation.
- Canonical full-repository verification is intentionally deferred to provider-native GitHub Actions on the exact PR head per `AGENTS.md`.

## Review

- Final exact-source architecture review: PASS with no findings at source fingerprint `88ed6bfd24a7e7d8eea718308734b36cd1434277913ad7572066ba6d33a812f3`.
- Earlier architecture review identified two issues. The documentation baseline mismatch was fixed. The proposed fail-fast registration for oversized skills was resolved differently to preserve the repository's fail-open Skills availability contract: oversized skills are omitted from `skills/list` and rejected by `skills/get`, while the wider gateway remains available.
- Safety/security and API-contract reviewer routes encountered provider 502/unusable-output failures. Manual exact-diff review covered URI parsing/traversal, snapshot drift, complete manifests, unlisted/digest/size/frontmatter rejection, negotiation/version gating, server+URI approval identity, interoperability bounds, and no implicit execution authority; no blocking finding remains.
- Upstream draft drift discovered during review was incorporated before publication: resource sizes, fixed interoperability bounds, `resultType`, and server+URI skill identity are reflected in the implementation.

## Git and merge

- Branch: `change/611-sep2640-skills-extension`
- Worktree: `.work/worktrees/611-sep2640-skills-extension`
- Commit: pending publication workflow
- Pull request / exact-head Actions / merge: pending
- Cleanup: pending verified merge

## Residual items

- SEP-2640 remains a draft upstream contract. Future upstream changes may require a bounded compatibility update; the implementation isolates that surface in `skills.sep2640` and advertises its pinned baseline.
