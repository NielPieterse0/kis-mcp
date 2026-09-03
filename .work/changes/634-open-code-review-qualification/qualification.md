# Open Code Review Qualification Evidence

Issue: #534
Change: `634-open-code-review-qualification`
Decision: **Not adopted**

## Decision boundary

This result rejects OCR integration under the current commissioned KIS environment. It does **not** claim that OCR has poor review quality. OCR never reached a successful review invocation, so comparative finding-quality and reviewer-discourse metrics are explicitly `not_measurable`.

No follow-up adapter issue is warranted because the mandatory hermetic execution prerequisite failed before OCR could provide incremental validated evidence.

## Pinned source identity

| Item | Exact identity |
| --- | --- |
| OCR npm package | `@alibaba-group/open-code-review@1.11.2` |
| Package integrity | `sha512-CdNWXg5FKpPlbPRMVQ6lwiOFpY683/02CDa3FOUeKQhYx2xxSIkh0Y0kX2b0v7qYF+ReaWhdgF2FDZjkxkFQ2Q==` |
| Windows x64 payload | `@alibaba-group/ocr-win32-x64@1.11.2` |
| Payload integrity | `sha512-lM68rf/hYmN343FqsLMQcpTGYx9+UO0jz+PA5BsLjHTkkjDEfNAKRa/hqV8nbn+aUl9gO3EF6+W2NCdpDbzUQQ==` |

The exact package and Windows payload were already present in the configured local npm cache. The qualification installed them offline into disposable state with lifecycle scripts disabled; no package download was required.

## Hermetic runtime evidence

1. `npm view --offline` confirmed the exact package version, `ocr` launcher, and integrity.
2. `npm pack --offline` reproduced the exact OCR package from cache and exposed its launcher/install contract.
3. The package installer would otherwise fetch a native release and checksum from GitHub; this path was not granted unrestricted network authority.
4. The exact Windows payload was installed explicitly from cache with `--offline --ignore-scripts`.
5. Windows Application Control blocked `opencodereview.exe` before `ocr version` could execute, both inside the isolated worktree and from central KIS temporary state.
6. WSL2 is present, but the Linux x64 OCR payload is not present in the approved local npm cache; `npm pack --offline @alibaba-group/ocr-linux-x64@1.11.2` failed `ENOTCACHED`.

## Containment evidence

- No `ocr init` was run.
- No OCR-managed `AGENTS.md`, skills, commands, repository config, commits, branches, PR comments, or fixes were created.
- No GitHub credential or OCR LLM credential was exposed to the OCR process.
- The configured KIS GitHub provider correctly rejected direct access to `alibaba/open-code-review`; its repository scope was not widened.
- The failed probes did not change any product, policy, settings, workflow, or authority path.

An initial focused `uv` invocation created a worktree-local `.venv`; it was moved recoverably to `C:\Projects\.kis-mcp\quarantine\634-accidental-worktree-venv-20260903` and is not repository state.

## Historical corpus selected before execution

The corpus was selected from repository-owned historical evidence before OCR review execution. The listed revisions identify the evidence used to classify each case; because the OCR runtime preflight failed globally, none is represented as an executed OCR review source.

| Case | Historical evidence revision | Basis |
| --- | --- | --- |
| Security | `8c3f9bee0ff8723a3334b8bf46bc2fa1699eca99` | Change 218 safety/security and API-contract boundary |
| Architecture | `d3f9647452faf877e843637b06ed73c221e7fef2` | Change 120 records two resolved architecture findings |
| API/contract | `61aaacf56b3290595c25d2d5fb99cc221aded9a8` | Change 249 records two resolved public-contract findings |
| Test quality | `01e56e4700ea4c9565f4c549a8f3d1045801f583` | Change 145 records review-driven boundary regression correction |
| Documentation/authority | `145052fb1fefd15bd5b2fb53babaccdfcee69916` | Change 110 records three corrected documentation authority findings |
| Clean | `2f353fb07a4eee1924368c7f9085c97bb9fb4ea7` | Change 211 records zero findings from independent code/security reviews |
| Large change | `d3f9647452faf877e843637b06ed73c221e7fef2` | Change 120 is a cross-cutting queue/Work Management change |

## Benchmark disposition

| Requested metric | Result |
| --- | --- |
| Validated true OCR findings | Not measurable; 0 successful OCR review runs |
| Known historical defects recovered | Not measurable |
| False positives / unsupported findings | Not measurable |
| Unique useful findings beyond KIS | Not measurable |
| Critical/high misses | Not measurable |
| Duration / provider-token cost | Review phase not entered; no OCR LLM/provider call |
| Human triage cost | Review phase not entered |
| Large-change coverage | Not measurable |
| OCR discourse vs equivalent independent reviewers | Not measurable; OCR agent never executed |

`benchmark-input.json` and `benchmark-result.json` preserve this state machine-readably. The decision helper rejects unpinned versions and rejects fabricated successful-review metrics when the runtime is blocked.

## Adoption decision

**Not adopted.** A native or advisory KIS adapter would require a runnable, pinned, contained OCR executable before incremental reviewer value could exist operationally. The commissioned Windows controls reject the exact pinned native payload, and the approved offline fallback lacks the Linux payload. Changing Application Control, widening external acquisition/network authority, or provisioning a new runtime solely to make OCR benchmarkable would add integration cost before any incremental finding value is demonstrated.

Issue #534 therefore closes at the qualification prerequisite gate. A future requalification is appropriate only if a commissioned environment can execute a pinned OCR payload without authority changes; that future work must rerun the full comparative corpus rather than inheriting any quality claim from this result.

## Sources and limitations

- Repository authority/evidence: `AGENTS.md` and the historical change closeouts named above.
- Package provenance: exact local npm-cache metadata/package contents for OCR `1.11.2` and the Windows x64 payload.
- External project documentation was used only to understand OCR's documented delegation/runtime contract; no external repository mutation or credentialed integration occurred.
- This qualification makes no claim about OCR performance on another OS, under a different Application Control policy, or with its own configured LLM provider.
- No product behavior changes are included in Change 634.
