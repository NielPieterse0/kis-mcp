# Closeout: GitHub Project Write Commissioning

## Implemented scope

- Preserved `kis-mcp` routing to `NielPieterse0` user Project #1.
- Added live REST Project-item compatibility for integer IDs, `content_type`, `fields`, and `html_url`.
- Changed Project management follow-up writes to prefer numeric `item_id` over GraphQL node `id`.
- Promoted only Work Management `reconciliation` from `read_only` to `enabled`; all automation remains disabled.
- Added focused commissioning regression tests and operator documentation.

## Live commissioning evidence

- GitHub MCP runtime: authenticated, mounted, tools discovered, live verified.
- Project: `KIS Work Management`, user Project #1, open.
- Required Status options: `Todo`, `In Progress`, `Done`.
- Tracking item: repository issue #102.
- Added issue #102 as the first Project item; numeric Project item ID: `225838119`.
- GraphQL node-ID update was rejected by the official provider as non-numeric.
- Digit-text numeric ID update succeeded and set `Status=In Progress`.
- Re-adding issue #102 returned the same numeric Project item ID `225838119`; inventory still contains exactly one matching item.
- Focused 085 + existing GitHub Project adapter suites: 22/22 passed.
- Canonical verification currently has three assertion failures: two pre-existing `college` registry expectation drifts in `tests/projects/**`, plus `tests/work_management/test_settings.py` still expecting `reconciliation=read_only` in a path exclusively owned by active change 084.
- External code-review backend was attempted and failed with `NvidiaNimError`; direct diff review and focused tests found no blocking 085 defect.
- Final high-level reconciliation replay/conflict/Done proof remains post-merge/restart evidence.
