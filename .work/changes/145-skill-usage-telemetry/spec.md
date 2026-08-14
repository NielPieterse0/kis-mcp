# Change Specification: Skill Usage Telemetry

- **Change ID**: `145-skill-usage-telemetry`
- **Status**: Active
- **Complexity**: medium
- **Risk triggers**: persistent state, public contract, sensitive-data handling

## Outcome

Add bounded, privacy-preserving, version-attributed Skills telemetry to KIS so downstream skill evaluation can distinguish discovery/load activity from explicitly attributed application and completion outcomes.

## Authority and scope

- `AGENTS.md`, `SPEC.md`, `docs/TRUST-MODEL.md`, and `policy/kis-mcp.policy.json` remain authoritative.
- KIS owns operational observation/reporting; `chatgpt-skill` owns behavioral effectiveness and admission decisions.
- The existing `RuntimeObservability` path is extended; no parallel tracing authority is introduced.
- Work policy remains exactly HR-001, HR-002, and HR-003.

## Requirements

- **REQ-001**: Correlate Skills operations with bounded request/activation/project identifiers without payload capture.
- **REQ-002**: Persist at most 20,000 redacted events and return at most 100 grouped report rows.
- **REQ-003**: Attribute longitudinal evidence to immutable skill package hashes.
- **REQ-004**: Never infer application/completion from a load; reported outcomes require a matching observed load.
- **REQ-005**: Missing tokens/tool calls/retries/verification metrics remain unobservable rather than invented.
- **REQ-006**: Skills telemetry operations retain correct read/change capability effects and long-tail exposure.

## Acceptance

1. Observed load/read/evaluation/mutation events carry the correct package hash and never store prompt/file/search payloads.
2. `record_skill_outcome` rejects unattributed outcomes and records matched `applied`, `completed`, or `failed` evidence separately.
3. `skill_telemetry_report` returns separate bounded counters and observable metric sample counts without an opaque quality score.
4. Request correlation is scoped to one boundary call and live evidence is bounded.
5. Real shared-skill commissioning proves discovery, load, completion attribution, mutation, refresh, and quarantine through the progressive capability surface.
6. Focused tests, scope validation, specialist review, and exact-head CI pass before merge.

## Risks and recovery

- SQLite contention or corruption must not silently alter Skills results; explicit telemetry failures remain corrective and state is outside repository authority.
- Cardinality/privacy drift is constrained by closed structured fields and bounded identifiers.
- Recovery is to quarantine/rebuild generated telemetry state; repository and Skills catalogue truth remain authoritative.

## Out of scope

- Behavioral with-skill versus baseline evaluation and skill admission/withdrawal decisions.
- Prompt, file-content, secret, credential, or arbitrary argument capture.
- A new external observability service or fourth Work policy rule.
