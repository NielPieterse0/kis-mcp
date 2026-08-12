# Governance Authority Drift Core Plan

**Development level:** Medium — new platform plane core with no mutation or policy authority.

**Architecture:** `evidence.py` reuses Discover read authority, `service.py` owns pure advisory evaluation, `contracts.py` owns result records, `settings.py` owns strict JSON configuration, and `tools.py` defines the future read-only public surface. Gateway composition is intentionally deferred until active change 099 releases the shared registration contract.

## Tasks

1. Add strict governance settings and schema.
2. Add bounded evidence collector using Discover `ReadAuthority`.
3. Add deterministic authority/ownership/drift evaluator and stable finding IDs.
4. Add the approved four read-only tool contracts without mounting them yet.
5. Verify service, evidence, settings, and FastMCP annotations in isolation.
6. Smoke the core against the actual KIS authority chain.
7. Run full repository verification and review the closed exact head.

## Constraints

- Govern never authorizes or blocks Work.
- No broad repository traversal independent of Discover.
- No semantic conflict claims without deterministic evidence.
- No overlap with active verification-selection change 099.
