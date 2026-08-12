# Change Specification: NIM Sub-agent Models

- **Change ID**: `095-nim-subagent-models`
- **Status**: Closed
- **Risk Profile**: rigorous

## Outcome

Add a bounded NVIDIA NIM benchmark surface that can smoke-test allowlisted experimental sub-agent models through the existing approved external connector before any model is promoted into the production reviewer profile set.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, `docs/OPERATIONS.md`, `settings/agents/code-review-agent.settings.json`, existing NVIDIA/reviewer implementation contracts.
- Owned paths: NVIDIA provider/reviewer implementation and tests, benchmark settings, capability effect classification, this change record.
- Shared paths: none.
- Excluded paths: policy, `AGENTS.md`, `SPEC.md`, `README.md`, `docs/OPERATIONS.md` while parallel authority-refresh changes own them.
- Dependencies: existing encrypted NVIDIA secret reference and approved external-provider runtime.
- Integration owner: this change branch only.

## Requirements

- **REQ-001**: Experimental model IDs SHALL be isolated from production `nano`, `super`, and `ultra` aliases.
- **REQ-002**: Benchmark calls SHALL accept only configured allowlisted aliases and 1-3 runs.
- **REQ-003**: Benchmark calls SHALL use the NVIDIA approved external connector, never local Work networking.
- **REQ-004**: Each run SHALL use one fixed read-only prompt that tests concrete correctness and security review ability.
- **REQ-005**: Candidate payloads SHALL use portable OpenAI-compatible fields and bounded tokens/timeouts.
- **REQ-006**: Suitability SHALL require every requested run to succeed, identify both required review categories, and remain within the configured latency limit.
- **REQ-007**: Benchmark output SHALL omit raw credentials, exception text, and full model responses.
- **REQ-008**: Benchmark SHALL remain discoverable long-tail, classified external + read-only, and SHALL NOT expand the direct tool profile.
- **REQ-009**: Production reviewer aliases SHALL remain unchanged until separate live smoke evidence supports promotion.

## Acceptance

1. **Given** an unlisted model alias, **When** benchmark is called, **Then** it is rejected before any provider invocation.
2. **Given** an allowlisted model, **When** benchmark runs, **Then** results contain bounded latency/quality evidence and no repository mutation.
3. **Given** a slow, failed, or incomplete model run, **When** suitability is calculated, **Then** the candidate is not suitable.
4. **Given** gateway composition, **When** capabilities are searched, **Then** `benchmark_nvidia_model` is eligible with `external` and `read_only` effects but absent from the direct list.
5. **Given** the complete 095 diff, **When** focused and canonical verification run, **Then** all applicable gates pass and changed paths remain within `scope.json`.

## Risks and recovery

- Risk: upstream model-specific parameters differ. Mitigation: benchmark payload intentionally omits Nemotron-only reasoning fields.
- Risk: endpoint queue/cold-start variance. Mitigation: support up to three identical runs and record median/max end-to-end latency.
- Risk: experimental surface becomes production behavior accidentally. Mitigation: separate benchmark allowlist and unchanged production profile contract.
- Recovery: revert the 095 commit; no persisted model state, credentials, policy, or production aliases are changed.

## Out of scope

- Promoting any candidate to a production reviewer alias before live benchmark evidence.
- Changing NVIDIA credentials, vault behavior, hard policy, direct-profile settings, Codex configuration, or parallel documentation work.
