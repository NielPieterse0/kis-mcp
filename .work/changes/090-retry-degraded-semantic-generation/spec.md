# Change Specification: Retry Degraded Semantic Generation

- **Change ID**: `090-retry-degraded-semantic-generation`
- **Status**: Approved by current commissioning request
- **Risk Profile**: standard

## Outcome

Prevent transient Serena failures from becoming sticky persisted Discover state. When a semantic provider is configured, a generation whose stored semantic evidence is degraded must be refreshed on the next read rather than reused indefinitely.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/OPERATIONS.md`.
- Owned implementation: `src/kis_mcp/discover/intelligence.py`.
- Owned regression: `tests/discover/test_project_intelligence.py`.
- Excluded: provider lifecycle, Serena configuration, persistence schema, policy rules.
- Base/integration target: `main`.

## Requirements

- **REQ-001**: A persisted generation with `semantic.status == "degraded"` MUST NOT be reused when a non-null semantic provider is configured.
- **REQ-002**: The next read MUST retry semantic enrichment using the same source/settings/provider fingerprint.
- **REQ-003**: If the retry succeeds, the refreshed generation MUST persist ready semantic evidence and supersede the degraded generation recoverably.
- **REQ-004**: Normal ready generations and null-semantic deterministic generations MUST retain existing reuse behavior.
