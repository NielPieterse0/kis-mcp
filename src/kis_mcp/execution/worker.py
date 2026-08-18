from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKER_RESULT_NAME = "worker-result.json"
_CANCEL_NAME = "cancel.requested"
_STDOUT_NAME = "stdout.log"
_STDERR_NAME = "stderr.log"
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_CREATE_SUSPENDED = 0x00000004
_CREATE_NO_WINDOW = 0x08000000
_STARTF_USESTDHANDLES = 0x00000100
_WAIT_OBJECT_0 = 0x00000000
_WAIT_TIMEOUT = 0x00000102
_PROCESS_SYNCHRONIZE = 0x00100000
_STILL_ACTIVE = 259


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _kernel32() -> Any:
    if sys.platform != "win32":
        raise OSError("local containment worker requires Windows")
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _configure_kernel32(kernel32: Any) -> None:
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(_StartupInfo),
        ctypes.POINTER(_ProcessInformation),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL


def _create_job(kernel32: Any) -> wintypes.HANDLE:
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = _ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel32.CloseHandle(job)
        raise error
    return job


def _parent_alive(kernel32: Any, pid: int) -> bool:
    handle = kernel32.OpenProcess(_PROCESS_SYNCHRONIZE, False, pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def _create_suspended_process(
    kernel32: Any,
    command: list[str],
    *,
    cwd: Path,
    stdout_file: Any,
    stderr_file: Any,
) -> _ProcessInformation:
    import msvcrt

    with open(os.devnull, "rb") as stdin_file:
        handles = [
            msvcrt.get_osfhandle(stdin_file.fileno()),
            msvcrt.get_osfhandle(stdout_file.fileno()),
            msvcrt.get_osfhandle(stderr_file.fileno()),
        ]
        previous = [os.get_handle_inheritable(handle) for handle in handles]
        for handle in handles:
            os.set_handle_inheritable(handle, True)
        try:
            startup = _StartupInfo()
            startup.cb = ctypes.sizeof(_StartupInfo)
            startup.dwFlags = _STARTF_USESTDHANDLES
            startup.hStdInput, startup.hStdOutput, startup.hStdError = handles
            info = _ProcessInformation()
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
            created = kernel32.CreateProcessW(
                None,
                command_line,
                None,
                None,
                True,
                _CREATE_SUSPENDED | _CREATE_NO_WINDOW,
                None,
                str(cwd),
                ctypes.byref(startup),
                ctypes.byref(info),
            )
            if not created:
                raise ctypes.WinError(ctypes.get_last_error())
            return info
        finally:
            for handle, inheritable in zip(handles, previous, strict=True):
                os.set_handle_inheritable(handle, inheritable)


def _terminate_job(kernel32: Any, job: wintypes.HANDLE) -> None:
    kernel32.TerminateJobObject(job, 125)


def _exit_code(kernel32: Any, process: wintypes.HANDLE) -> int | None:
    value = wintypes.DWORD()
    if not kernel32.GetExitCodeProcess(process, ctypes.byref(value)):
        return None
    return None if value.value == _STILL_ACTIVE else int(value.value)


def _run(command: list[str], state_dir: Path, cwd: Path, timeout_ms: int, parent_pid: int) -> dict[str, Any]:
    started_at = _utc_now()
    started = time.monotonic()
    kernel32 = _kernel32()
    _configure_kernel32(kernel32)
    state_dir.mkdir(parents=True, exist_ok=True)
    job = _create_job(kernel32)
    process = _ProcessInformation()
    assigned = False
    status = "containment_failed"
    exit_code: int | None = None
    reason = "local containment did not start"
    try:
        with (state_dir / _STDOUT_NAME).open("wb") as stdout_file, (
            state_dir / _STDERR_NAME
        ).open("wb") as stderr_file:
            process = _create_suspended_process(
                kernel32, command, cwd=cwd, stdout_file=stdout_file, stderr_file=stderr_file
            )
            if not kernel32.AssignProcessToJobObject(job, process.hProcess):
                kernel32.TerminateProcess(process.hProcess, 125)
                raise ctypes.WinError(ctypes.get_last_error())
            assigned = True
            if kernel32.ResumeThread(process.hThread) == 0xFFFFFFFF:
                _terminate_job(kernel32, job)
                raise ctypes.WinError(ctypes.get_last_error())
            kernel32.CloseHandle(process.hThread)
            process.hThread = None
            deadline = started + (timeout_ms / 1000)
            while True:
                wait = kernel32.WaitForSingleObject(process.hProcess, 50)
                if wait == _WAIT_OBJECT_0:
                    exit_code = _exit_code(kernel32, process.hProcess)
                    status = "completed"
                    reason = "verification process exited"
                    break
                if (state_dir / _CANCEL_NAME).is_file():
                    status = "cancelled"
                    reason = "cancellation requested"
                    _terminate_job(kernel32, job)
                    kernel32.WaitForSingleObject(process.hProcess, 5000)
                    exit_code = _exit_code(kernel32, process.hProcess)
                    break
                if not _parent_alive(kernel32, parent_pid):
                    status = "parent_lost"
                    reason = "owning KIS process is no longer running"
                    _terminate_job(kernel32, job)
                    kernel32.WaitForSingleObject(process.hProcess, 5000)
                    exit_code = _exit_code(kernel32, process.hProcess)
                    break
                if time.monotonic() >= deadline:
                    status = "timeout"
                    reason = "verification timeout exceeded"
                    _terminate_job(kernel32, job)
                    kernel32.WaitForSingleObject(process.hProcess, 5000)
                    exit_code = _exit_code(kernel32, process.hProcess)
                    break
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        if assigned:
            _terminate_job(kernel32, job)
    finally:
        if process.hThread:
            kernel32.CloseHandle(process.hThread)
        if process.hProcess:
            kernel32.CloseHandle(process.hProcess)
        kernel32.CloseHandle(job)
    return {
        "schema_version": 1,
        "status": status,
        "reason": reason,
        "exit_code": exit_code,
        "child_pid": int(process.dwProcessId) if process.dwProcessId else None,
        "job_assigned": assigned,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "duration_ms": max(0, int(round((time.monotonic() - started) * 1000))),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--timeout-ms", required=True, type=int)
    parser.add_argument("--parent-pid", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    if not command:
        result = {
            "schema_version": 1,
            "status": "failed_to_start",
            "reason": "verification command is empty",
            "exit_code": None,
            "child_pid": None,
            "job_assigned": False,
            "started_at": _utc_now(),
            "finished_at": _utc_now(),
            "duration_ms": 0,
        }
    else:
        try:
            result = _run(
                command,
                state_dir,
                Path(args.cwd),
                args.timeout_ms,
                args.parent_pid,
            )
        except Exception as exc:
            result = {
                "schema_version": 1,
                "status": "containment_failed",
                "reason": f"{type(exc).__name__}: {exc}",
                "exit_code": None,
                "child_pid": None,
                "job_assigned": False,
                "started_at": _utc_now(),
                "finished_at": _utc_now(),
                "duration_ms": 0,
            }
    _write_json(state_dir / WORKER_RESULT_NAME, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
