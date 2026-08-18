# Tasks: Skills MCP Resources

- [x] Consult normative MCP `2025-11-25` resource contracts.
- [x] Confirm repository FastMCP dependency is `3.4.4`.
- [x] Confirm all historical touched files equal the Change 174 series base.
- [x] Port only the final historical Skills resource/delivery payload through `5cf2406`.
- [x] Run focused Skills tests and Ruff.
- [x] Run scope check.

## External exact-head close gate

- Freeze one immutable head, then run code-quality, API-contract, architecture reviews and GitHub Actions against that same head.
- Merge, align, close #362, and clean without a metadata-only follow-up commit.