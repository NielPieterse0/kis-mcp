# Change: Project Inventory Repository Filter

- **Change ID**: `200-project-inventory-repository-filter`
- **Risk Profile**: lean

## Outcome

Complete Change 199 live commissioning by applying the configured repository filter at the GitHub Project provider boundary so unattended housekeeping can traverse the shared Project without unrelated-page truncation.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Repository-bound GitHub Project inventory reads must send `query=repo:<owner/name>` to `list_project_items` on every page.
- Existing local repository filtering remains as defensive validation of provider results.
- Project bindings without a repository keep shared-Project visibility and send no repository query.
- The live provider contract must accept the same `repo:<owner/name>` filter used by the adapter.

## Implementation and verification

- Implementation notes: Added provider-side repository filtering before pagination; no change to item normalization, local defensive filtering, item-limit semantics, or unbound Project inventory behavior.
- Live contract evidence: `projects_list/list_project_items` accepted `repo:NielPieterse0/kis-mcp` and `repo:NielPieterse0/commodity`; the commodity query returned commodity-only items.
- Focused checks: `tests/providers/github/projects/test_adapter.py` passed 14 tests; Ruff passed; `git diff --check` passed; governed scope check passed.
- Review findings: code-quality, API-contracts, and architecture reviews were complete and clean on working-tree fingerprint `3f2b93332b93ba0645f63ef44c5bfa8e5a3e083cdebd0f17c9806851f3758e6e`; no blocking findings.
- Residual risk: commissioning remains incomplete until the merged runtime is restarted and both unattended housekeeping runners produce fresh successful preview receipts.
- Closeout state: implementation and specialist review complete; publication, exact-head Actions, merge, and live commissioning pending.
