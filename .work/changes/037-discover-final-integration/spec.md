# Change Specification: Discover Final Integration

- **Change ID**: `037-discover-final-integration`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Complete the approved bounded public Discover surface with four operations—`inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change`—using the existing server registration seams and internal services, without installing Tool or Provider packages or modifying policy/settings authority.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, and the operator-approved donor capability audit.
- Runtime integration remains within `src/kis_mcp/discover/**`; `server.py` already invokes the Discover registration seams and is not modified.
- Public contracts and regression coverage are owned under `contracts/discover/**` and `tests/discover/**`.
- Discover product-spec status and dedicated final-integration documentation are owned here.
- Tool and Provider implementation directories, policy, settings, `SPEC.md`, and `docs/OPERATIONS.md` remain excluded.

## Requirements

- **REQ-001**: `register_discover_tools` must register `inspect_project` and `get_code_context`, and `register_change_tools` must register `inspect_change` plus `analyze_change` when the service supports analysis. Every public operation must be read-only, non-destructive, idempotent, and closed-world.
- **REQ-002**: `InspectProjectService` must remain the server-created façade and delegate code-context requests to `ContextBrokerService` with the same configured boundary and Discover settings.
- **REQ-003**: `get_code_context` must accept an explicit project, task, and complete explicit budget and return the existing version-1 response contract.
- **REQ-004**: `inspect_change` must expose `working_tree`, `staged`, `commit`, `range`, and `branch`, with refs validated by the existing strict contract while preserving the one-argument working-tree default.
- **REQ-005**: `analyze_change` must compose local change inventory and impact analysis for supported local Git targets.
- **REQ-006**: `analyze_change` must also accept bounded caller-supplied file changes and caller-supplied GitHub pull-request metadata without executing a connector or accessing the network.
- **REQ-007**: Supplied changes, task terms, dependency relationships, relationship impacts, tests, and verification handoffs must remain bounded by configured Discover limits and explicit request budgets.
- **REQ-008**: Task terms must reach `ImpactGraphService`; the service must not report task-token impact unavailable when terms were supplied.
- **REQ-009**: Contract, configuration, and task-term relationships must include explicit provenance and confidence and must not be represented as deterministic when they are heuristic.
- **REQ-010**: The unified response must include evidence-backed implementation steps, affected tests, and non-executable verification handoffs.
- **REQ-011**: Structural request and Discover errors for all public operations must be deterministic JSON `ToolError` payloads without new `HR-*` decision codes.
- **REQ-012**: Existing task-term-free `InspectImpactRequest` serialization and existing `inspect_project` and `inspect_change(path)` callers must remain compatible.
- **REQ-013**: Raw `inspect_impact`, provider admission, and project catalog services must remain internal.
- **REQ-014**: Checked-in request/response schemas and end-to-end tests must cover the new workflow, normalization, budgets, annotations, server composition, and failure paths.
- **REQ-015**: Documentation must distinguish implemented local behavior, supplied-context normalization, internal services, and staged provider-backed capabilities.

## Acceptance

1. The mounted runtime exposes `inspect_project`, `inspect_change`, `get_code_context`, and `analyze_change` without exposing raw `inspect_impact`, provider admission, or project catalog tools.
2. `get_code_context` delegates the exact `GetCodeContextRequest`, including explicit budget values.
3. `inspect_change` accepts every supported local source shape and preserves its working-tree default.
4. `analyze_change` handles local targets and bounded supplied changes, including normalized GitHub repository and SHA metadata, without connector execution.
5. Task terms, contract/configuration relationship evidence, implementation steps, affected tests, and verification handoffs are present when supported and bounded by the declared budgets.
6. Invalid requests return deterministic structural JSON without `HR-*` codes.
7. Existing Discover behavior and legacy request serialization remain compatible.
8. Focused Discover tests, full Discover regressions, change-governance checks, and full repository verification pass on the integrated head.
9. No Tool or Provider package is installed and no policy/settings authority is changed.

## Risks and recovery

- Risk: broadening public tool signatures can break existing callers.
- Mitigation: preserve existing defaults and parameter names; add only optional fields and a separate workflow.
- Risk: caller-supplied metadata or relationship expansion can create unbounded input/output.
- Mitigation: enforce configured maximum change/task counts and make dependency plus relationship evidence share the explicit dependant budget.
- Risk: heuristic contract/configuration links could be interpreted as deterministic.
- Mitigation: emit explicit provenance and medium/low confidence.
- Risk: Discover could cross into provider or Work responsibilities.
- Mitigation: normalize supplied remote context only; do not execute connectors, verification commands, repository code, or package installation.
- Recovery: revert the implementation commits. No persistent state, policy migration, credentials, provider installation, or external side effect is introduced.

## Out of scope

- Connector execution or external network access from Discover.
- Dynamic JavaScript imports, alias/package resolution, and external module resolution.
- Semantic-provider installation or activation.
- Verification execution inside Discover.
- Background indexing or implicit scans of `C:\Projects`.
- Public provider-admission, project-catalog, or raw `inspect_impact` tools.
