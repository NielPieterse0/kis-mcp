from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path, PureWindowsPath
from typing import Any

from .contracts import (
    CleanupDisposition,
    ExecutionEvidence,
    ExecutionLifecycleState,
    ExecutionReadiness,
    ExecutionRequest,
    ExecutionResult,
    ReadinessStatus,
)
from .process import Runner, ProcessOutcome, clean_process_text, run_nested_process
from .settings import HyperVProfileSettings, RunnerProfileSettings

_GUEST_RESULT = re.compile(r"(?m)^__KIS_GUEST_RESULT=(\{.*\})\s*$")


class HyperVDisposableExecutionProvider:
    backend_id = "windows-hyperv"

    def __init__(
        self,
        runner: Runner,
        settings: HyperVProfileSettings,
        *,
        profile_id: str,
        image_id: str,
        toolchain_id: str,
    ) -> None:
        self._runner = runner
        self._settings = settings
        self._profile_id = profile_id
        self._image_id = image_id
        self._toolchain_id = toolchain_id

    @classmethod
    def from_profile(
        cls,
        runner: Runner,
        profile: RunnerProfileSettings,
    ) -> "HyperVDisposableExecutionProvider":
        if profile.backend_id != cls.backend_id or profile.hyperv is None:
            raise ValueError("runner profile is not a Hyper-V disposable execution profile")
        return cls(
            runner,
            profile.hyperv,
            profile_id=profile.profile_id,
            image_id=profile.image_id,
            toolchain_id=profile.toolchain_id,
        )

    async def readiness(self) -> ExecutionReadiness:
        outcome = await self._phase(
            self._readiness_script(),
            timeout_ms=self._settings.startup_timeout_ms,
        )
        diagnostic = _diagnostic("readiness", outcome)
        if outcome.exit_code == 0:
            return ExecutionReadiness(
                backend_id=self.backend_id,
                status=ReadinessStatus.READY,
                reason="Hyper-V host commands and configured template checkpoint are available",
                diagnostics=(diagnostic,),
            )
        return ExecutionReadiness(
            backend_id=self.backend_id,
            status=ReadinessStatus.UNAVAILABLE,
            reason="Hyper-V host prerequisites or configured template checkpoint are unavailable",
            diagnostics=(diagnostic,),
        )

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if (
            request.profile.backend_id != self.backend_id
            or request.profile.profile_id != self._profile_id
            or request.profile.image_id != self._image_id
            or request.profile.toolchain_id != self._toolchain_id
        ):
            return self._result(
                request,
                status="incomplete",
                failure="profile_identity_mismatch",
                cleanup=CleanupDisposition.NOT_REQUIRED,
                lifecycle=(ExecutionLifecycleState.REQUESTED, ExecutionLifecycleState.INCOMPLETE),
            )
        if not request.source.exact:
            return self._result(
                request,
                status="incomplete",
                failure="source_identity_required",
                cleanup=CleanupDisposition.NOT_REQUIRED,
                lifecycle=(ExecutionLifecycleState.REQUESTED, ExecutionLifecycleState.INCOMPLETE),
            )
        started = time.perf_counter()
        state_root = Path(self._settings.state_root)
        evidence_root = state_root / "evidence"
        lifecycle = [ExecutionLifecycleState.REQUESTED, ExecutionLifecycleState.READINESS]
        availability = await self.readiness()
        diagnostics: list[str] = list(availability.diagnostics)
        if availability.status is ReadinessStatus.UNAVAILABLE:
            lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
            return self._result(
                request,
                status="incomplete",
                failure="backend_unavailable",
                cleanup=CleanupDisposition.NOT_REQUIRED,
                duration_ms=_elapsed_ms(started),
                diagnostics=tuple(diagnostics),
                lifecycle=tuple(lifecycle),
            )

        try:
            request_root, attempt_number, request_key = _allocate_attempt_root(
                state_root, request.request_id
            )
            evidence_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
            diagnostics.append(f"host-state-exception: {type(exc).__name__}: {exc}")
            return self._result(
                request,
                status="incomplete",
                failure="lifecycle_failed",
                cleanup=CleanupDisposition.NOT_REQUIRED,
                duration_ms=_elapsed_ms(started),
                diagnostics=tuple(diagnostics),
                lifecycle=tuple(lifecycle),
            )

        vm_name = f"kis-{request_key}-{attempt_number:06d}"
        archive = request_root / "source.zip"
        guest_stdout = ""
        guest_stderr = ""
        guest_exit: int | None = None
        status = "incomplete"
        failure = "lifecycle_failed"
        cleanup = CleanupDisposition.NOT_REQUIRED
        transferred_bytes: int | None = None
        stdout_truncated = False
        stderr_truncated = False
        receipt_path = evidence_root / f"{request_key}-{attempt_number:06d}.json"
        lifecycle_started = True

        try:
            lifecycle.append(ExecutionLifecycleState.MATERIALIZING)
            materialize = await self._phase(
                self._materialize_script(request, archive),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("materialize-source", materialize))
            if materialize.exit_code != 0:
                failure = (
                    "source_mismatch"
                    if "KIS_SOURCE_MISMATCH" in materialize.text
                    else "lifecycle_failed"
                )
                raise _LifecycleStop
            if archive.exists():
                transferred_bytes = archive.stat().st_size

            lifecycle.append(ExecutionLifecycleState.PROVISIONING)
            clone = await self._phase(
                self._clone_script(vm_name, request_root),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("clone-checkpoint", clone))
            if clone.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.STARTING)
            start = await self._phase(
                self._start_script(vm_name),
                timeout_ms=min(request.timeout_ms, self._settings.startup_timeout_ms),
            )
            diagnostics.append(_diagnostic("start-guest", start))
            if start.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.TRANSFERRING)
            inject = await self._phase(
                self._inject_script(vm_name, archive),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("inject-source", inject))
            if inject.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.EXECUTING)
            execute = await self._phase(
                self._guest_execute_script(vm_name, request),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("execute-guest", execute))
            if execute.exit_code != 0:
                raise _LifecycleStop
            guest = _guest_result(execute.text)
            if guest is None:
                failure = "timeout_or_incomplete"
                raise _LifecycleStop
            guest_exit = guest["exit_code"]
            guest_stdout, stdout_truncated = _bound_text(
                guest["stdout"], request.evidence_limit_chars
            )
            guest_stderr, stderr_truncated = _bound_text(
                guest["stderr"], request.evidence_limit_chars
            )
            status = "passed" if guest_exit == 0 else "failed"
            failure = "none" if guest_exit == 0 else "execution_failed"
            lifecycle.append(ExecutionLifecycleState.CAPTURING)
            self._write_receipt(
                receipt_path,
                request=request,
                status=status,
                exit_code=guest_exit,
                stdout=guest_stdout,
                stderr=guest_stderr,
                diagnostics=tuple(diagnostics),
                duration_ms=_elapsed_ms(started),
                transferred_bytes=transferred_bytes,
                captured_before_cleanup=True,
                lifecycle=tuple(lifecycle),
            )
        except _LifecycleStop:
            lifecycle.append(ExecutionLifecycleState.CAPTURING)
            self._write_receipt(
                receipt_path,
                request=request,
                status=status,
                exit_code=guest_exit,
                stdout=guest_stdout,
                stderr=guest_stderr,
                diagnostics=tuple(diagnostics),
                duration_ms=_elapsed_ms(started),
                transferred_bytes=transferred_bytes,
                captured_before_cleanup=True,
                failure=failure,
                lifecycle=tuple(lifecycle),
            )
        except Exception as exc:
            status = "incomplete"
            failure = "lifecycle_failed"
            lifecycle.append(ExecutionLifecycleState.CAPTURING)
            diagnostics.append(f"lifecycle-exception: {type(exc).__name__}: {exc}")
        finally:
            if lifecycle_started:
                lifecycle.append(ExecutionLifecycleState.CLEANING)
                try:
                    cleanup_outcome = await self._phase(
                        self._cleanup_script(vm_name, request_root),
                        timeout_ms=self._settings.cleanup_timeout_ms,
                    )
                    diagnostics.append(_diagnostic("cleanup", cleanup_outcome))
                except Exception as exc:
                    cleanup_outcome = None
                    diagnostics.append(f"cleanup-exception: {type(exc).__name__}: {exc}")
                cleanup_failed = cleanup_outcome is None or cleanup_outcome.exit_code != 0
                if not cleanup_failed:
                    cleanup = CleanupDisposition.QUARANTINED
                else:
                    try:
                        quarantine = await self._phase(
                            self._quarantine_script(vm_name, request_root),
                            timeout_ms=self._settings.cleanup_timeout_ms,
                        )
                        diagnostics.append(_diagnostic("quarantine", quarantine))
                    except Exception as exc:
                        quarantine = None
                        diagnostics.append(f"quarantine-exception: {type(exc).__name__}: {exc}")
                    cleanup = (
                        CleanupDisposition.QUARANTINED
                        if quarantine is not None and quarantine.exit_code == 0
                        else CleanupDisposition.FAILED
                    )
                    status = "incomplete"
                    failure = "cleanup_failed"
                if cleanup is CleanupDisposition.QUARANTINED:
                    lifecycle.append(ExecutionLifecycleState.QUARANTINED)
                    lifecycle.append(
                        ExecutionLifecycleState.INCOMPLETE
                        if cleanup_failed or status == "incomplete"
                        else ExecutionLifecycleState.COMPLETED
                    )
                else:
                    lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
        truncated = stdout_truncated or stderr_truncated
        self._write_receipt(
            receipt_path,
            request=request,
            status=status,
            exit_code=guest_exit,
            stdout=guest_stdout,
            stderr=guest_stderr,
            diagnostics=tuple(diagnostics),
            duration_ms=_elapsed_ms(started),
            transferred_bytes=transferred_bytes,
            captured_before_cleanup=True,
            cleanup=cleanup.value,
            failure=failure,
            lifecycle=tuple(lifecycle),
        )
        return self._result(
            request,
            status=status,
            failure=failure,
            cleanup=cleanup,
            exit_code=guest_exit,
            duration_ms=_elapsed_ms(started),
            stdout=guest_stdout,
            stderr=guest_stderr,
            diagnostics=tuple(diagnostics),
            truncated=truncated,
            receipt_path=str(receipt_path),
            transferred_bytes=transferred_bytes,
            lifecycle=tuple(lifecycle),
        )

    async def _phase(self, body: str, *, timeout_ms: int) -> ProcessOutcome:
        return await run_nested_process(
            self._runner,
            command=_with_terminal_receipt(body),
            timeout_ms=timeout_ms,
        )

    def _result(
        self,
        request: ExecutionRequest,
        *,
        status: str,
        failure: str,
        cleanup: CleanupDisposition,
        exit_code: int | None = None,
        duration_ms: int = 0,
        stdout: str = "",
        stderr: str = "",
        diagnostics: tuple[str, ...] = (),
        truncated: bool = False,
        receipt_path: str | None = None,
        transferred_bytes: int | None = None,
        lifecycle: tuple[ExecutionLifecycleState, ...] = (),
    ) -> ExecutionResult:
        return ExecutionResult(
            request_id=request.request_id,
            backend_id=self.backend_id,
            status=status,
            exit_code=exit_code,
            duration_ms=duration_ms,
            source_revision=request.source.revision,
            image_id=self._image_id,
            toolchain_id=self._toolchain_id,
            cleanup=cleanup,
            evidence=ExecutionEvidence(
                stdout=stdout,
                stderr=stderr,
                diagnostics=diagnostics,
                truncated=truncated,
                receipt_path=receipt_path,
                transferred_bytes=transferred_bytes,
            ),
            failure_classification=failure,
            lifecycle=lifecycle,
        )

    def _readiness_script(self) -> str:
        required = (
            "Get-VMHost",
            "Get-VMSnapshot",
            "Export-VMSnapshot",
            "Import-VM",
            "Rename-VM",
            "Start-VM",
            "Stop-VM",
            "Set-VM",
            "Get-VMNetworkAdapter",
            "Disconnect-VMNetworkAdapter",
            "Copy-VMFile",
            "Invoke-Command",
        )
        names = ",".join(_ps_quote(item) for item in required)
        return (
            f"$required=@({names}); "
            "foreach($name in $required){Get-Command -Name $name -ErrorAction Stop | Out-Null}; "
            "Get-VMHost -ErrorAction Stop | Out-Null; "
            f"Get-VMSnapshot -VMName {_ps_quote(self._settings.template_vm)} "
            f"-Name {_ps_quote(self._settings.checkpoint_name)} -ErrorAction Stop | Out-Null"
        )

    def _materialize_script(self, request: ExecutionRequest, archive: Path) -> str:
        return (
            f"$project={_ps_quote(request.source.project_path)}; "
            f"$revision={_ps_quote(request.source.revision)}; "
            f"$archive={_ps_quote(str(archive))}; "
            "$actual=(& git -C $project rev-parse ($revision + '^{commit}')).Trim(); "
            "if($LASTEXITCODE -ne 0 -or $actual -ne $revision){"
            "Write-Output ('KIS_SOURCE_MISMATCH expected=' + $revision + ' actual=' + $actual); "
            "throw 'exact source identity mismatch'}; "
            "New-Item -ItemType Directory -Force -Path (Split-Path -Parent $archive) | Out-Null; "
            "& git -C $project archive --format=zip --output=$archive $revision; "
            "if($LASTEXITCODE -ne 0){throw 'git archive failed'}"
        )

    def _clone_script(self, vm_name: str, request_root: Path) -> str:
        export_root = request_root / "export"
        vm_root = request_root / "vm"
        vhd_root = request_root / "vhd"
        return (
            f"$exportRoot={_ps_quote(str(export_root))}; "
            f"$vmRoot={_ps_quote(str(vm_root))}; "
            f"$vhdRoot={_ps_quote(str(vhd_root))}; "
            "New-Item -ItemType Directory -Force -Path $exportRoot,$vmRoot,$vhdRoot | Out-Null; "
            f"$snapshot=Get-VMSnapshot -VMName {_ps_quote(self._settings.template_vm)} "
            f"-Name {_ps_quote(self._settings.checkpoint_name)} -ErrorAction Stop; "
            "Export-VMSnapshot -VMSnapshot $snapshot -Path $exportRoot -ErrorAction Stop; "
            "$vmcx=Get-ChildItem -Path $exportRoot -Filter '*.vmcx' -Recurse | Select-Object -First 1; "
            "if($null -eq $vmcx){throw 'exported checkpoint contains no vmcx'}; "
            "$vm=Import-VM -Path $vmcx.FullName -Copy -GenerateNewId "
            "-VirtualMachinePath $vmRoot -VhdDestinationPath $vhdRoot -ErrorAction Stop; "
            f"Rename-VM -VM $vm -NewName {_ps_quote(vm_name)} -ErrorAction Stop; "
            "$guestAdapters=@(Get-VMNetworkAdapter -VM $vm -ErrorAction Stop); "
            "if($guestAdapters.Count -gt 0){$guestAdapters | Disconnect-VMNetworkAdapter -ErrorAction Stop}"
        )

    def _start_script(self, vm_name: str) -> str:
        return f"Start-VM -Name {_ps_quote(vm_name)} -ErrorAction Stop | Out-Null"

    def _inject_script(self, vm_name: str, archive: Path) -> str:
        guest_archive = str(PureWindowsPath(self._settings.guest_workspace) / "source.zip")
        return (
            f"Copy-VMFile -Name {_ps_quote(vm_name)} "
            f"-SourcePath {_ps_quote(str(archive))} "
            f"-DestinationPath {_ps_quote(guest_archive)} "
            "-FileSource Host -CreateFullPath -Force -ErrorAction Stop"
        )

    def _guest_execute_script(self, vm_name: str, request: ExecutionRequest) -> str:
        arguments_json = json.dumps(
            list(request.arguments), ensure_ascii=True, separators=(",", ":")
        )
        workspace = self._settings.guest_workspace
        archive = str(PureWindowsPath(workspace) / "source.zip")
        return (
            f"$user=$env:{self._settings.guest_username_env}; "
            f"$password=$env:{self._settings.guest_password_env}; "
            "if([string]::IsNullOrWhiteSpace($user) -or [string]::IsNullOrWhiteSpace($password)){"
            "throw 'Hyper-V guest credential environment is incomplete'}; "
            "$secure=ConvertTo-SecureString $password -AsPlainText -Force; "
            "$credential=[pscredential]::new($user,$secure); "
            f"$payload=Invoke-Command -VMName {_ps_quote(vm_name)} -Credential $credential "
            "-ScriptBlock { param($workspace,$archive,$exe,$argumentsJson) "
            "$argv=@(ConvertFrom-Json -InputObject $argumentsJson); "
            "Expand-Archive -LiteralPath $archive -DestinationPath $workspace -Force; "
            "Set-Location -LiteralPath $workspace; "
            "$output=(& $exe @argv 2>&1 | Out-String); "
            "$code=$LASTEXITCODE; "
            "[pscustomobject]@{exit_code=$code;stdout=$output;stderr=''} | ConvertTo-Json -Compress "
            f"}} -ArgumentList {_ps_quote(workspace)},{_ps_quote(archive)},{_ps_quote(request.executable)},{_ps_quote(arguments_json)} "
            "-ErrorAction Stop; "
            "Write-Output ('__KIS_GUEST_RESULT=' + $payload)"
        )

    def _cleanup_script(self, vm_name: str, request_root: Path) -> str:
        marker = request_root / "KIS_RETIRED.txt"
        return (
            f"$vm=Get-VM -Name {_ps_quote(vm_name)} -ErrorAction SilentlyContinue; "
            "if($null -ne $vm){"
            "if($vm.State -ne 'Off'){Stop-VM -VM $vm -TurnOff -Force -ErrorAction Stop}; "
            "Set-VM -VM $vm -AutomaticStartAction Nothing -ErrorAction Stop; "
            "$adapters=@(Get-VMNetworkAdapter -VM $vm -ErrorAction Stop); "
            "if($adapters.Count -gt 0){$adapters | Disconnect-VMNetworkAdapter -ErrorAction Stop}; "
            "Rename-VM -VM $vm -NewName ('kis-quarantine-' + $vm.Id.Guid) -ErrorAction Stop}; "
            f"New-Item -ItemType Directory -Force -Path {_ps_quote(str(request_root))} | Out-Null; "
            f"Set-Content -LiteralPath {_ps_quote(str(marker))} "
            "-Value 'KIS_RETIRED: stopped, network-disconnected, non-autostart guest retained for recoverable operator cleanup' -Encoding UTF8"
        )

    def _quarantine_script(self, vm_name: str, request_root: Path) -> str:
        marker = request_root / "KIS_QUARANTINED.txt"
        return (
            f"$vm=Get-VM -Name {_ps_quote(vm_name)} -ErrorAction SilentlyContinue; "
            "if($null -ne $vm -and $vm.State -ne 'Off'){"
            "Stop-VM -VM $vm -TurnOff -Force -ErrorAction Stop}; "
            f"New-Item -ItemType Directory -Force -Path {_ps_quote(str(request_root))} | Out-Null; "
            f"Set-Content -LiteralPath {_ps_quote(str(marker))} "
            "-Value 'KIS_QUARANTINED: cleanup failed; manual inspection required' -Encoding UTF8"
        )

    def _write_receipt(
        self,
        path: Path,
        *,
        request: ExecutionRequest,
        status: str,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        diagnostics: tuple[str, ...],
        duration_ms: int,
        transferred_bytes: int | None,
        captured_before_cleanup: bool,
        cleanup: str | None = None,
        failure: str | None = None,
        lifecycle: tuple[ExecutionLifecycleState, ...] = (),
    ) -> None:
        payload = {
            "schema_version": 1,
            "contract": "hyperv-execution-receipt-v1",
            "request_id": request.request_id,
            "project_id": request.project_id,
            "source_revision": request.source.revision,
            "image_id": self._image_id,
            "toolchain_id": self._toolchain_id,
            "status": status,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout": stdout,
            "stderr": stderr,
            "diagnostics": list(diagnostics),
            "transferred_bytes": transferred_bytes,
            "captured_before_cleanup": captured_before_cleanup,
            "cleanup": cleanup,
            "failure_classification": failure,
            "lifecycle": [state.value for state in lifecycle],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )


class _LifecycleStop(Exception):
    pass


def _with_terminal_receipt(body: str) -> str:
    return (
        "$ErrorActionPreference='Stop'; $kisCode=0; try { "
        + body
        + " } catch { Write-Output ('KIS_PHASE_ERROR=' + $_.Exception.Message); $kisCode=1 }; "
        + 'Write-Output "__KIS_EXECUTION_EXIT_CODE=$kisCode"; exit $kisCode'
    )


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _allocate_attempt_root(state_root: Path, request_id: str) -> tuple[Path, int, str]:
    request_key = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:20]
    namespace = state_root / "requests" / request_key
    namespace.mkdir(parents=True, exist_ok=True)
    for attempt_number in range(1, 1_000_000):
        attempt_root = namespace / f"{attempt_number:06d}"
        try:
            attempt_root.mkdir()
        except FileExistsError:
            continue
        return attempt_root, attempt_number, request_key
    raise RuntimeError("execution attempt namespace is exhausted")


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _diagnostic(phase: str, outcome: ProcessOutcome) -> str:
    text, truncated = clean_process_text(outcome.text, 2000)
    suffix = " [truncated]" if truncated else ""
    return f"{phase}: exit={outcome.exit_code}; {text}{suffix}".strip()


def _guest_result(text: str) -> dict[str, Any] | None:
    matches = _GUEST_RESULT.findall(text)
    if not matches:
        return None
    try:
        payload = json.loads(matches[-1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    exit_code = payload.get("exit_code")
    stdout = payload.get("stdout")
    stderr = payload.get("stderr")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return None
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        return None
    return {"exit_code": exit_code, "stdout": stdout.strip(), "stderr": stderr.strip()}


def _bound_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    head = max_chars // 2
    tail = max_chars - head
    return (
        f"{text[:head]}\n... [execution evidence truncated] ...\n{text[-tail:]}",
        True,
    )


__all__ = ["HyperVDisposableExecutionProvider"]
