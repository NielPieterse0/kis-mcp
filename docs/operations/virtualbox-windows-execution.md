# VirtualBox Disposable Windows Execution

## Status

`windows-virtualbox` is an implemented disposable execution backend beneath the provider-neutral KIS execution contract. The checked-in `windows-virtualbox-proof` profile remains disabled until host prerequisites, the KIS-owned template, credentials, and real-work commissioning are complete.

Implementation is not live commissioning. A missing or inconsistent prerequisite must return an unavailable/incomplete result; it must never be treated as a passing verification.

## Authority boundary

- Work hard rules remain HR-001, HR-002, and HR-003 only.
- VirtualBox host installation and driver changes write outside `C:\Projects`; perform them as a separate supervised operator action, not through KIS Work.
- Initial commissioning does not disable Hyper-V, VBS, Memory Integrity, Smart App Control, Defender, or equivalent host protections.
- Hyper-V remains an alternate disposable Windows provider behind the same request/result/readiness contract.
- GitHub Actions routing, runner registration, and scale-set integration are outside this provider slice.

## KIS-owned state

The repository profile uses:

```text
C:\Projects\.kis-mcp\execution\virtualbox\
├── vbox-home\       # VBOX_USER_HOME / VirtualBox.xml registry
├── requests\        # one immutable attempt directory per execution
├── evidence\        # bounded execution receipts
└── credentials\     # operator-created guest password file
```

Every provider `VBoxManage` invocation sets `VBOX_USER_HOME` to the configured `vbox-home`. Clone base folders are created inside the per-attempt request directory. Readiness validates both the current template with `showvminfo --machinereadable` and the exact named snapshot with `snapshot ... showvminfo`; it rejects missing/out-of-bound configuration, disk/ISO/storage paths, or configured shared folders before cloning.

## Host prerequisites

Before live commissioning:

1. Install a compatible Oracle VirtualBox 7.x release through a supervised host-administration path.
2. Confirm the configured `VBoxManage.exe` path exists.
3. Create the configured KIS VirtualBox state directories beneath `C:\Projects\.kis-mcp`.
4. Use the KIS `VBOX_USER_HOME` while creating/registering the template so the global VirtualBox registry is not written to the normal Windows user profile.
5. Keep the default machine/template folder beneath the same KIS VirtualBox state root.
6. Build/register `kis-windows-template` with a supported Windows guest, Oracle Guest Additions, and the repository-declared toolchain required by the intended verification profiles.
7. Remove all configured shared folders and leave the template powered off.
8. Create the powered-off `clean` snapshot used by the profile.
9. Create a purpose-specific guest account with the minimum rights needed to expand the injected source archive and execute declared verification commands.

Oracle VirtualBox supports relocating its global configuration with `VBOX_USER_HOME`; guest control supports password-file authentication, source copy, directory creation, and guest command execution. The provider uses those surfaces rather than host checkout mounts or plaintext password arguments.

## Credential input

Create the guest password file beneath:

```text
C:\Projects\.kis-mcp\execution\virtualbox\credentials\
```
Set only the file path and guest username in process-scoped environment variables:

```powershell
$env:KIS_VIRTUALBOX_GUEST_USERNAME = 'kis-runner'
$env:KIS_VIRTUALBOX_GUEST_PASSWORD_FILE = 'C:\Projects\.kis-mcp\execution\virtualbox\credentials\guest-password.txt'
```

The configured password file must be an absolute path inside the provider state root and must exist before readiness can pass. The password value is not stored in repository settings, generated commands, diagnostics, or receipts.

## Per-attempt lifecycle

For an exact-source request the provider performs:

1. readiness: credentials, `VBoxManage`, KIS-owned template configuration, no shared folders, and `clean` snapshot;
2. exact Git commit resolution and archive creation on the host;
3. snapshot clone into a fresh per-attempt base folder;
4. pre-start isolation: all eight NIC slots set to `none`, clipboard disabled, clipboard file transfer disabled, drag-and-drop disabled, VRDE off, autostart off, and USB controllers off;
5. headless guest start and Guest Additions `userland` readiness;
6. guest workspace creation and archive injection with `guestcontrol copyto`;
7. declared verification execution through `guestcontrol run` using password-file authentication;
8. bounded result/evidence capture;
9. power-off and recoverable quarantine rename with isolation settings reapplied.

Normal retirement does not call `unregistervm --delete` and does not delete the VM directory. Retained guests remain available for supervised diagnosis or later HR-003-compatible retirement.

## Commissioning sequence

Commission in increasing risk order. Do not enable the repository profile merely because unit tests pass.

1. **Host readiness** — confirm VirtualBox installation/version and that normal KIS commands still run without application-control regression.
2. **Template readiness** — prove the template registry/configuration and snapshot are entirely beneath the KIS state boundary and contain no shared folders.
3. **Synthetic proof** — run one exact-source declared verification through the VirtualBox provider and inspect its receipt plus quarantined guest.
4. **Repeat proof** — rerun the same request ID and prove a fresh attempt directory, fresh clone, deterministic source identity, bounded evidence, and no state leakage from the first guest.
5. **Failure proof** — exercise source mismatch, guest execution failure, timeout/incomplete execution, and quarantine failure paths. None may return `passed`.
6. **Performance observation** — record clone/start/transfer/execute/quarantine timing and observe whether the current Windows hypervisor/VBS configuration materially affects correctness or acceptable throughput.
7. **Real-work programme** — execute the issue #324 commissioning workloads below before declaring the substrate commissioned.

## Required real-work programme

Commissioning must include all of the following:

- drive the critical KIS parallel-agent backlog through the substrate, including isolation, reconciliation, lifecycle/restart, timeout, concurrency, and observability work where still applicable;
- complete one Small, one Medium, and one Large governed `kis-mcp` change through the normal KIS lifecycle using the disposable Windows path where the declared verification is compatible;
- complete one or two real governed changes in at least one registered external product/tool-user repository;
- repeat representative work to prove deterministic retry/resume and absence of cross-attempt state contamination.

Synthetic tests are prerequisite evidence only; they do not replace these real-work commissioning cases.

## Commissioning gates

Do not mark VirtualBox production-ready until evidence proves:

- every run starts from the clean versioned template snapshot and exact requested source revision;
- host checkout, `.work`, central KIS state, operator profile, host credentials, and arbitrary host paths are not mounted into the guest;
- VirtualBox global state and VM clone state remain beneath `C:\Projects\.kis-mcp\execution\virtualbox`;
- the guest has no configured shared folders and all network adapters remain disconnected/disabled for the proof workload;
- clipboard, file-transfer clipboard, drag-and-drop, VRDE, USB integration, and autostart remain disabled;
- password values do not appear in settings, process commands, diagnostics, receipts, or Git-visible files;
- receipts are bounded and bind request, source, image, toolchain, lifecycle, cleanup, and failure classification;
- repeat/retry attempts allocate fresh state and do not reuse a prior mutable guest;
- normal retirement remains recoverable and no automatic VM deletion path is introduced;
- host security controls remain enabled unless a later separate operator decision explicitly changes them.

## Hyper-V revisit point

Keep the Hyper-V provider and follow-up work available for comparison. Revisit Hyper-V/VBS coexistence only if VirtualBox commissioning evidence shows a correctness, compatibility, or material performance reason to do so. That decision is separate from this provider implementation and must not be inferred from VirtualBox availability.
