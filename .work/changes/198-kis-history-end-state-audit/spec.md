# Change Specification: KIS History and End-State Audit

- **Change ID**: `198-kis-history-end-state-audit`
- **Status**: Active
- **Complexity**: medium
- **Risk trigger**: `public_contract`
- **Source audit**: GitHub issue #375
- **Remediation umbrella**: GitHub issue #378

## Outcome

Persist the complete #375 historical, semantic-diff, current-state, and live-tool audit as historical engineering evidence without implementing any remediation finding.

## Authority and scope

- Current product truth remains owned by root `SPEC.md` and subordinate module specs.
- Operator procedure remains owned by `docs/OPERATIONS.md` and `docs/operations/**`.
- This change owns only historical audit evidence under `docs/development/audits/**` and the historical archive index.
- The audit report must not silently become a competing current-product authority.
- Findings that require product, contract, configuration, provider, Work Management, or runtime changes remain follow-up work under #378 or an already-existing owning issue.

## Requirements

- **REQ-001:** Preserve the state-zero-to-current chronology and architecture turning points reconstructed in #375.
- **REQ-002:** Persist standalone Decision, Assumption, Risk/Approval, Hold/Deferred, and Gap/Correction registers with evidence/provenance status.
- **REQ-003:** Persist the final intended-current -> repository -> documentation -> live-tool commissioning reconciliation at `5f5a319b389715ef9b5283e999ef33322ae5ff51`.
- **REQ-004:** Record positive live controls as well as defects so remediation does not re-open already-correct boundaries.
- **REQ-005:** Record operator-observed Project view gaps, including Decisions, Assumptions/Risks, and Holds, alongside tool-reported view evidence without falsely resolving the disagreement.
- **REQ-006:** Link current remediation to #378 and existing narrower owners instead of implementing or duplicating those fixes here.

## Acceptance

1. **Given** the append-only #375 checkpoint chain, **when** the audit evidence is read from `docs/development/audits/**`, **then** a future session can reconstruct the major architecture chronology and terminal dispositions without this chat.
2. **Given** the final live commissioning pass, **when** the report is read, **then** every material mismatch found between intended current behavior and the running tool is explicitly classified with a recommendation/owner.
3. **Given** the archive authority rules, **when** current behavior changes later, **then** this audit remains clearly historical evidence and does not override canonical current authority.
4. The change contains no product/source/configuration remediation.

## Risks and recovery

- **Risk:** audit prose could be mistaken for current authority. **Mitigation:** explicit historical-evidence banner and links to canonical owners.
- **Risk:** current findings could be flattened into one oversized implementation slice. **Mitigation:** #378 is an umbrella; remediation stays bounded by ownership domain.
- **Recovery:** documentation-only changes can be reverted without affecting runtime/product behavior.

## Out of scope

- Fixing Serena exposure, Discover merge-commit handling, provider commissioning state, merge queue state, Project views, canonical specs, or historical stale records.
- Restarting or reconfiguring either KIS runtime.
