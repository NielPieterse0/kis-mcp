# Discover Provider Admission

## Purpose

This slice converts one explicitly selected, checked-in JSON provider-candidate manifest into evidence for later Govern and Work decisions. It does not install, activate, authenticate, execute, contact, or approve a provider.

## Trust boundary

- The caller selects both the project and repository-relative manifest path.
- The manifest is read only through Discover `ReadAuthority` and existing file-size/link/path controls.
- No directory search, provider registry lookup, package resolution, network access, credential access, process execution, or target-code import occurs.
- Manifest contents are candidate-declared evidence, not trusted facts.
- Discover returns `pending_govern`; Govern remains the decision authority.
- The Work handoff contains declarative validation steps with `execution_available=false` and no executable fields.

## Version-1 manifest

The JSON object requires exactly these top-level fields:

```json
{
  "schema_version": 1,
  "candidate_id": "provider:example",
  "name": "Example Provider",
  "provider_type": "mcp_server",
  "revision": "pinned-revision",
  "license": "MIT",
  "maintainer": "Example Team",
  "capabilities": ["read", "search"],
  "effects": {
    "reads_project": true,
    "writes_project": false,
    "executes_commands": false,
    "network_access": false,
    "credentials": false
  },
  "authentication": "none",
  "installation": "bundled",
  "compatibility": {
    "mcp_protocol": ["2025-06-18"],
    "platforms": ["windows"]
  },
  "readiness": {
    "schema_present": true,
    "health_contract_present": true,
    "deterministic": true,
    "conformance_tests": ["contract/provider.json"]
  },
  "evidence": [
    {
      "kind": "manifest",
      "path": "provider-candidate.json",
      "summary": "Checked-in provider declaration."
    }
  ],
  "overlaps": []
}
```

Unknown keys, unsupported versions, invalid types, unsafe paths, and malformed JSON fail structurally. Collections are normalized, deduplicated, sorted, and bounded by the request budget.

## Outputs

- normalized candidate evidence with content digest and provenance;
- unresolved security, licensing, readiness, overlap, and operational risks;
- a Govern admission request fixed to `pending_govern`;
- a non-executing Work conformance plan;
- explicit unknowns, omissions, confidence, truncation reasons, and deterministic response fingerprint.

Schemas:

- `contracts/discover/provider-candidate.schema.json`
- `contracts/discover/provider-admission-request.schema.json`

## Integration seam

`ProviderAdmissionService.inspect()` is intentionally internal in this slice. The final Discover integration change may compose it behind an explicit operator-selected manifest input. It must not introduce implicit manifest discovery or a second policy authority.
