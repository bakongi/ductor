"""Tests for CommandRegistry and OrchestratorResult."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from ductor_bot.auth.audit import AuditLog
from ductor_bot.auth.principal import Principal
from ductor_bot.auth.roles import Cap
from ductor_bot.auth.service import AuthorizationService
from ductor_bot.config import AgentConfig
from ductor_bot.orchestrator.registry import CommandRegistry, OrchestratorResult


@pytest.fixture
def registry() -> CommandRegistry:
    return CommandRegistry()


def test_orchestrator_result_defaults() -> None:
    r = OrchestratorResult(text="hello")
    assert r.text == "hello"
    assert r.stream_fallback is False


async def test_dispatch_async_handler(registry: CommandRegistry) -> None:
    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    registry.register_async("/test", handler)

    result = await registry.dispatch("/test", AsyncMock(), 1, "/test")
    assert result is not None
    assert result.text == "ok"
    handler.assert_called_once()


async def test_dispatch_unknown_returns_none(registry: CommandRegistry) -> None:
    result = await registry.dispatch("/unknown", AsyncMock(), 1, "/unknown")
    assert result is None


async def test_prefix_match(registry: CommandRegistry) -> None:
    handler = AsyncMock(return_value=OrchestratorResult(text="matched"))
    registry.register_async("/model ", handler)

    result = await registry.dispatch("/model opus", AsyncMock(), 1, "/model opus")
    assert result is not None
    assert result.text == "matched"


async def test_exact_match_no_extra(registry: CommandRegistry) -> None:
    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    registry.register_async("/status", handler)

    result = await registry.dispatch("/status extra", AsyncMock(), 1, "/status extra")
    assert result is None


async def test_dispatch_strips_bot_mention(registry: CommandRegistry) -> None:
    """Commands like /status@mybot in group chats must match /status."""
    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    registry.register_async("/status", handler)

    result = await registry.dispatch("/status@mybot", AsyncMock(), 1, "/status@mybot")
    assert result is not None
    assert result.text == "ok"


async def test_prefix_match_strips_bot_mention(registry: CommandRegistry) -> None:
    """/model@mybot sonnet must match the prefix entry /model ."""
    handler = AsyncMock(return_value=OrchestratorResult(text="matched"))
    registry.register_async("/model ", handler)

    result = await registry.dispatch("/model@mybot sonnet", AsyncMock(), 1, "/model@mybot sonnet")
    assert result is not None
    assert result.text == "matched"


# -- Capability enforcement tests --


async def test_capability_enforced_admin_allowed() -> None:
    """Admin principal can execute capability-gated commands."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    reg = CommandRegistry(authz=authz)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    admin = Principal.telegram(100)
    result = await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=admin)
    assert result is not None
    assert result.text == "ok"
    handler.assert_called_once()


async def test_capability_enforced_user_denied() -> None:
    """Non-admin principal is denied capability-gated commands."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    reg = CommandRegistry(authz=authz)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    user = Principal.telegram(999)
    result = await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=user)
    assert result is not None
    assert "admin" in result.text.lower()
    handler.assert_not_called()


async def test_no_capability_allows_all() -> None:
    """Commands without capability restriction allow any principal."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    reg = CommandRegistry(authz=authz)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/status", handler)

    user = Principal.telegram(999)
    result = await reg.dispatch("/status", AsyncMock(), 1, "/status", principal=user)
    assert result is not None
    assert result.text == "ok"


async def test_legacy_mode_allows_all() -> None:
    """When no admin_ids configured, all principals bypass capability checks."""
    config = AgentConfig()  # no admin_ids
    authz = AuthorizationService(config)
    reg = CommandRegistry(authz=authz)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    user = Principal.telegram(999)
    result = await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=user)
    assert result is not None
    assert result.text == "ok"


async def test_no_principal_bypasses_check() -> None:
    """When principal is None (system/internal), capability check is skipped."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    reg = CommandRegistry(authz=authz)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    result = await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=None)
    assert result is not None
    assert result.text == "ok"


async def test_audit_log_on_deny(tmp_path: Path) -> None:
    """Denied commands are logged to the audit log."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    audit = AuditLog(tmp_path / "audit.jsonl")
    reg = CommandRegistry(authz=authz, audit_log=audit)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    user = Principal.telegram(999)
    await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=user)

    entries = audit.read_all()
    assert len(entries) == 1
    assert entries[0]["action"] == "access_denied"
    assert entries[0]["result"] == "denied"


async def test_audit_log_on_success(tmp_path: Path) -> None:
    """Successful commands are logged to the audit log."""
    config = AgentConfig(admin_ids=[100])
    authz = AuthorizationService(config)
    audit = AuditLog(tmp_path / "audit.jsonl")
    reg = CommandRegistry(authz=authz, audit_log=audit)

    handler = AsyncMock(return_value=OrchestratorResult(text="ok"))
    reg.register_async("/model", handler, capability=Cap.MODEL_SELECT)

    admin = Principal.telegram(100)
    await reg.dispatch("/model", AsyncMock(), 1, "/model", principal=admin)

    entries = audit.read_all()
    assert len(entries) == 1
    assert entries[0]["action"] == "command_executed"
