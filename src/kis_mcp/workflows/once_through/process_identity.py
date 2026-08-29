from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

from .state import OnceThroughStateError

_PROCESS_TERMINATE = 0x0001
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259


class _FileTime(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


@dataclass(frozen=True, slots=True)
class WindowsProcessIdentity:
    pid: int
    creation_time_100ns: int
    image_path: str

    def to_json_dict(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "creation_time_100ns": self.creation_time_100ns,
            "image_path": self.image_path,
        }


def _kernel32():
    if not hasattr(ctypes, "WinDLL"):
        raise OnceThroughStateError(
            "PROCESS_IDENTITY_UNSUPPORTED",
            "exact process-handle identity requires Windows",
        )
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _open_process(pid: int, access: int):
    kernel32 = _kernel32()
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return kernel32, None
        raise OnceThroughStateError(
            "PROCESS_IDENTITY_OPEN_FAILED",
            f"OpenProcess failed for PID {pid} with Windows error {error}",
        )
    return kernel32, handle


def _close_handle(kernel32, handle) -> None:
    if handle:
        kernel32.CloseHandle(handle)


def _identity_from_handle(kernel32, handle, pid: int) -> WindowsProcessIdentity:
    creation = _FileTime()
    exit_time = _FileTime()
    kernel_time = _FileTime()
    user_time = _FileTime()
    if not kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel_time),
        ctypes.byref(user_time),
    ):
        raise OnceThroughStateError(
            "PROCESS_IDENTITY_QUERY_FAILED",
            f"GetProcessTimes failed for PID {pid}",
        )
    buffer = ctypes.create_unicode_buffer(32768)
    size = wintypes.DWORD(len(buffer))
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
        raise OnceThroughStateError(
            "PROCESS_IDENTITY_QUERY_FAILED",
            f"QueryFullProcessImageNameW failed for PID {pid}",
        )
    created = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    return WindowsProcessIdentity(
        pid=pid,
        creation_time_100ns=created,
        image_path=buffer.value.casefold(),
    )


def read_process_identity(pid: int) -> WindowsProcessIdentity | None:
    kernel32, handle = _open_process(pid, _PROCESS_QUERY_LIMITED_INFORMATION)
    if handle is None:
        return None
    try:
        return _identity_from_handle(kernel32, handle, pid)
    finally:
        _close_handle(kernel32, handle)


def terminate_exact_process(expected: WindowsProcessIdentity) -> bool:
    kernel32, handle = _open_process(
        expected.pid,
        _PROCESS_QUERY_LIMITED_INFORMATION | _PROCESS_TERMINATE,
    )
    if handle is None:
        return False
    try:
        observed = _identity_from_handle(kernel32, handle, expected.pid)
        if observed != expected:
            raise OnceThroughStateError(
                "CANDIDATE_PROCESS_IDENTITY_MISMATCH",
                "recorded PID now refers to a different OS process identity",
            )
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise OnceThroughStateError(
                "PROCESS_IDENTITY_QUERY_FAILED",
                f"GetExitCodeProcess failed for PID {expected.pid}",
            )
        if exit_code.value != _STILL_ACTIVE:
            return False
        if not kernel32.TerminateProcess(handle, 1):
            raise OnceThroughStateError(
                "CANDIDATE_PROCESS_TERMINATE_FAILED",
                f"TerminateProcess failed for PID {expected.pid}",
            )
        return True
    finally:
        _close_handle(kernel32, handle)


__all__ = [
    "WindowsProcessIdentity",
    "read_process_identity",
    "terminate_exact_process",
]
