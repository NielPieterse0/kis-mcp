# Change Specification: Workflow Discovery Bridge

- **Change ID**: `079-workflow-discovery-bridge`
- **Status**: Approved for implementation
- **Risk Profile**: rigorous
- **Development level**: Complex — public Work/Discover behavior and cross-plane integration

## Outcome

Deliver the next two approved workflow/discovery slices: bounded `plan_change` preparation and exact-head CI guidance, plus a Discover-to-Work `run_verification` execution bridge and verification workflow hardening.

## Authority and scope

Authority order is `AGENTS.md` → `docs/TRUST-MODEL.md` → `SPEC.md` → `docs/PLATFORM-CONCEPT.md` → policy JSON → `docs/OPERATIONS.md`. The attached optimization programme supplies the approved feature design. Preserve HR-001/002/003 unchanged, progressive exposure, original provider schemas, and Discover's read-only boundary.

Active change 063 exclusively owns central capability/workflow files; this change must not overlap those paths unless that claim is cleanly released and `scope.json` is updated first.

## Requirements

- **REQ-001**: Add read-only `plan_change` that composes existing bounded project/change/impact evidence into authority, affected-code/test, verification, risk, and active-claim guidance without executing repository code.
- **REQ-002**: Add Work `run_verification(project, verification_id)` that re-discovers an approved verification declaration by stable ID, never accepts arbitrary command text, executes through the existing Work middleware/provider process surface, and returns `verification-result-v1` evidence.
- **REQ-003**: Add discoverable `verify-current-change` and `triage-exact-head-ci` workflow metadata, with executable-step integrity so unresolved executable steps cannot be presented as eligible.
- **REQ-004**: Improve deterministic workflow recommendation for realistic verification/change-planning language without adding model routing or widening the direct tool catalogue unnecessarily.
- **REQ-005**: Preserve bounded outputs, structural errors distinct from HR decisions, and no network execution through the local Work path.

## Acceptance

1. A working-tree change can be planned with deterministic affected tests and verification IDs plus bounded active-claim conflict evidence.
2. A discovered verification ID can be executed through Work and returns status, exit code, duration, command identity, bounded evidence, and failure classification; unknown IDs fail structurally before process execution.
3. Workflow recommendations include `verify-current-change` for natural verification intent and do not recommend workflows with unresolved executable steps.
4. Exact-head CI triage workflow declares the approved structured failure classes and composes existing GitHub operations rather than adding low-level wrappers.
5. Focused tests, change-scope validation, final diff review, and `scripts/verify.ps1` pass on each PR batch.

## Risks and recovery

Primary risks are command-injection through discovered declarations, duplicated Discover logic, central workflow conflicts with active change 063, and misleading eligibility. Mitigate by mapping only fixed discovered profiles/arguments, composing existing services, respecting claims, and validating executable step resolution. Recovery is branch/PR revert; no migration or persistent state is introduced.

## Out of scope

Govern implementation, unrestricted workflow execution, arbitrary shell verification, new GitHub low-level tools, provider authentication changes, policy changes, and runtime commissioning automation.
