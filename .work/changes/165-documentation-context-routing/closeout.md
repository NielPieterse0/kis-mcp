# Closeout: Documentation Context Routing

## Implemented scope

- Replaced unconditional six-document loading in `AGENTS.md` with explicit precedence plus task/path applicability routing.
- Preserved repository workflow, documentation ownership, Skills routing, HR-001/HR-002/HR-003, isolated worktrees/path claims, exact-head verification, repository standards, and closeout gates.
- Removed current-capability/provider/status duplication from `docs/PLATFORM-CONCEPT.md`; `SPEC.md` is now the explicit owner of current implementation truth throughout that target document.
- Made no source, test, policy, settings, operations-runbook, module-spec, or `SPEC.md` change.

## Context reduction

- `AGENTS.md`: 19,294 -> 10,149 bytes, a 9,145-byte / 47.4% reduction.
- `docs/PLATFORM-CONCEPT.md`: 27,329 -> 18,284 bytes, a 9,045-byte / 33.1% reduction.
- Combined changed durable docs: 46,623 -> 28,433 bytes, a 18,190-byte / 39.0% reduction.
- The previous six-owner traversal totalled 191,748 bytes. Only `AGENTS.md` plus the active change record are now unconditional; other canonical owners are loaded by applicability.

## Validation evidence

- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed; only declared owned paths changed.
- `python -m pytest tests/test_repository_scope.py -q`: 17 passed.
- `python -m pytest tests/govern/test_governance_evidence.py tests/govern/test_governance_service.py -q`: 7 passed.
- Canonical full repository verification remains owned by the pull-request workflow on the exact GitHub head.

## Review and delivery gates

Exact-source documentation and architecture reviews are required before publication because this slice changes authority routing. Their returned KIS evidence is authoritative and is not copied back into this file after source freeze, which would invalidate the reviewed fingerprint.

Git commit, pull-request head, GitHub Actions verification, merge readiness, merge, and cleanup are likewise authoritative in Git/KIS/GitHub rather than duplicated into this historical record after source freeze.

## Recovery

Revert the documentation change commit. No runtime state, schema, migration, policy value, credential, or product behavior is changed.

## Residual items

- `SPEC.md` simplification is deliberately deferred because active change 159 owns it.
- `docs/OPERATIONS.md` remains unchanged and authoritative for operator procedure; it is no longer mandatory context for unrelated implementation slices.
- Machine-generated path-to-context routing is not introduced here. Consider it only as a separate bounded slice if measured manual routing remains costly.
- Historical `docs/development/**` records remain intact and investigation-only by default.
