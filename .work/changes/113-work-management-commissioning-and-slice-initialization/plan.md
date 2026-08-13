# Work Management Commissioning And Slice Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers TDD for behavior changes and verification-before-completion at every gate.

**Goal:** Make Work Management initialization a prerequisite for every new governed change, backfill 110-112, and leave the rich GitHub Project commissioning gap explicit and operable.

**Architecture:** Keep GitHub/Work Management mutation outside local change governance. Existing bounded GitHub issue + Project reconciliation operations create the operational record first; `change-governance.py` then requires and stores stable initialization evidence in a schema-version-2 scope. Schema v1 stays valid for historical records.

**Tech Stack:** Python 3, pytest, PowerShell wrapper, Git worktrees, FastMCP Work Management/GitHub provider operations, JSON/Markdown repository authority.

## Global constraints

- Preserve HR-001, HR-002, and HR-003 as the only Work hard rules.
- Do not add network calls to `change-governance.py` or `change-workflow.ps1`.
- Do not use unrestricted GraphQL or bypass the approved GitHub MCP boundary.
- Keep historical schema-version-1 scopes valid.
- Use preview-first/idempotent Project reconciliation and no delete operations.
- Keep `112-system-audit-review` untouched.

---

### Task 1: Version change-scope Work Management evidence

**Requirements:** REQ-001, REQ-002, REQ-003, REQ-004

**Files:**
- Modify: `tests/test_change_governance.py`
- Modify: `scripts/change-governance.py`

**Interfaces:**
- Produce `WorkManagementClaim(project_id, record_id, source_repository, source_number, source_kind, documentation_impact)`.
- `create_change_worktree(...)` receives the same six values and emits `schema_version: 2` plus `work_management`.
- [ ] Add failing tests proving schema v1 remains valid, schema v2 requires exact Work Management fields, invalid record/source/documentation-impact values fail, and new worktrees emit v2 evidence.
- [ ] Run the focused tests and confirm they fail for missing v2 behavior.
- [ ] Implement the smallest typed parser/serializer and `new` CLI arguments without network dependencies.
- [ ] Run `pytest tests/test_change_governance.py -q` and confirm green.

### Task 2: Reconcile repository/operator guidance

**Requirements:** REQ-001, REQ-008, REQ-009, REQ-010

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `.work/programmes/work-management/target-spec.md`
- Modify: `.work/programmes/work-management/roadmap.md`
- Modify: `.agents/skills/kis-mcp/references/operator-support.md`
- Modify: `docs/development/github-project-onboarding/commissioning.md`

- [ ] Document the required sequence: initialize Work Management record -> preview/apply Project reconciliation -> create governed worktree with evidence.
- [ ] Document schema-v2 arguments and historical v1 compatibility.
- [ ] Record the current rich-schema limitation and exact operator-only UI commissioning checklist without implying completion.
- [ ] Search for stale guidance that still permits `change-workflow new` without Work Management evidence.

### Task 3: Backfill recent governed slices and residual work

**Requirements:** REQ-005, REQ-006, REQ-007, REQ-008

**External state:** GitHub issue + Project #1 only through approved KIS/GitHub provider operations.

- [ ] Create/update specification-slice issues for 110, 111, and existing 112 with links to repository change records, PR/merge/verification evidence, and truthful lifecycle status.
- [ ] Preview then apply Project reconciliation for 110-113 using only currently supported live fields.
- [ ] Create separate residual records for the rich Project schema/view commissioning gap and DBHub/DockerHub commissioning-status persistence defect.
- [ ] Record Docker Hub search incompatibility/dependency debt as deferred/risk evidence only if it can be represented without conflating it with the completed 111 parent.
- [ ] Re-read Project inventory and preserve any unsupported-field limitation explicitly.
### Task 4: Commission and verify current operational projection

**Requirements:** REQ-008, REQ-009, REQ-010

- [ ] Run `project_management_schema_status` and capture exact missing fields/options/views.
- [ ] Perform every supported bounded commissioning action automatically.
- [ ] If custom fields/status options/views still require GitHub UI, stop only that commissioning sub-step and provide the operator the exact remaining checklist.
- [ ] After any operator UI action, re-run schema status before claiming readiness.

### Task 5: Review, verify, deliver, and close

**Requirements:** all

- [ ] Update 113 `scope.json` itself to schema v2 with `SPEC-113` / issue #138 evidence and documentation impact `planned`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run focused governance and Work Management tests, `git diff --check`, then `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Run code-quality, architecture/API-contract, and documentation reviews on the final bounded diff; fix blocking findings and re-run affected verification.
- [ ] Update Work Management lifecycle/verification evidence for 113 before PR preparation and after exact merge/documentation reconciliation.
- [ ] Prepare the exact verified change for PR review, merge only the authorized head, reconcile post-merge documentation, mark the parent slice Done only after closeout, and clean the worktree safely.

## Recovery

- Revert the 113 implementation commit to restore schema-v1-only new-change behavior; historical scopes remain valid throughout.
- GitHub issues/Project items are retained rather than deleted; incorrect projections are corrected by reconciliation.
- If rich Project UI commissioning is incomplete, retain the three-status projection and keep the explicit commissioning task open.
