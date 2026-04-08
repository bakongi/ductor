"""Process health diagnostics for running background tasks."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from ductor_bot.tasks.models import TaskEntry

_IO_SAMPLE_INTERVAL = 2.0  # seconds between I/O samples


async def check_process_health(entry: TaskEntry) -> dict[str, Any]:
    """Return diagnostic info about a task's CLI subprocess.

    Reads /proc/{pid}/ to determine process state, memory, I/O activity,
    and network connections.  Two I/O snapshots are taken to detect activity.
    """
    info: dict[str, Any] = {
        "task_id": entry.task_id,
        "name": entry.name,
        "status": entry.status,
        "pid": entry.pid,
        "provider": entry.provider,
        "model": entry.model,
    }

    # Elapsed time
    if entry.status == "running" and entry.created_at:
        info["running_seconds"] = round(time.time() - entry.created_at)

    if not entry.pid:
        info["process"] = "no_pid"
        info["detail"] = "PID not recorded (task may predate this feature)"
        return info

    proc = Path(f"/proc/{entry.pid}")
    if not await asyncio.to_thread(proc.is_dir):
        info["process"] = "dead"
        info["detail"] = f"Process {entry.pid} no longer exists"
        return info

    info["process"] = "alive"

    # Process state
    status_data = await _read_proc_file(proc / "status")
    if status_data:
        for line in status_data.splitlines():
            if line.startswith("State:"):
                info["state"] = line.split("\t", 1)[-1].strip()
            elif line.startswith("VmRSS:"):
                info["memory_kb"] = _parse_kb(line)
            elif line.startswith("Threads:"):
                info["threads"] = int(line.split()[-1])

    # I/O activity: take two snapshots
    io1 = await _read_io(proc)
    if io1:
        await asyncio.sleep(_IO_SAMPLE_INTERVAL)

        # Re-check process is still alive
        if not await asyncio.to_thread(proc.is_dir):
            info["process"] = "dead"
            info["detail"] = "Process exited during health check"
            return info

        io2 = await _read_io(proc)
        if io2:
            read_delta = io2["rchar"] - io1["rchar"]
            write_delta = io2["wchar"] - io1["wchar"]
            info["io_activity"] = {
                "read_bytes_per_sec": round(read_delta / _IO_SAMPLE_INTERVAL),
                "write_bytes_per_sec": round(write_delta / _IO_SAMPLE_INTERVAL),
                "active": read_delta > 0 or write_delta > 0,
            }

    # Network connections (active sockets)
    net_info = await _check_network(proc)
    if net_info:
        info["network"] = net_info

    # TASKMEMORY.md last modified
    if entry.tasks_dir:
        tm_path = Path(entry.tasks_dir) / entry.task_id / "TASKMEMORY.md"
        mtime = await _file_mtime(tm_path)
        if mtime:
            info["taskmemory_updated_ago_seconds"] = round(time.time() - mtime)

    return info


async def _read_proc_file(path: Path) -> str:
    """Read a /proc file, returning empty string on failure."""
    try:
        return await asyncio.to_thread(path.read_text, "utf-8")
    except OSError:
        return ""


async def _read_io(proc: Path) -> dict[str, int] | None:
    """Parse /proc/{pid}/io into a dict."""
    text = await _read_proc_file(proc / "io")
    if not text:
        return None
    result: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split(":", 1)
        if len(parts) == 2:
            try:
                result[parts[0].strip()] = int(parts[1].strip())
            except ValueError:
                pass
    return result if "rchar" in result else None


async def _check_network(proc: Path) -> dict[str, Any] | None:
    """Check for active TCP connections."""
    tcp_data = await _read_proc_file(proc / "net/tcp")
    if not tcp_data:
        return None

    lines = tcp_data.strip().splitlines()[1:]  # skip header
    established = sum(1 for line in lines if _tcp_state(line) == "01")  # ESTABLISHED
    if not established:
        return None
    return {"established_connections": established}


def _tcp_state(line: str) -> str:
    """Extract TCP state hex code from /proc/net/tcp line."""
    parts = line.split()
    return parts[3] if len(parts) > 3 else ""


def _parse_kb(line: str) -> int:
    """Parse 'VmRSS:   12345 kB' into integer KB."""
    parts = line.split()
    for p in parts:
        if p.isdigit():
            return int(p)
    return 0


async def _file_mtime(path: Path) -> float | None:
    """Return mtime of a file, or None if missing."""
    try:
        stat = await asyncio.to_thread(path.stat)
        return stat.st_mtime
    except OSError:
        return None
