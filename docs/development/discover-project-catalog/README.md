# Discover Project Catalog

## Purpose

The project catalog returns bounded identity and relationship evidence for one explicit caller-selected set of local projects. It is an internal D8 foundation and does not enumerate the configured project boundary.

## Trust boundary

- Every project path is supplied explicitly by the caller and resolved independently through Discover `ReadAuthority`.
- Duplicate canonical projects fail structurally.
- Only budget-retained selected roots are scanned.
- Sibling or referenced projects that were not explicitly selected are never resolved or scanned.
- No process, Git command, package manager, language server, provider runtime, credential, or network client is used.
- Repository content remains untrusted evidence and cannot expand the selected set.

## Supported manifest evidence

The service inventories only:

- root `package.json`;
- root `pyproject.toml`;
- root-level `*.csproj`.

Supported static relationships are deliberately narrow:

| Ecosystem | Accepted form | Relationship |
|---|---|---|
| npm | dependency values beginning with `file:` or `link:` | `npm_local_dependency` |
| Python | Poetry dependency tables and uv source entries containing a string `path` | `python_path_dependency` |
| .NET | `<ProjectReference Include="...">` | `dotnet_project_reference` |
| Explicit selection | one selected project root is contained by another | `contains_selected_project` |

A relationship is returned only when the normalized candidate path matches a retained explicitly selected project. Multiple declarations with different subjects remain separate evidence.

## Unknowns

The catalog reports, without following the path:

- `UNSELECTED_PROJECT_REFERENCE` when a local reference is not in the explicit retained selection;
- `TARGET_PROJECT_OMITTED` when a selected target was removed by the project budget;
- `REFERENCE_OUTSIDE_BOUNDARY` when a reference escapes or cannot be normalized beneath the configured boundary;
- `MANIFEST_READ_FAILED` when safe bounded reading fails;
- `MANIFEST_PARSE_FAILED` when a selected manifest is malformed or unsupported structurally.

## Budgets and determinism

The request separately bounds projects, manifests, relationships, and unknowns. The response includes exact omission counts and stable truncation reasons. For identical explicit selections, bytes, settings, and budgets, ordering and the substantive fingerprint are deterministic.

Schemas:

- `contracts/discover/project-catalog-request.schema.json`
- `contracts/discover/project-catalog-response.schema.json`

## Integration seam

`ProjectCatalogService.inspect()` remains internal in this slice. The final Discover integration may compose it behind an explicit selected-project list. It must not add boundary enumeration, automatic sibling discovery, background indexing, or target following.
