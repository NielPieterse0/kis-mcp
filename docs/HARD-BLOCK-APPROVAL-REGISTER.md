# Hard-Block Approval Register

## Purpose

This document is exclusively the operator approval register for active hard-block or quarantine decisions enforced under:

- `HR-001` — a proven write outside `C:\Projects`;
- `HR-002` — a proven external-network operation through local Work;
- `HR-003` — a proven permanent-delete operation that must become quarantine or be rejected when safe quarantine is impossible.

This register must not contain:

- allowed behavior;
- parser coverage or implementation notes that do not block;
- removed or rejected mappings;
- structural input errors;
- unsupported provider tools or arguments;
- startup, installation, readiness, compatibility, or configuration invariants;
- recovery-integrity rules that are not HR decisions.

Those matters are documented separately in `docs/NON-HARD-CONTROLS.md`.

## Governing approval test

Approve an entry only when the complete concrete invocation and its resolved resultant effects positively establish `HR-001`, `HR-002`, or `HR-003`.

A prompt phrase, tool name, executable, command, flag, URL string, capability category, destructive appearance, possibility of misuse, parser uncertainty, or missing coverage is not independently sufficient.

For each entry, mark exactly one operator decision:

- **Approve** — retain the active hard block or quarantine behavior.
- **Revise** — narrow or correct it before approval.
- **Reject** — remove the hard block or transformation.

---

# HR-001 — Proven write outside `C:\Projects`

## HR1-01 — Explicit provider write destinations

**Implementation:** Active hard-block mapping.

The adapter reports only provider arguments that are effective write destinations. For `write_pdf`, `outputPath` is the write target when supplied; otherwise `path` is overwritten and becomes the write target.

**Hard-block condition:** The effective write destination resolves outside `C:\Projects`.

**Evidence/tests:** `test_direct_write_tool_reports_path`, `test_write_pdf_reports_only_the_effective_output_path`, and policy boundary tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR1-02 — Move source or destination outside the boundary

**Implementation:** Active hard-block mapping.

A move mutates directory entries at both the source and destination. Existing ancestors are resolved without following the final entry itself.

**Hard-block condition:** Either effective entry resolves outside `C:\Projects`.

**Evidence/tests:** `test_move_reports_entry_mutations` and policy entry-mutation tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR1-03 — Effective path through links or junctions

**Implementation:** Active hard-block mapping.

Content writes follow the effective final target. Entry mutations resolve existing ancestors without following the final entry.

**Hard-block condition:** A textually in-boundary path resolves to an effective write location outside `C:\Projects`.

**Evidence/tests:** path normalization, link, junction, and prefix-collision tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR1-04 — Explicit shell output redirection

**Implementation:** Active hard-block mapping.

Recognized unquoted output redirections identify a concrete destination and are resolved relative to the invocation working directory.

**Hard-block condition:** The redirection destination resolves outside `C:\Projects`.

**Evidence/tests:** `test_terminal_redirection_outside_boundary_is_detected`, `test_relative_redirection_uses_command_working_directory`.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR1-05 — Known write-command destination

**Implementation:** Active hard-block mapping.

Known copy, create, and PowerShell content-write contracts are used only to identify their concrete destination operands.

**Hard-block condition:** The resolved destination operand is outside `C:\Projects`.

**Evidence/tests:** `test_positional_powershell_write_path_is_detected` and command-path tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR1-06 — Mutating local Git operation outside the boundary

**Implementation:** Active hard-block mapping.

The resolver distinguishes supported read-only and mutating Git forms. For a resolved mutating form, the concrete working directory is the write target.

**Hard-block condition:** A mutating Git form is resolved and its working directory is outside `C:\Projects`.

**Evidence/tests:** `test_read_only_git_forms_do_not_claim_a_write_target`, `test_mutating_git_forms_report_the_working_directory`.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

## HR1-07 — Serena effective mutation destination outside the boundary

**Implementation:** Proposed provider mapping; production implementation pending operator approval.

Serena exposes file, symbol, refactoring, memory, project-configuration, index, cache, and logging operations that can produce writes. The adapter will resolve each pinned provider contract to its actual effective write or entry-mutation destinations using the active project, project-relative arguments, provider-state locations, move source and destination, and documented argument precedence. Serena tool names, optional status, beta status, or general editing capability are not sufficient to claim a write effect.

**Hard-block condition:** A complete Serena invocation resolves one or more effective write or entry-mutation destinations outside `C:\Projects`.

**Permitted forms:** Reads outside the boundary remain permitted. A mutating Serena invocation whose complete resolved write set remains inside `C:\Projects` is forwarded. An unresolved or malformed provider argument is handled as a structural/provider error rather than an HR-001 decision.

**Evidence/tests required before activation:** Exact schema fixtures for every enabled mutating Serena tool; project-relative and absolute path tests; alias-precedence tests; move source/destination tests; provider-state, memory, index, cache, and log location tests; link, junction, and prefix-collision tests; permitted in-boundary counterexamples.

**Reason approval is required:** This mapping teaches the gateway how Serena-specific arguments and provider state become concrete write effects. An overbroad mapping would suppress valid Serena capability; an incomplete mapping could permit a proven HR-001 write.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

# HR-002 — Proven external network through Work

## HR2-01 — Known network client with an external target

**Implementation:** Active hard-block mapping.

A known network-client executable is only a resolver hint. The resolver identifies concrete target positions and excludes known option values such as headers and output paths. For `scp`, an explicit URL, UNC target, or SCP-style remote operand is required.

**Hard-block condition:** A consuming target position resolves to an external host or endpoint.

**Evidence/tests:** `test_terminal_network_command_is_detected`, `test_network_client_option_values_are_not_mistaken_for_targets`, `test_network_client_positional_host_is_detected`, `test_scp_requires_an_explicit_remote_operand`, `test_localhost_network_client_is_allowed`.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR2-02 — Package operation with an explicit external source

**Implementation:** Active hard-block mapping.

Package-manager names, operation names, package names, lockfile actions, missing operands, and unresolved source aliases do not establish HR-002.

**Hard-block condition:** The invocation contains an explicit external URL, remote Git dependency, UNC/SCP reference, or registry/source value that is itself an explicit external reference.

**Evidence/tests:** `test_ambiguous_package_operations_are_not_blocked_by_category`, `test_local_package_install_is_allowed`, `test_explicit_offline_package_operations_are_allowed`, `test_explicit_remote_git_and_package_targets_are_blocked`.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR2-03 — Git operation with an external remote

**Implementation:** Active hard-block mapping.

For `fetch`, `pull`, and `push`, named and default remotes are resolved from local Git configuration where possible. `clone` and `ls-remote` use their explicit target. An unresolved alias does not establish HR-002.

**Hard-block condition:** The explicit or locally resolved remote is external.

**Evidence/tests:** `test_git_pull_without_resolved_remote_is_not_blocked_by_category`, `test_git_named_remote_is_resolved_from_local_config`, `test_git_local_remote_is_allowed`, and explicit remote Git tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR2-04 — UNC or SCP-style external target

**Implementation:** Active hard-block mapping.

UNC and SCP-style strings are evaluated only when consumed as the actual target of a known network, Git, or package operation.

**Hard-block condition:** The consumed target identifies a non-loopback external host.

**Evidence/tests:** network-client, SCP, package-source, and Git-target tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR2-05 — Enabling Desktop Commander telemetry

**Implementation:** Active hard-block mapping.

The pinned provider interprets only boolean `false` and string `"false"` as telemetry-disabled values.

**Hard-block condition:** `set_config_value` targets `telemetryEnabled` with a value that the pinned provider does not interpret as disabled.

**Evidence/tests:** `test_enabling_telemetry_is_network_intent`, `test_disabling_telemetry_is_not_network_intent`.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

## HR2-06 — Serena shell command with a proven external target

**Implementation:** Proposed provider mapping; production implementation pending operator approval.

Serena exposes `execute_shell_command`. The adapter will pass the complete command, effective working directory, shell form, and resolved arguments into the existing command-effect resolver. The Serena tool name, presence of a URL-like string, unknown executable, or general ability to start a process does not independently establish external-network intent.

**Hard-block condition:** The complete Serena shell invocation resolves under the existing exact command contracts to an operation that consumes a non-loopback external host, endpoint, registry, package source, or remote.

**Permitted forms:** Local commands, loopback access, commands without a proven external target, help or dry-run forms, and unresolved command shapes are not blocked under HR-002. Other proven effects from the same command remain subject to HR-001 and HR-003.

**Evidence/tests required before activation:** Exact Serena shell schema fixture; working-directory propagation; quoted and escaped argument handling; known network-client targets and option values; package-source and Git-remote resolution; localhost counterexamples; unknown-command counterexamples; composed-command tests.

**Reason approval is required:** This mapping connects a new provider shell contract to the existing HR-002 resolver. It must preserve Serena shell capability while blocking only complete invocations that prove an external Work-network effect.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

# HR-003 — Proven permanent deletion

## HR3-01 — Direct provider delete tools

**Implementation:** Active quarantine transformation.

Exact provider delete targets inside `C:\Projects` are moved intact to quarantine. The provider delete tool is not called.

**Hard-rule condition:** The invoked provider contract is a delete operation with an exact in-boundary target.

**Result:** Quarantine the target; reject only if safe quarantine cannot be completed.

**Evidence/tests:** middleware direct-delete and quarantine tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR3-02 — Known delete command with explicit operands

**Implementation:** Active hard-block mapping.

Known delete commands contribute delete effects only when explicit operands are resolved. Help and PowerShell `-WhatIf` forms do not establish delete intent.

**Hard-block condition:** The command explicitly requests permanent deletion of one or more resolved targets and cannot be safely forwarded as quarantine-equivalent behavior.

**Result:** Reject with `HR-003_QUARANTINE_REQUIRED` and direct the operation to the quarantine interface.

**Evidence/tests:** terminal delete, shell-wrapper, middleware, and policy quarantine tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR3-03 — Destructive `git clean`

**Implementation:** Active hard-block mapping.

Dry-run forms are not blocked. A forced non-dry-run `git clean` proves permanent-delete intent, but the command does not itself provide an exact safe quarantine target set.

**Hard-block condition:** A non-dry-run destructive `git clean` invocation is resolved.

**Result:** Reject with `HR-003_QUARANTINE_REQUIRED`; do not treat the repository root as the delete target.

**Evidence/tests:** `test_git_clean_and_reset_are_classified_by_exact_effect` and middleware Git-clean test.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR3-04 — Delete target outside `C:\Projects`

**Implementation:** Active hard block under HR-001 before quarantine.

Deleting an external directory entry is a write outside the approved boundary. External material is not moved into the local quarantine.

**Hard-block condition:** A resolved delete target is outside `C:\Projects`.

**Result:** Reject as `HR-001_WRITE_OUTSIDE_PROJECTS`.

**Evidence/tests:** policy external-delete tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR3-05 — Delete the `C:\Projects` boundary itself

**Implementation:** Active hard block.

The project boundary cannot be moved beneath a quarantine directory located inside itself.

**Hard-block condition:** The exact delete target is `C:\Projects`.

**Result:** Reject as `HR-003_QUARANTINE_FAILED`.

**Evidence/tests:** project-boundary quarantine tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

## HR3-06 — Safe quarantine cannot be completed

**Implementation:** Active hard block.

Permanent deletion is never forwarded as fallback.

**Hard-block condition:** A proven delete operation cannot be moved intact and recorded safely in quarantine.

**Result:** Reject as `HR-003_QUARANTINE_FAILED`.

**Evidence/tests:** quarantine failure and middleware failure tests.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

## HR3-07 — Serena whole-memory-file deletion

**Implementation:** Proposed quarantine mapping; production implementation pending operator approval.

At the candidate Serena `1.6.1` contract, `delete_memory` requests deletion of one complete memory file. The adapter will resolve the effective memory file from the active project, memory name, `SERENA_HOME`, and configured Serena project-data location. The provider delete operation is not forwarded when the exact file target is resolved.

**Hard-rule condition:** `delete_memory` resolves one exact existing memory file inside `C:\Projects` and requests permanent removal of that complete artifact.

**Result:** Move the memory file intact into kis-mcp quarantine and record restoration metadata. If the exact target is outside `C:\Projects`, apply HR-001. If the target cannot be resolved exactly or safe quarantine cannot complete, return the applicable structural error or `HR-003_QUARANTINE_FAILED`; never forward permanent deletion as fallback.

**Not included:** `delete_lines`, `safe_delete_symbol`, `jet_brains_safe_delete`, replacements, and refactorings that alter content within a retained source file are treated as content writes under HR-001, not whole-artifact deletion. A later pinned Serena contract that can delete a complete file or directory requires a new or revised approved mapping before activation.

**Evidence/tests required before activation:** Exact `delete_memory` schema fixture; project and global memory-path resolution; traversal and alias rejection; exact quarantine and restore tests; outside-boundary tests; missing-target and quarantine-failure tests; counterexamples proving partial code deletion remains an ordinary in-boundary write.

**Reason approval is required:** This mapping converts a new provider-specific whole-file delete contract into the existing recoverable quarantine behavior while avoiding an overbroad interpretation of every code-removal operation as HR-003.

**Recommended disposition:** Approve.

**Operator decision:** [ ] Approve  [ ] Revise  [ ] Reject

---

## Approval procedure

Review each active hard-block or quarantine entry in order:

1. confirm the complete concrete invocation proves the stated HR outcome;
2. confirm the decision is not based on category, name, possibility, or uncertainty;
3. confirm tests cover both blocked and permitted forms;
4. mark **Approve**, **Revise**, or **Reject**;
5. record any required narrowing before final approval.

No item is approved solely because tests pass. The operator decision is the approval record.
