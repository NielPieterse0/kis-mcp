# Env Expanded Shell Mutations Implementation Plan

**Goal:** Close #288 with the smallest parser/effect/policy change that preserves definite unresolved shell mutation targets and blocks them structurally before forwarding.

**Architecture:** Keep existing shell target recognition. Partition each recognized mutation target into resolved or unresolved evidence. Carry both through nested effect merging. Track cmd delayed-expansion mode as bounded shell state with wrapper-option precedence, but never expand environment syntax inside KIS. Policy rejects structural unresolved-target evidence before hard-rule attribution, then evaluates resolved effects normally.

**Tech stack:** Python 3.13, pytest, Ruff, KIS change governance, GitHub Actions Canonical Verification.

## Global constraints

- Stay inside `scope.json`; no #270/#278/#241/#258/#289 work.
- Preserve the three-rule trust model and `unresolved_delete` semantics.
- Add regression coverage before closeout and use exact-head CI for canonical verification.

### Task 1: Effect contract and parser preservation

**Files:** `src/kis_mcp/models.py`, `src/kis_mcp/command_intent.py`, `src/kis_mcp/shell_parser.py`, `tests/test_p1_command_hardening.py`, `tests/test_process_state.py`, `tests/test_shell_parser.py`

- [x] Add unresolved write/entry/delete target evidence without changing original positional field meaning.
- [x] Partition recognized mutation targets instead of dropping failed resolutions.
- [x] Merge unresolved evidence across nested/wrapped shell recursion.
- [x] Cover cmd percent expansion/modifiers, delayed `!VAR!`, PowerShell variables/subexpressions, and unknown-command non-mutation behavior.
- [x] Persist cmd delayed-expansion state, honor last wrapper `/V` switch before `/c`/`/k`, and ignore payload switch text.
- [x] Preserve literal `%`, disabled `!name!`, and wholly single-quoted PowerShell marker paths while detecting active expansion across adjacent quoted/unquoted fragments.

### Task 2: Structural policy gate

**Files:** `src/kis_mcp/policy.py`, `tests/test_policy.py`

- [x] Treat path-validation failure on definite write/entry/delete targets as structural invalid invocation.
- [x] Reject explicit unresolved mutation evidence with `INVALID_INVOCATION_PATH` and no HR rule ID.
- [x] Give structural unresolved-target evidence precedence over HR attribution in mixed-effect invocations.
- [x] Preserve HR-001 for fully resolved external paths and HR-003 for targetless destructive intent/quarantine.

### Task 3: End-to-end forwarding gate

**Files:** `tests/test_middleware.py`

- [x] Prove env/subexpression redirection, write, delete, move, and create commands are rejected before provider forwarding.
- [x] Prove structural errors are not labeled HR-001/HR-003.

### Task 4: Review, verification, and delivery

- [x] Run scope check, focused tests, Ruff, and focused repository verification (143 tests, Ruff, diff check, governed scope check all green).
- [x] Run code-quality, safety-security, architecture, and API-contract reviews against the final exact source (manual exact-diff fallback after configured reviewer backends failed safely).
- [ ] Commit and prepare a reviewable pull request through KIS.
- [ ] Require exact-head Canonical Verification success.
- [ ] Merge only the approved exact head, refresh `main`, close #288, and clean the merged worktree.
