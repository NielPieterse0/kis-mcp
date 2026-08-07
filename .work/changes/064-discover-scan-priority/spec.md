# Change Specification: Discover Scan Evidence Priority

- **Change ID**: `064-discover-scan-priority`
- **Status**: Approved for implementation by the operator's Discover remediation directive
- **Development level**: Medium — behavior change in a reused repository-evidence primitive with bounded, reversible scope

## Outcome

Make narrow Discover scans preserve the smallest useful repository evidence instead of letting alphabetical auxiliary trees consume `max_files` / `max_total_bytes` before application source. Preserve deterministic traversal safety, exclusions, structural limits, and final output ordering.

## Evidence

- Live bounded `inspect_project` on `kis-mcp` consumed its early budget in `.agents` / `.archive` material and produced poor application context before reaching `src`.
- `RepositoryScanner` currently applies `max_files` and `max_total_bytes` during alphabetical depth-first traversal.
- Scanner is reused by project inspection, context brokering, contracts, impact, and project catalogue services; selection therefore belongs behind one stable scanner contract rather than being reimplemented by callers.
- Current Discover product authority requires manifest-first, relevance-aware, smallest-sufficient evidence and deterministic bounded behavior.

## Requirements

- **REQ-001**: Filesystem traversal MUST retain canonical project authority, exclusions, link/reparse rejection, hard-link policy, file-size checks, max depth, max directories, max visited entries, and timeout behavior.
- **REQ-002**: `max_files` and `max_total_bytes` MUST remain enforced during traversal, but safe directory entries MUST be visited in deterministic evidence-priority order rather than raw alphabetical order.
- **REQ-003**: Root project manifests/instructions and conventional application source roots MUST outrank hidden/auxiliary/archive trees under constrained budgets.
- **REQ-004**: Tests/contracts/configuration/documentation MUST remain eligible and ordered ahead of generic auxiliary material, but application source must not be starved by them.
- **REQ-005**: Returned `RepositorySnapshot.files`, directories, and exclusions MUST remain deterministically label-sorted for consumer compatibility.
- **REQ-006**: Exact-capacity scans MUST not claim truncation; omitted eligible candidates due file or byte budget MUST report the existing `max_files` and/or `max_total_bytes` reasons.
- **REQ-007**: Selection logic MUST be a focused pure module, not additional scanner monolith branching.

## Acceptance

1. A fixture with many `.agents` / `.archive` files, `pyproject.toml`, and `src/app.py`, constrained to two files, returns `pyproject.toml` and `src/app.py`.
2. Existing deterministic scanner, depth, directory, visited-entry, exclusion, per-file byte, and hardening tests remain green.
3. Existing same-priority alphabetical cases retain stable results.
4. New priority-policy unit tests prove deterministic ranking independently of filesystem traversal; existing scanner tests continue to prove budget accounting.
5. Full Discover and architecture-boundary tests pass on the final implementation head.
6. Exact-head repository workflow with full verification passes before merge.

## Modularity decision

FACT: traversal safety and evidence-budget selection have different change reasons and can be tested independently.
REC: introduce `scan_selection.py` as a pure selection seam consumed by `scanner.py`.
RISK: over-general ranking rules could hide relevant unconventional projects; keep tiers small, deterministic, conventional, and fall back to lexical ordering rather than excluding unknown paths.

## Out of scope

- changing global limits or exclusions;
- task-specific semantic ranking in Context Broker;
- capability search/description/workflow fixes;
- impact-analysis precision;
- `.work` governance evidence integration.
