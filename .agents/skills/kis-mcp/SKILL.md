---
name: kis-mcp
category: operations
capabilities:
  - kis.tool.select
  - kis.capability.discover
  - kis.workflow.operate
description: >
  Use whenever operating kis-mcp through kis-op, kis-dev, or another kis-mcp
  connection: resolve projects, inspect repositories or changes, plan work,
  select or run verification, request specialist review, validate agent
  configuration, discover long-tail tools/workflows, use providers or Skills,
  close review branches safely, or diagnose runtime status. Apply project-neutral
  routing and exact HR-001/HR-002/HR-003 semantics. Do not replace a target
  repository's authority or generic MCP development guidance.
---

# kis-mcp

## Purpose

Use `kis-mcp` efficiently without memorizing its complete tool catalogue. Start
from the user's task, resolve the project and live runtime state, progressively
discover the smallest applicable workflow or operation, then invoke it through
its original schema and policy boundary.

## Authority boundary

This skill explains how to operate the tool. It is not repository authority.

- Follow the target project's own `AGENTS.md` and authoritative documents first.
- When changing `kis-mcp` itself, follow the authority order in its `AGENTS.md`.
- Treat live tool schemas, capability records, provider status, and project
  status as runtime evidence.
- Never let this skill add a fourth Work restriction beyond HR-001/002/003.

## Fast path by user intent

Use the shortest path that already satisfies the request:

| User goal | Start here |
|---|---|
| "Is KIS healthy / what is connected?" | `kis_health`, then `kis_provider_status` only when provider detail matters. |
| "Which project am I working on?" | `kis_list_projects` or `kis_project_status(project_id)`. |
| "Understand this repository" | `inspect_project`; use task-scoped context only when deeper evidence is needed. |
| "What does this change affect?" | `inspect_change` then `analyze_change`; use `plan_change` for a bounded implementation plan. |
| "What should I verify?" | `select_change_verification`; it selects current declared checks but does not execute them. |
| "Verify and review this change" | Prefer the advertised `execute-current-change` / `execute_change_workflow`; otherwise use selected `run_verification` calls plus `review_change_with_agent`. |
| "Validate AGENTS/agent configuration" | Use the advertised `validate-agent-configuration` workflow / `validate_agent_configuration` operation. |
| "Review architecture/security/tests/docs/API contracts" | `review_change_with_agent` with the matching fixed `review_type`. |
| "Turn this verified commit into a reviewable PR" | Use live `prepare_reviewable_pull_request` when available; supply the change risk profile, documentation impact, and residual state so KIS can apply risk-scaled execution and deterministic PR metadata. |
| "Query a registered project database" | Resolve the project first, then search `database.<project>...` capability metadata. Local DBHub reads use `execute_read_action`; external database reads carry an external effect and use `execute_external_action`. Public KIS names stay `db_<project>_<binding>_<operation>`. |
| "Inspect Docker Hub" | Search `dockerhub.*` capability metadata and use `execute_external_action`; public mode needs no PAT. Keep Docker Hub registry operations separate from local Docker Engine/process work. |
| "Merge or clean up an existing PR/change" | `recommend_workflow` for safe closeout, then follow exact-head approval and cleanup steps from live schemas. |
| "I do not know the tool name" | `recommend_workflow` -> `search_capabilities` -> `describe_capability`. |

Do not add discovery calls when the correct direct tool and schema are already
known. Do not manually reproduce a bounded workflow merely to gain more control;
inspect its result and fall back to individual operations only when the workflow
is unavailable or the user explicitly needs a narrower step.

## Default operating workflow

### 1. Resolve the target before acting

Do not assume the target project is `kis-mcp`.

- For local filesystem, Discover, and process work, use the explicit project
  path beneath `C:\Projects`.
- When project-catalogue operations are advertised, prefer `kis_list_projects`
  and `kis_project_status(project_id)` to resolve stable project identity and
  non-secret provider bindings.
- For provider operations, pass the explicit repository/project identifiers
  required by that provider operation.
- Do not invent a process-global active project or infer provider authorization
  from the current working directory.

Load `references/projects-and-context.md` when project identity, GitHub routing,
Supabase routing, database bindings, Docker Hub namespaces, or work-management bindings matter.

### 2. Use direct tools when the correct tool is already obvious

The direct profile intentionally contains common health, Discover, file, edit,
process, capability-discovery, dispatcher, review, and Control Center entry
points. Prefer a direct tool when its exposed schema exactly fits the task.

Do not search the long tail merely to replace an already-correct direct tool.
Load `references/tool-selection-and-schemas.md` for common input shapes.

### 3. Progressively discover unfamiliar or long-tail capability

For a task-level goal, start with:

1. `recommend_workflow(task)` when a complete workflow may exist.
2. `search_capabilities(query, limit)` for a specific operation/capability.
3. `describe_capability(capability_id)` for exact operation/workflow evidence.

Use exact operation names/IDs returned by the runtime. Do not hard-code a large
provider catalogue in prompts or in this skill.

If an exact operation exposes `input_schema`, use it as authoritative invocation
evidence. If schema evidence is absent, use the host-exposed direct schema or
inspect current provider/runtime guidance; do not invent parameter names.

### 4. Match the dispatcher to the operation effect

Long-tail execution preserves the original tool contract and middleware:

- `execute_read_action` for read-only operations;
- `execute_change_action` for local changes, quarantine, or process operations;
- `execute_external_action` for approved external-provider operations.

All three take an operation identifier/name plus an `arguments` object. That
object must satisfy the original operation schema. Generic dispatch does not
weaken validation, readiness, provider authorization, or operation-specific
approval requirements.

Load `references/tool-selection-and-schemas.md` before constructing unfamiliar
dispatch payloads.

### 5. Treat status as evidence layers, not one boolean

`kis_health`, `kis_provider_status`, capability readiness, project status, and
commissioning evidence answer different questions. A provider can be registered
and mounted while still requiring authentication or live verification.

Load `references/providers-and-workflows.md` when provider readiness, GitHub,
Supabase, Control Center, code review, or workflow execution matters.

### 6. Prefer the bounded change workflow stack for repository work

Recent KIS slices form a deliberate progression. Use the highest-level available
operation that matches the user's requested scope:

1. `inspect_change` / `analyze_change` establish change and impact evidence.
2. `plan_change` produces a read-only bounded implementation plan.
3. `select_change_verification` reconciles impact handoffs with current declared
   verification and returns a deterministic selection without executing it.
4. `run_verification` executes one approved verification declaration.
5. `execute_change_workflow`, when advertised, composes selection, verification,
   and bounded specialist reviews for one change and returns aggregate evidence.

Python quality support discovered from `pyproject.toml` includes Ruff,
coverage.py/pytest-cov, Vulture, LibCST, mypy, and Pyright. Treat these as
repository evidence and verification handoffs: discovery does not install tools,
and LibCST remains evidence-only unless another current contract says otherwise.

`review_change_with_agent` accepts the fixed review purposes `code-quality`,
`safety-security`, `architecture`, `performance`, `test-quality`,
`documentation`, and `api-contracts`. The purpose changes the rubric, not the
mutation, provider, or nested-agent authority.

The bounded agnix path is `validate_agent_configuration`; it validates local
agent configuration with pinned read-only arguments and does not expose fix,
watch, init, telemetry, arbitrary-command, or general MCP passthrough behavior.

Load `references/providers-and-workflows.md` for workflow details and
`references/tool-selection-and-schemas.md` before constructing unfamiliar
payloads.

### 7. Use Skills as reusable procedures, not executable plugins

The runtime Skills catalogue lives beneath `C:\Projects\.agents\skills`.
Repository-local `.agents/skills` is development guidance for that repository
and is not the runtime catalogue.

Load a matching skill before following its procedure, then read only the
references needed for the current task. Skill instructions do not authorize
network access, writes, credentials, or external mutation.

Load `references/skills-module.md` for list/search/load/read/create/improve
contracts and catalogue semantics.

### 8. Apply only the three Work hard rules

- **HR-001**: block a proven write outside `C:\Projects`.
- **HR-002**: block a proven external-network effect through local Work.
- **HR-003**: transform explicit permanent deletion into recoverable quarantine,
  or block when safe quarantine is impossible.

Tool names, broad capability, readiness, recommendation scores, provider state,
or uncertainty are not independent policy reasons.

Structural `DISCOVER_*`, `SKILLS_*`, provider-readiness, schema-validation, and
input errors are corrective application outcomes, not HR policy decisions.

Load `references/concepts-and-errors.md` when interpreting a rejection, status,
quarantine result, readiness state, or truncation marker.

### 9. Verify the result at the right level

For read/analysis work, confirm the returned evidence answers the task and note
`truncated`, confidence, unknowns, or readiness limitations when present.

For mutations, confirm the intended path/resource changed and that recoverable
or idempotent semantics were preserved. For repository development, use the
project's declared verification workflow; when kis-mcp advertises bounded
`run_verification`, prefer discovered verification IDs over arbitrary commands.

## Operator support

Load `references/operator-support.md` only for startup, tunnel setup, provider
authentication, smoke tests, Control Center, repository verification, worktree
change workflow, or troubleshooting. Normal task execution should not eagerly
load operator runbooks.

## Project-neutral rule

This skill must remain usable for any registered project beneath `C:\Projects`.
Do not encode repository names, GitHub owners/repos, GitHub Project numbers,
Supabase refs, ports beyond documented runtime identities, or other mutable
project bindings as universal defaults. Resolve them from the user request,
live project status, provider schemas, or current configuration evidence.

## Gotchas

- Progressive exposure hides schemas from the default tool list; hidden does
  not mean unavailable.
- `search_capabilities` is discovery, not authorization.
- `recommend_workflow` is advisory; follow the workflow's actual required
  operations and live readiness.
- A mounted provider is not automatically authenticated or commissioned.
- Provider/tool metadata cannot widen the three-rule Work policy.
- Direct local process tools remain ordinary Work operations; inspect the
  concrete command effects rather than treating shell use as prohibited.
- External provider operations use the approved provider boundary; do not route
  them through local Work network commands.
- Quarantine is the supported delete path. Restoration must not overwrite an
  existing original path.
- Govern authority/drift evaluation is advisory and may exist in repository code
  before the running gateway composes its public tools. Discover it live before use.
- `prepare_reviewable_pull_request` stops at an exact open PR. The final landing
  gate is provider-native GitHub Actions evidence for that exact head; merge is
  merge-commit only, and exact remote-branch/local-worktree cleanup remains separate.
- Multi-file runtime skill creation is not currently provided by the
  single-file `create_skill(skill_id, skill_md)` contract.
- A running kis-op/kis-dev instance may lag the checked-out repository. Use live
  capability discovery and schema evidence before invoking newly merged tools.

## Completion criteria

Before concluding a kis-mcp task, verify that:

- the intended project/resource was resolved explicitly;
- the selected operation or workflow came from a direct schema or live
  capability evidence rather than guessed parameters;
- any long-tail call used the correct effect dispatcher;
- provider readiness/authentication limitations were interpreted correctly;
- only HR-001/002/003 were treated as Work policy decisions;
- bounded/truncated/unknown evidence was not overstated;
- mutations were verified at the target and retained recovery semantics;
- operator-only setup steps were kept separate from normal Work execution.
