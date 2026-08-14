# Skill Usage Telemetry Design

## Status

Approved implementation slice for `kis-mcp#234`, supporting `chatgpt-skill#49`.
KIS owns observation and reporting; `chatgpt-skill` owns behavioral effectiveness and admission decisions.

## Research decision

Use the existing KIS `RuntimeObservability` model instead of introducing a second tracing stack.
The design follows these current primary-source constraints:

- OpenTelemetry: use stable low-cardinality operation/event names, bounded attributes/events, and duration/timestamp evidence.
- W3C Trace Context: correlate related operations with explicit identifiers rather than payload inspection.
- OpenAI Agents SDK: tracing may carry workflow/group identifiers, but sensitive model/tool inputs and outputs can and should be excluded.
- OpenAI usage: token/request metrics are useful only when actually returned by the runtime/provider.
- OpenInference: mature AI observability composes with OpenTelemetry and uses explicit masking/configuration rather than bespoke prompt logging.
- Langfuse OSS: operational telemetry can be useful without exporting raw traces, prompts, observations, scores, or datasets.

Primary references:

- https://opentelemetry.io/docs/specs/otel/trace/api/
- https://opentelemetry.io/docs/specs/otel/trace/sdk/
- https://www.w3.org/TR/trace-context/
- https://openai.github.io/openai-agents-python/tracing/
- https://openai.github.io/openai-agents-python/usage/
- https://github.com/Arize-ai/openinference
- https://github.com/langfuse/langfuse

## Architecture

### 1. Live evidence

Extend `RuntimeObservability` with a bounded `SkillActivityRecord` deque.
Every record is payload-free and contains only low-cardinality event identity, skill identity, immutable snapshot/hash evidence, correlation IDs, outcome, duration, and optional observed counters.
Control Center exposes this bounded live evidence beside the existing tool/boundary evidence.

### 2. Durable evidence

Persist the same redacted skill events in a KIS-owned SQLite database beneath `RuntimeConfig.state_root`.
SQLite is part of Python, supports concurrent KIS operation/development runtimes, and avoids a new service or dependency.
Retention is row-bounded; oldest events are pruned after successful inserts.
The database contains no prompt text, skill contents, file contents, raw search query, credentials, or arbitrary tool arguments.

### 3. Observed versus reported evidence

KIS automatically observes discovery, load, resource search/read, refresh, structural evaluation, create, and improve operations.
A load is recorded as `loaded`, never as an application or completion.

Actual application/completion cannot be inferred from a read call. Add an explicit `record_skill_outcome` operation that records caller-attributed `applied`, `completed`, or `failed` evidence only when it matches an earlier observed load by skill, activation ID, snapshot, and entrypoint SHA-256.
Reported outcome evidence is labeled `reported`; it is not represented as independently observed runtime truth.

### 4. Correlation

Reserve the MCP boundary request ID before dispatch and place it in a `contextvars.ContextVar` for the lifetime of the call.
Skills telemetry reads that request ID without inspecting the request payload.
Optional `activation_id` and `project_id` parameters allow an agent/runtime to correlate load, resource reads, and reported outcomes when those identities are actually known.
Unknown project/session metrics remain null/`unknown`; they are never inferred from filesystem paths or conversation content.

## Event contract

Stable event names:

- `skill_discovered`
- `skill_loaded`
- `skill_resource_discovered`
- `skill_resource_read`
- `skill_catalogue_refreshed`
- `skill_evaluated`
- `skill_created`
- `skill_improved`
- `skill_applied`
- `skill_completed`
- `skill_failed`

Common fields: event ID/time, event name, source (`observed` or `reported`), skill ID, snapshot ID, content SHA-256, project ID, activation ID, request ID, outcome, duration, and error class.
Optional numeric fields are `total_tokens`, `tool_calls`, and `retries`; optional verification evidence is boolean.
Those optional metrics are recorded only when the caller has actual observations; absence remains null and reports it as not observable.

## Public interface

Keep existing Skills operations and add:

- `record_skill_outcome(...)` — bounded telemetry mutation; validates attribution against a prior observed load.
- `skill_telemetry_report(...)` — bounded read-only grouped evidence by skill/version/project.

Add optional `activation_id` and `project_id` to `load_skill` and `read_skill_file` so resource activity can be correlated without embedding payloads.
Search/list discovery remains automatically observed without retaining raw queries.

The report exposes separate counters for discovered, loaded, resource-read, applied, completed, failed, evaluation, and mutation events plus observed duration/metric sample counts. It does not calculate one opaque quality score.

## Retention and failure behavior

Default durable retention is 20,000 redacted events; reports return at most 100 grouped rows.
Database initialization and inserts use bounded SQLite timeouts and transactions.
Telemetry failure must not silently change skill results: read operations continue while the telemetry failure is surfaced as a diagnostic/log; explicit telemetry writes fail correctively.
Catalogue mutation semantics and HR-001/2/3 remain unchanged.

## Testing

Test-first coverage must prove:

1. request correlation is stable within one boundary call and cleared afterwards;
2. live skill activity is bounded and contains no prompt/file/tool argument values;
3. durable events survive service recreation and prune deterministically;
4. load/resource operations record the correct skill snapshot/hash identity;
5. raw search queries are absent from live and durable evidence;
6. an attributed outcome without a matching observed load is rejected;
7. matching reported application/completion evidence is retained separately from loads;
8. unavailable token/tool/retry metrics remain null/not-observable;
9. reports group by skill, version/hash, and project without collapsing to a single score;
10. existing policy/tool-surface and repository verification remain green.

## Scope boundary

This slice does not decide whether a skill is good or bad. It supplies trustworthy usage/outcome evidence.
`chatgpt-skill#49` consumes this evidence alongside trigger evals, candidate-vs-baseline assertions, verification evidence, timing/cost metrics where observable, and human review to produce the behavioral scorecard.
