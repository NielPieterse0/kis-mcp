# Change Specification: Context7 and Serena Adapters

- **Change ID:** `040-context7-serena-adapters`
- **Status:** Approved for complete staged implementation; HR1-07, HR2-06, and HR3-07 remain subject to their recorded verification conditions
- **Risk profile:** Elevated because Serena exposes mutation, shell, and whole-artifact deletion effects
- **Dependency:** Merged `029-tools-code-tooling` foundation; HR2-06 activation additionally depends on corrected shared command-resolver behavior

## Outcome

Integrate two independent adapters behind the existing provider-neutral Tools foundation:

1. Context7 as an approved external documentation-evidence service.
2. Serena as a local MCP semantic-code provider with provider-managed storage configured and verified beneath `C:\Projects`.

The adapters remain independent. Failure, absence, disablement, or conditional capability inactivity in one must not prevent the other or the wider kis-mcp runtime from starting.

## Existing authority

- Preserve exactly HR-001, HR-002, and HR-003.
- Use `docs/HARD-BLOCK-APPROVAL-REGISTER.md` as the only operator approval register for hard blocks or quarantine transforms.
- Do not create a separate approval list or Serena-specific policy engine.
- Do not suppress tools by name, category, overlap, destructive appearance, optional status, or possible misuse.
- Context7 normal lookup operations use the approved external-provider boundary, not the local Work network path.
- Serena invocations are evaluated only through concrete resolved effects.
- Unknown or unsupported effect resolution is not proof of a hard-rule violation.

## Authoritative upstream baselines

- Context7: official `upstash/context7` MCP distribution; candidate pin `@upstash/context7-mcp@3.2.0`.
- Serena: official `serena-agent` distribution; candidate pin `1.6.1`.

Final pins, integrity values, and captured upstream tool contracts must be recorded in JSON and verified before commissioning.

## Operator decisions and activation state

### HR1-07 — Revise

The mapping is narrowed to invocation-controlled destinations only:

- explicit file paths;
- project-relative file and symbol edits;
- exact memory-file paths;
- move source and destination entries;
- explicit output destinations.

Provider-managed cache, index, log, temporary, configuration, language-server, and runtime-state roots are installation and readiness invariants. They do not independently create per-invocation HR-001 blocks unless the concrete invocation explicitly selects or changes such a destination.

HR1-07 is operator-approved as of 2026-08-06 and activates only after its exact per-operation contract tests pass. Missing resolver coverage must not become a blanket Serena rejection.

### HR2-06 — Approved conditionally

Serena `execute_shell_command` may delegate to the shared command-effect resolver only after:

1. the shared resolver includes approved corrections for network-bearing options, connection routing, proxy targets, DNS overrides, jump hosts, case-sensitive short options, shell quoting/redirection, and exact operand contracts;
2. the adapter preserves command text or argument vectors, working directory, shell type, quoting, argument boundaries, and explicitly represented environment target data;
3. tests prove that dry-run status alone is not treated as evidence of no network use.

This slice implements only the approved resolver corrections required by HR2-06. Serena shell activation remains contingent on the focused shared-resolver and Serena delegation tests passing.

### HR3-07 — Approved conditionally

Serena `delete_memory` may be transformed into quarantine only after pinned-contract evidence establishes the complete deleted or modified artifact set, including related metadata, catalogue, index, or consistency state.

The implementation must:

- resolve exact non-ambiguous paths;
- reject wildcard, traversal, ambiguous alias, outside-global-memory, and unknown-artifact-set cases;
- quarantine the complete proven artifact set;
- never call the provider delete operation after successful quarantine;
- test restoration and subsequent Serena behavior for stale or regenerated metadata.

### Context7 — No hard-block entry

Context7's two read-only documentation operations use the approved external-provider boundary. Identity, endpoint, credential references, response budgets, installation, and readiness remain provider controls rather than HR-001/002/003 blocks.

## Implementation boundary

### Context7 adapter

- Expose only upstream `resolve-library-id` and `query-docs` operations.
- Use a fixed approved provider identity and endpoint configuration.
- Do not expose arbitrary endpoint, credential, setup, removal, or provider-passthrough operations.
- Keep installation and package state beneath `C:\Projects\.kis-mcp\context7`.
- Bound outputs and redact credential information from readiness and errors.

### Serena bootstrap and provider storage

- Launch the pinned server over stdio.
- Configure Serena home, project data, cache, index, log, temporary, language-server, configuration, and memory roots beneath `C:\Projects` where supported by the pinned provider.
- Verify those roots through installer and readiness checks rather than per-invocation policy.
- Preserve upstream operations except where an activated, operator-approved HR mapping applies.
- Keep unavailable or conditionally inactive operations explicit without disabling unrelated Serena capability.

### Serena invocation effects

- Resolve exact per-operation argument contracts and documented precedence.
- Do not generically classify every path-like argument as a mutation destination.
- Reuse the corrected shared command resolver for shell effects without modifying it in this slice.
- Transform `delete_memory` only when the complete artifact set is proven.

## Explicit non-rules

The following are not blockers:

- Serena tool names or broad editing capability;
- provider-managed state roots that are correctly configured beneath `C:\Projects`;
- reading outside `C:\Projects` without a proven external write;
- unknown or unsupported effect resolution;
- a dry-run label without analysis of actual network consumption;
- Context7 documentation content, library names, queries, or returned examples;
- provider overlap with Desktop Commander;
- optional or beta status alone.

## Acceptance criteria

1. The existing hard-block register records HR1-07 as revised and HR2-06/HR3-07 as conditionally approved.
2. HR1-07 is not activated without explicit approval of its narrowed wording.
3. Context7 and Serena bootstrap can be implemented independently of unresolved Serena activation gates.
4. Serena provider-managed storage is controlled through settings, installation, and readiness checks rather than broad per-invocation blocking.
5. HR2-06 activates only against the corrected shared resolver with preserved command semantics.
6. HR3-07 activates only after complete pinned-contract artifact evidence and consistency tests.
7. Condition failure disables only the affected Serena operation or mapping, not the whole provider.
8. Focused tests, change-governance checks, and full repository verification pass before merge.
