# Change Specification: Work Management Command Plane

- **Change ID**: `125-work-management-command-plane`
- **Status**: Approved
- **Complexity**: `large`
- **Risk Triggers**: `architecture_boundary`, `external_action`, `public_contract`

## Outcome

Make Work Management authoritative for operational intent and next-work direction while preserving repository, Git/GitHub, and Actions authority for implementation and evidence. Standardize intake, automate the normal work lifecycle, and keep governance/classification definitions in checked-in settings or contracts rather than executable constants.

## Authority and scope

- Work Management owns priority, effort, work state, hold/defer, scheduling, queue ordering, and execution claims.
- `.work/changes` owns governed change definition, complexity, and risk classification once implementation begins.
- Git/GitHub owns revision, branch, pull-request, and merge facts.
- GitHub Actions owns landing verification evidence.
- KIS performs directional reconciliation; no last-write-wins authority is permitted.
- GitHub issues own bounded outcome, context, acceptance criteria, discussion, and native relationships.

## Requirements

- **REQ-001 — Authority map:** checked-in configuration MUST declare field authority and synchronization direction for every command/evidence field.
- **REQ-002 — Standard intake:** one issue form MUST standardize bounded outcome titles and the issue sections `Outcome`, `Context`, `Acceptance criteria`, `Constraints / dependencies`, and `Evidence / references` without copying Project-owned metadata into the body.
- **REQ-003 — Work versus delivery state:** Project `Status` MUST represent operator Work State and include `Ready`; implementation progress MUST be represented separately as `Delivery Stage`.
- **REQ-004 — Planning versus governance:** Work Management `Effort` MUST remain distinct from repository-governed `Complexity`; Complexity and Risk Triggers remain optional before implementation and become evidence projections once a governed change exists.
- **REQ-005 — Classification controls:** supported complexities, risk triggers, base reviews, risk-trigger reviews, and verification limits MUST come from checked-in settings shared by local change governance and change execution.
- **REQ-006 — Ready queue:** KIS MUST deterministically select only eligible unclaimed work using configured priority/queue-rank/effort/age ordering and explain exclusions.
- **REQ-007 — Claims:** claim/release MUST be conflict-safe, explicit, attributable, and non-expiring by default; claim metadata MUST be Work Management-owned.
- **REQ-008 — Lifecycle automation:** bounded task operations MUST support next, claim, release, hold, defer, transition, and guarded completion through the existing reconciliation backend rather than unrestricted provider mutation.
- **REQ-009 — Completion:** Work State MUST NOT become `Done` until applicable traceability, verification, documentation, approval, and hold constraints are satisfied.
- **REQ-010 — Relationships:** native GitHub issue hierarchy/dependency evidence MUST be preserved and used when observable; absence of provider evidence MUST be reported rather than guessed.
- **REQ-011 — Provisioning:** schema/status tooling MUST plan missing command-plane fields/options/views and apply only mutations supported by the bounded provider; unsupported provisioning MUST remain explicit.
- **REQ-012 — Efficiency:** normal commands MUST refresh live evidence on demand; scheduled reconciliation is optional hygiene, not a correctness dependency.
- **REQ-013 — Prior requirements:** decision/disposition, holds with review triggers, assumptions/risks, revision/source-review evidence, hierarchy, documentation reconciliation, and retained history MUST continue to work.
- **REQ-014 — Portfolio:** the same command-plane contract MUST remain project-neutral across all configured managed repositories.

## Acceptance

1. Given an Inbox issue, when it is triaged, then Project fields carry operational metadata without duplicating it in the issue body.
2. Given multiple Ready items, when next work is requested, then one deterministic unclaimed candidate is returned with ranking and exclusion evidence.
3. Given two claims for the same item, when observed Project state changes, then stale reconciliation fails closed instead of overwriting the existing claim.
4. Given a governed change, when its scope classification is read, then exact Complexity/Risk Triggers project into Work Management and applicable configured review safeguards are selected.
5. Given merged work with incomplete required closeout, when completion is requested, then Work State remains open and the blocking evidence is reported.
6. Given the live shared Project lacks required fields/options/views, when commissioning runs, then exact drift and supported repair are reported without fake success.

## Recovery and out of scope

- Configuration changes are reversible by restoring the prior checked-in manifests/settings.
- Claim mutations are recoverable through explicit release/takeover; no automatic claim expiry is introduced.
- No generic GraphQL, unrestricted REST client, second work database, or duplicated GitHub provider is introduced.
- Existing active concurrent change claims are not overwritten.
