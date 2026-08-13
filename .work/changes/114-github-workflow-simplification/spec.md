# Change Specification: GitHub Workflow Simplification

- **Change ID**: `114-github-workflow-simplification`
- **Status**: Approved for implementation
- **Development level**: Complex
- **Risk Profile**: rigorous

## Outcome

Preserve the current exact-head, recovery, evidence, path-claim, and bounded-automation guarantees while materially reducing repeated lifecycle artifacts, verification, reviewer attempts, GitHub transactions, and Work Management coupling.

## Authority and bootstrap

- Operator approval and the 2026-08-13 GitHub/repository methodology audit define product scope.
- Repository artifacts and Git history remain authoritative; GitHub Issues/Projects are operational projections.
- Bootstrap source: GitHub issue `#141` (`112: System Audit Review`), already projected `In Progress`; no duplicate issue is required for 114.
- Local `main` at change creation: `677d7f9c8351e046e2e1c557b8b48364a8a3e342`.
- GitHub `main` at change creation: `f459cbb460f793bfef055bea1af35e3039dacc9c`.
- Both commits have tree `6e52a9a1b02f9206f9ebc5c0f3dd7d5de9024a4a`; classify this as tree-equivalent history, not content divergence.
- `scope.json` owns the implementation paths; change 112 owns only its audit record and does not conflict.
## Requirements

- **REQ-001 — Executable risk model:** `lean`, `standard`, and `rigorous` must determine required lifecycle artifacts and review/verification weight. `scope.json` remains universal; lean uses a compact `change.md`; standard retains the full current record; rigorous adds high-risk evidence when applicable.
- **REQ-002 — Local authority:** governed change creation must be possible from an authoritative local record without a pre-existing GitHub issue/PR. Work Management linkage is optional projection metadata and can be reconciled afterward.
- **REQ-003 — No routine closeout PR:** immutable merge facts belong to GitHub; Work Management projects final state. Do not require a second code PR solely to persist post-merge facts.
- **REQ-004 — Verification hierarchy:** use focused tests during development, selected affected checks before publication, and one canonical full repository verification on the exact GitHub PR head. Do not repeat the full suite for metadata-only closeout.
- **REQ-005 — Exact-head CI gate:** normal PR activity must trigger canonical GitHub CI; KIS must observe check-run/Actions evidence for the exact head before exact-head merge.
- **REQ-006 — Early base classification:** initialization records local and remote default-branch SHA/tree evidence and classifies same SHA, tree-equivalent history, or content divergence before implementation proceeds.
- **REQ-007 — Merge/cleanup policy:** repository configuration standardizes merge commits; squash/rebase are disabled where KIS can enforce or configure them. KIS exact-head merge and recoverable exact-head remote branch cleanup remain the landing authority.
- **REQ-008 — Deterministic PR metadata:** PR coordination must emit meaningful outcome, change/risk/scope, source and published head, verification/review, documentation impact, and residual-state metadata rather than empty/generic bodies.
- **REQ-009 — GitHub MCP optimization:** retain progressive exposure and `toolsets=all` unless measured startup/catalogue evidence justifies narrowing. Add upstream configuration modeling only where evidence shows value.
- **REQ-010 — Project provider capability:** expose safe provider-native project reads including project/status-update detail and batch `update_project_items`; keep deletion, project creation, and iteration-field creation outside this program.
- **REQ-011 — Provider-native evidence:** use official GitHub MCP PR/check-run/Actions operations instead of duplicate custom read wrappers.
- **REQ-012 — Preserve exact Git invariants:** retain immutable registered-commit publication, tree-equivalent reconciliation, exact-head merge, and recoverable exact-head branch deletion; thin only orchestration that duplicates provider capability without adding an invariant.
- **REQ-013 — Provider currency:** verify the current stable official GitHub MCP release and upgrade through the pinned-provider conformance path when compatible; an upgrade does not substitute for missing Project schema/view APIs.
- **REQ-014 — Repository basics:** pin GitHub Actions dependencies by immutable SHA and enable practical dependency/security advisory visibility without adding irrelevant ceremony.
- **REQ-015 — Documentation:** update governing operational guidance and KIS-MCP operator guidance so authority, verification, CI, PR, and closeout behavior match implementation.
- **REQ-016 — Efficiency invariant:** each fact/evidence class is produced once at the layer that owns it; avoid duplicate environment synchronization, duplicate focused/full test execution, redundant specialist-review attempts, and post-merge evidence PRs.

## Acceptance

1. A lean governed change can be created locally with only the lean record set and no mandatory GitHub source number; standard/rigorous records retain stronger artifacts.
2. Existing schema-v1/v2 change records remain readable and safe during migration.
3. New initialization reports local/remote base relation when remote evidence is available, including the tree-equivalent case.
4. CI runs automatically for pull requests and performs one canonical full verification path without first duplicating the same full-suite tests/environment synchronization.
5. Exact-head remote CI/check evidence is consumable by the existing completion workflow before merge.
6. Normal completion does not require a second repository PR solely to write GitHub-owned merge facts.
7. PR metadata is non-empty and deterministic for coordinator-created PRs.
8. Safe additional GitHub Project operations are available through progressive provider exposure and batch updates reduce repeated field-write calls.
9. Exact publication/reconciliation/merge/deletion invariants and the three Work hard rules are unchanged.
10. The Work Management Project target remains the existing 18-field / 12-view design.
11. Focused tests and the final exact-head canonical CI pass; no redundant full local verification is required after that exact-head result.

## Explicit exclusion

- Change 114 leaves the existing Work Management 18-field / 12-view target schema unchanged.
- Generic repository ceremony such as CODEOWNERS, mandatory reviewer bureaucracy, or release environments is not introduced without a KIS-specific requirement.

## Risks and recovery

- Cross-cutting workflow changes can weaken delivery gates if coupled incorrectly; tests must establish risk/artifact/CI/merge invariants independently.
- Backward compatibility is required for existing schema-v1/v2 change records.
- Provider mutations remain pinned and reversible through normal settings rollback plus runtime restart.
- Git and branch cleanup retains recoverable refs/quarantine semantics; no force deletion is introduced.
