# 005 Discover Foundation Closeout

## Status

Implementation, integration, review, verification, push, and draft pull-request creation are complete. The branch and worktree remain active for review. The pull request is intentionally unmerged.

## Delivery

| Field | Value |
|---|---|
| Branch | `change/005-discover-foundation` |
| Worktree | `C:\Projects\kis-mcp\.work\worktrees\005-discover-foundation` |
| Foundation commit | `ee1336c` |
| Latest-main integration commit | `0b6280e` |
| Base | `main` at `f9e0c16` |
| Pull request | `#13 — Add bounded inspect_project discovery foundation` |
| Pull-request URL | `https://github.com/NielPieterse0/kis-mcp/pull/13` |
| Pull-request state | Open, draft, unmerged |

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
- Independent landing review found and fixed evidence compaction that could discard evidence still referenced by manifests, verification declarations, instructions, or other nested response structures.
- Independent landing review changed minimum-output compaction to preserve required Work handoffs or fail with `DISCOVER_OUTPUT_BUDGET_TOO_SMALL` rather than silently erase them.
- Independent landing review fixed scp-style Git remote sanitization so query strings and fragments cannot leak through local Git evidence.
- Independent landing review added `.kis-mcp` to the checked-in Discover exclusions so inspection of `C:\Projects` cannot traverse central generated provider, cache, tunnel, or runtime state.
- Final full locked verification passed with the four regression tests and two expected platform skips.
- A fresh `operation` HTTP smoke passed all 30-tool, Discover, health, representative Work, and quarantine checks. The attempted all-instance rerun stopped before `development` because port `127.0.0.1:8011` was already occupied by an external process; no process was terminated during review.
- A final adversarial resilience probe found that recursive Python import-cycle detection could exceed the interpreter call stack on a valid deep module graph and escape the stable Discover result contract with `RecursionError`.
- Replaced recursive strongly connected component traversal with deterministic iterative traversal and added a 1,500-module regression proving bounded completion beyond the Python call stack.
- Final integration diff review after the repair found no remaining blocking code issue.

## Known repository limitation

Repository-wide `change-workflow.ps1 validate` still recursively counts merged historical claims copied into every active worktree as duplicate active changes. The failure references changes 004, 006, 008, 009, and 010 rather than Discover scope. Current-checkout governance inside `scripts/verify.ps1` passed, and the bounded change check passed. This unrelated governance defect was not modified in the Discover slice.

## Deferred items

- Semantic-provider and remote-evidence integration remain later Discover roadmap stages.
- Non-Python structural indexing remains deferred.
- External Secure MCP Tunnel and ChatGPT app commissioning remain dependent on operator-supplied tunnel configuration.
- The branch and worktree remain active until pull-request review and merge.
