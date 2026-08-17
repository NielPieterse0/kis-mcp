# Change Specification: VirtualBox Disposable Windows Provider

- **Change ID**: `180-virtualbox-disposable-windows-provider`
- **Status**: Approved for implementation by the operator's explicit `implement #324 virtualbox` instruction after the VirtualBox-first commissioning decision was recorded on issue #324.
- **Complexity**: Large
- **Develop-code level**: Complex
- **Risk triggers**: architecture boundary, deployment, persistent state, security

## Outcome

Add a VirtualBox-backed disposable Windows execution provider beneath the existing provider-neutral verification contract, preserving `local-process` and `windows-hyperv` as alternate providers. Establish a deterministic proof path and operator commissioning boundary without changing GitHub workflow routing.

## Authority and scope

- Repository authority: `AGENTS.md` → `docs/TRUST-MODEL.md` → `SPEC.md` → `docs/PLATFORM-CONCEPT.md` → policy/settings.
- Roadmap/work identity: GitHub issue `#324`, Work Management `SPEC-324`.
- Exact path ownership and exclusions: `scope.json`.
- The August 17 issue #324 commissioning decision is the approved provider-direction update: VirtualBox first; do not change Hyper-V/VBS/Memory Integrity during initial implementation.
- `.github/workflows/**` remains excluded.

## Requirements

- **REQ-001**: Add `windows-virtualbox` through the existing execution provider/profile/result contract without changing verification result semantics or Work hard rules.
- **REQ-002**: Keep all VirtualBox mutable global configuration, VM clone state, evidence, and attempt state within the configured KIS state root under `C:\Projects` by forcing an isolated `VBOX_USER_HOME`.
- **REQ-003**: Materialize only the exact requested Git revision as a bounded archive; do not mount/share the mutable host checkout, host KIS state, operator profile, or host credentials into the guest.
- **REQ-004**: Clone a KIS-owned Windows template snapshot into fresh per-attempt state, require its configuration and absolute host-backed media paths to remain inside the VirtualBox state root, disable all guest NICs plus clipboard/file-transfer/drag-and-drop before first start, and reject configured shared folders.
- **REQ-005**: Use Oracle Guest Additions guest control for bounded source injection and verification execution. Guest authentication uses a purpose-specific username plus a password-file path supplied by environment; the password itself must not be embedded in settings, receipts, or generated command text.
- **REQ-006**: Readiness must fail closed when `VBoxManage`, the KIS-owned VirtualBox home, template VM, clean snapshot, or required credential-file input is unavailable or inconsistent.
- **REQ-007**: Every lifecycle failure returns `incomplete` unless an executed verification explicitly returns `failed`; no missing guest result, startup timeout, source mismatch, or cleanup problem can return `passed`.
- **REQ-008**: Normal retirement is HR-003-compatible: power off, disconnect/disable networking, disable autostart, rename/retain the guest in quarantine, and persist bounded evidence. Automatic unregister/delete is prohibited.
- **REQ-009**: Generalize the internal disposable-verification proof service to the provider protocol so the same exact-source proof can exercise Hyper-V or VirtualBox without backend-specific verification semantics.
- **REQ-010**: Add a disabled-by-default `windows-virtualbox-proof` repository profile until host VirtualBox + KIS-owned template prerequisites are commissioned.
- **REQ-011**: Preserve Hyper-V implementation and document it as an alternate/future comparison path; do not enable/disable Hyper-V, VBS, Memory Integrity, Smart App Control, or Defender in this change.
- **REQ-012**: Record the real-work commissioning programme from issue #324 as post-implementation commissioning, not as synthetic unit-test evidence.

## Acceptance

1. Settings/schema tests accept a strict VirtualBox profile and reject state roots or password files outside the KIS boundary.
2. Provider tests prove lifecycle order: readiness → exact-source archive → isolated snapshot clone → pre-start isolation → start/Guest Additions readiness → copy → execute → capture → quarantine.
3. Tests prove `VBOX_USER_HOME`, clone base folder, receipt path, and password-file path remain bounded and no password value is serialized or placed in generated command text.
4. Tests prove configured shared folders, missing prerequisites, source mismatch, stale profile identity, repeated request IDs, guest-control failure, and cleanup failure fail closed.
5. Existing Hyper-V/local-process execution tests continue to pass.
6. One declared verification can be exercised by the provider-neutral proof service with both Hyper-V and VirtualBox fakes.
7. `scripts/change-workflow.ps1 check`, `git diff --check`, focused execution/verification tests, architecture/security review, and applicable repository verification pass on the final tree.
8. Live VirtualBox execution is reported only if this host has a compatible VirtualBox installation plus commissioned KIS template; absence of those prerequisites remains an explicit commissioning gate.

## Risks and recovery

- **Host virtualization compatibility**: Microsoft hypervisor/VBS may materially affect VirtualBox on this host. Measure during commissioning; do not change host security/virtualization configuration in this slice.
- **VirtualBox host writes**: default VirtualBox global state targets the user profile. Force `VBOX_USER_HOME` and clone storage into KIS state, and reject a template whose configuration file is outside that boundary.
- **Credential exposure**: guest-control requires guest authentication. Use a bounded password file referenced by environment and never log its contents.
- **Guest escape/host exposure**: disable NICs, shared clipboard, file transfers, drag-and-drop, VRDE, USB, and shared folders before guest start; source enters only through Guest Additions copy control.
- **Recovery**: disable the VirtualBox profile and retain quarantined guests/evidence; `local-process` and Hyper-V remain unchanged fallbacks.

## Out of scope

- Installing/upgrading Oracle VirtualBox or kernel drivers through Work; those host writes are outside `C:\Projects` and require a separate supervised operator action.
- Building the Windows golden image from scratch in this change.
- GitHub Actions runner registration, `actions/scaleset`, canonical workflow migration, or `.github/workflows/**` changes.
- `import-isolate` integration.
- Declaring commissioning complete before the real-work programme on issue #324 is executed.