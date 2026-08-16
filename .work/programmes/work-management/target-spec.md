# Work Management Programme Specification

## Document status

| Field | Value |
|---|---|
| Product | `kis-mcp` Platform |
| Capability | Provider-neutral multi-project work management and review evidence |
| Change | `168-work-management-authority-currentness` |
| Status | P0-P5 implementation and the current saved-view commissioning tranche are complete; live readiness remains dynamic runtime evidence |
| Date | 2026-08-16 |
| Current implementation | Provider-neutral P0-P5 identity, command lifecycle, inventory, intake, governance, traceability, review evidence, deterministic reconciliation, portfolio status, a bounded 25-field GitHub Project schema commissioner, declared semantics for all 12 saved views, behavioral saved-view verification, fixed-shape CLI/CI, and task-level platform composition |
| Runtime dependency | Change `047-capability-composition-and-tool-experience` |
| Initial backend | GitHub Issues, Projects, Pull Requests, Actions, and official GitHub MCP server |
| Applicability | Multiple managed repositories and projects |

This document defines the complete capability and records the implemented P0-P5 boundary. Configuration, authentication, Project existence, and enabled automation remain separate commissioning evidence; unverified external state is not implied by implementation.

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative. GitHub product features and plan limits remain external facts and MUST be capability-detected before use.

## 1. Product decision

`kis-mcp` MUST provide one provider-neutral work-management capability for all configured projects. GitHub is the initial operational backend, while each managed repository remains authoritative for its own artifacts and implementation history.

```text
Managed repository = authoritative artifacts and implementation history
Configured work backend = authoritative operational status and programme view
kis-mcp = project identity, contracts, orchestration, reconciliation, and evidence routing
```
The initial adapter MUST extend the existing official GitHub MCP provider. The provider-neutral domain MUST permit additional approved backends later without changing record, lifecycle, review, or traceability contracts. GitLab, Jira, a custom project database, or a replacement project-management UI are not required components.

GitHub Projects supplies table, board, and roadmap views over issues, pull requests, and draft items. The GitHub adapter MUST use those native views before adding custom presentation.

## 2. Authority model

The following order applies within this capability:

1. Repository authority documents define product, policy, architecture, and operating rules.
2. Versioned repository artifacts define each specification slice, plan, task set, implementation, verification, and closeout.
3. Git commits and pull requests prove exact revisions and implementation history.
4. GitHub Actions and repository verification artifacts prove execution results.
5. GitHub Project fields record current operational status and programme metadata.
6. GitHub issues record discussions, proposals, decisions, findings, holds, risks, and actionable work.
7. `kis-mcp` reconciles these layers without silently changing their authority.

A Project field or issue body MUST NOT supersede the authority documents, policy files, specifications, plans, or committed change artifacts resolved for the affected managed project.

A material accepted decision is complete only after its owning repository authority is updated, or the decision explicitly records that no repository authority change is required.

## 3. Capability outcome

The operator MUST be able to open one configured programme view and determine, for one project or across the configured portfolio:

- what ideas have been captured;
- what work is proposed, approved, active, blocked, on hold, deferred, or complete;
- what specification slices exist and which implementation evidence belongs to each slice;
- what decisions, assumptions, risks, approvals, and findings remain open;
- what reviews ran, what they covered, and what records they produced;
- what can be executed next without violating dependencies or hold conditions;
- what remains from the overall product specification.
## 4. Scope

The capability covers:

- rapid intake of ideas and unstructured to-do items;
- structured work items and implementation planning;
- specification-slice and change-record traceability;
- first-class decisions, assumptions, risks, approvals, holds, and deferments;
- code, security, repository, architecture, modularity, and documentation review runs;
- validated finding extraction and remediation tracking;
- Git branch, worktree, pull-request, verification, merge, and closeout coordination;
- configurable GitHub Actions and local CLI reconciliation;
- programme views, status reporting, progress summaries, and drift detection;
- stable identity and separation for multiple local projects and repositories;
- documentation impact, pre-merge updates, and post-merge reconciliation state.

The initial platform owner MAY be a user account. Organization-level issue types and issue fields MUST be treated as optional enhancements because they require an organization context.

## 5. Non-goals

The capability MUST NOT:

- copy complete authoritative specifications into issue bodies;
- maintain a second implementation database outside Git and GitHub;
- expose one unrestricted generic project-mutation operation;
- permit project metadata to authorize or deny ordinary Work invocations;
- add a fourth hard rule beyond HR-001, HR-002, and HR-003;
- auto-install, auto-upgrade, or silently reconfigure the GitHub provider;
- depend on paid GitHub branch rulesets or private-repository protections;
- delete issues, project items, reports, change records, or review evidence permanently;
- claim compliance merely because a workflow ran or a Project field was populated.

## 6. GitHub Project model

The Project name MUST be configurable per backend binding. A shared portfolio Project and separate per-project Projects MUST both be supported.

The Project MUST contain one logical record collection and multiple saved views. Separate views MUST filter the same records rather than duplicate them into independent lists.

### 6.1 Record types

| Record type | Stable prefix | Purpose |
|---|---|---|
| Idea | `IDEA-` | Untriaged thought, opportunity, or reminder |
| Task | `TASK-` | Bounded actionable work |
| Specification Slice | `SPEC-` | Approved or proposed product/change outcome |
| Review Run | `REV-` | One scoped assessment against an exact target |
| Finding | `FIND-` | Validated defect, gap, or remediation candidate |
| Decision | `DEC-` | Proposed, accepted, rejected, or superseded decision |
| Assumption | `ASM-` | Explicit proposition requiring validation or monitoring |
| Risk | `RISK-` | Uncertain event with likelihood and consequence |
| Approval | `APP-` | Operator or designated reviewer authorization record |
| Hold | `HOLD-` | Protected pause with resumption conditions |
| Research | `RES-` | Time-bounded investigation with a decision outcome |
| Defect | `BUG-` | Confirmed behavioral defect |
| Security Finding | `SEC-` | Validated security-specific finding |

Decisions, assumptions, risks, approvals, and holds MUST be first-class issues. They MUST NOT exist only as free-text attributes inside an implementation issue or pull request.

A draft Project item MAY capture an idea before issue creation. KIS MUST convert a draft into a repository issue when the item acquires dependencies, decisions, implementation evidence, ownership, or a durable review requirement.

### 6.2 Core lifecycle

Work command state and implementation delivery stage are separate axes. `Status` records operator command state:

```text
Inbox -> Triage -> Proposed -> Approved -> Ready -> Active -> Done
```

Alternative Work states are `Blocked`, `On Hold`, `Deferred`, `Rejected`, and `Superseded`. Implementation progress is projected independently through `Delivery Stage` (`None`, `Change Created`, `Implementing`, `PR Open`, `Review`, `CI Pending`, `CI Failed`, `CI Passed`, `Merged`, `Documentation`, `Commissioning`, `Complete`). Verification evidence is projected through `Verification`; neither delivery nor verification state replaces Work command authority.

Each Work-state transition MUST have a declared source state, target state, actor, prerequisites, and side effects. Configuration MAY disable a transition, but configuration MUST NOT invent an HR policy decision.

### 6.3 Core fields

The canonical operational projection uses exactly 25 managed fields and MUST remain below GitHub's Project field limit. Additional GitHub built-ins or historical unmanaged fields do not become KIS command authority.

| Field | Type | Required for |
|---|---|---|
| Status | Single select | Work command state |
| Record Type | Single select | Typed managed records |
| Priority | Single select | Executable work |
| Effort | Single select | Queue planning |
| Delivery Stage | Single select | Implementation progress |
| Execution Owner | Text | Conflict-safe execution claims |
| Blocked By | Text | Observable dependency evidence |
| Documentation Impact | Single select | Documentation lifecycle |
| Complexity | Single select | Repository change classification projection |
| Risk Triggers | Text | Repository change risk projection |
| Project ID | Text | Stable managed-project identity |
| Repository | Repository | Source repository identity |
| Module | Text | Product/module routing |
| Change ID | Text | Governed change identity |
| Origin | Single select | Intake/review/verification/implementation provenance |
| Disposition | Single select | Findings, risks, decisions, and assumptions |
| Verification | Single select | Verification evidence state |
| Severity | Single select | Findings and risks |
| Confidence | Single select | Findings and assumptions |
| Review Trigger | Text | Holds, deferments, and assumptions |
| Target Date | Date | Planned work |
| Iteration | Iteration | Optional delivery cadence |
| Source Review | Text | Records extracted from a review |
| Authority Revision | Text | Exact commit or immutable artifact revision |
| External Link | Text | PR, report, workflow run, or other evidence |

Repository labels SHOULD classify stable secondary dimensions such as `module:*`, `severity:*`, and `origin:*`. KIS MUST avoid encoding the same state independently in labels and Project fields unless one is a generated compatibility projection.

### 6.4 Required views

1. `01 Inbox` — untriaged ideas and tasks.
2. `02 Programme Table` — all active records and key fields.
3. `03 Delivery Board` — Kanban grouped by Status.
4. `04 Roadmap` — dated or iterated specification and implementation slices.
5. `05 Specification Slices` — proposed through completed specification records.
6. `06 Decisions` — proposed, accepted, rejected, and superseded decisions.
7. `07 Assumptions and Risks` — open validation and mitigation work.
8. `08 Holds and Deferred` — paused items with review triggers.
9. `09 Reviews and Findings` — review runs and extracted records.
10. `10 Verification` — work awaiting or failing verification.
11. `11 Documentation and Closeout` — records awaiting documentation reconciliation or final closeout.
12. `12 Completed` — closed records retained for history.

The checked-in `settings/work-management/github-project-schema.json` owns each view's executable layout, filter, visible-field order, sort/group configuration, and board vertical grouping. A named view shell is not sufficient commissioning evidence. `project_management_schema_status` MUST report semantic drift when an observed canonical view differs on any declared dimension and MUST require bounded behavioral evidence that filtered saved views return only matching records. The bounded registered-Project commissioner MAY repair only API-supported view semantics without exposing arbitrary API access or a delete/recreate path. Under the current GitHub contract, missing views can be created with complete semantics and existing views can be updated in place for layout, filter, and visible fields; sort, group, and vertical-group configuration are observable but not exposed by the current view-update input, so drift in those dimensions remains explicit and unready.

## 7. Intake and triage

KIS MUST support low-friction capture through a command equivalent to:

```text
capture_work_item(project_id, title, note?, record_type="Idea", priority?, module?)
```

New items MUST enter `Inbox` unless the operator supplies a valid explicit state. Intake MUST NOT require a complete specification, owner, estimate, or due date.

Triage MUST decide one of these outcomes:

- convert to a bounded task;
- promote to a specification slice;
- open a research item;
- record a decision, assumption, risk, approval, or hold;
- defer with a review trigger;
- reject with a reason;
- retain in Inbox for later clarification.

`get_next_work_item(project_id?)` MUST exclude records that are blocked, on hold, deferred, rejected, superseded, missing required approval, or dependent on incomplete records. The selection result MUST explain every filter and ordering factor.

## 8. Specification and implementation traceability

Each governed change MUST retain the existing repository artifacts:

```text
.work/changes/<change-id>/
├── scope.json
├── spec.md
├── plan.md
├── tasks.md
└── closeout.md
```

The corresponding GitHub specification-slice issue MUST link to exact repository paths and immutable commit revisions. It MUST summarize status and outcome, not duplicate the complete documents.

Traceability MUST support:

```text
Idea -> Decision -> Specification Slice -> Change ID -> Branch/Worktree
     -> Pull Request -> Verification -> Merge Commit -> Closeout
```

A specification slice MAY create multiple implementation tasks or pull requests. Every implementation record MUST identify one owning specification slice or state why no specification slice is required.

### 8.1 Decision and assumption extraction

A material decision discovered during implementation MUST create or update a `DEC-` issue with:

- context and decision statement;
- status and decision owner;
- alternatives considered;
- consequences and affected modules;
- source change, review, or discussion;
- repository authority that must be updated;
- predecessor, superseding decision, and implementation evidence.

An assumption MUST record confidence, validation method, review trigger, expiry or invalidation condition, and the records that depend on it.

KIS MUST be able to report:

- accepted decisions not reflected in repository authority;
- assumptions that are overdue for validation;
- active work depending on invalidated assumptions;
- superseded decisions still referenced by active work.

### 8.2 Holds and deferments

A hold MUST record:

- reason and responsible owner;
- protected branches, worktrees, change records, or artifacts;
- dependency or date that triggers review;
- resumption conditions;
- cancellation conditions;
- last review date and next required action.

A deferred item MUST contain a review trigger. KIS SHOULD flag a deferred item without a trigger as incomplete governance metadata.

KIS MUST NOT clean, archive, or recommend execution of a protected worktree merely because its implementation appears merged. Repository change governance remains authoritative for cleanup eligibility.

## 9. Review and assessment workflow

Every code review, security review, repository assessment, modularity assessment, documentation audit, or compliance-oriented check MUST create one `REV-` record before or at workflow start.
The review record MUST identify:

- review type and workflow version;
- exact repository, branch, commit, range, pull request, or path scope;
- requester, start time, completion state, and coverage status;
- evidence budget, exclusions, assumptions, and unknowns;
- canonical report and structured-result locations;
- extracted child records and their dispositions.

The normalized result contract SHOULD contain:

```json
{
  "schema_version": 1,
  "review_id": "REV-023",
  "review_type": "security",
  "target": {"project_id": "example-project", "repository": "owner/repository", "commit": "<sha>"},
  "status": "completed",
  "coverage": {"complete": true, "reviewed": [], "gaps": []},
  "observations": [],
  "findings": [],
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "artifacts": []
}
```

Canonical review evidence SHOULD be versioned under:

```text
.work/reviews/<review-id>/
├── request.json
├── report.md
├── result.json
├── coverage.json
├── report.sarif       # when applicable
└── closeout.json
```

Change `055-work-management-review-evidence` confirms this canonical namespace and implements provider-neutral artifact-manifest validation only. Runtime persistence, atomic writes, retention, conflict handling, and workflow integration remain P5 responsibilities.

### 9.1 Observation triage

The workflow MUST classify each observation before creating a child record:

```text
Rejected | Informational | Recommendation | Assumption | Decision required
Validated finding | Risk | Deferred candidate
```

A report sentence MUST NOT automatically become a task. Only validated findings, explicit governance records, or operator-selected recommendations MAY create durable child issues.

Supported extraction modes are:

| Mode | Child records |
|---|---|
| `report_only` | None |
| `validated_findings` | Validated findings and security findings |
| `full_governance` | Findings, decisions, assumptions, risks, holds, and deferments |

The default mode MUST be configurable. The initial default SHOULD be `validated_findings`.

A finding lifecycle MUST be:

```text
Candidate -> Validated -> Accepted | Rejected | Deferred | Risk Accepted
          -> Remediation -> Verification -> Closed
```

Each finding MUST preserve source evidence, location, confidence, severity, validation disposition, remediation record, fix pull request, and follow-up verification.

## 10. Modular architecture

The capability MUST align with change 047's domain contribution and workflow composition model.

```text
GitHub Project / Issues / PRs / Actions
                |
                v
Provider-specific GitHub adapter
                |
                v
Provider-neutral work-management contracts
                |
                +--> lifecycle and traceability service
                +--> review-record service
                +--> reconciliation service
                |
                v
Workflow descriptors and bounded Work operations
                |
                v
047 capability composition and gateway exposure
```
### 10.1 Target package boundaries

```text
src/kis_mcp/work_management/
├── contracts.py        provider-neutral records and commands
├── settings.py         strict JSON configuration
├── lifecycle.py        transition rules and prerequisites
├── traceability.py     artifact and relationship validation
├── reviews.py          review evidence, triage, extraction, and finding lifecycle
├── reconciliation.py   desired-versus-observed state
├── service.py          application facade
└── platform.py         047 capability contributions

src/kis_mcp/providers/github/
└── project_management.py  GitHub MCP/API adaptation only

src/kis_mcp/workflows/project_management/
├── descriptors.py      complete user-task workflows
├── reviews.py          review-run coordination
└── delivery.py         spec-to-closeout coordination
```

The exact paths remain subject to a fresh modularity assessment after 047 merges.

The provider-neutral package MUST NOT import FastMCP, GitHub MCP tool implementations, gateway code, or provider-specific response layouts.

The GitHub adapter MUST own GitHub identifiers, pagination, field discovery, OAuth scope interpretation, API errors, and conversion to normalized contracts.

Workflow modules MUST depend on normalized service contracts. They MUST NOT import GitHub adapter internals.

Gateway composition MUST consume only `platform.py` entry points created or approved by the 047 architecture.

The initial target boundary table below remains declared design evidence. Change `055-work-management-review-evidence` also collected measured 90-day repository evidence for the current `work_management` and `workflows` units and directly inspected the existing review and traceability modules. No Modularity Assessment Score is claimed because representative read-set/edit-set and isolation evidence remain unmeasured. Each implementation phase MUST continue to preserve, split, or merge units based on current cohesion, coupling, blast radius, change reasons, and agent-workability evidence.

### 10.2 Declared boundary assessment

| Unit | Evidence | One outcome | Contract | Stays behind | Reversal |
|---|---|---|---|---|---|
| `U-01 work_management` | `D` | Normalize records, lifecycle, traceability, and reconciliation | Provider-neutral commands and results | GitHub identities and transport | Low while contracts are internal |
| `U-02 github project adapter` | `D` | Translate official GitHub operations to normalized contracts | Adapter interface owned by U-01 | MCP/API schemas, pagination, scopes, and errors | Low with contract tests |
| `U-03 project workflows` | `D` | Compose complete intake, delivery, review, and status tasks | Workflow descriptors and service ports | Provider selection and transport | Medium after public exposure |
| `U-04 automation assets` | `D` | Run repeatable CLI and CI reconciliation | Versioned settings, schemas, and structured results | Domain decisions and provider internals | Low when workflows remain optional |

`D` means declared target-design evidence for the table. The P4 collector measured `src/kis_mcp/work_management` at 2,515 LOC, nine relevant commits, fan-in three, and fan-out two, and measured `src/kis_mcp/workflows` at 719 LOC, four relevant commits, fan-in one, and fan-out four. Direct inspection confirmed that review-domain contracts belong in a new `work_management/reviews.py` unit rather than extending `traceability.py` or making the advisory `workflows/code_review` adapter authoritative. Read-set/edit-set ratio, hidden coupling, and isolated-test effort remain unmeasured and are explicit future assessment triggers.

The design intentionally avoids a single catch-all workflow module and avoids provider logic in the domain core. It also avoids premature micro-modules for each record type; record-specific behavior SHOULD remain cohesive lifecycle strategies until measured change evidence justifies another seam.

## 11. Public workflow surface

The platform SHOULD expose task-level operations rather than raw Project mutations:

| Operation | Outcome |
|---|---|
| `capture_work_item` | Create an Inbox idea or typed issue |
| `list_work_items` | Query bounded records with fields and relationships |
| `get_next_work_item` | Select and explain the next executable item |
| `triage_work_item` | Classify and transition one Intake record |
| `record_decision` | Create or update a first-class decision |
| `record_assumption` | Create or update a monitored assumption |
| `place_work_on_hold` | Create a hold and protect linked assets |
| `defer_work_item` | Defer with a required review trigger |
| `start_specification_slice` | Link a Project record to a governed change |
| `link_implementation` | Attach branch, worktree, PR, and commit evidence |
| `run_review_workflow` | Create and execute one typed review run |
| `triage_review_result` | Validate observations and create child records |
| `record_verification` | Attach exact check and workflow-run evidence |
| `reconcile_project_state` | Detect and optionally repair safe drift |
| `get_programme_status` | Summarize progress, blockers, risks, documentation state, and gaps for a project or portfolio |

Mutating operations MUST support an idempotency key. Bulk operations MUST return per-record outcomes and MUST NOT hide partial failure.
## 12. Initial GitHub provider strategy

The initial backend implementation MUST prefer the pinned official GitHub MCP server already registered in `kis-mcp`.

The provider currently supports dedicated `projects`, `issues`, `labels`, `pull_requests`, and `actions` toolsets. KIS MUST capability-detect the exact tools exposed by the pinned release before enabling a workflow.

Initial provider access SHOULD enable only the toolsets and individual tools required for the configured workflows. The existing `all` configuration MAY remain during transition, but the final commissioned profile SHOULD use an explicit allowlist.

The adapter MUST prefer dedicated Project tools for project reads and writes. It MAY use GitHub's ProjectV2 GraphQL API through an approved external connector when the pinned MCP release lacks a required operation.

The initial capability MUST NOT expose arbitrary GraphQL passthrough. Every fallback query or mutation MUST have a fixed operation shape and normalized response contract.

GitHub OAuth scopes MUST be discovered and reported separately from local readiness. Read-only workflows SHOULD require `read:project`; project mutation requires `project` or the equivalent current GitHub authorization.

## 13. Configuration

Configuration MUST use strict, versioned JSON with a matching JSON Schema. A future default path SHOULD be:

```text
settings/work-management/github-projects.settings.json
```

Configuration MUST separate capability enablement, workflow behavior, automation, and enforcement expectations.

```json
{
  "schema_version": 1,
  "enabled": false,
  "portfolio_id": "default",
  "managed_projects": [
    {
      "project_id": "example-project",
      "local_root": "<project-root>",
      "repository": "owner/repository",
      "backend_binding": "github-default"
    }
  ],
  "backend_bindings": [
    {
      "binding_id": "github-default",
      "provider": "github",
      "owner": "owner",
      "owner_type": "user",
      "project_number": null
    }
  ],
  "features": {},
  "automation": {},
  "gates": {}
}
```
### 13.1 Feature controls

Each feature MUST support one of `disabled`, `read_only`, or `enabled` where mutation is meaningful.

Configurable features SHOULD include:

- intake and triage;
- decisions, assumptions, risks, approvals, and holds;
- specification-slice synchronization;
- pull-request and verification linking;
- review-run registration and extraction;
- project bootstrap and schema reconciliation;
- programme summaries and status updates.

Automation controls MUST independently enable or disable:

- auto-add of matching issues and pull requests;
- default status assignment;
- close-to-done and reopen synchronization;
- pull-request merge synchronization;
- review result extraction;
- scheduled drift detection;
- safe automatic repair.

Gate modes MUST be `off`, `advisory`, or `required`. A required gate MUST fail only its workflow or merge-readiness result. It MUST NOT become a new FastMCP Work prohibition.

Configuration changes MUST be reviewable in Git, and secrets MUST NOT be stored in the settings file.

## 14. Documentation feedback milestones

Every specification or implementation slice MUST classify documentation impact when the slice is created. The classification values are `not_assessed`, `none`, `planned`, `in_progress`, `pre_merge_complete`, and `post_merge_complete`.

The workflow MUST create a documentation task when impact is `planned`. The task MUST identify the affected authority, README, operations, architecture, product, module, and change-closeout artifacts for the selected managed project.

Before a pull request is declared merge-ready, the workflow MUST require one of:

- all pre-merge documentation updates are present on the branch; or
- an explicit `none` decision with rationale and reviewer evidence.

A merged pull request MUST create a `documentation_reconciliation_due` milestone event. The record MUST capture the pull-request number, merge commit, affected project, documentation task, and required post-merge updates.

The work item MUST remain in `Documentation` until merge-specific closeout data, implementation status, README or operating guidance, and any affected authoritative specifications are reconciled. Only then MAY the item transition to `Done`.

The documentation milestone MUST be configurable as `off`, `advisory`, or `required`. `required` affects delivery readiness and closeout only; it MUST NOT add a Work hard rule.

## 15. Automation model

The implementation MUST use GitHub's built-in Project workflows before custom Actions or KIS reconciliation.

Built-in automation SHOULD cover default status, closed-item completion, merged-PR completion, auto-add, and archival when the available GitHub Project supports the required rule.
Custom automation MUST be idempotent and reconcile desired state against observed state before mutation.

Recommended event handling:

| Event | Default action |
|---|---|
| Issue or draft created | Add to Project and set `Inbox` |
| Issue converted or triaged | Apply record type and required fields |
| Change record created | Link or create specification-slice issue |
| Pull request opened | Link implementation and set `Review` when configured |
| Pull request merged | Record merge commit and set `Verification` or `Done` |
| Issue closed or reopened | Synchronize lifecycle state |
| Review completed | Attach report and queue configured extraction |
| Finding accepted | Create or link remediation task |
| Hold trigger satisfied | Queue review; do not resume automatically by default |
| Scheduled reconciliation | Report drift and apply only approved safe repairs |

Automatic archival MUST preserve Project fields and issue history. KIS MUST use reversible archive or close operations instead of deletion.

## 16. CLI and local workflow

A future repository-local CLI SHOULD use fixed-shape commands through:

```text
pwsh -NoProfile -File scripts/project-workflow.ps1 <command> [validated arguments]
```

The PowerShell wrapper SHOULD delegate to a Python implementation and propagate structured exit codes.

Candidate commands are:

```text
status | bootstrap | inventory | reconcile | capture | triage
next | link-change | link-pr | review-import | verify-traceability
```

Every read command MUST support bounded JSON output. Every mutation command MUST support `--dry-run`; safe reconciliation SHOULD default to dry-run until explicitly enabled in JSON.
## 17. CI and Git workflow

The capability SHOULD define reusable GitHub Actions workflows for:

- pull-request traceability validation;
- Project schema and settings validation;
- change-record and Project-state reconciliation;
- review report ingestion and finding extraction;
- scheduled stale hold, assumption, and decision checks;
- programme status generation.

Workflow triggers MAY include `pull_request`, `push` to `main`, `workflow_dispatch`, `workflow_call`, and a configurable schedule.

The CI gate catalogue SHOULD include:

| Gate | Purpose |
|---|---|
| `project-settings` | Parse JSON and validate schema |
| `project-schema-drift` | Compare required fields, values, and views |
| `change-traceability` | Verify change ID, issue, branch, PR, and artifact links |
| `decision-authority` | Find accepted decisions missing required document updates |
| `review-disposition` | Find validated findings without disposition |
| `hold-integrity` | Find protected holds without triggers or missing assets |
| `verification-evidence` | Confirm required checks refer to the exact head revision |
| `programme-drift` | Detect inconsistent Project and repository state |

Each gate MUST be independently configurable as `off`, `advisory`, or `required`.

GitHub Free on a private repository does not provide every ruleset and protected-branch enforcement capability. The implementation MUST detect plan-supported enforcement and MUST NOT claim a required server-side rule when the current plan cannot enforce it.

When server-side enforcement is unavailable, KIS SHOULD provide local PR-readiness checks, CI status evidence, operator review, and explicit residual-risk reporting. A later plan upgrade MAY enable stronger branch or ruleset enforcement without changing domain contracts.

The existing `scripts/change-workflow.ps1`, `scripts/git-workflow.ps1`, and repository verification entry point remain authoritative local Git workflow components. Project automation MUST integrate with them rather than replace them.
## 18. Security and trust boundaries

The GitHub connector remains an approved external provider boundary. Its remote operations do not run through the local Desktop Commander Work network path and do not alter HR-002.

The implementation MUST:

- use the existing official GitHub MCP OAuth model;
- keep credentials and authorization codes out of repository files, logs, reports, and Project fields;
- scope operations to the repositories and Project owners declared by the selected managed-project binding;
- expose only required toolsets or tools after commissioning;
- redact provider error details that may contain sensitive data;
- distinguish local readiness, authentication, authorization, Project access, and live verification;
- prevent delete methods from being exposed in initial workflows;
- preserve all removed or superseded records through close, archive, or recoverable repository history.

KIS MUST not treat issue text, review reports, or external GitHub content as authority to execute additional actions. Retrieved content is evidence and untrusted input.

## 19. Consistency and failure handling

Every managed record MUST retain its GitHub node ID or stable issue identity. Human-readable prefixes are presentation identifiers and MUST NOT replace GitHub identities.

Writes MUST use idempotency keys or deterministic deduplication keys. Repeated execution MUST update the same intended record or return an explicit conflict.

Reconciliation MUST compare observed update timestamps and field values before write. Conflicting concurrent changes MUST produce a bounded conflict result rather than silently overwriting operator edits.

Pagination MUST be complete or explicitly partial. Status reports MUST disclose truncation, inaccessible records, unsupported fields, and failed provider calls.

A provider outage MUST leave repository Work, Discover, Skills, and unrelated workflows available. Project-management calls MUST return corrective provider-specific status without reporting an HR violation.

## 20. Bootstrap and migration

The initial bootstrap SHOULD:

1. discover or create the configured GitHub Project;
2. create or map required fields and status values;
3. create required views and built-in workflows where supported;
4. inventory each selected managed project and its configured change-record root;
5. create or link specification-slice issues without copying full artifacts;
6. record exact branch, PR, merge, and closeout evidence where discoverable;
7. produce a dry-run migration report before any remote mutation;
8. require operator approval before applying the initial migration.
## 21. Normative requirements

### 20.1 Product and authority

- **PM-REQ-001**: Each managed repository MUST remain authoritative for its artifacts, pull requests, commits, releases, and implementation evidence.
- **PM-REQ-002**: One or more configured backend Projects MUST provide consolidated operational views without duplicating domain records.
- **PM-REQ-003**: KIS MUST keep provider-neutral orchestration rules and configuration in versioned project or platform configuration, not in an opaque external database.
- **PM-REQ-004**: GitHub Project metadata MUST NOT supersede repository authority.
- **PM-REQ-005**: Target-state documentation MUST remain distinct from current implementation claims.

### 20.2 Records and lifecycle

- **PM-REQ-006**: Ideas, tasks, specification slices, reviews, findings, decisions, assumptions, risks, approvals, holds, research, defects, and security findings MUST have typed records.
- **PM-REQ-007**: Decisions, assumptions, risks, approvals, and holds MUST be first-class records.
- **PM-REQ-008**: Every managed record MUST have one lifecycle state and stable GitHub identity.
- **PM-REQ-009**: Holds and deferments MUST include a review trigger.
- **PM-REQ-010**: `get_next_work_item` MUST exclude non-executable states and explain selection.
- **PM-REQ-011**: Lifecycle transitions MUST be settings-driven, deterministic, and validated.
- **PM-REQ-012**: Close and archive operations MUST preserve history and fields.

### 20.3 Traceability

- **PM-REQ-013**: Each governed implementation MUST link to its specification slice or an explicit exemption.
- **PM-REQ-014**: Specification issues MUST link to immutable artifact revisions.
- **PM-REQ-015**: Branch, worktree, PR, verification, merge, and closeout evidence MUST be independently queryable.
- **PM-REQ-016**: Accepted decisions MUST identify affected repository authority.
- **PM-REQ-017**: Reconciliation MUST detect orphaned, duplicated, stale, and contradictory relationships.
### 20.4 Reviews and evidence

- **PM-REQ-018**: Every review workflow MUST create a review-run record with exact scope and target revision.
- **PM-REQ-019**: Review workflows MUST return a normalized result and explicit coverage status.
- **PM-REQ-020**: Full reports MUST be retained as durable evidence outside transient chat output.
- **PM-REQ-021**: Observation triage MUST precede child-record creation.
- **PM-REQ-022**: Findings MUST preserve validation, disposition, remediation, and follow-up verification.
- **PM-REQ-023**: Extraction mode MUST be configurable per review type.
- **PM-REQ-024**: Partial review coverage MUST be visible in the Project and report.

### 20.5 Architecture and provider

- **PM-REQ-025**: Provider-neutral domain contracts MUST remain independent of GitHub response layouts and FastMCP.
- **PM-REQ-026**: GitHub-specific behavior MUST remain inside the GitHub adapter boundary.
- **PM-REQ-027**: Workflows MUST depend on normalized services rather than provider internals.
- **PM-REQ-028**: Gateway composition MUST use 047 platform contribution entry points.
- **PM-REQ-029**: The official GitHub MCP server MUST be the preferred external provider.
- **PM-REQ-030**: Exact Project, issue, PR, label, and Actions tools MUST be capability-detected.
- **PM-REQ-031**: Generic GraphQL passthrough MUST NOT be part of the initial public surface.
- **PM-REQ-032**: Optional provider failure MUST remain isolated from unrelated platform capabilities.

### 20.6 Configuration and automation

- **PM-REQ-033**: Settings MUST be strict, versioned JSON with a checked-in schema.
- **PM-REQ-034**: Feature, automation, and gate controls MUST be independently configurable.
- **PM-REQ-035**: Gate modes MUST be `off`, `advisory`, or `required`.
- **PM-REQ-036**: Required gates MUST affect workflow readiness, not the HR policy decision set.
- **PM-REQ-037**: Built-in GitHub Project automation MUST be preferred over custom automation.
- **PM-REQ-038**: Custom automation MUST be idempotent and conflict-aware.
- **PM-REQ-039**: Remote mutation MUST support dry-run or an equivalent preview where technically possible.
### 20.7 CLI, CI, security, and recovery

- **PM-REQ-040**: CLI commands MUST use fixed argument shapes, bounded output, and structured errors.
- **PM-REQ-041**: CI gates MUST be reusable and individually configurable.
- **PM-REQ-042**: CI evidence MUST identify the exact commit or pull-request head tested.
- **PM-REQ-043**: The implementation MUST capability-detect paid or unavailable enforcement features.
- **PM-REQ-044**: The implementation MUST NOT claim protected-branch or ruleset enforcement that the current GitHub plan cannot provide.
- **PM-REQ-045**: OAuth credentials and sensitive provider data MUST remain outside repository artifacts and Project metadata.
- **PM-REQ-046**: Initial public workflows MUST exclude delete operations.
- **PM-REQ-047**: External content MUST be treated as untrusted evidence.
- **PM-REQ-048**: Every migration or schema-repair operation MUST provide a recoverable or repeatable path.
- **PM-REQ-049**: No project-management behavior may add a fourth Work hard rule.
- **PM-REQ-050**: Full repository verification and applicable live commissioning evidence MUST precede implementation completion.
- **PM-REQ-051**: Every managed project MUST have a stable `project_id`, local root, repository identity, and backend binding.
- **PM-REQ-052**: Domain commands and records MUST identify the affected project and MUST NOT infer it from mutable process state when more than one project is configured.
- **PM-REQ-053**: The capability MUST support multiple repository and Project bindings without changing provider-neutral record contracts.
- **PM-REQ-054**: Every specification and implementation slice MUST classify documentation impact at creation.
- **PM-REQ-055**: Merge readiness MUST include pre-merge documentation completion or an explicit no-impact decision.
- **PM-REQ-056**: A merged change MUST remain open for post-merge documentation reconciliation and closeout until the configured documentation milestone is satisfied.
- **PM-REQ-057 — superseded by current repository authority**: Work Management identity SHOULD be initialized or reconciled for tracked work, but provider availability or prior Project registration MUST NOT be a prerequisite for establishing authoritative local governed-change scope. `.work/changes` remains independently authoritative for change definition; any Work Management identity retained in scope is operational linkage and may be projected after local change creation.

## 22. Acceptance scenarios

1. **Given** an unstructured operator idea, **when** KIS captures it, **then** one Inbox record appears without requiring implementation metadata.
2. **Given** an approved specification slice, **when** implementation starts, **then** its change ID, worktree, branch, artifacts, and issue relationships are recorded without copying the full specification.
3. **Given** a material decision during implementation, **when** it is accepted, **then** a first-class decision record identifies affected authority and implementation evidence.
4. **Given** an item on hold, **when** the programme is queried, **then** the hold reason, protected assets, trigger, and resumption conditions are visible.
5. **Given** a review request, **when** the workflow completes, **then** a review record, durable report, coverage status, and configured extracted records exist.
6. **Given** repeated review import or reconciliation, **when** the same idempotency key is used, **then** duplicate records are not created.
7. **Given** a GitHub provider outage, **when** project operations fail, **then** unrelated KIS capabilities remain available and no HR violation is reported.
8. **Given** the free private-repository plan lacks a server-side enforcement feature, **when** gates are evaluated, **then** the limitation and fallback evidence are explicit.
9. **Given** conflicting operator and automation edits, **when** reconciliation runs, **then** it reports a conflict instead of silently overwriting the operator state.
10. **Given** a completed and merged change, **when** closeout finishes, **then** its issue, Project item, PR, verification, merge commit, and closeout record remain traceable.
11. **Given** two configured repositories, **when** portfolio status is requested, **then** records remain attributable to their stable project identities and can be filtered per project.
12. **Given** a merged pull request with documentation impact, **when** merge completes, **then** the work item enters `Documentation` and cannot become `Done` until post-merge reconciliation is recorded.
13. **Given** Work Management is unavailable or the source record has not yet been projected, **when** a governed local change is created from a clean authoritative base, **then** local change authority remains valid and its Work Management linkage can be reconciled later without provider access being a governance prerequisite.

## 23. Delivery sequence

| Phase | Outcome | Dependency |
|---|---|---|
| P0 | Approve this specification, multi-project identity model, documentation milestones, and target backend schema | Change 049 |
| P1 | Read-only GitHub Project inventory and normalized contracts | Change 047 merged |
| P2 | Intake, typed records, decisions, assumptions, risks, approvals, and holds | P1 |
| P3 | Change-record, branch, worktree, PR, verification, and closeout traceability | P2 |
| P4 | Review-run evidence, normalized reports, triage, and finding extraction | P2 and resolved manifest-only EvidenceStore decision |
| P5 | Built-in workflows, Actions, CLI reconciliation, and programme status | P3 and P4 |
| P6 | Optional stronger enforcement and organization-level enhancements | Capability and plan support |

Each phase MUST use a separate governed change ID, isolated worktree, bounded ownership claim, review, verification, pull request, and safe cleanup.

Before each implementation phase, a modularity assessment MUST evaluate the proposed units and seams against the current post-047 codebase. A proposed split MUST identify its contract, dependency direction, verification, and reversal cost. Unmeasured evidence MUST produce a defer trigger rather than a fabricated score.

## 24. Risks and recovery

| Risk | Mitigation | Recovery |
|---|---|---|
| Project and repository state drift | Idempotent reconciliation and immutable artifact links | Rebuild Project projections from Git and issues |
| Duplicate records | Stable IDs and idempotency keys | Merge or close duplicates without deleting history |
| Excessive field/schema complexity | Canonical projection fixed at 25 managed fields with strict manifest validation and modular feature flags | Reconcile from the manifest; disable optional feature use without deleting historical Project data |
| Provider tool contract changes | Exact version pin, capability detection, contract tests | Disable affected workflows and retain read-only status |
| Automation overwrites operator edits | Optimistic concurrency and conflict reporting | Reapply operator state from issue history |
| Paid feature assumptions | Plan capability detection and explicit fallbacks | Downgrade gate to advisory with residual-risk record |
| Review noise pollutes backlog | Validation and configurable extraction modes | Close extracted records as rejected, retaining provenance |
| Authority duplication | Store summaries and immutable links only | Regenerate Project metadata from authoritative artifacts |

The complete capability can be disabled through JSON without deleting GitHub records. Provider operations, Actions workflows, and project reconciliation MUST fail safely when disabled.

## 25. Programme workspace

The long-lived working authority for this capability is:

```text
.work/programmes/work-management/
├── programme.json
├── target-spec.md
└── roadmap.md
```

Child implementation slices remain under `.work/changes/<change-id>/` and use independent worktrees, scopes, tests, reviews, verification, pull requests, and closeout. Stable reader-facing documentation is updated only at the configured documentation milestones.

## 26. Implementation decisions
### Resolved

- **PM-OPEN-001 — resolved by change 057**: Backend topology is a configurable mix of shared portfolio and per-project bindings in strict versioned settings.
- **PM-OPEN-002 — resolved by changes 055 and 057**: `.work/reviews/<review-id>/` is canonical. P5 adds bounded atomic persistence, idempotent replay, optimistic updates, and conflict retention without a delete surface.
- **PM-OPEN-003 — resolved by existing provider commissioning and change 057**: The initial adapter uses the pinned official GitHub MCP `v1.8.0` at revision `ca8ab52dcc45b86fae190398178fd22edb7b1362`.
- **PM-OPEN-004 — resolved by change 057**: Supported Project read/add/update methods are capability-detected and composed. Built-in workflow provisioning remains explicit unsupported capability and requires operator setup when needed.
- **PM-OPEN-005 — resolved by change 057**: Project schema and record changes require explicit preview/apply selection and idempotency, but do not introduce a new approval-record type.

### Commissioning state

Change `058-work-management-commissioning` established the registered shared Project #1 binding. Later Work Management slices enabled bounded reconciliation and command-plane operations; changes 152 and 155 added the registered schema commissioner, provisioned the canonical fields/options/views, corrected empty Project field normalization, and established the 25-field command plane. Change 157 made each of the 12 saved views an executable semantic contract rather than a name/layout shell; change 162 added bounded behavioral saved-view readback and fail-closed unverified diagnostics; change 166 completed the correction by requiring every canonical view to constrain `Status` to current command-plane lifecycle values and by recommissioning all 12 views to zero mismatch/unverified state. Evidence-backed legacy lifecycle reconciliation moved only records with authoritative disposition evidence; ambiguous legacy `Todo` backlog remains unmanaged historical state and is excluded by canonical view filters.

Current live readiness is deliberately **not** frozen as a success claim in this programme document. `project_management_schema_status` is the runtime authority for the current Project observation and must compare fields, options, view layouts, filters, visible fields, sort/group configuration, and board vertical grouping against the checked-in manifest. `project_management_schema_plan` must be empty after successful commissioning. The bounded registered-Project commissioner may create missing manifest elements and repair only API-supported view semantics; unsupported semantic drift remains explicit rather than being reported as ready. Dated final live evidence belongs in the closing issue/change record.

`reconciliation` and programme status are enabled; `intake` and `review_import` remain read-only, and all native/custom automation flags remain disabled unless separately commissioned. Those feature choices are not schema-readiness defects and do not alter the Work authority model.

## 27. External product sources

External product facts relevant to the current semantic-view contract were reverified on 2026-08-16 against:

- GitHub Projects overview: <https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects>
- GitHub Project fields and limits: <https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields>
- GitHub Issues, sub-issues, and dependencies: <https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues>
- GitHub Project API automation: <https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects>
- GitHub Project filtering: <https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/filtering-projects>
- GitHub Project views REST API: <https://docs.github.com/en/rest/projects/views?apiVersion=2026-03-10>
- GitHub Projects GraphQL reference: <https://docs.github.com/en/graphql/reference/projects>
- GitHub Project automation: <https://docs.github.com/enterprise-cloud@latest/issues/planning-and-tracking-with-projects/automating-your-project>
- GitHub repository ruleset availability: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- Official GitHub MCP server: <https://github.com/github/github-mcp-server>

External documentation describes current platform capability, not KIS implementation status. The implementation phase MUST reverify plan limits, OAuth scopes, API contracts, and MCP tool names against the selected pinned release.
