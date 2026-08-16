# Change: Development History Boundary

- **Change ID**: `170-development-history-boundary`
- **Repository complexity**: `small`
- **Documentation level**: Small

## Outcome

Make `docs/development/**` explicitly historical/search-only through one concise index without moving, renaming, or rewriting retained evidence.

## Authority and scope

- `AGENTS.md` already classifies `docs/development/**` as historical/specialist engineering evidence.
- This slice adds only `docs/development/README.md` plus this change record.
- Existing historical files remain byte-for-byte untouched.
- No current product, operator, policy, settings, source, test, or module-spec authority changes.

## Acceptance

1. The archive index states that the subtree is not normal implementation context or current product/operator authority.
2. It explains when historical search is appropriate: provenance, prior decisions, regressions, or investigation.
3. It provides category-level navigation without attempting to restate the content/status of every historical file.
4. All relative links in the new index resolve.
5. Governed scope check, focused repository tests, documentation review, and `git diff --check` pass.

## Recovery

Revert the documentation-only commit; no historical evidence is moved or deleted.
