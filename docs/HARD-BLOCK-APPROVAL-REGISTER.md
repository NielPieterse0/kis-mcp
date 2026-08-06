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

**Operator Comments:**

The register says only the effective provider destination is reported. Current handling can collect multiple alias fields, notably edit_block.file_path and edit_block.path, without establishing which one the provider actually consumes. An inactive external alias could therefore block a valid in-boundary write.

Define provider argument precedence for every alias-bearing tool. Report exactly one effective destination where the provider uses precedence. Reject structurally if mutually exclusive fields are invalid.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

## HR1-02 — Move source or destination outside the boundary

**Implementation:** Active hard-block mapping.

A move mutates directory entries at both the source and destination. Existing ancestors are resolved without following the final entry itself.

**Hard-block condition:** Either effective entry resolves outside `C:\Projects`.

**Evidence/tests:** `test_move_reports_entry_mutations` and policy entry-mutation tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR1-03 — Effective path through links or junctions

**Implementation:** Active hard-block mapping.

Content writes follow the effective final target. Entry mutations resolve existing ancestors without following the final entry.

**Hard-block condition:** A textually in-boundary path resolves to an effective write location outside `C:\Projects`.

**Evidence/tests:** path normalization, link, junction, and prefix-collision tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR1-04 — Explicit shell output redirection

**Implementation:** Active hard-block mapping.

Recognized unquoted output redirections identify a concrete destination and are resolved relative to the invocation working directory.

**Hard-block condition:** The redirection destination resolves outside `C:\Projects`.

**Evidence/tests:** `test_terminal_redirection_outside_boundary_is_detected`, `test_relative_redirection_uses_command_working_directory`.

**Recommended disposition:** Approve.

**Operator Comments:**

The register says only unquoted redirections are detected, but the current regex does not maintain shell quote state. A literal > inside a quoted string can be interpreted as a redirection.

Parse redirection through the shell tokenizer/state machine. Prove that the operator itself is syntactic redirection, not quoted text, escaped text, comparison syntax, or argument data.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

## HR1-05 — Known write-command destination

**Implementation:** Active hard-block mapping.

Known copy, create, and PowerShell content-write contracts are used only to identify their concrete destination operands.

**Hard-block condition:** The resolved destination operand is outside `C:\Projects`.

**Evidence/tests:** `test_positional_powershell_write_path_is_detected` and command-path tests.

**Recommended disposition:** Approve.

**Operator Comments:**

“Known copy, create, and PowerShell contracts” is too vague. Current generic extraction of non-option values can mistake option values for destinations—for example values associated with New-Item -ItemType, touch -d, or future command options.

Replace generic positional inference with exact per-command contracts: supported options, which options consume values, positional destination index, parameter precedence, and supported modes.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

## HR1-06 — Mutating local Git operation outside the boundary

**Implementation:** Active hard-block mapping.

The resolver distinguishes supported read-only and mutating Git forms. For a resolved mutating form, the concrete working directory is the write target.

**Hard-block condition:** A mutating Git form is resolved and its working directory is outside `C:\Projects`.

**Evidence/tests:** `test_read_only_git_forms_do_not_claim_a_write_target`, `test_mutating_git_forms_report_the_working_directory`.

**Recommended disposition:** Approve.

**Operator Comments:**

The text claims read-only and mutating Git forms are distinguished, but some operations are classified only by command name. Forms such as git add --dry-run, git commit --dry-run, and help modes can be falsely classified as writes.

Add exact dry-run, help, porcelain/report-only, and no-op classifications. Resolve actual --git-dir, --work-tree, index, common directory, and explicit output targets rather than using the working directory as a broad fallback.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

---

## HR1-07 — Serena invocation-controlled mutation outside the boundary

**Implementation:** Approved provider mapping; production activation requires the recorded exact-contract tests.

The Serena adapter resolves only destinations controlled by the concrete enabled invocation: explicit file paths, project-relative file or symbol edits, exact memory-file paths, move source and destination entries, and explicit output destinations. Serena tool names, editing capability, provider optionality, and unresolved effect coverage do not establish a write effect.

**Hard-block condition:** An enabled Serena invocation resolves an invocation-controlled file mutation or entry mutation outside `C:\Projects`.

**Separate provider-storage invariant:** Serena cache, index, log, temporary, configuration, language-server, and default runtime-state roots must be configured beneath `C:\Projects` and verified by installation and readiness checks. Those provider-managed roots do not independently cause a per-invocation HR-001 block unless the specific invocation explicitly selects or changes that destination.

**Permitted forms:** Reads outside the boundary remain permitted. A mutating invocation whose proven invocation-controlled destinations remain inside `C:\Projects` is forwarded. Unknown or unsupported effect resolution is not proof of HR-001. Malformed input may be rejected as a structural/provider error, but missing resolver coverage must not become a blanket Serena rejection.

**Evidence/tests required before activation:** Exact pinned schema fixtures for each enabled invocation-controlled mutation; documented argument precedence; project-relative and absolute path resolution; move source/destination effects; memory-file resolution; explicit output paths; link, junction, traversal, and prefix-collision cases; permitted in-boundary and unknown-effect counterexamples. Provider-managed storage is tested separately through installer and readiness tests.

**Reason approval is required:** The mapping must stop proven Serena writes outside the boundary without turning incidental provider-managed storage into a broad per-invocation blocker that suppresses otherwise valid Serena capability.

**Recommended disposition:** Approve.

**Operator Comments:**

Separate invocation-controlled mutations from provider-managed storage. Cache, index, log, temporary, configuration, and runtime-state roots belong to installation and startup invariants unless a concrete invocation explicitly selects or alters them. Unknown or unsupported effect resolution is not proof of HR-001.

The narrowed wording is approved for implementation on 2026-08-06.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

---

# HR-002 — Proven external network through Work

## HR2-01 — Known network client with an external target

**Implementation:** Active hard-block mapping.

A known network-client executable is only a resolver hint. The resolver identifies concrete target positions and excludes known option values such as headers and output paths. For `scp`, an explicit URL, UNC target, or SCP-style remote operand is required.

**Hard-block condition:** A consuming target position resolves to an external host or endpoint.

**Evidence/tests:** `test_terminal_network_command_is_detected`, `test_network_client_option_values_are_not_mistaken_for_targets`, `test_network_client_positional_host_is_detected`, `test_scp_requires_an_explicit_remote_operand`, `test_localhost_network_client_is_allowed`.

**Recommended disposition:** Approve.

**Operator Comments:**

The target parser excludes several values that can themselves cause external network access. Current examples include proxy and connection-routing options such as --proxy, --connect-to, and --resolve. Case-folding also risks conflating curl’s case-sensitive -x and -X.

Divide options into non-network data values and network-bearing target values. Preserve case-sensitive short-option semantics. Treat proxy, jump-host, DNS override, connection-routing, and similar values as consuming network targets.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

## HR2-02 — Package operation with an explicit external source

**Implementation:** Active hard-block mapping.

Package-manager names, operation names, package names, lockfile actions, missing operands, and unresolved source aliases do not establish HR-002.

**Hard-block condition:** The invocation contains an explicit external URL, remote Git dependency, UNC/SCP reference, or registry/source value that is itself an explicit external reference.

**Evidence/tests:** `test_ambiguous_package_operations_are_not_blocked_by_category`, `test_local_package_install_is_allowed`, `test_explicit_offline_package_operations_are_allowed`, `test_explicit_remote_git_and_package_targets_are_blocked`.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR2-03 — Git operation with an external remote

**Implementation:** Active hard-block mapping.

For `fetch`, `pull`, and `push`, named and default remotes are resolved from local Git configuration where possible. `clone` and `ls-remote` use their explicit target. An unresolved alias does not establish HR-002.

**Hard-block condition:** The explicit or locally resolved remote is external.

**Evidence/tests:** `test_git_pull_without_resolved_remote_is_not_blocked_by_category`, `test_git_named_remote_is_resolved_from_local_config`, `test_git_local_remote_is_allowed`, and explicit remote Git tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR2-04 — UNC or SCP-style external target

**Implementation:** Active hard-block mapping.

UNC and SCP-style strings are evaluated only when consumed as the actual target of a known network, Git, or package operation.

**Hard-block condition:** The consumed target identifies a non-loopback external host.

**Evidence/tests:** network-client, SCP, package-source, and Git-target tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR2-05 — Enabling Desktop Commander telemetry

**Implementation:** Active hard-block mapping.

The pinned provider interprets only boolean `false` and string `"false"` as telemetry-disabled values.

**Hard-block condition:** `set_config_value` targets `telemetryEnabled` with a value that the pinned provider does not interpret as disabled.

**Evidence/tests:** `test_enabling_telemetry_is_network_intent`, `test_disabling_telemetry_is_not_network_intent`.

**Recommended disposition:** Approve.

**Operator Comments:**

“Not interpreted as disabled” is not automatically equivalent to “proven to enable telemetry.” Invalid, null, unsupported, or rejected values may produce a structural error rather than network activity.

Define the pinned provider’s exact accepted values and resulting persisted/runtime state. Block only values proven to produce enabled telemetry. Classify rejected or invalid values as structural/provider errors.

**Operator decision:** [ ] Approve  [x] Revise  [ ] Reject

---

## HR2-06 — Serena shell command with a proven external target

**Implementation:** Approved conditionally; production activation is blocked until the shared exact command resolver satisfies the recorded revision conditions.

Serena exposes `execute_shell_command`. The adapter must preserve the provider's actual command text or argument vector, effective working directory, shell type, quoting and argument boundaries, and explicitly represented environment-derived target information. It delegates that unchanged semantic input to the corrected shared command-effect resolver. The Serena tool name, presence of URL-like data, unknown executable, dry-run label, or general process capability does not independently establish external-network intent.

**Hard-block condition:** The complete preserved Serena shell invocation resolves under corrected exact command contracts to an operation that consumes a non-loopback external host, endpoint, registry, package source, proxy, connection-routing target, DNS override, jump host, or remote.

**Permitted forms:** Permit only when the resolved invocation does not prove external-network consumption. Local commands, loopback access, URL-like data without a network consumer, and unresolved command shapes are not blocked under HR-002. Dry-run status alone does not establish absence of network access. Other proven effects from the same command remain subject to HR-001 and HR-003.

**Activation conditions:**

1. The shared resolver includes the approved corrections for network-bearing options, case-sensitive short options, shell quoting/redirection, and exact command operand contracts.
2. The Serena adapter does not reconstruct or normalize the command in a way that changes quoting, argument boundaries, shell semantics, or effective working directory.
3. Serena-specific tests prove delegation to the corrected resolver and include dry-run forms that still consume an external target.

**Evidence/tests required before activation:** Exact pinned Serena shell schema fixture; command-text and argument-vector preservation; working-directory and shell propagation; quoted and escaped arguments; proxy, connection-routing, DNS-override, jump-host, package-source, and Git-remote targets; case-sensitive short options; localhost and URL-as-data counterexamples; unknown-command counterexamples; composed-command tests; dry-run network counterexamples.

**Reason approval is required:** This connects Serena's shell contract to the shared HR-002 resolver without introducing a blanket shell restriction or a Serena-specific duplicate policy engine.

**Recommended disposition:** Approve subject to the activation conditions above.

**Operator Comments:**

Approval is conditional on use of the revised exact command resolver, preservation of Serena command semantics, and removal of any assumption that dry-run status alone proves no network access.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

---

# HR-003 — Proven permanent deletion

## HR3-01 — Direct provider delete tools

**Implementation:** Active quarantine transformation.

Exact provider delete targets inside `C:\Projects` are moved intact to quarantine. The provider delete tool is not called.

**Hard-rule condition:** The invoked provider contract is a delete operation with an exact in-boundary target.

**Result:** Quarantine the target; reject only if safe quarantine cannot be completed.

**Evidence/tests:** middleware direct-delete and quarantine tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR3-02 — Known delete command with explicit operands

**Implementation:** Active hard-block mapping.

Known delete commands contribute delete effects only when explicit operands are resolved. Help and PowerShell `-WhatIf` forms do not establish delete intent.

**Hard-block condition:** The command explicitly requests permanent deletion of one or more resolved targets and cannot be safely forwarded as quarantine-equivalent behavior.

**Result:** Reject with `HR-003_QUARANTINE_REQUIRED` and direct the operation to the quarantine interface.

**Evidence/tests:** terminal delete, shell-wrapper, middleware, and policy quarantine tests.

**Recommended disposition:** Approve.

**Operator Comments:**

The resolver can determine exact literal delete paths, but middleware rejects all terminal delete commands because only direct provider delete tools are transformed. This is safe but unnecessarily removes capability.

Transform simple, exact terminal delete forms directly into quarantine. Continue rejecting wildcards, expressions, pipelines, recursive dynamic selections, command substitutions, unresolved variables, and other cases where the complete target set is not proven.

**Operator decision:** [] Approve  [x] Revise  [ ] Reject

## HR3-03 — Destructive `git clean`

**Implementation:** Active hard-block mapping.

Dry-run forms are not blocked. A forced non-dry-run `git clean` proves permanent-delete intent, but the command does not itself provide an exact safe quarantine target set.

**Hard-block condition:** A non-dry-run destructive `git clean` invocation is resolved.

**Result:** Reject with `HR-003_QUARANTINE_REQUIRED`; do not treat the repository root as the delete target.

**Evidence/tests:** `test_git_clean_and_reset_are_classified_by_exact_effect` and middleware Git-clean test.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR3-04 — Delete target outside `C:\Projects`

**Implementation:** Active hard block under HR-001 before quarantine.

Deleting an external directory entry is a write outside the approved boundary. External material is not moved into the local quarantine.

**Hard-block condition:** A resolved delete target is outside `C:\Projects`.

**Result:** Reject as `HR-001_WRITE_OUTSIDE_PROJECTS`.

**Evidence/tests:** policy external-delete tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR3-05 — Delete the `C:\Projects` boundary itself

**Implementation:** Active hard block.

The project boundary cannot be moved beneath a quarantine directory located inside itself.

**Hard-block condition:** The exact delete target is `C:\Projects`.

**Result:** Reject as `HR-003_QUARANTINE_FAILED`.

**Evidence/tests:** project-boundary quarantine tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

## HR3-06 — Safe quarantine cannot be completed

**Implementation:** Active hard block.

Permanent deletion is never forwarded as fallback.

**Hard-block condition:** A proven delete operation cannot be moved intact and recorded safely in quarantine.

**Result:** Reject as `HR-003_QUARANTINE_FAILED`.

**Evidence/tests:** quarantine failure and middleware failure tests.

**Recommended disposition:** Approve.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

---

## HR3-07 — Serena whole-memory-file deletion

**Implementation:** Approved conditionally; production activation requires pinned-contract completeness evidence.

At the candidate Serena `1.6.1` contract, `delete_memory` requests deletion of one complete memory artifact. Before activation, the adapter must prove the complete deleted artifact set, including any manifest, catalogue, metadata, index, or related state changed by the provider operation. The adapter resolves exact paths from the active project, memory name, configured Serena home, and configured project-data roots.

**Hard-rule condition:** `delete_memory` resolves one exact, complete, known artifact set inside `C:\Projects` and requests permanent removal of those artifacts.

**Result:** Move every proven artifact in the complete set intact through one transactional `QuarantineService.quarantine_many(...)` batch and record the returned restoration metadata. Do not call Serena's delete operation after quarantine. If any resolved target is outside `C:\Projects`, apply HR-001 and do not import it into quarantine. If the complete set cannot be proven exactly, aliases are ambiguous, traversal or wildcards are present, or safe quarantine cannot complete, return the applicable structural error or `HR-003_QUARANTINE_FAILED`; never forward permanent deletion as fallback.

**Global-memory condition:** Global Serena memory is covered only when its exact configured storage path is beneath `C:\Projects`. An outside global-memory artifact is rejected under HR-001 and is never moved into local quarantine.

**Not included:** `delete_lines`, `safe_delete_symbol`, `jet_brains_safe_delete`, replacements, and refactorings that alter content within a retained source file are content writes under HR-001, not whole-artifact deletion. A later pinned contract that deletes another complete file or directory requires a revised approved mapping before activation.

**Activation conditions:**

1. Pinned-contract evidence establishes the complete artifact set deleted or modified by `delete_memory`.
2. Tests cover all related metadata, index, catalogue, and consistency effects.
3. Serena's provider delete operation is never called after successful quarantine.
4. Resolution is exact and rejects wildcard, traversal, ambiguous aliases, and unknown artifact sets.
5. Quarantine, restore, and subsequent Serena behavior are tested for stale or regenerated metadata.

**Evidence/tests required before activation:** Exact `delete_memory` schema and source fixture; project and permitted global memory resolution; full artifact-set enumeration; traversal, wildcard, and alias rejection; no-provider-delete assertion; exact quarantine and restore; outside-boundary rejection; quarantine failure; post-quarantine readiness and stale-metadata behavior; counterexamples proving partial code deletion remains an ordinary content write.

**Reason approval is required:** This maps one provider-specific whole-artifact deletion to recoverable quarantine while requiring proof that skipping the provider operation does not leave an unknown deletion set or untested consistency effects.

**Recommended disposition:** Approve subject to the activation conditions above.

**Operator Comments:**

Approval is conditional on pinned-contract proof of the complete deleted artifact set, tests for metadata and index effects, no provider delete call after quarantine, and exact non-ambiguous path resolution.

**Operator decision:** [x] Approve  [ ] Revise  [ ] Reject

---

## Approval procedure

Review each active hard-block or quarantine entry in order:

1. confirm the complete concrete invocation proves the stated HR outcome;
2. confirm the decision is not based on category, name, possibility, or uncertainty;
3. confirm tests cover both blocked and permitted forms;
4. mark **Approve**, **Revise**, or **Reject**;
5. record any required narrowing before final approval.

No item is approved solely because tests pass. The operator decision is the approval record.
