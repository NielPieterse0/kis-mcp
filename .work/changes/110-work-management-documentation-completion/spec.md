# Change Specification: Work Management Documentation Completion

- **Change ID**: `110-work-management-documentation-completion`
- **Status**: Approved / active
- **Risk Profile**: rigorous

## Outcome

Complete the already-approved Work Management programme by commissioning its GitHub Project operational projection and exposing the existing documentation lifecycle end to end, without introducing generated module documentation.

## Authority and invariants

- `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, policy, and `docs/OPERATIONS.md` remain authoritative in that order.
- `.work/programmes/work-management/target-spec.md` is the approved Work Management programme contract.
- Repository artifacts and Git history remain authoritative engineering truth.
- GitHub Project is the authoritative operational projection only.
- KIS performs bounded reconciliation/orchestration; GitHub never overwrites repository authority implicitly.
- HR-001, HR-002, and HR-003 remain the only Work prohibitions.

## Requirements

- **REQ-001**: Define the approved 18-field and 12-view Project schema as strict, reviewable JSON and detect live schema drift deterministically.
- **REQ-002**: Expose Project schema/readiness evidence through bounded task-level operations; no delete or unrestricted GraphQL surface may be introduced.
- **REQ-003**: Add documentation impact to work-item intake using the existing `DocumentationImpact` contract.
- **REQ-004**: Expose existing merge-readiness evaluation as the pre-merge documentation gate.
- **REQ-005**: Expose creation/application/completion of `documentation_reconciliation_due` / `post_merge_complete` events after merge.- **REQ-006**: Keep required work in `Documentation` until post-merge reconciliation is complete and project that lifecycle state back to GitHub only through explicit reconciliation.
- **REQ-007**: Make PR, exact-head verification, merge, closeout, documentation task, and authority revision metadata representable by the Project schema and task-level workflow output.
- **REQ-008**: Keep native/custom automation conservative; enable nothing that has not been individually proven against Project #1.
- **REQ-009**: Commission every schema element supported by the approved official GitHub MCP surface and report unsupported field/view provisioning explicitly rather than bypassing the provider boundary.
- **REQ-010**: Update current authority, programme, commissioning, operator, and skill documentation to the actual commissioned state.

## Acceptance

1. Given the checked-in schema manifest and live Project #1 fields, schema status reports exact missing/type/option drift with deterministic ordering.
2. Given a captured implementation/specification item, documentation impact is explicit at intake rather than implicit later.
3. Given exact PR and verification evidence, merge readiness blocks required documentation that is not `pre_merge_complete` or an evidenced `none` decision.
4. Given merge evidence, KIS can deterministically create the due milestone, apply it to the work record, complete it at an exact revision, and only then permit required `Done`.
5. GitHub Project writes remain preview-first/idempotent/conflict-aware and expose no delete/unrestricted GraphQL operation.
6. Focused tests, scope check, specialist review, canonical verification, live Project evidence, exact-head PR merge, lifecycle reconciliation, and safe cleanup are recorded.

## Risks and recovery

- GitHub MCP v1.8.0 does not expose generic Project field or saved-view creation. Unsupported provisioning must remain an explicit commissioning gap, not be bypassed with direct network/GraphQL access.
- Any live Project mutation must be reversible or additive and scoped to `NielPieterse0/#1`.
- Repository changes remain recoverable through Git commits/PR heads; remote branch deletion retains recovery SHA.

## Out of scope

- Generated/code-derived module documentation (Slice 2).
- New Work hard rules, unrestricted GitHub API/GraphQL, destructive Project operations, or unrelated provider work.
