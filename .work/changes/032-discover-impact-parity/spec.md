# Change Specification: Discover Impact Parity

- **Change ID**: `032-discover-impact-parity`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Harvest the remaining deterministic change-impact intelligence from `dev-intel-tool` revision `a6af216bf09c59c659b16697673c2149d6fdbea1` without importing its runtime, policy, settings authority, network behavior, or product identity.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, and the current operator direction.
- Donor evidence: `dev-intel-tool` branch `origin/feat/change-impact-intelligence` at `a6af216bf09c59c659b16697673c2149d6fdbea1`.
- Owned implementation: `src/kis_mcp/discover/analyzers/**`, `src/kis_mcp/discover/impact_graph.py`, `src/kis_mcp/discover/impact_contracts.py`.
- Owned tests: `tests/discover/impact_parity/**` plus the currently claimed impact tests.
- Owned traceability: `docs/development/discover-foundation/source-harvest.md`.
- Integration owner: a later Discover final-integration change.

## Requirements

- **REQ-001**: Add a deterministic ordered analyzer registry and pipeline whose inputs are existing bounded Discover snapshots, Python index data, safe read authority, changed paths, and verification declarations.
- **REQ-002**: Add architecture-component detection with deterministic grouping, configured bounds inherited from Discover settings, and explicit truncation.
- **REQ-003**: Add local Python and JavaScript/TypeScript dependency resolution without importing repository code, spawning processes, or using network access. Dynamic or unresolved imports remain explicit unknowns.
- **REQ-004**: Extend impact analysis to use analyzer outputs for direct and bounded transitive dependency impact, affected tests, configuration, contract, documentation, and verification evidence while preserving the current response contract.
- **REQ-005**: Preserve existing Python symbol, call, inheritance, and verification behavior and deterministic fingerprints.
- **REQ-006**: Correct unsupported `ee18566` donor references to the recoverable authoritative revisions `26d1a2f` and `ae73081`, and record `a6af216` as the remaining change-impact donor.
- **REQ-007**: Keep standalone donor runtime, GitHub execution, network access, installer scripts, duplicate policy/settings authority, and incompatible product wording excluded.

## Acceptance

1. **Given** a Python repository, **when** impact analysis runs, **then** local imports, symbols, calls, inheritance, dependants, tests, and verification handoffs remain deterministic and bounded.
2. **Given** JavaScript or TypeScript static relative imports, **when** impact analysis runs, **then** local dependency edges and reverse dependants are returned without executing code.
3. **Given** dynamic, external, malformed, or unresolved imports, **when** analysis runs, **then** the result records bounded diagnostics or unknowns instead of inventing dependencies.
4. **Given** component, contract, configuration, documentation, or test changes, **when** impact analysis runs, **then** the affected evidence and applicable verification handoffs are retained.
5. **Given** identical repository state and budgets, **when** analysis repeats, **then** substantive ordering and fingerprints are identical.
6. **Given** the donor harvest register, **when** traceability is reviewed, **then** every donor revision is recoverable and the unharvested/excluded boundary is explicit.

## Risks and recovery

- Risk: broad dependency heuristics may overstate impact.
- Mitigation: only static relative/local imports are treated as deterministic; transitive and conventional evidence is labelled in provenance and bounded.
- Risk: parser failures or large repositories may produce partial graphs.
- Mitigation: preserve diagnostics, unknowns, omissions, configured budgets, and truncation reasons.
- Recovery: revert the change commit; no persistent data, configuration, external provider, or schema migration is introduced.

## Out of scope

- Public FastMCP registration and shared server composition.
- Remote GitHub or GitLab evidence.
- Provider admission, installation, activation, or conformance execution.
- Cross-repository scanning or relationships.
- Semantic-provider or language-server integration.
