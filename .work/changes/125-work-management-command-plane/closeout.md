# Closeout: Work Management Command Plane

## Implemented scope

- Restored the original federated model at field granularity: Work Management commands operational intent; repository/Git/GitHub/Actions remain authoritative for implementation and evidence facts.
- Added checked-in command-plane and change-governance settings plus JSON Schemas so authority, transitions, ranking, complexity, risk triggers, artifacts, verification limits, and specialist reviews are not hidden executable policy.
- Added standard Work Item issue intake with plain bounded titles and only outcome/context/acceptance/dependency/evidence body sections.
- Added `Ready`, `Effort`, `Delivery Stage`, execution claims, deterministic next-work selection, take-next, claim/release, hold/defer/transition, guarded completion, and authoritative change-classification projection.
- Preserved optimistic Project revisions through the GitHub adapter and fail-closed reconciliation path.
- Converted the shared Project schema from `kis-mcp` identity to portfolio `default`, retained 12 views, and kept the baseline to 24 fields.
- Added typed schema commissioning plans; missing Project fields/options/views remain explicit provider gaps when the bounded official GitHub MCP cannot provision them.

## Original programme requirement sweep

| Earlier requirement | Result in change 125 |
|---|---|
| Repository artifacts/history remain authoritative | Preserved; `.work`, Git/GitHub and Actions are evidence authorities. |
| Work backend owns operational status/programme direction | Restored for Work State, Priority, Effort, scheduling, holds/deferment and execution claims. |
| Provider-neutral KIS orchestration/reconciliation | Preserved; new command logic is in provider-neutral Work Management services. |
| One central programme view / next executable work | Strengthened with Ready-only deterministic selection and one-call take-next. |
| First-class decisions, assumptions, risks, approvals and holds | Preserved in existing record model/schema/views. |
| Holds/deferment require review triggers | Preserved and now configuration-driven. |
| Change/PR/verification/documentation traceability | Preserved; completion remains guarded by existing traceability/documentation evidence. |
| 12 native Project views | Preserved. |
| Fewer than 25 baseline Project fields | Preserved at 24 fields. |
| No second implementation database / no unrestricted mutation | Preserved. |
| Do not copy authoritative specifications into issues | Strengthened; issue form contains only bounded source content. |
| Complete Work metadata duplicated in issue bodies | Deliberately retired because it creates competing operational authority; Project-owned facts now stay in Project fields. |

## Validation evidence

- Live source/Project registration: issue #177 was created with the new concise issue-body shape and registered into shared Project #1 through bounded KIS reconciliation.
- Live schema evidence before implementation: Project #1 exposes only the legacy thin field surface, so rich command-plane commissioning is correctly reported as not ready.
- Affected automated tests: 242 collected and passed across `tests/work_management`, `tests/workflows/project_management`, `tests/providers/github/projects`, change controls, and change governance on current `main` after review corrections.
- Settings/vocabulary focused suite: 51 passed before the broader affected run.
- Exact changed-Python Ruff format/check: passed after final review corrections.
- `git diff --check`: passed after final review corrections.
- `scripts/change-workflow.ps1 check`: passed after rebase; it will be rerun after this closeout reconciliation before publication.

## Review / publication

- Required by exact classification: `code-quality`, `architecture`, `api-contracts`.
- Both configured specialist backends were attempted repeatedly and failed independently (`nvidia-nim` upstream/agent backend failures; `codex-cli` timeout/backend failures), so backend failure was not treated as review success.
- Exact-diff manual review found and corrected six concrete contract defects: missing dependency evidence could still select work; Project/native queue fields lacked complete authority mapping; boolean settings accepted truthy strings; the completion claim-release setting was ignored; transition metadata could overwrite evidence-owned fields; and generic transitions could mutate/bypass execution claims.
- Each correction has focused regression coverage and is included in the 242-test affected pass.
- Branch: `change/125-work-management-command-plane`.
- Worktree: `.work/worktrees/125-work-management-command-plane`.
- Exact commit / PR / canonical exact-head Actions: pending.

## Residual commissioning constraint

- The current bounded official GitHub MCP Project write surface can update Project item fields but does not expose general custom-field creation, single-select option provisioning, field-type migration, or saved-view creation. KIS therefore emits a typed `provider_gap` repair plan instead of bypassing the provider with unrestricted GraphQL/REST or claiming false readiness.
- Until Project #1 receives the required fields/options, live `next/claim/hold/defer` commissioning against issue #177 cannot be completed end to end; source registration and schema-drift commissioning are already live-verified.
