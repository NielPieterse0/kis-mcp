# Change Specification: Context7 and Serena Adapters

- **Change ID:** `040-context7-serena-adapters`
- **Status:** Planning gate pending operator approval of new hard-block mappings
- **Risk profile:** Elevated because Serena exposes mutation, shell, and file-delete effects
- **Dependency:** Merged `029-tools-code-tooling` foundation

## Outcome

Integrate two independent adapters behind the existing provider-neutral Tools foundation:

1. Context7 as an approved external documentation-evidence service.
2. Serena as a local MCP semantic-code provider with its provider state redirected beneath `C:\Projects\.kis-mcp`.

The adapters remain independent. Failure, absence, or disablement of one must not prevent the other or the wider kis-mcp runtime from starting.

## Existing authority

- Preserve exactly HR-001, HR-002, and HR-003.
- Use `docs/HARD-BLOCK-APPROVAL-REGISTER.md` as the only operator approval register for hard blocks or quarantine transforms.
- Do not create a separate approval list.
- Do not suppress tools merely by name, category, overlap, destructive appearance, or possible misuse.
- Context7 normal lookup operations use the approved external-provider boundary, not the local Work network path.
- Serena invocations are evaluated by their concrete resolved effects.

## Authoritative upstream baselines

- Context7: official `upstash/context7` MCP distribution; current candidate pin `@upstash/context7-mcp@3.2.0`.
- Serena: official `serena-agent` PyPI distribution; current candidate pin `1.6.1`.

The final pins and integrity values must be recorded in JSON and verified by installers before commissioning.

## New hard-block mappings requiring operator decision

Only the following proposed mappings are added to the existing register:

- **HR1-07 — Serena effective mutation destination outside `C:\Projects`.** Resolve actual provider destinations for file edits, symbol refactors, moves, memory writes, project/config writes, generated indexes, caches, logs, and shell-command write effects. Block only when the effective destination is proven outside the boundary.
- **HR2-06 — Serena shell command with a proven external target.** Map `execute_shell_command` into the existing exact command-effect resolver. Block only when the complete command proves an external-network operation.
- **HR3-07 — Serena whole-artifact deletion.** Transform an exact `delete_memory` file deletion, and any pinned Serena operation proven to delete a complete file or directory, into quarantine. Partial code edits such as deleting lines or a symbol are ordinary content writes, not whole-artifact deletion.

Context7 adds no hard-block entry because its two read-only lookup tools are intentionally hosted behind the approved external-service boundary. Installation, endpoint identity, credentials, and readiness are non-hard controls rather than additional policy prohibitions.

## Implementation boundary after approval

### Context7 adapter

- Expose the upstream `resolve-library-id` and `query-docs` contracts without unrelated CLI setup/remove commands.
- Use a fixed approved Context7 endpoint and secret reference; do not expose arbitrary endpoint or credential mutation as public tools.
- Keep installation and package state beneath `C:\Projects\.kis-mcp\context7`.
- Report bounded readiness without leaking credentials.

### Serena adapter

- Launch the pinned server over stdio.
- Keep `SERENA_HOME`, configuration, logs, caches, indexes, memories, and language-server state beneath approved `C:\Projects` locations where supported by the pinned provider.
- Preserve upstream tools unless a concrete invocation resolves to HR-001, HR-002, or HR-003.
- Reuse the existing Work effect resolver for shell-command effects rather than creating a second command policy.
- Resolve provider-native path aliases and project-relative paths to their single effective targets before policy evaluation.

## Explicit non-rules

The following are not blockers:

- Serena tool names or broad editing capability;
- reading a project outside `C:\Projects` when no write outside the boundary is produced;
- an unknown shell command or incomplete prediction;
- Context7 documentation content, library names, queries, or returned examples;
- provider overlap with Desktop Commander;
- optional or beta status alone.

## Acceptance criteria

1. The existing hard-block register contains the three proposed Serena entries with pending operator decisions and exact reasons.
2. No production adapter implementation begins until those entries are approved or amended.
3. After approval, both adapters have independent descriptors, settings, readiness probes, installers, contracts, and tests.
4. Context7 normal lookups use only the approved external-service boundary.
5. Serena mutating and shell calls reuse HR-001/002/003 effect enforcement without creating another policy rule.
6. Focused tests and full repository verification pass before a reviewable PR is raised.
