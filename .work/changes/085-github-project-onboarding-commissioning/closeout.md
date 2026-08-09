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
- Focused 085 + existing GitHub Project adapter suites: 22/22 passed; the final settings/project-onboarding regression set passed 10/10 after reconciling the stale `reconciliation=read_only` assertion left behind by the now-closed parallel change.
- Final canonical `scripts/verify.ps1` on the integrated 085 worktree passed at 100% pytest completion with two existing expected skips; configuration, interpreter, dependencies, Python syntax, change governance, and repository line-ending checks all passed.
- External code-review backend was attempted and failed with `NvidiaNimError`; direct diff review and focused/full verification found no blocking 085 defect.
- Fresh `kis-dev` reload completed on the integrated 085 `main` tree.
- High-level reconciliation preview for issue #102 produced `update` from `In Progress` to `Done` at observed revision `2026-08-09T12:03:24Z`.
- Apply with idempotency key `085-closeout-done-v1` succeeded and returned provider revision `2026-08-09T16:31:47Z`; replaying the identical request with the same key returned the identical successful outcome without a second command.
- A second apply request with stale expected revision `2026-08-09T12:03:24Z` against observed revision `2026-08-09T16:31:47Z` returned `action=conflict`, `applied=false`, `success=false`.
- Final live Project item `225838119` is `Status=Done`; issue #102 is closed/completed; bounded Project inventory contains exactly one item and `hasNextPage=false`.
- 085 implementation and commissioning are complete; only governed worktree/branch cleanup remains after repository-wide final integration.
