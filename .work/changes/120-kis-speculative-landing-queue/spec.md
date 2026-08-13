# Change Specification: KIS Speculative Landing Queue

- **Change ID**: `120-kis-speculative-landing-queue`
- **Status**: Approved for implementation
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `deployment`, `external_action`, `persistent_state`, `public_contract`
- **Work record**: `SPEC-120` / GitHub issue #167

## Outcome

Implement and commission a bounded registered-GitHub landing queue that freezes exact PR head SHAs, builds cumulative merge candidates from the exact GitHub `main`, runs canonical Actions verification on exact candidate commits, invalidates stale generations, and advances `main` only with a fast-forward compare-and-swap.

## Authority and scope

Authoritative inputs are `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, issue #167, and the operator-provided merge-queue design.

Queue configuration is repository-owned JSON. Generated queue state is non-authoritative and remains below `C:\Projects\.kis-mcp`. GitHub/Git remain authoritative for repository identity, PR state, commits, checks, and the base ref. All remote mutation remains bounded to centrally registered repositories and reuses the existing exact registered-GitHub publication boundary.

## Requirements

1. FIFO entries freeze PR number, exact head SHA, base branch, enqueue time, and generation.
2. Each candidate is cumulative: `C0=base`, `Ci=merge(Ci-1, Hi)` as a real two-parent merge commit.
3. Candidate refs use `kis-readonly-queue/<base>/g<generation>/pr-<number>`.
4. CI evidence binds to exact generation, base SHA, ordered member heads, and candidate SHA.
5. Predecessor failure/conflict/head movement/dequeue or base movement invalidates affected successors and increments generation.
6. V1 policy is FIFO + `merge` + `allgreen`, build concurrency 3, merge groups 1-3, zero merge wait, no jump, squash, rebase, or HEADGREEN.
7. Landing revalidates live base, open/non-draft PR state, exact heads, target branch, candidate membership, exact candidate Actions success, and ancestry.
8. Landing uses fast-forward exact-base compare-and-swap through the existing registered publication primitive. Failed CAS never retries a stale candidate.
9. Queue state persists atomically under generated state and never becomes repository authority.
10. Existing Work Management readiness, exact-head review, canonical verification, policy, and registered-target validation remain required.

## Acceptance

- Deterministic tests cover frozen identity, cumulative graph construction, bounded speculative concurrency, conflict/failure/base invalidation, exact CI binding, ALLGREEN prefix selection, and exact-base landing.
- Canonical verification runs for `kis-readonly-queue/main/**` pushes and continues to execute the single repository verifier.
- Capability/workflow descriptors expose bounded queue status/enqueue/reconcile/dequeue/land operations.
- Work-managed queue completion requires the existing merge-readiness gate before enqueue and documentation reconciliation after landing.
- `SPEC.md` and `docs/OPERATIONS.md` describe only implemented behavior.
- Exact PR-head GitHub Actions verification passes before merge.
- Post-merge commissioning exercises the live registered queue path, including candidate publication, exact candidate Actions verification, base advancement, tracking refresh, and observed indirect PR merge.

## Risks and recovery

- Stale evidence: controlled by generation + exact candidate SHA/member identity.
- Direct base advancement: controlled by registered-target validation, ALLGREEN evidence, ancestry, and exact expected-base lease.
- Queue-state drift: live GitHub/Git reconciliation precedes mutation; state can be rebuilt.
- Candidate conflict/failure: offending entry is removed and successors are rebuilt in a new generation.
- CAS failure: `main` remains unchanged; the generation is stale and must be rebuilt.

## Out of scope

Jump priority, HEADGREEN, squash/rebase queue methods, deployment trains/solo semantics, ETA calculation, AI conflict resolution, generic Git/GitHub orchestration, and non-registered repositories.