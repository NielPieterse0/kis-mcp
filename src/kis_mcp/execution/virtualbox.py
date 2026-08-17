from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path, PureWindowsPath
from typing import Any

from ..paths import is_within_windows_boundary
from .contracts import (
    CleanupDisposition,
    ExecutionEvidence,
    ExecutionLifecycleState,
    ExecutionReadiness,
    ExecutionRequest,
    ExecutionResult,
    ReadinessStatus,
)
from .process import ProcessOutcome, Runner, clean_process_text, run_nested_process
from .settings import RunnerProfileSettings, VirtualBoxProfileSettings

_GUEST_RESULT = re.compile(r"(?m)^__KIS_GUEST_RESULT=(\{.*\})\s*$")
_MACHINE_INFO = re.compile(r'(?m)^([^=]+)="(.*)"\s*$')
_SHARED_FOLDER = re.compile(r"(?mi)^SharedFolder(?:Name|Path)[^=]*=")
_SNAPSHOT_CONFIG = re.compile(r"(?mi)^Config file:\s*(.+?)\s*$")
_SNAPSHOT_FIXED_PATH = re.compile(
    r"(?mi)^(?:Config file|Snapshot folder|Log folder):\s*(.+?)\s*$"
)
_SNAPSHOT_STORAGE = re.compile(r"(?mi)^.+?\(\d+,\s*\d+\):\s*(.+?)\s*$")
_SNAPSHOT_SHARED_FOLDER = re.compile(r"(?mi)\bHost path:\s*['\"]?.+")


class VirtualBoxDisposableExecutionProvider:
    backend_id = "windows-virtualbox"

    def __init__(
        self,
        runner: Runner,
        settings: VirtualBoxProfileSettings,
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
        cls, runner: Runner, profile: RunnerProfileSettings
    ) -> "VirtualBoxDisposableExecutionProvider":
        if profile.backend_id != cls.backend_id or profile.virtualbox is None:
            raise ValueError("runner profile is not a VirtualBox disposable execution profile")
        return cls(
            runner,
            profile.virtualbox,
            profile_id=profile.profile_id,
            image_id=profile.image_id,
            toolchain_id=profile.toolchain_id,
        )

    async def readiness(self) -> ExecutionReadiness:
        credentials, credential_error = self._credentials()
        if credential_error is not None:
            return ExecutionReadiness(
                backend_id=self.backend_id,
                status=ReadinessStatus.UNAVAILABLE,
                reason="VirtualBox guest credential input is unavailable or unsafe",
                diagnostics=(credential_error,),
            )
        assert credentials is not None
        diagnostics: list[str] = []
        version = await self._vbox(
            ("--version",), timeout_ms=self._settings.startup_timeout_ms
        )
        diagnostics.append(_diagnostic("virtualbox-version", version))
        if version.exit_code != 0:
            return self._unavailable(
                "VBoxManage is unavailable", tuple(diagnostics)
            )
        info = await self._vbox(
            ("showvminfo", self._settings.template_vm, "--machinereadable"),
            timeout_ms=self._settings.startup_timeout_ms,
        )
        diagnostics.append(_diagnostic("template-info", info))
        if info.exit_code != 0:
            return self._unavailable(
                "VirtualBox template VM is unavailable", tuple(diagnostics)
            )
        config_path = _machine_info_value(info.text, "CfgFile")
        if config_path is None or not is_within_windows_boundary(
            config_path, boundary=self._settings.state_root
        ):
            diagnostics.append("template configuration is outside the KIS VirtualBox state root")
            return self._unavailable(
                "VirtualBox template VM is not KIS-owned", tuple(diagnostics)
            )
        if _template_has_external_host_path(
            info.text, boundary=self._settings.state_root
        ):
            diagnostics.append("template references a host path outside the KIS VirtualBox state root")
            return self._unavailable(
                "VirtualBox template storage is not KIS-owned", tuple(diagnostics)
            )
        if _SHARED_FOLDER.search(info.text) is not None:
            diagnostics.append("template has configured shared folders")
            return self._unavailable(
                "VirtualBox template exposes host shared folders", tuple(diagnostics)
            )
        snapshot = await self._vbox(
            (
                "snapshot",
                self._settings.template_vm,
                "showvminfo",
                self._settings.snapshot_name,
            ),
            timeout_ms=self._settings.startup_timeout_ms,
        )
        diagnostics.append(_diagnostic("template-snapshot", snapshot))
        if snapshot.exit_code != 0:
            return self._unavailable(
                "VirtualBox template snapshot is unavailable", tuple(diagnostics)
            )
        snapshot_config = _snapshot_config_path(snapshot.text)
        if snapshot_config is None or not is_within_windows_boundary(
            snapshot_config, boundary=self._settings.state_root
        ):
            diagnostics.append(
                "snapshot configuration is missing or outside the KIS VirtualBox state root"
            )
            return self._unavailable(
                "VirtualBox template snapshot is not KIS-owned", tuple(diagnostics)
            )
        if _snapshot_has_external_host_path(
            snapshot.text, boundary=self._settings.state_root
        ):
            diagnostics.append(
                "snapshot references a host path outside the KIS VirtualBox state root"
            )
            return self._unavailable(
                "VirtualBox template snapshot storage is not KIS-owned", tuple(diagnostics)
            )
        if _SNAPSHOT_SHARED_FOLDER.search(snapshot.text) is not None:
            diagnostics.append("snapshot has configured shared folders")
            return self._unavailable(
                "VirtualBox template snapshot exposes host shared folders", tuple(diagnostics)
            )
        return ExecutionReadiness(
            backend_id=self.backend_id,
            status=ReadinessStatus.READY,
            reason="VirtualBox, KIS-owned template snapshot, and guest credential input are available",
            diagnostics=tuple(diagnostics),
        )

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if not self._profile_matches(request):
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
        lifecycle = [ExecutionLifecycleState.REQUESTED, ExecutionLifecycleState.READINESS]
        readiness = await self.readiness()
        diagnostics = list(readiness.diagnostics)
        if readiness.status is ReadinessStatus.UNAVAILABLE:
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
        credentials, credential_error = self._credentials()
        if credential_error is not None or credentials is None:
            lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
            return self._result(
                request,
                status="incomplete",
                failure="backend_unavailable",
                cleanup=CleanupDisposition.NOT_REQUIRED,
                duration_ms=_elapsed_ms(started),
                diagnostics=tuple((*diagnostics, credential_error or "credentials unavailable")),
                lifecycle=tuple(lifecycle),
            )
        state_root = Path(self._settings.state_root)
        evidence_root = state_root / "evidence"
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
        quarantine_name = f"kis-quarantine-{request_key}-{attempt_number:06d}"
        archive = request_root / "source.zip"
        vm_root = request_root / "vm"
        receipt_path = evidence_root / f"{request_key}-{attempt_number:06d}.json"
        guest_stdout = ""
        guest_stderr = ""
        guest_exit: int | None = None
        transferred_bytes: int | None = None
        status = "incomplete"
        failure = "lifecycle_failed"
        cleanup = CleanupDisposition.NOT_REQUIRED
        stdout_truncated = False
        stderr_truncated = False
        vm_may_exist = False
        vm_confirmed = False

        try:
            lifecycle.append(ExecutionLifecycleState.MATERIALIZING)
            materialize = await self._phase(
                self._materialize_script(request, archive), timeout_ms=request.timeout_ms
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
            vm_may_exist = True
            clone = await self._vbox(
                (
                    "clonevm",
                    self._settings.template_vm,
                    f"--snapshot={self._settings.snapshot_name}",
                    f"--name={vm_name}",
                    f"--basefolder={vm_root}",
                    "--register",
                ),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("clone-snapshot", clone))
            if clone.exit_code != 0:
                raise _LifecycleStop
            vm_confirmed = True
            harden = await self._vbox(
                ("modifyvm", vm_name, *_isolation_arguments()),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("isolate-guest", harden))
            if harden.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.STARTING)
            start = await self._vbox(
                ("startvm", vm_name, "--type=headless"),
                timeout_ms=min(request.timeout_ms, self._settings.startup_timeout_ms),
            )
            diagnostics.append(_diagnostic("start-guest", start))
            if start.exit_code != 0:
                raise _LifecycleStop
            wait = await self._vbox(
                (
                    "guestcontrol",
                    vm_name,
                    "waitrunlevel",
                    f"--timeout={min(request.timeout_ms, self._settings.startup_timeout_ms)}",
                    "userland",
                ),
                timeout_ms=min(request.timeout_ms, self._settings.startup_timeout_ms),
            )
            diagnostics.append(_diagnostic("guest-additions-ready", wait))
            if wait.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.TRANSFERRING)
            username, password_file = credentials
            mkdir = await self._vbox(
                (
                    "guestcontrol",
                    vm_name,
                    "mkdir",
                    f"--username={username}",
                    f"--passwordfile={password_file}",
                    "--parents",
                    self._settings.guest_workspace,
                ),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("prepare-guest-workspace", mkdir))
            if mkdir.exit_code != 0:
                raise _LifecycleStop
            copy = await self._vbox(
                (
                    "guestcontrol",
                    vm_name,
                    "copyto",
                    f"--username={username}",
                    f"--passwordfile={password_file}",
                    f"--target-directory={self._settings.guest_workspace}",
                    str(archive),
                ),
                timeout_ms=request.timeout_ms,
            )
            diagnostics.append(_diagnostic("inject-source", copy))
            if copy.exit_code != 0:
                raise _LifecycleStop

            lifecycle.append(ExecutionLifecycleState.EXECUTING)
            execute = await self._vbox(
                self._guest_run_arguments(vm_name, request, username, password_file),
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
        except _LifecycleStop:
            if not lifecycle or lifecycle[-1] is not ExecutionLifecycleState.CAPTURING:
                lifecycle.append(ExecutionLifecycleState.CAPTURING)
        except Exception as exc:
            status = "incomplete"
            failure = "lifecycle_failed"
            lifecycle.append(ExecutionLifecycleState.CAPTURING)
            diagnostics.append(f"lifecycle-exception: {type(exc).__name__}: {exc}")

        if vm_may_exist:
            lifecycle.append(ExecutionLifecycleState.CLEANING)
            poweroff = await self._safe_vbox(
                ("controlvm", vm_name, "poweroff"),
                timeout_ms=self._settings.cleanup_timeout_ms,
            )
            diagnostics.append(_diagnostic("poweroff", poweroff))
            retire = await self._safe_vbox(
                (
                    "modifyvm",
                    vm_name,
                    *_isolation_arguments(),
                    f"--name={quarantine_name}",
                ),
                timeout_ms=self._settings.cleanup_timeout_ms,
            )
            diagnostics.append(_diagnostic("quarantine", retire))
            if retire.exit_code == 0:
                cleanup = CleanupDisposition.QUARANTINED
                lifecycle.append(ExecutionLifecycleState.QUARANTINED)
                lifecycle.append(
                    ExecutionLifecycleState.INCOMPLETE
                    if status == "incomplete"
                    else ExecutionLifecycleState.COMPLETED
                )
            else:
                cleanup = CleanupDisposition.FAILED
                status = "incomplete"
                if vm_confirmed:
                    failure = "cleanup_failed"
                lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
        else:
            lifecycle.append(ExecutionLifecycleState.INCOMPLETE)

        truncated = stdout_truncated or stderr_truncated
        receipt_reference: str | None = str(receipt_path)
        try:
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
                cleanup=cleanup.value,
                failure=failure,
                lifecycle=tuple(lifecycle),
            )
        except Exception as exc:
            diagnostics.append(f"receipt-exception: {type(exc).__name__}: {exc}")
            status = "incomplete"
            if failure == "none":
                failure = "lifecycle_failed"
            if lifecycle and lifecycle[-1] is ExecutionLifecycleState.COMPLETED:
                lifecycle[-1] = ExecutionLifecycleState.INCOMPLETE
            elif not lifecycle or lifecycle[-1] is not ExecutionLifecycleState.INCOMPLETE:
                lifecycle.append(ExecutionLifecycleState.INCOMPLETE)
            receipt_reference = None
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
            receipt_path=receipt_reference,
            transferred_bytes=transferred_bytes,
            lifecycle=tuple(lifecycle),
        )

    def _profile_matches(self, request: ExecutionRequest) -> bool:
        return (
            request.profile.backend_id == self.backend_id
            and request.profile.profile_id == self._profile_id
            and request.profile.image_id == self._image_id
            and request.profile.toolchain_id == self._toolchain_id
        )

    def _credentials(self) -> tuple[tuple[str, str] | None, str | None]:
        username = os.environ.get(self._settings.guest_username_env, "").strip()
        password_file = os.environ.get(
            self._settings.guest_password_file_env, ""
        ).strip()
        if not username or not password_file:
            return None, "VirtualBox guest username/password-file environment is incomplete"
        password_path = PureWindowsPath(password_file)
        if not password_path.is_absolute() or not password_path.drive:
            return None, "VirtualBox guest password file must be an absolute Windows path"
        if not is_within_windows_boundary(
            password_file, boundary=self._settings.state_root
        ):
            return None, "VirtualBox guest password file must remain within the virtualbox state root"
        if not Path(password_file).is_file():
            return None, "VirtualBox guest password file does not exist"
        return (username, password_file), None

    def _unavailable(
        self, reason: str, diagnostics: tuple[str, ...]
    ) -> ExecutionReadiness:
        return ExecutionReadiness(
            backend_id=self.backend_id,
            status=ReadinessStatus.UNAVAILABLE,
            reason=reason,
            diagnostics=diagnostics,
        )

    async def _phase(self, body: str, *, timeout_ms: int) -> ProcessOutcome:
        return await run_nested_process(
            self._runner,
            command=_with_terminal_receipt(body),
            timeout_ms=timeout_ms,
        )

    async def _vbox(
        self, arguments: tuple[str, ...], *, timeout_ms: int
    ) -> ProcessOutcome:
        return await self._phase(
            self._vbox_script(arguments), timeout_ms=timeout_ms
        )

    async def _safe_vbox(
        self, arguments: tuple[str, ...], *, timeout_ms: int
    ) -> ProcessOutcome:
        try:
            return await self._vbox(arguments, timeout_ms=timeout_ms)
        except Exception as exc:
            return ProcessOutcome(
                text=f"virtualbox cleanup exception: {type(exc).__name__}: {exc}",
                exit_code=None,
                duration_ms=0,
            )

    def _vbox_script(self, arguments: tuple[str, ...]) -> str:
        rendered = " ".join(_ps_quote(item) for item in arguments)
        return (
            f"$env:VBOX_USER_HOME={_ps_quote(self._settings.vbox_user_home)}; "
            f"& {_ps_quote(self._settings.vboxmanage_path)} {rendered}; "
            "$vboxCode=$LASTEXITCODE; "
            "if($null -eq $vboxCode){$vboxCode=1}; "
            "if($vboxCode -ne 0){throw ('VBoxManage failed with exit code ' + $vboxCode)}"
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

    def _guest_run_arguments(
        self,
        vm_name: str,
        request: ExecutionRequest,
        username: str,
        password_file: str,
    ) -> tuple[str, ...]:
        workspace = self._settings.guest_workspace
        archive = str(PureWindowsPath(workspace) / "source.zip")
        argv_json = json.dumps(list(request.arguments), ensure_ascii=True, separators=(",", ":"))
        script = (
            "$ErrorActionPreference='Stop'; "
            f"$workspace={_ps_quote(workspace)}; "
            f"$archive={_ps_quote(archive)}; "
            f"$exe={_ps_quote(request.executable)}; "
            f"$argv=@(ConvertFrom-Json -InputObject {_ps_quote(argv_json)}); "
            "Expand-Archive -LiteralPath $archive -DestinationPath $workspace -Force; "
            "Set-Location -LiteralPath $workspace; "
            "$stdout=''; $stderr=''; $code=0; "
            "try {$stdout=(& $exe @argv 2>&1 | Out-String); "
            "$code=$LASTEXITCODE; if($null -eq $code){$code=0}} "
            "catch {$stderr=$_.Exception.Message; $code=127}; "
            "$payload=[pscustomobject]@{exit_code=$code;stdout=$stdout;stderr=$stderr} | ConvertTo-Json -Compress; "
            "Write-Output ('__KIS_GUEST_RESULT=' + $payload)"
        )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        powershell = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        return (
            "guestcontrol",
            vm_name,
            "run",
            f"--exe={powershell}",
            f"--username={username}",
            f"--passwordfile={password_file}",
            "--wait-stdout",
            "--wait-stderr",
            f"--timeout={request.timeout_ms}",
            "--",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
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
        cleanup: str,
        failure: str,
        lifecycle: tuple[ExecutionLifecycleState, ...],
    ) -> None:
        payload = {
            "schema_version": 1,
            "contract": "virtualbox-execution-receipt-v1",
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


def _isolation_arguments() -> tuple[str, ...]:
    network = tuple(f"--nic{index}=none" for index in range(1, 9))
    return (
        *network,
        "--clipboard-mode=disabled",
        "--clipboard-file-transfers=disabled",
        "--drag-and-drop=disabled",
        "--vrde=off",
        "--autostart-enabled=off",
        "--usb-ohci=off",
        "--usb-ehci=off",
        "--usb-xhci=off",
    )


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


def _machine_info_value(text: str, key: str) -> str | None:
    for match in _MACHINE_INFO.finditer(text):
        if match.group(1).strip().casefold() == key.casefold():
            return match.group(2).strip()
    return None


def _template_has_external_host_path(text: str, *, boundary: str) -> bool:
    for match in _MACHINE_INFO.finditer(text):
        value = match.group(2).strip()
        path = PureWindowsPath(value)
        if path.is_absolute() and not is_within_windows_boundary(value, boundary=boundary):
            return True
    return False


def _snapshot_config_path(text: str) -> str | None:
    match = _SNAPSHOT_CONFIG.search(text)
    if match is None:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def _snapshot_has_external_host_path(text: str, *, boundary: str) -> bool:
    for match in _SNAPSHOT_FIXED_PATH.finditer(text):
        value = match.group(1).strip().strip("'\"")
        if _snapshot_path_is_unsafe(value, boundary=boundary):
            return True
    for match in _SNAPSHOT_STORAGE.finditer(text):
        value = re.sub(r"\s+\(UUID:.*\)\s*$", "", match.group(1)).strip().strip("'\"")
        if value.casefold() in {"empty", "none", "not attached"}:
            continue
        if _snapshot_path_is_unsafe(value, boundary=boundary):
            return True
    return False


def _snapshot_path_is_unsafe(value: str, *, boundary: str) -> bool:
    if not value:
        return True
    path = PureWindowsPath(value)
    if not path.is_absolute():
        return True
    return not is_within_windows_boundary(value, boundary=boundary)


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


__all__ = ["VirtualBoxDisposableExecutionProvider"]
