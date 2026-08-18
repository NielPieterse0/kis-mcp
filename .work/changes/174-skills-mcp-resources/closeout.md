# Closeout: Skills MCP Resources

## Implemented scope
- Added `skill:///` catalogue index and canonical entrypoint/supporting-resource FastMCP templates.
- Added snapshot-verified exact-byte reads for text and binary skill resources.
- Preserved one canonical `SKILL.md` URI, progressive disclosure, and data-only script/asset semantics.
- Updated the durable Skills module product specification.

## Validation evidence
- Focused checks: 19/19 passed across `test_resources.py`, Skills architecture, and gateway composition.
- Governed check: `scripts/change-workflow.ps1 check` passed with only declared paths.
- Diff scope check: `git diff --check` passed.
- Canonical exact-head repository verification remains a pull-request/CI gate.

## Review
- Architecture review: clean; no findings.
- API-contract review: one medium diagnostic-classification finding in resource revalidation; fixed by preserving path/link codes and mapping missing/drift to `SKILLS_RESOURCE_STALE`.
- Final Codex API re-review: no implementation defect; one low public-boundary test-coverage finding.
- Resolution: added FastMCP-level assertions for unsafe paths, missing/stale resources, link rejection, and canonical-entrypoint alias rejection; focused tests reran 19/19 green.

## Git and merge
- Branch: `change/174-skills-mcp-resources`
- Worktree: `.work/worktrees/174-skills-mcp-resources`
- Commit: pending
- Pull request or merge: pending exact-head CI
- Cleanup: pending verified merge

## Residual items
- Delivery-path telemetry remains #314 and is intentionally not implemented in this change.