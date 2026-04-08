"""Tests for task process health diagnostics."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ductor_bot.tasks.models import TaskEntry
from ductor_bot.tasks.process_health import check_process_health


def _make_entry(
    pid: int = 0,
    status: str = "running",
    tasks_dir: str = "",
    **kwargs: object,
) -> TaskEntry:
    defaults = dict(
        task_id="abc123",
        chat_id=42,
        parent_agent="main",
        name="Test Task",
        prompt_preview="do something",
        provider="gemini",
        model="flash",
        status=status,
        created_at=time.time() - 60,
        pid=pid,
    )
    defaults.update(kwargs)
    if tasks_dir:
        defaults["tasks_dir"] = tasks_dir
    return TaskEntry(**defaults)  # type: ignore[arg-type]


class TestNoProcess:
    async def test_no_pid(self) -> None:
        entry = _make_entry(pid=0)
        health = await check_process_health(entry)
        assert health["process"] == "no_pid"
        assert health["task_id"] == "abc123"

    async def test_dead_process(self) -> None:
        # Use a PID that certainly doesn't exist
        entry = _make_entry(pid=999999999)
        health = await check_process_health(entry)
        assert health["process"] == "dead"
        assert "999999999" in health.get("detail", "")


class TestAliveProcess:
    async def test_own_process(self) -> None:
        """Use the current process PID — guaranteed to be alive."""
        pid = os.getpid()
        entry = _make_entry(pid=pid)
        health = await check_process_health(entry)

        assert health["process"] == "alive"
        assert health["pid"] == pid
        assert "state" in health
        assert "memory_kb" in health
        assert health["memory_kb"] > 0
        assert "threads" in health
        assert "running_seconds" in health

    async def test_io_activity_present(self) -> None:
        """I/O activity section should be present for a live process."""
        pid = os.getpid()
        entry = _make_entry(pid=pid)
        health = await check_process_health(entry)

        assert "io_activity" in health
        io = health["io_activity"]
        assert "read_bytes_per_sec" in io
        assert "write_bytes_per_sec" in io
        assert "active" in io

    async def test_taskmemory_freshness(self, tmp_path: Path) -> None:
        """TASKMEMORY.md mtime should be reported when present."""
        task_dir = tmp_path / "abc123"
        task_dir.mkdir()
        tm = task_dir / "TASKMEMORY.md"
        tm.write_text("# progress")

        entry = _make_entry(pid=os.getpid(), tasks_dir=str(tmp_path))
        health = await check_process_health(entry)

        assert "taskmemory_updated_ago_seconds" in health
        assert health["taskmemory_updated_ago_seconds"] >= 0

    async def test_no_taskmemory(self, tmp_path: Path) -> None:
        """Missing TASKMEMORY.md should not cause errors."""
        entry = _make_entry(pid=os.getpid(), tasks_dir=str(tmp_path))
        health = await check_process_health(entry)
        assert "taskmemory_updated_ago_seconds" not in health


class TestFinishedTask:
    async def test_finished_task_no_running_seconds(self) -> None:
        entry = _make_entry(pid=0, status="done")
        health = await check_process_health(entry)
        assert "running_seconds" not in health
