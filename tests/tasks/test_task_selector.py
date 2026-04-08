"""Tests for task selector callbacks (check button)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from ductor_bot.tasks.hub import TaskHub
from ductor_bot.tasks.models import TaskSubmit
from ductor_bot.tasks.registry import TaskRegistry


@pytest.fixture
def registry(tmp_path: Path) -> TaskRegistry:
    return TaskRegistry(
        registry_path=tmp_path / "tasks.json",
        tasks_dir=tmp_path / "tasks",
    )


def _make_config(**overrides: object) -> MagicMock:
    config = MagicMock()
    config.enabled = True
    config.max_parallel = 5
    config.timeout_seconds = 60.0
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


def _make_hub(registry: TaskRegistry, tmp_path: Path) -> TaskHub:
    cli = MagicMock()
    cli.resolve_provider = MagicMock(return_value=("gemini", "flash"))
    return TaskHub(
        registry,
        MagicMock(workspace=tmp_path),
        cli_service=cli,
        config=_make_config(),
    )


class TestCheckCallback:
    async def test_check_running_task(self, registry: TaskRegistry, tmp_path: Path) -> None:
        from ductor_bot.orchestrator.selectors.task_selector import handle_task_callback

        hub = _make_hub(registry, tmp_path)
        entry = registry.create(
            TaskSubmit(
                chat_id=42,
                prompt="test",
                message_id=1,
                thread_id=None,
                parent_agent="main",
                name="TestCheck",
            ),
            "gemini",
            "flash",
        )
        # Set PID to current process so health check sees it alive
        registry.update_status(entry.task_id, "running", pid=os.getpid())

        resp = await handle_task_callback(hub, 42, f"tsc:check:{entry.task_id}")

        assert "TestCheck" in resp.text
        assert "alive" in resp.text.lower()
        assert resp.buttons is not None

    async def test_check_nonexistent_task(self, registry: TaskRegistry, tmp_path: Path) -> None:
        from ductor_bot.orchestrator.selectors.task_selector import handle_task_callback

        hub = _make_hub(registry, tmp_path)
        resp = await handle_task_callback(hub, 42, "tsc:check:nonexistent")
        assert "not found" in resp.text.lower() or "не найдена" in resp.text.lower()

    async def test_check_dead_process(self, registry: TaskRegistry, tmp_path: Path) -> None:
        from ductor_bot.orchestrator.selectors.task_selector import handle_task_callback

        hub = _make_hub(registry, tmp_path)
        entry = registry.create(
            TaskSubmit(
                chat_id=42,
                prompt="test",
                message_id=1,
                thread_id=None,
                parent_agent="main",
                name="DeadTask",
            ),
            "gemini",
            "flash",
        )
        registry.update_status(entry.task_id, "running", pid=999999999)

        resp = await handle_task_callback(hub, 42, f"tsc:check:{entry.task_id}")

        assert "dead" in resp.text.lower()

    async def test_check_no_pid(self, registry: TaskRegistry, tmp_path: Path) -> None:
        from ductor_bot.orchestrator.selectors.task_selector import handle_task_callback

        hub = _make_hub(registry, tmp_path)
        entry = registry.create(
            TaskSubmit(
                chat_id=42,
                prompt="test",
                message_id=1,
                thread_id=None,
                parent_agent="main",
                name="NoPidTask",
            ),
            "gemini",
            "flash",
        )

        resp = await handle_task_callback(hub, 42, f"tsc:check:{entry.task_id}")

        assert "no_pid" in resp.text.lower() or "pid not" in resp.text.lower()
