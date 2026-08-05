# Implementation Plan: Line Ending Hygiene

## Approach

1. Add regression tests for the canonical attributes, repository configuration entry point, EOL parser, and verifier registration.
2. Run the focused tests and record the expected failure.
3. Add `.gitattributes`, `.editorconfig`, and `scripts/configure-repository.ps1`.
4. Invoke repository configuration from change creation and verification.
5. Add `verify_repository_line_endings()` to inspect local Git configuration and `git ls-files --eol` output.
6. Set repository-local Git configuration and run `git add --renormalize .` once.
7. Review the mechanical diff for semantic changes and scope compliance.
8. Run focused tests, whitespace validation, change governance, and full verification serially.

## Design constraints

- LF is canonical for text, including PowerShell scripts.
- `.bat` and `.cmd` remain explicit CRLF exceptions.
- Binary files are explicitly non-text.
- The verifier evaluates Git’s actual index and worktree classification, not filename assumptions alone.
- The configuration script changes only repository-local Git configuration.

## Recovery

Revert the hygiene commit to restore the previous tracked bytes and remove the repository policies. No system Git configuration is modified.
