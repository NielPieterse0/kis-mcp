# Tasks: Documentation Authority Refresh

- [x] Confirm authority and scope against the operator audit and live repository authorities.
- [x] Implement the approved authority/documentation refresh within the registered worktree.
- [x] Add the bounded Git-attribute line-ending guard after the staging failure exposed KIS write-path CRLF drift.
- [x] Prove the guard with red/green focused tests covering LF, explicit CRLF, binary, nested `.gitattributes`, non-Git pass-through, inherited Git environment isolation, and middleware forwarding.
- [x] Run `scripts/change-workflow.ps1 validate` and `check`; active changes `093` and `094` remain non-overlapping and 094 stays inside its expanded scope.
- [x] Review the complete diff, authority boundaries, current-state claims, Control Center contradiction, middleware behavior, and provider boundary. Configured Codex and NVIDIA advisory backends were attempted but failed before producing findings; no advisory pass is claimed.
- [x] Normalize the owned files to repository EOL policy, run `git diff --check`, focused regressions, and canonical `scripts/verify.ps1`; full verification passed with repository line-ending policy clean, pytest exit `0`, and 247 Python files syntax-checked.
- [ ] Commit, publish, create/complete the PR, merge the exact reviewed head, reconcile local `main`, and run safe cleanup.
