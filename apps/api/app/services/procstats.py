"""
CPU and memory, per machine and per process, from Windows itself (analysis monitor).

No package needed, so a Sarce Node without internet keeps updating itself (ADR 0010). Everything returns None off
Windows or when a process has gone. CPU needs two samples, so `Sampler` keeps the previous one per process.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes

WINDOWS = sys.platform == "win32"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
CPUS = os.cpu_count() or 1


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD), ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64), ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64), ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class _Counters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _ticks(ft: wintypes.FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # 100-ns units


def memory() -> tuple[float, float] | None:
    """(share of RAM in use, total GB)."""
    if not WINDOWS:
        return None
    status = _MemoryStatus()
    status.dwLength = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.dwMemoryLoad / 100, status.ullTotalPhys / 1024**3


def uptime_s() -> int | None:
    return int(ctypes.windll.kernel32.GetTickCount64() // 1000) if WINDOWS else None


def _process_times(pid: int) -> tuple[int, float | None] | None:
    """(kernel + user CPU time in 100-ns ticks, working set in MB) for a process."""
    if not WINDOWS or not pid:
        return None
    kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        counters = _Counters()
        counters.cb = ctypes.sizeof(_Counters)
        rss = counters.WorkingSetSize / 1024**2 if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb) else None
        return _ticks(kernel) + _ticks(user), rss
    finally:
        kernel32.CloseHandle(handle)


class Sampler:
    """CPU % (of the whole machine) and memory per process, and for the machine, from successive samples."""

    def __init__(self) -> None:
        self._last: dict[int, tuple[float, int]] = {}
        self._system: tuple[int, int] | None = None

    def process(self, *pids: int | None) -> tuple[float | None, float | None]:
        """CPU % and MB for these processes together (a worker and its Stockfish)."""
        cpu, rss, any_seen = 0.0, 0.0, False
        now = time.monotonic()
        for pid in pids:
            if not pid:
                continue
            sample = _process_times(pid)
            if sample is None:
                self._last.pop(pid, None)
                continue
            ticks, mb = sample
            any_seen = True
            rss += mb or 0.0
            previous = self._last.get(pid)
            self._last[pid] = (now, ticks)
            if previous:
                wall = now - previous[0]
                if wall > 0:
                    cpu += (ticks - previous[1]) / 1e7 / wall / CPUS * 100
        return (round(cpu, 1), round(rss, 1)) if any_seen else (None, None)

    def system_cpu(self) -> float | None:
        """Whole-machine CPU % since the previous call."""
        if not WINDOWS:
            return None
        idle, kernel, user = (wintypes.FILETIME() for _ in range(3))
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        busy_total = (_ticks(kernel) + _ticks(user), _ticks(idle))
        previous, self._system = self._system, busy_total
        if not previous:
            return None
        total = busy_total[0] - previous[0]  # kernel time includes idle time
        idle_delta = busy_total[1] - previous[1]
        return round(max(0.0, min(100.0, (total - idle_delta) / total * 100)), 1) if total > 0 else None

    def machine(self) -> dict:
        mem = memory()
        return {
            "cpu": self.system_cpu(),
            "memUsed": None if mem is None else round(mem[0], 3),
            "memTotalGb": None if mem is None else round(mem[1], 1),
            "uptimeS": uptime_s(),
        }
