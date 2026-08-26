# Change Specification: Lossless Legacy Transfer Ledger

- **Change ID**: `241-lossless-legacy-transfer-ledger`
- **Status**: Approved by Work #497 selection/claim
- **Risk Profile**: standard
- **Development level**: Medium — deterministic historical/current traceability; no product behavior change

## Outcome

Produce deterministic requirement-level traceability proving lossless transfer of all #497 legacy obligations into #475/#488-#496, with MCP 2026 re-baselining and retained deferred triggers explicit.

## Authority and scope

- Repository authority: `AGENTS.md` and the existing documentation authority hierarchy.
- Work authority: GitHub/Work #497 plus immutable source issue bodies #144-#480 and programme issues #488-#496.
- MCP authority: local 2026-07-28 corpus rooted at `C:\Projects\References\mcp-specification\mcp-docs-2026-07-28-direct-md-clean\markdown\000-index.md`; schema authority is `055-specification-schema-reference.md`.
- Current implementation evidence: merged `main`, Change 239/240 evidence for #475, current tests/contracts/source, and live `kis-dev` reads where verification claims require runtime evidence.
- Owned paths: `docs/development/audits/2026-08-26-lossless-legacy-transfer/**` and this change record.
- Shared/excluded paths: none; no current product authority document or runtime/source implementation is changed.

## Requirements

- **REQ-001 Source integrity**: account for exactly 84 superseded legacy issues across #488-#496 plus retained Deferred #476-#480, with #475 separately accounted for; detect duplicate/missing source ownership mechanically.
- **REQ-002 Requirement expansion**: normalize every material source outcome, defect, invariant, constraint, acceptance requirement, commissioning obligation, and deferred trigger into deterministic requirement rows.
- **REQ-003 Disposition**: every row receives exactly one #497 disposition and one current owner/evidence path; `Superseded` status alone is never evidence.
- **REQ-004 MCP 2026 re-baseline**: MCP-facing rows cite applicable 2026-07-28 specification/schema pages and distinguish historical FastMCP 3/MCP 2025 prescriptions from preserved outcomes/current replacements.
- **REQ-005 Deferred preservation**: #476-#480 remain first-class `future_triggered` owners with their objective triggers intact; newly discovered deferred #475 follow-ups remain separate evidence rather than being silently absorbed.
- **REQ-006 Verification evidence**: `implemented_verify` rows identify current exact-source/live evidence or remain explicitly unverified; no historical implementation claim is promoted without current evidence.
- **REQ-007 Duplicate architecture review**: cross-programme dependencies are represented as producer/consumer interfaces, not duplicate ownership, and current product authority is not duplicated by the audit artifact.

## Acceptance

1. Machine checks prove the superseded source set is 84/84 unique and becomes 89/89 unique only after adding #476-#480.
2. The JSON ledger has deterministic IDs, controlled dispositions, programme/source uniqueness, explicit current owner/evidence, deferred triggers, and MCP references where applicable.
3. The audit note records source-to-programme counts, preserved deferred items, #475 current evidence, MCP 2026 authority, duplicate-owner review, and every gap that blocks a terminal disposition.
4. No source/runtime/product-authority files are modified; `change-workflow.ps1 check` and repository verification pass on the final exact head.
5. Independent review confirms the ledger does not silently drop source obligations or revive retired FastMCP 3/MCP 2025 implementation authority.

## Risks and recovery

- Risk: historical issue bodies can contain overlapping wording or implementation prescriptions that are obsolete under MCP 2026.
- Mitigation: preserve outcomes/invariants separately from prescriptions; record explicit programme ownership and current-spec replacement rationale.
- Risk: an `implemented_verify` disposition may overstate current proof.
- Mitigation: require exact current evidence references and leave unresolved rows as `implement_current` with a bounded programme/verifier owner.
- Recovery: this is documentation evidence only; revert the governed change if the ledger methodology is found unsound.

## Out of scope

- Implementing any #488-#496 product requirement.
- Closing or changing the activation state of #476-#480.
- Restarting or modifying `kis-op`.
- Rewriting historical source issues or using this audit as current product authority.
