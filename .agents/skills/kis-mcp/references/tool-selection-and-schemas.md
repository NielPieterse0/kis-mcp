# Tool Selection and Schema Patterns

## Load when

Read this reference when choosing between direct tools and the discoverable
long tail, constructing an unfamiliar tool payload, or interpreting kis-mcp
schema/effect metadata.

## Progressive exposure model

kis-mcp intentionally keeps the normal tool list bounded. The live catalogue
contains three practical layers:

1. **Direct** — frequent operations whose schemas are already exposed to the host.
2. **Discoverable** — valid long-tail operations found through capability search
   and invoked through their original schemas.
3. **Status-only** — disabled, unavailable, auth-gated, build-failed, or
   mount-failed operations that remain visible as evidence but are ineligible.

Do not equate hidden-from-direct-list with unavailable.

## Discovery sequence

Use the smallest sequence needed:

```text
recommend_workflow(task)
search_capabilities(query, limit)
describe_capability(capability_id)
```

`search_capabilities` returns compact contribution, operation, and workflow
records. Exact IDs/names rank above generic capability matches.

`describe_capability` is the preferred exact view. For operation records, inspect
at least:

- `operation_id` and `name`;
- `description`;
- `effects`;
- `readiness` and `eligible`;
- `eligibility_reasons`;
- `execution_surface`;
- `input_schema` when the running runtime exposes it.

If an older runtime returns no useful `input_schema`, do not guess. Use a direct
host schema when available, or inspect the current provider/tool contract.

## Dispatcher contracts

All long-tail dispatchers use this outer shape:

```json
{
  "operation": "exact_operation_name_or_id",
  "arguments": {}
}
```

The `arguments` object must match the original operation's schema.

- `execute_read_action`: operation must be read-only.
- `execute_change_action`: operation must include local-change, quarantine, or
  process effect and no incompatible external effect.
- `execute_external_action`: operation must include the external effect.

Capability-control operations cannot recursively dispatch themselves.
Operations that still require their original approval workflow are not made
approval-free by generic dispatch.

## Common direct tool shapes

These are stable usage patterns; the live host schema remains authoritative.

### Repository discovery

```json
{"path":"C:\\Projects\\example","limits":null}
```

`inspect_project` accepts an absolute local project path and optional positive
limits that may only narrow configured maxima.

`inspect_change` accepts a project path plus change-source fields when exposed:

```json
{
  "path":"C:\\Projects\\example",
  "source":"working_tree",
  "commit_ref":null,
  "base_ref":null,
  "head_ref":null
}
```

Use only the fields required by the selected source. Safe Git refs are
structural inputs, not arbitrary shell commands.

### Change-aware verification selection

`select_change_verification` is read-only. It reconciles change-impact handoffs
against current declared verification profiles and does not run commands:

```json
{
  "project":"C:\\Projects\\example",
  "source":"working_tree",
  "task_terms":["tests","type checking"],
  "max_verifications":20
}
```

For commit/range/branch sources, supply only the corresponding ref fields from
the live schema. `max_verifications` is bounded by the operation contract.

### Bounded change execution

When advertised, `execute_change_workflow` is the preferred orchestration layer
for "verify and review this change" requests:

```json
{
  "project":"C:\\Projects\\example",
  "source":"working_tree",
  "task_terms":[],
  "max_verifications":20,
  "verification_timeout_ms":120000,
  "review_types":["code-quality","test-quality"]
}
```

Optional `review_backend` and `review_model` must follow the current reviewer
contract. Omitting `review_types` defaults the workflow to `code-quality`. The
workflow composes only its fixed selection, verification, and review operations;
it is not an arbitrary command/workflow executor.

### File reads

```json
{"path":"C:\\Projects\\example\\README.md","offset":0,"length":200}
```

Prefer absolute paths. Use `read_multiple_files` with a `paths` array when the
same task needs several known files. For large files, paginate rather than
requesting the entire artifact.

### Text edits and writes

For surgical text replacement:

```json
{
  "file_path":"C:\\Projects\\example\\file.txt",
  "old_string":"exact old text",
  "new_string":"replacement",
  "expected_replacements":1
}
```

Use `write_file` for create/rewrite/append operations with explicit `path`,
`content`, and `mode`. Prefer small focused edits over whole-file rewrites.

### Processes

`start_process` requires a command and bounded timeout:

```json
{"command":"git status --short","timeout_ms":120000,"shell":"powershell"}
```

For interactive processes, retain the returned PID and use
`interact_with_process`. For long or deferred output, use `read_process_output`
with bounded pagination.

## Schema discipline

- JSON object means object/map, not a JSON-encoded string.
- Arrays remain arrays; do not flatten them into comma-separated strings unless
  the original schema explicitly requires a string.
- Preserve `null`/omitted distinctions when the schema makes a field optional.
- Prefer exact operation IDs/names returned by the current runtime.
- Treat result `schema_version` as contract evidence; do not silently reinterpret
  a future version using an older shape.
- If a result says `truncated: true`, follow the operation's pagination or
  narrowing mechanism before claiming completeness.
