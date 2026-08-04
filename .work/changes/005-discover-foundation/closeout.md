# 005 Discover Foundation Closeout

## Status

Implementation, integration, review, and local verification are complete. The branch is ready to push and open as a draft pull request. It must remain unmerged until reviewed.

## Delivery

| Field | Value |
|---|---|
| Branch | `change/005-discover-foundation` |
| Worktree | `C:\Projects\kis-mcp\.work\worktrees\005-discover-foundation` |
| Foundation commit | `ee1336c` |
| Current-main integration commit | `9a8237c` |
| Base | `main` |
| Pull request | Pending draft creation |

## Implemented outcome

- Added one versioned read-only `inspect_project` MCP operation.
- Added immutable request, response, evidence, repository, Git, verification, Python-structure, confidence, truncation, recommendation, assumption, unknown, and handoff contracts with JSON schemas.
- Added canonical project identity, provider-neutral read authority, deterministic bounded scanning, repository/framework/manifest/instruction/CI/contract detection, non-executing verification discovery, pure Python AST indexing, and bounded local Git evidence.
- Added deterministic result budgeting and reference-preserving compaction.
- Added a thin FastMCP binder and one additive composition-root registration.
- Added donor traceability while retaining no runtime dependency on `sdk-tool`, `dev-intel-tool`, or `mcp-tool`.
- Added architecture tests preventing Work, provider, donor, network, uncontrolled traversal, and misplaced subprocess dependencies.
- Extended local HTTP smoke verification to require and execute `inspect_project`.

## Restriction and policy review

- No new HR rule was added; `policy/kis-mcp.policy.json` remains limited to HR-001, HR-002, and HR-003.
- No command, executable, tool-name, argument, provider-capability, or ordinary Desktop Commander restriction was added.
- Discover retrieval limits, exclusions, allowed text types, encodings, hard-link behavior, timeouts, and budgets are owned by `settings/kis-mcp.settings.json`.
- Interface constants are limited to approved versioned contracts and stable public field names.
- Discover performs no network requests and does not execute repository code, tests, builds, or discovered verification commands.
- Discover structural failures use `DISCOVER_*` codes and are not reported as Work-policy decisions.

## Validation evidence

- `pwsh -File scripts/verify.ps1` passed after current `main` integration and again after smoke-contract changes.
- The locked environment passed configuration, interpreter, dependency, syntax, current-checkout governance, pytest, and service verification gates with two expected skips.
- `pwsh -File scripts/smoke-chatgpt.ps1 -AllInstances -TimeoutSeconds 90` passed for `operation` and `development`.
- Each local HTTP instance exposed 30 tools and passed `inspect_project`, `kis_health`, representative read/write/edit/process operations, and recoverable quarantine; the network-only feedback tool remained absent.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` passed and reported only declared paths.
- Git whitespace validation passed.

## Review findings and resolutions

- Fixed pytest module-name collision by packaging `tests/discover`.
- Fixed raw invalid-limit `ValueError` leakage by returning stable corrective `DISCOVER_LIMIT_INVALID` errors.
- Added missing public registration and error-normalization tests.
- Added donor-independent import and architecture-boundary tests.
- Removed accidental `server.py` line-ending churn before commit.
- Found and closed the post-Discover HTTP smoke gap by requiring a real bounded `inspect_project` call on both instances.
- Final uncommitted integration diff review found no remaining blocking issue.

## Known repository limitation

Repository-wide `change-workflow.ps1 validate` still recursively counts merged historical claims copied into every active worktree as duplicate active changes. The failure references changes 004, 006, 008, 009, and 010 rather than Discover scope. Current-checkout governance inside `scripts/verify.ps1` passed, and the bounded change check passed. This unrelated governance defect was not modified in the Discover slice.

## Deferred items

- Semantic-provider and remote-evidence integration remain later Discover roadmap stages.
- Non-Python structural indexing remains deferred.
- External Secure MCP Tunnel and ChatGPT app commissioning remain dependent on operator-supplied tunnel configuration.
- The branch and worktree remain active until pull-request review and merge.
