# Documentation Authority Refresh Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Documentation level:** Complex — this slice changes governing source-of-truth ownership across multiple authority documents.

**Executable sub-slice level:** Small — one bounded compatibility behavior in the existing Work middleware, with focused TDD coverage and no new policy decision, provider, dependency, setting, or persistence model.

**Goal:** Refresh current authoritative documentation around one governed fact / one canonical owner, remove current authority duplication and contradictions, and prevent KIS text-write line-ending drift by honoring each Git worktree's effective attributes without rewriting historical records or changing policy.

**Architecture:** Put repository-wide document routing in `AGENTS.md`; keep `README.md` as a concise human projection; keep hard-rule semantics in `docs/TRUST-MODEL.md`; keep current product truth in `SPEC.md` without editing it in this slice; keep target-state concepts in `docs/PLATFORM-CONCEPT.md`; keep operator procedure in `docs/OPERATIONS.md`. Replace duplicated authority with links and explicit scope boundaries. For KIS text mutations, add one narrow pre-forwarding normalizer that asks local Git for the target path's effective `text`/`eol` attributes and rewrites only newline-bearing provider arguments; Desktop Commander remains the filesystem writer.

**Tools:** repository `develop-docs` workflow, KIS/ Desktop Commander file operations, `scripts/change-workflow.ps1`, Git, repository verification, and independent advisory review when available.

## Global constraints

- Stay inside `scope.json`.
- Do not edit `SPEC.md` or the Discover product spec while active change `093` owns them.
- Do not rewrite historical `.work/changes/**` or `docs/development/**` evidence.
- Do not change source/runtime behavior beyond the bounded Git-attribute line-ending normalizer; do not change settings, policy, contracts, or commissioning behavior.
- Preserve useful human orientation while removing duplicate canonical detail.
- Any factual current-state statement must be supported by current authority or repository evidence.

## Source-to-section traceability

| Requirement | Target | Source/evidence | Verification |
|---|---|---|---|
| REQ-001/002 | `AGENTS.md` | operator audit; current authority order; change workflow | diff review; scope check; repository verify |
| REQ-003 | `README.md` | operator audit; `AGENTS.md`; `SPEC.md`; `docs/OPERATIONS.md` | diff review; link/verification checks |
| REQ-004 | `docs/PLATFORM-CONCEPT.md` | operator audit; `AGENTS.md`; target/current-state boundary | diff review; repository verify |
| REQ-005 | `docs/OPERATIONS.md` | current `SPEC.md` and current mounted-provider description in the same file | contradiction search; repository verify |
| REQ-006 | `docs/TRUST-MODEL.md` | current `AGENTS.md` authority order | diff review; repository verify |
| REQ-007/008 | all | scope exclusions; Git diff; policy/current-state authorities | change-workflow check; Git diff; repository verify |
| REQ-009/010 | `src/kis_mcp/line_endings.py`, middleware composition, focused tests | `.gitattributes`; effective local Git attributes; Desktop Commander exact-string write behavior | red/green focused pytest; middleware forwarding test; repository line-ending verifier; full verify |

---

### Task 1: Establish documentation ownership

**Files:**
- Modify: `AGENTS.md`
- Verify: authority routing, active-vs-historical change record semantics, and no duplicate owner assignments.

- Add the one-governed-fact / one-canonical-owner rule.
- Define concise routing for authorities, scoped module specs, active change records, supporting evidence, skills, and machine-readable facts.
- State that merged `.work` records are historical evidence and are not continuously refreshed.

### Task 2: Thin the human landing page

**Files:**
- Modify: `README.md`
- Verify: human orientation remains sufficient and volatile implementation/operations details defer to canonical owners.

- Keep product purpose, capability summary, repository navigation, quick start, and verification entry point.
- Remove or compress duplicated provider lifecycle, work-management, Discover, and configuration detail.
- Add explicit navigation-only authority wording.

### Task 3: Bound trust and target-state authorities

**Files:**
- Modify: `docs/TRUST-MODEL.md`
- Modify: `docs/PLATFORM-CONCEPT.md`

- Add a narrow trust-model scope boundary without repeating repository workflow.
- Replace the target-state file-by-file ownership table with a reference to `AGENTS.md`.
- Preserve target-state Govern concepts without claiming they are currently implemented.

### Task 4: Reconcile operations

**Files:**
- Modify: `docs/OPERATIONS.md`

- Add a concise operator-runbook authority boundary.
- Correct the Control Center mounted/standalone contradiction.
- Keep implementation/architecture doctrine as references rather than duplicated definitions.

### Task 5: Prevent KIS line-ending drift

**Files:**
- Create: `src/kis_mcp/line_endings.py`
- Modify: `src/kis_mcp/middleware.py`
- Modify: `src/kis_mcp/gateway/composition.py`
- Create: `tests/test_line_endings.py`

- Write focused tests first and confirm the missing normalizer fails collection.
- Implement Git-attribute resolution for `text` and `eol` without parsing `.gitattributes` patterns in KIS.
- Normalize newline-bearing `write_file` and `edit_block` arguments before provider forwarding.
- Preserve `eol=crlf`, skip `text=unset` binary paths, and leave unresolved/non-Git paths unchanged.
- Confirm focused tests pass after correcting the inherited-EOL/binary edge case.

### Task 6: Review and verify

- Review the complete diff against the operator audit and current authorities.
- Search for remaining current-authority contradictions introduced or left in owned files.
- Run `pwsh -File scripts/change-workflow.ps1 check` from the worktree.
- Run focused line-ending tests and canonical repository verification from the worktree.
- Run an independent advisory review if the configured reviewer is ready; resolve blocking findings and rerun affected evidence.
- Update tasks and closeout with exact verification and review evidence.

### Task 7: Publish, merge, and clean up

- Commit the reviewed branch.
- Publish the branch and create a pull request.
- Confirm required checks and merge exact reviewed head through the approved registered-GitHub path.
- Fast-forward/reconcile local `main` to the merged result without disturbing other worktrees.
- Run post-merge verification/reporting as applicable.
- Run `scripts/change-workflow.ps1 cleanup 094-documentation-authority-refresh` from clean primary `main`.
