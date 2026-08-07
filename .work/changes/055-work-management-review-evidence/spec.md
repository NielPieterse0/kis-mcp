# Change Specification: Work Management Review Evidence

- **Change ID**: `055-work-management-review-evidence`
- **Status**: Approved from the work-management programme P4 authority
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Implement the internal provider-neutral P4 contracts and deterministic services for review-run evidence, explicit coverage, observation triage, finding extraction, and finding lifecycle management.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and `.work/programmes/work-management/target-spec.md` sections 9, 21.4, and 23.
- Owned implementation: `src/kis_mcp/work_management/reviews.py`.
- Owned tests: `tests/work_management/test_reviews.py`.
- Shared integration: package exports, architecture test, and work-management programme records.
- Excluded: policy, providers, GitHub APIs, gateway composition, remote mutation, filesystem persistence, CLI, CI, and deferred change 040.
- Dependency: completed P2 typed records and governance contracts. P3 traceability remains compatible but is not modified.

## Modularity assessment

### Scope and evidence

- Subject class: code-module seams for the P4 domain and the existing advisory review workflow.
- Horizon: tracked repository history from the last 90 days.
- Mode: Mode A plus direct code inspection.
- Evidence strength: Medium. LOC, commits, subjects, Python fan-in/out, co-change, module contents, and public imports are measured. Representative read-set/edit-set ratios and isolated-test effort remain unmeasured.

| Unit | Measured evidence | Decision |
|---|---|---|
| `src/kis_mcp/work_management` | 2,515 LOC, 9 commits, fan-in 3, fan-out 2, co-changes with `tests/work_management` | Preserve the provider-neutral domain boundary. |
| `src/kis_mcp/workflows` | 719 LOC, 4 commits, fan-in 1, fan-out 4 | Preserve as execution/workflow composition, not evidence authority. |
| `traceability.py` | 1,048 lines by direct inspection and one distinct responsibility already implemented | Do not extend with independent review semantics. |
| `workflows/code_review` | Bounded local evidence collector and advisory backend normalization | Keep adapter-specific execution separate from durable review records. |

### Structural decision

Add one cohesive `work_management/reviews.py` module. It owns normalized review contracts, evidence-path manifests, coverage, observation disposition, extraction policy, and finding lifecycle. It may import only provider-neutral work-management contracts. Existing workflow adapters may consume these contracts in P5 but P4 does not modify or publicly compose them.

### EvidenceStore decision

The canonical repository-relative namespace for durable review evidence is confirmed as:

```text
.work/reviews/<review-id>/
├── request.json
├── report.md
├── result.json
├── coverage.json
├── report.sarif       # optional when applicable
└── closeout.json
```

P4 models and validates this artifact manifest. It does not implement a generic EvidenceStore service or perform filesystem writes. Persistence, atomicity, conflict handling, retention, and provider-backed workflow integration remain P5 responsibilities.

## Requirements

- **REQ-001**: Review-run records MUST identify project, review ID, review type, workflow version, requester, exact target, start/completion state, extraction mode, exclusions, assumptions, unknowns, and evidence budget.
- **REQ-002**: Review targets MUST identify an exact repository and at least one immutable or bounded scope selector: commit, range, pull request, branch, or repository-relative paths.
- **REQ-003**: Coverage MUST explicitly distinguish reviewed scope, gaps, completion, and truncation; incomplete coverage MUST remain visible in serialized results.
- **REQ-004**: Evidence manifests MUST generate and validate the canonical `.work/reviews/<REV-id>/` paths without performing persistence.
- **REQ-005**: Review results MUST serialize observations, findings, decisions, assumptions, risks, artifacts, coverage, status, and diagnostics through immutable JSON-safe contracts.
- **REQ-006**: Every observation MUST be triaged before extraction as rejected, informational, recommendation, assumption, decision required, validated finding, risk, or deferred candidate.
- **REQ-007**: Extraction modes MUST be `report_only`, `validated_findings`, and `full_governance`. Report-only MUST create no child candidates. Validated-findings MUST create only validated finding/security-finding candidates. Full-governance MAY additionally create decision, assumption, risk, hold, deferred, and explicitly operator-selected recommendation task candidates when the observation disposition and requested record type support them.
- **REQ-008**: Extracted child candidates MUST retain source review ID, source observation ID, deterministic deduplication key, project identity, evidence, confidence, severity where applicable, and the intended record type.
- **REQ-009**: Finding records MUST support the lifecycle `candidate -> validated -> accepted | rejected | deferred | risk_accepted -> remediation -> verification -> closed`, with deterministic transition validation.
- **REQ-010**: Findings MUST preserve source evidence, location, confidence, severity, validation disposition, remediation record, fix pull request, and follow-up verification references.
- **REQ-011**: Provider-neutral review contracts MUST NOT import FastMCP, gateway, provider, workflow, or GitHub-specific modules.
- **REQ-012**: P4 MUST remain internal only. Public composition, executable orchestration, persistence, provider adaptation, CLI, CI, automation, and live commissioning remain P5.

## Acceptance

1. **Given** a valid review request against an exact commit, **when** serialized, **then** project, workflow, target, exclusions, assumptions, unknowns, budget, and extraction mode are explicit and JSON-safe.
2. **Given** partial review coverage, **when** normalized, **then** the result reports `complete=false`, named gaps, and truncation without claiming full coverage.
3. **Given** a `REV-` identifier, **when** the evidence manifest is created, **then** every canonical artifact path is repository-relative beneath `.work/reviews/<review-id>/` and the SARIF path is optional.
4. **Given** an informational or rejected observation, **when** extraction runs in any mode, **then** no durable child candidate is produced.
5. **Given** validated finding observations, **when** extraction runs in `validated_findings`, **then** deterministic finding candidates are produced and repeated extraction returns equivalent keys rather than duplicates.
6. **Given** governance observations, **when** extraction runs in `full_governance`, **then** only disposition-compatible decision, assumption, risk, hold, deferred, finding, or security-finding candidates are returned.
7. **Given** an invalid finding transition, **when** evaluated, **then** the transition is rejected without changing the finding record.
8. **Given** the P4 package, **when** architecture tests inspect imports, **then** no forbidden platform or provider dependency exists.

## Risks and recovery

- Risk: duplicating the existing advisory code-review response format. Mitigation: the workflow remains an adapter; P4 defines the normalized durable domain contract only.
- Risk: creating a premature generic storage subsystem. Mitigation: model validated artifact paths and manifests only; defer persistence to P5.
- Risk: automatically converting report noise into work. Mitigation: require explicit observation disposition and extraction-mode filtering.
- Risk: one large review module becoming another traceability monolith. Mitigation: keep the module limited to one domain purpose and defer a split until measured change evidence supports it.
- Recovery: revert the P4 commit. No provider state, external system, migration, or persisted review artifact is modified by this slice.

## Out of scope

- Changes to the existing advisory agent or its backends.
- Creating `.work/reviews/<review-id>/` evidence during runtime.
- GitHub issue or Project creation.
- Public MCP operations, workflow descriptors, gateway exposure, settings, schemas, CLI, CI, and reconciliation.
- P5 automation and portfolio status.
