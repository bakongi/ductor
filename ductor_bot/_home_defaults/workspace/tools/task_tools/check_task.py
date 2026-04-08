#!/usr/bin/env python3
"""Check health of a running background task.

Usage:
    python3 check_task.py TASK_ID
"""

from __future__ import annotations

import os
import sys


def _load_shared() -> tuple[object, object]:
    tools_dir = os.path.dirname(__file__)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from _shared import get_api_url, get_json

    return get_api_url, get_json


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 check_task.py TASK_ID", file=sys.stderr)
        sys.exit(1)

    task_id = sys.argv[1]
    get_api_url, get_json = _load_shared()
    url = get_api_url(f"/tasks/check?task_id={task_id}")
    result = get_json(url)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    name = result.get("name", "?")
    status = result.get("status", "?")
    pid = result.get("pid", 0)
    process = result.get("process", "unknown")
    provider = result.get("provider", "?")
    model = result.get("model", "?")

    print(f"Task: {name} [{task_id}]")
    print(f"Status: {status} | Provider: {provider}/{model}")
    print(f"PID: {pid} | Process: {process}")

    if "running_seconds" in result:
        secs = result["running_seconds"]
        mins = secs // 60
        print(f"Running: {mins}m {secs % 60}s")

    if "detail" in result:
        print(f"Detail: {result['detail']}")
        return

    if "state" in result:
        mem_mb = result.get("memory_kb", 0) / 1024
        threads = result.get("threads", "?")
        print(f"State: {result['state']} | Memory: {mem_mb:.0f} MB | Threads: {threads}")

    io_info = result.get("io_activity")
    if io_info:
        read_rate = io_info["read_bytes_per_sec"]
        write_rate = io_info["write_bytes_per_sec"]
        active = io_info["active"]
        status_str = "ACTIVE" if active else "IDLE"
        print(f"I/O: {status_str} (read: {_human_rate(read_rate)}, write: {_human_rate(write_rate)})")

    net_info = result.get("network")
    if net_info:
        conns = net_info.get("established_connections", 0)
        print(f"Network: {conns} active connection(s)")

    if "taskmemory_updated_ago_seconds" in result:
        ago = result["taskmemory_updated_ago_seconds"]
        print(f"TASKMEMORY.md: updated {ago}s ago")


def _human_rate(bps: int) -> str:
    if bps >= 1024 * 1024:
        return f"{bps / 1024 / 1024:.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps} B/s"


if __name__ == "__main__":
    main()
