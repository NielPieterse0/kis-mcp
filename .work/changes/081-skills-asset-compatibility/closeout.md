# Closeout: Skills Asset Compatibility

## Implemented scope

- Raised JSON-governed Skills limits to 2,000,000 bytes/file and 3,000,000 bytes/skill.
- Added `.svg`, `.css`, `.html`, `.js`, and `.ttl` as explicitly permitted packaged text suffixes.
- Added exact configured extensionless filename support with initial `LICENSE` allowance; unknown extensionless files remain rejected.
- Applied the same allowed-filename contract to catalogue reads and validated text replacements.
- Added explicit capability metadata for the 12 newly installed shared Skills.
- Replaced composition-count assumptions with settings-derived counts where the count is a catalogue contract.

## Validation evidence

- TDD regression: `test_catalogue_accepts_exact_allowed_extensionless_filename_only` failed before the `virtual_file` fix and passed after it.
- Focused Skills/capability/Gateway suite: 28 passed on the final implementation state.
- Repository verification: final commit-candidate `scripts/verify.ps1` rerun passed after the review fix and line-ending normalization.
- Diff scope check: final commit-candidate `scripts/change-workflow.ps1 check` rerun passed after the review fix and line-ending normalization.

## Review

- Direct diff review found one Important consistency issue: configured `LICENSE` was readable but `validate_replacement()` rejected it through `virtual_file()`.
- Resolution: added failing regression coverage first, then minimally extended `virtual_file()` to honor configured text filenames while preserving binary `.png` rejection.
- NVIDIA advisory reviewer failed with `AGENT_BACKEND_FAILED:NvidiaNimError`; Codex CLI reviewer reported unavailable. No external agent review pass is claimed.

## Git and merge

- Branch: `change/081-skills-asset-compatibility`
- Worktree: `.work/worktrees/081-skills-asset-compatibility`
- Implementation commit: `30df06a7b8da42dd8adb13dbc5e6950f69321170`.
- Implementation PR: #100 — `Support packaged Skills assets`; merged from the exact authorized head.
- Exact-head Work Management gate: `Validate P5 at exact revision` passed for `30df06a7b8da42dd8adb13dbc5e6950f69321170` (check run `93145314280`).
- Merge commit: `c1352fadf736dca0724468b6e67aed8f85e7d624`.
- Metadata closeout: this record closes the change claim; governed cleanup may proceed after the closeout-only PR lands.

## Residual items

- Run governed 081 worktree/branch cleanup after this closeout record lands, then rerun canonical `main` verification.
- Preserve clean change 040 unchanged throughout.
