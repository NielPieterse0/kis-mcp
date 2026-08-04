# P2 Operational Hardening Specification

## Development level

Medium. The slice contains three independently testable fixes across Discover, quarantine, and deployment configuration. It does not alter HR-001, HR-002, HR-003, provider authorization, tunnel behavior, or active Work parsing.

## Context

The full-main code review identified eight P2 findings. Active changes already own five: tunnel setup lifecycle (`013`), exact network-command resolution (`015` integration boundary), and Discover schema/traversal/Python-diagnostic hardening (`016`). This slice owns the remaining non-overlapping findings and records those dependencies for integrated closure.

## Requirements

### R1 — Preserve verification declaration/handoff integrity

When output compaction retains a verification handoff, retain the declaration identified by that handoff. A declaration and its handoff are one semantic retention unit. Reference validation must reject an orphaned verification handoff.

### R2 — Bound quarantine integrity work

Payload hashing must use iterative traversal and explicit limits for entries, bytes, depth, and elapsed time. Limit exhaustion must raise a stable quarantine-integrity error before unbounded work or recursion failure. Symlinks and reparse points remain hashed as links and are not followed.

`list_records(limit=N)` must bound inspected operation entries instead of validating the complete store before returning N records. Corruption inside the bounded inspected window remains an error; entries beyond that window are not inspected by that call.

### R3 — Make the deployment model explicit

`kis-mcp` is a supervised source-checkout application, not a redistributable standalone wheel. Runtime configuration is authoritative only from a repository root containing `settings/kis-mcp.settings.json` and `policy/kis-mcp.policy.json`.

The project metadata and operations documentation must state this model. Default configuration loading outside a valid checkout must fail with a stable, corrective `KIS_MCP_SOURCE_CHECKOUT_REQUIRED` message rather than an incidental missing-file path.

## Constraints

- Exactly three hard rules; no new block, allowlist, or permission model.
- No new runtime dependency.
- No edits to active `013`, `015`, or `016` owned paths except declared shared files.
- No provider module edits; provider packaging remains outside this source-checkout model.
- All behavior changes require failing tests first.

## Acceptance criteria

1. A compaction regression test proves every retained `run_verification` handoff resolves to a retained declaration.
2. Quarantine tests prove bounded entry, byte, depth, and time failures and prove no recursive stack failure.
3. A listing test proves `limit=1` does not validate later operation directories.
4. Distribution tests prove wheel publication is not declared and default runtime loading outside a repository checkout raises the stable source-checkout error.
5. Focused tests, scope check, diff check, syntax validation, and full repository verification pass on the final branch, subject only to the pre-existing governance duplicate-claim defect.
