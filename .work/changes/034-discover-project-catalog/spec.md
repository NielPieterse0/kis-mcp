# Change Specification: Discover Project Catalog

- **Change ID**: `034-discover-project-catalog`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Add bounded, deterministic cross-repository identity and relationship evidence for an explicit caller-selected set of local projects without enumerating `C:\Projects`, following unselected paths, importing project code, executing processes, or using the network.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and Phase D8 of `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`.
- Owned implementation: `src/kis_mcp/discover/project_catalog/**`.
- Owned tests: `tests/discover/project_catalog/**`.
- Owned schemas: `contracts/discover/project-catalog-request.schema.json` and `contracts/discover/project-catalog-response.schema.json`.
- Owned documentation: `docs/development/discover-project-catalog/**`.
- Public registration and shared-server composition remain reserved for the final Discover integration change.

## Requirements

- **REQ-001**: Accept only an explicit non-empty ordered set of local project paths beneath the configured Discover boundary. Duplicate canonical projects fail structurally.
- **REQ-002**: Resolve each selected project independently through existing `ReadAuthority`; never enumerate the boundary or infer sibling projects.
- **REQ-003**: Read only a fixed bounded manifest set from each selected project: `package.json`, `pyproject.toml`, and root-level `*.csproj` files already present in that selected project snapshot.
- **REQ-004**: Normalize project identities, manifest evidence, local path references, relationship provenance, confidence, unknowns, omissions, truncation, and a deterministic fingerprint.
- **REQ-005**: Detect only static local relationships that resolve exactly to another selected project:
  - npm dependency values using `file:` or `link:`;
  - Python path dependencies declared in supported `pyproject.toml` tables;
  - .NET `<ProjectReference Include="...">` values;
  - explicit nested-selection containment.
- **REQ-006**: Do not follow, scan, or resolve an unselected target as a project. Record it as an explicit unknown with source manifest and normalized candidate path.
- **REQ-007**: Reject references escaping the configured boundary or traversing unsafe path chains. Preserve source evidence without returning secret-bearing content.
- **REQ-008**: Apply explicit request budgets to projects, manifests, relationships, and unknowns with exact deterministic omission counts.
- **REQ-009**: Use no subprocess, Git command, provider runtime, network client, credentials, package manager, language server, or target-code import.

## Acceptance

1. Given explicit selected repositories with supported local path references, cataloging returns stable project identities and relationships only among those selections.
2. Given sibling repositories not selected by the caller, cataloging never enumerates or inspects them.
3. Given npm `file:` or `link:`, Python path dependency, .NET `ProjectReference`, or nested selected roots, the relationship includes source, target, type, source manifest, provenance, and confidence.
4. Given an unselected or unresolved local target, the target is not scanned and an explicit unknown is returned.
5. Given duplicate canonical selections, outside-boundary paths, unsafe links, malformed manifests, invalid request budgets, or unsupported request shapes, the operation fails or degrades safely with structural diagnostics.
6. Given identical selected paths, repository bytes, settings, and budgets, ordering, omissions, and fingerprint are identical.
7. Request and response serialize successfully against their Draft 2020-12 schemas.

## Risks and recovery

- Risk: manifest path syntax can be ecosystem-specific or ambiguous.
- Mitigation: support only narrow static forms; unresolved forms remain unknown rather than guessed.
- Risk: relationship discovery could become implicit whole-boundary scanning.
- Mitigation: selection membership is checked before any target project resolution; only selected project roots are scanned.
- Recovery: revert the implementation commit. No persistent state, network call, configuration mutation, or external effect is introduced.

## Out of scope

- Background indexing, Sourcegraph, SCIP, language servers, embeddings, or semantic providers.
- Git submodule execution, remote identity lookup, forge evidence, package-registry resolution, or workspace command execution.
- Cross-repository change impact beyond relationship evidence.
- Public FastMCP registration and shared server changes.
