# KIS State Ownership Module Product Spec

Status: #278 foundation contract under verification. Subordinate to root `SPEC.md`, `docs/TRUST-MODEL.md`, and `docs/PLATFORM-CONCEPT.md`.

## Purpose and boundary

`kis_mcp.state` defines where future KIS state belongs in the centrally partitioned architecture selected by #272/#277. It performs pure path/key construction: no directory creation, state write, Git lookup, credential move, or consumer migration. Migration/commissioning remain #279/#280. The repository's current deployment model is explicitly `source-checkout-only`; #278 therefore loads the checked-in contract from that checkout and does not introduce wheel/package-resource distribution work.

Fixed compatibility anchors:
- project boundary `C:\Projects`; state root `C:\Projects\.kis-mcp`;
- quarantine exactly `C:\Projects\.kis-mcp\quarantine`;
- existing secrets at `C:\Projects\.kis-mcp\secrets`;
- existing GitHub CLI auth at `C:\Projects\.mcp-external-state\gh-config` remains compatibility-only;
- `<registered-project>\.temp\kis` remains reconstructible/non-authoritative.

## Ownership contract

Single data authority: `contracts/state/state-ownership.contract.json`. `kis_mcp.state.contract` loads only that checked-in authority at runtime, rejects unsupported repository contract/namespace versions without coercion, and verifies the complete version-1 contract against a canonical compatibility fingerprint before exposing it. `state_ownership_contract()` returns a copy. `state-ownership.contract.schema.json` owns structural/independent validation in tests and CI rather than becoming a second runtime data source. Internal responsibilities are split into `contract`, `identity`, and `resolver` modules behind the unchanged `kis_mcp.state` facade.

The **full-contract compatibility fingerprint** is distinct from each resolved namespace's `identity_fingerprint`. For contract version 1, serialize the complete parsed JSON document with `ensure_ascii=true`, `sort_keys=true`, compact separators `(',', ':')`, **no trailing newline**, encode as UTF-8, then SHA-256 hash the bytes. The supported v1 digest is `2a926e9bef80d12c9f75dd5b4bdbdb6c3f1a9f9ab2dfecd1c558d8f384e3d48f`, anchored by `_SUPPORTED_CONTRACT_V1_FINGERPRINT` in `kis_mcp.state.contract`. Do not replace that digest to make a semantic edit pass. Changes to public/wire structure require a supported `schema_version` transition; changes to namespace roots, ownership semantics, identity/source normalization, namespace fingerprint semantics, or compatibility locations require a supported `namespace_version` transition; changes affecting both require both transitions. A new version must add explicit runtime support and a new compatibility anchor. This slice intentionally performs no consumer migration.

| Class | Identity | Namespace |
|---|---|---|
| `global-authority` | none | `global/authority/<key>` |
| `global-cache` | none | `global/cache/<key>` |
| `shared-auth` | none | `global/auth/<key>` |
| `project-specific` | project | `projects/<project>/state/<key>` |
| `worktree-specific` | project, source | `projects/<project>/sources/<source>/state/<key>` |
| `runtime-instance-specific` | runtime | `runtime/<runtime>/state/<key>` |
| `ephemeral` | runtime, project, source | `runtime/<runtime>/projects/<project>/sources/<source>/ephemeral/<key>` |
| `reconstructible-cache` | project, source | `projects/<project>/sources/<source>/reconstructible/<key>` |
| `durable-evidence` | project, source | `projects/<project>/sources/<source>/evidence/<key>` |
| `recovery-quarantine` | none | `quarantine` |

Generic `state` segments keep project/source/runtime namespaces from owning specialized ancestors. `resolve_many()` / `validate_namespace_uniqueness()` reject exact collisions and ancestor/descendant overlap using normalized Windows paths.

## Identity and wire contracts

Logical project/runtime/state keys use lower-case kebab syntax, max 128, with strip + casefold canonicalization. Governed change IDs require repository `NNN-kebab-case`. Source identity has one canonical selection rule: a worktree rooted at `<project>\.work\worktrees\<NNN-kebab-change-id>` resolves to `change-<governed-id>`; any other valid worktree root resolves to `worktree-<sha256>` over its normalized case-insensitive absolute Windows path beneath `C:\Projects`. This keeps a governed worktree from acquiring both change and worktree namespaces without requiring Git lookup.

`expected_identities` must contain the complete identity set; mismatch fails `STATE_IDENTITY_STALE`. Request mappings are defensively copied and public serialization emits canonical values.

Public wire schemas:
- `state-namespace-request.schema.json`
- `state-namespace-result.schema.json`
- `state-namespace-error.schema.json`

Serialized results carry the contract `namespace_version` plus one canonical `relative_path`; the absolute Python `namespace.path` is a local convenience derived from the fixed contract state root and is intentionally not duplicated on the wire. `namespace_version` also participates in the canonical fingerprint document so namespace-grammar revisions cannot reuse an earlier identity fingerprint. The machine contract also publishes identity grammar/canonicalization, diagnostic limits, the closed error-code vocabulary, and the reproducible SHA-256 canonical-JSON fingerprint algorithm/test vector.

## API example

```python
source = derive_change_source_id("163-state-ownership-namespace")
namespace = StateNamespaceResolver().resolve(StateNamespaceRequest(
    ownership=StateOwnershipClass.DURABLE_EVIDENCE,
    state_key="verification",
    identities={"project_id": "kis-mcp", "source_id": source},
))
```

`namespace.path` is always beneath the approved KIS state root. Errors use `StateNamespaceErrorCode` with non-empty messages and diagnostics bounded to 8 fields / 64-char keys / 160-char values.

## Compatibility and handoff

#278 does not reinterpret or relocate existing state. Provider/tool installations and safe caches remain global; secrets/auth/quarantine paths remain unchanged; existing Discover, review/verification, merge-queue, provider/runtime, workflow, and repo-local recovery state stays on current paths until explicit migration.

#241/#251 must consume this ownership/namespace contract rather than create another persistence-root model; #251 still owns its lease/fence/checkpoint semantics. #279 classifies/migrates consumers with rollback; #280 commissions isolation, stale-state rejection, restart/recovery, auth reuse, and resource acceptance.

## Invariants

1. Global and scoped state cannot share ownership accidentally.
2. Source-sensitive state requires project + source identity.
3. Current-process/liveness state requires runtime identity.
4. Resolved namespaces remain under `C:\Projects\.kis-mcp`.
5. Quarantine retains existing HR-003 authority.
6. Repo-local recovery stays reconstructible only.
7. Existing consumer paths remain legacy until explicit migration.
